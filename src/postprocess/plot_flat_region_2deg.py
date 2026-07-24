#!/usr/bin/env python3
"""Render diagnostic binary angle-threshold maps for a thickness run."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (
    PROBE_AREA_M2,
    PROBE_RADIUS_M,
    Face,
    FlatAreaResult,
    read_faces,
    select_flat_surface,
)

RED = (211, 55, 48)
BLUE = (42, 91, 176)
EDGE = (235, 238, 242)
INK = (28, 31, 35)
PROBE = (78, 82, 88)
SERIES_COLORS = (
    (35, 87, 137),
    (211, 84, 0),
    (0, 132, 115),
    (167, 66, 125),
    (230, 159, 0),
    (86, 180, 233),
    (213, 94, 0),
)


def angle_text(angle_deg: float) -> str:
    return f"{angle_deg:g}"


def angle_slug(angle_deg: float) -> str:
    return angle_text(angle_deg).replace(".", "p")


def font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def panel(
    title: str,
    faces: dict[int, Face],
    selected: set[int],
    result: FlatAreaResult,
    angle_deg: float,
) -> Image.Image:
    width, height = 650, 650
    margin, plot_size = 44, 550
    extent = 1.12 * PROBE_RADIUS_M
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), title, fill=INK, font=font(22))

    def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
        return (
            round(margin + plot_size / 2 + point[0] / extent * plot_size / 2),
            round(48 + plot_size / 2 - point[2] / extent * plot_size / 2),
        )

    for element, face in sorted(faces.items()):
        center_x = sum(point[0] for point in face.points) / 3.0
        center_z = sum(point[2] for point in face.points) / 3.0
        if math.hypot(center_x, center_z) > 1.18 * PROBE_RADIUS_M:
            continue
        draw.polygon(
            [pixel(point) for point in face.points],
            fill=RED if element in selected else BLUE,
            outline=EDGE,
            width=1,
        )

    center_x = margin + plot_size / 2
    center_y = 48 + plot_size / 2
    radius_px = PROBE_RADIUS_M / extent * plot_size / 2
    draw.ellipse(
        (center_x - radius_px, center_y - radius_px,
         center_x + radius_px, center_y + radius_px),
        outline=INK,
        width=3,
    )
    area_mm2 = result.projected_area * 1e6
    draw.text(
        (margin, 610),
        f"{angle_text(angle_deg)} deg area={area_mm2:.3f} mm2   faces={result.face_count}",
        fill=INK,
        font=font(16),
    )
    return image


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(first * second for first, second in zip(a, b))


def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    magnitude = math.sqrt(_dot(vector, vector))
    return tuple(component / magnitude for component in vector)


def _camera_basis(
    direction: tuple[float, float, float],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    forward = _unit(direction)
    right = _unit(_cross((0.0, 1.0, 0.0), forward))
    vertical = _unit(_cross(forward, right))
    return right, vertical, forward


def _probe_lines(bottom_y_mm: float, height_mm: float = 2.6) -> list[list[tuple[float, float, float]]]:
    radius_mm = PROBE_RADIUS_M * 1e3
    segments = 36
    bottom = [
        (radius_mm * math.cos(2 * math.pi * index / segments), bottom_y_mm,
         radius_mm * math.sin(2 * math.pi * index / segments))
        for index in range(segments + 1)
    ]
    top = [(x, y + height_mm, z) for x, y, z in bottom]
    sides = [[bottom[index], top[index]] for index in range(0, segments, 6)]
    return [bottom, top, *sides]


def _render_3d_panel(
    title: str,
    layers: list[tuple[dict[int, Face], set[int], str]],
    direction: tuple[float, float, float],
    probe_bottom_y_mm: float,
    *,
    section_band_mm: float | None = None,
) -> Image.Image:
    width, height = 680, 520
    margin = 28
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), title, fill=INK, font=font(20))
    right, vertical, forward = _camera_basis(direction)

    triangles: list[tuple[float, list[tuple[float, float]], tuple[int, int, int]]] = []
    all_projected: list[tuple[float, float]] = []
    for faces, selected, clip in layers:
        for element, face in faces.items():
            center = tuple(sum(point[index] for point in face.points) / 3.0 for index in range(3))
            center_mm = tuple(value * 1e3 for value in center)
            if clip == "negative_x" and center_mm[0] > 0:
                continue
            if clip == "positive_x" and center_mm[0] < 0:
                continue
            if section_band_mm is not None and abs(center_mm[2]) > section_band_mm:
                continue
            points_mm = [tuple(value * 1e3 for value in point) for point in face.points]
            projected = [(_dot(point, right), _dot(point, vertical)) for point in points_mm]
            depth = sum(_dot(point, forward) for point in points_mm) / 3.0
            triangles.append((depth, projected, RED if element in selected else BLUE))
            all_projected.extend(projected)

    probe_lines = _probe_lines(probe_bottom_y_mm)
    projected_probe = [
        [(_dot(point, right), _dot(point, vertical)) for point in line]
        for line in probe_lines
    ]
    all_projected.extend(point for line in projected_probe for point in line)
    if not all_projected:
        return image
    min_x = min(point[0] for point in all_projected)
    max_x = max(point[0] for point in all_projected)
    min_y = min(point[1] for point in all_projected)
    max_y = max(point[1] for point in all_projected)
    available_width = width - 2 * margin
    available_height = height - 82
    scale = min(
        available_width / max(max_x - min_x, 1e-9),
        available_height / max(max_y - min_y, 1e-9),
    )
    offset_x = margin + (available_width - (max_x - min_x) * scale) / 2 - min_x * scale
    offset_y = 50 + (available_height - (max_y - min_y) * scale) / 2 + max_y * scale

    def pixel(point: tuple[float, float]) -> tuple[int, int]:
        return round(offset_x + point[0] * scale), round(offset_y - point[1] * scale)

    for _, projected, color in sorted(triangles, key=lambda item: item[0]):
        draw.polygon([pixel(point) for point in projected], fill=color, outline=EDGE, width=1)
    for line in projected_probe:
        draw.line([pixel(point) for point in line], fill=PROBE, width=3)
    draw.rectangle((margin, height - 26, margin + 18, height - 10), fill=RED)
    draw.text((margin + 24, height - 28), "effective", fill=INK, font=font(13))
    draw.rectangle((margin + 116, height - 26, margin + 134, height - 10), fill=BLUE)
    draw.text((margin + 140, height - 28), "not included", fill=INK, font=font(13))
    draw.line((margin + 258, height - 18, margin + 286, height - 18), fill=PROBE, width=3)
    draw.text((margin + 294, height - 28), "probe", fill=INK, font=font(13))
    return image


def _section_segment(
    points: tuple[tuple[float, float, float], ...]
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    intersections: list[tuple[float, float]] = []
    for start, end in zip(points, (*points[1:], points[0])):
        z1, z2 = start[2], end[2]
        if z1 == 0 and z2 == 0:
            intersections.extend(((start[0], start[1]), (end[0], end[1])))
        elif z1 == 0:
            intersections.append((start[0], start[1]))
        elif z2 == 0:
            intersections.append((end[0], end[1]))
        elif z1 * z2 < 0:
            fraction = -z1 / (z2 - z1)
            intersections.append((
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            ))
    unique: list[tuple[float, float]] = []
    for point in intersections:
        if not any(math.hypot(point[0] - other[0], point[1] - other[1]) < 1e-9
                   for other in unique):
            unique.append(point)
    if len(unique) < 2:
        return None
    return max(
        ((first, second) for index, first in enumerate(unique) for second in unique[index + 1:]),
        key=lambda pair: math.hypot(pair[0][0] - pair[1][0], pair[0][1] - pair[1][1]),
    )


def _render_section_panel(
    outer_faces: dict[int, Face],
    outer_selected: set[int],
    inner_faces: dict[int, Face],
    inner_selected: set[int],
    probe_bottom_y_mm: float,
) -> Image.Image:
    width, height = 680, 520
    margin = 28
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), "CENTRAL Z=0 SECTION - OUTER/INNER", fill=INK, font=font(20))
    segments: list[tuple[tuple[float, float], tuple[float, float], tuple[int, int, int]]] = []
    for faces, selected in ((outer_faces, outer_selected), (inner_faces, inner_selected)):
        for element, face in faces.items():
            points_mm = tuple(tuple(value * 1e3 for value in point) for point in face.points)
            segment = _section_segment(points_mm)
            if segment is not None:
                segments.append((*segment, RED if element in selected else BLUE))
    radius_mm = PROBE_RADIUS_M * 1e3
    probe_points = (
        (-radius_mm, probe_bottom_y_mm),
        (radius_mm, probe_bottom_y_mm),
        (radius_mm, probe_bottom_y_mm + 2.6),
        (-radius_mm, probe_bottom_y_mm + 2.6),
    )
    all_points = [point for start, end, _ in segments for point in (start, end)]
    all_points.extend(probe_points)
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    available_width = width - 2 * margin
    available_height = height - 82
    scale = min(
        available_width / max(max_x - min_x, 1e-9),
        available_height / max(max_y - min_y, 1e-9),
    )
    offset_x = margin + (available_width - (max_x - min_x) * scale) / 2 - min_x * scale
    offset_y = 50 + (available_height - (max_y - min_y) * scale) / 2 + max_y * scale

    def pixel(point: tuple[float, float]) -> tuple[int, int]:
        return round(offset_x + point[0] * scale), round(offset_y - point[1] * scale)

    for color in (BLUE, RED):
        for start, end, segment_color in segments:
            if segment_color == color:
                draw.line((pixel(start), pixel(end)), fill=color, width=4 if color == RED else 2)
    closed_probe = (*probe_points, probe_points[0])
    draw.line([pixel(point) for point in closed_probe], fill=PROBE, width=3)
    draw.rectangle((margin, height - 26, margin + 18, height - 10), fill=RED)
    draw.text((margin + 24, height - 28), "effective", fill=INK, font=font(13))
    draw.rectangle((margin + 116, height - 26, margin + 134, height - 10), fill=BLUE)
    draw.text((margin + 140, height - 28), "not included", fill=INK, font=font(13))
    draw.line((margin + 258, height - 18, margin + 286, height - 18), fill=PROBE, width=3)
    draw.text((margin + 294, height - 28), "probe", fill=INK, font=font(13))
    return image


def render_multiview(
    output: Path,
    case: str,
    thickness_mm: float,
    indent_mm: float,
    outer_faces: dict[int, Face],
    outer_selected: set[int],
    inner_faces: dict[int, Face],
    inner_selected: set[int],
    angle_deg: float,
) -> None:
    selected_y = [
        point[1] * 1e3
        for element in outer_selected
        for point in outer_faces[element].points
    ]
    if not selected_y:
        selected_y = [
            point[1] * 1e3
            for face in outer_faces.values()
            for point in face.points
            if math.hypot(point[0], point[2]) <= PROBE_RADIUS_M
        ]
    probe_bottom = statistics.median(selected_y)
    panels = (
        _render_3d_panel(
            "OUTER AE - OBLIQUE 3D", [(outer_faces, outer_selected, "all")],
            (1.2, 0.85, 1.0), probe_bottom,
        ),
        _render_3d_panel(
            "INNER AC - OBLIQUE 3D", [(inner_faces, inner_selected, "all")],
            (-1.1, 0.65, 1.2), probe_bottom,
        ),
        _render_3d_panel(
            "HALF-CUT 3D - OUTER/INNER", [
                (outer_faces, outer_selected, "negative_x"),
                (inner_faces, inner_selected, "positive_x"),
            ],
            (1.25, 0.65, 1.0), probe_bottom,
        ),
        _render_section_panel(
            outer_faces, outer_selected, inner_faces, inner_selected, probe_bottom
        ),
    )
    canvas = Image.new("RGB", (1380, 1110), (242, 244, 247))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 14),
        f"{angle_text(angle_deg)} DEG DIAGNOSTIC FLAT REGION MULTIVIEW   "
        f"t={thickness_mm:.2f} mm   indent={indent_mm:.2f} mm",
        fill=INK,
        font=font(25),
    )
    for index, view in enumerate(panels):
        canvas.paste(view, (10 + (index % 2) * 685, 58 + (index // 2) * 525))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def render_case(
    attempt: Path,
    output: Path,
    case: str,
    thickness_mm: float,
    indent_mm: float,
    angle_deg: float,
) -> dict[str, str | float | int]:
    inner_preload = read_faces(attempt / "inner_preload_faces.csv")
    inner_final = read_faces(attempt / "inner_final_faces.csv")
    outer_preload = read_faces(attempt / "outer_preload_faces.csv")
    outer_final = read_faces(attempt / "outer_final_faces.csv")
    outer, outer_selected = select_flat_surface(
        outer_preload, outer_final, angle_limit_deg=angle_deg
    )
    inner, inner_selected = select_flat_surface(
        inner_preload, inner_final, angle_limit_deg=angle_deg
    )

    canvas = Image.new("RGB", (1320, 735), (246, 247, 249))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 12),
        f"{angle_text(angle_deg)} DEG DIAGNOSTIC FLAT REGION   "
        f"t={thickness_mm:.2f} mm   indent={indent_mm:.2f} mm",
        fill=INK,
        font=font(24),
    )
    canvas.paste(panel("OUTER AE", outer_final, outer_selected, outer, angle_deg), (10, 52))
    canvas.paste(panel("INNER AC", inner_final, inner_selected, inner, angle_deg), (660, 52))
    draw.rectangle((32, 707, 54, 727), fill=RED)
    draw.text((62, 707),
              f"effective: displaced, central-connected, normal angle <= {angle_text(angle_deg)} deg",
              fill=INK, font=font(14))
    draw.rectangle((760, 707, 782, 727), fill=BLUE)
    draw.text((790, 707), "not included", fill=INK, font=font(14))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    multiview_output = output.with_name(output.stem + "_multiview.png")
    render_multiview(
        multiview_output,
        case,
        thickness_mm,
        indent_mm,
        outer_final,
        outer_selected,
        inner_final,
        inner_selected,
        angle_deg,
    )
    return {
        "case": case,
        "eyelid_thickness_mm": thickness_mm,
        "indent_mm": indent_mm,
        "angle_deg": angle_deg,
        "outer_flat_area_mm2": outer.projected_area * 1e6,
        "outer_coverage_fraction": outer.projected_area / PROBE_AREA_M2,
        "outer_selected_faces": outer.face_count,
        "inner_flat_area_mm2": inner.projected_area * 1e6,
        "inner_selected_faces": inner.face_count,
        "ae_over_ac": (
            outer.projected_area / inner.projected_area if inner.projected_area > 0 else ""
        ),
        "image": str(output),
        "multiview_image": str(multiview_output),
    }


def write_manifest(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    fields = tuple(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(
    path: Path,
    rows: list[dict[str, str | float | int]],
    image_field: str = "image",
) -> None:
    columns = 3
    tile_width, tile_height = 440, 270
    rows_count = math.ceil(len(rows) / columns)
    matrix = Image.new("RGB", (columns * tile_width, rows_count * (tile_height + 30)), "white")
    draw = ImageDraw.Draw(matrix)
    for index, row in enumerate(rows):
        source = Image.open(str(row[image_field])).convert("RGB")
        source.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + 30)
        matrix.paste(source, (x + (tile_width - source.width) // 2, y))
        draw.text(
            (x + 10, y + tile_height + 4),
            f"t={float(row['eyelid_thickness_mm']):.2f} mm  coverage={float(row['outer_coverage_fraction'])*100:.1f}%",
            fill=INK,
            font=font(15),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix.save(path, format="PNG", optimize=True)


def write_angle_sweep_summary(
    path: Path,
    rows: list[dict[str, str | float | int]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (
            float(row["angle_deg"]),
            float(row["eyelid_thickness_mm"]),
        ),
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(ordered[0]))
        writer.writeheader()
        writer.writerows(ordered)


def render_angle_sweep_trend(
    path: Path,
    rows: list[dict[str, str | float | int]],
) -> None:
    width, height = 1320, 620
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (24, 16),
        "DIAGNOSTIC FLAT REGION ANGLE SWEEP   indent=0.28 mm",
        fill=INK,
        font=font(24),
    )
    angles = sorted({float(row["angle_deg"]) for row in rows})
    thicknesses = sorted({float(row["eyelid_thickness_mm"]) for row in rows})
    x_min, x_max = min(angles), max(angles)
    ratio_values = [
        float(row["ae_over_ac"])
        for row in rows
        if row["ae_over_ac"] not in ("", None)
    ]
    ratio_maximum = max(ratio_values, default=1.0)
    ratio_ceiling = next(
        (limit for limit in (12.0, 20.0, 50.0, 100.0, 200.0) if ratio_maximum <= limit),
        10.0 ** math.ceil(math.log10(ratio_maximum)),
    )

    panels = (
        (60, "outer coverage (%)", 0.0, 105.0, False),
        (700, "flat-area ratio Ae / Ac (log scale)", 0.8, ratio_ceiling, True),
    )
    for origin_x, title, y_min, y_max, logarithmic in panels:
        left, top, plot_w, plot_h = origin_x + 62, 92, 520, 390
        draw.text((origin_x + 18, 58), title, fill=INK, font=font(18))
        draw.line((left, top, left, top + plot_h), fill=INK, width=2)
        draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill=INK, width=2)

        def x_pixel(value: float) -> int:
            if x_max == x_min:
                return left + plot_w // 2
            return round(left + (value - x_min) / (x_max - x_min) * plot_w)

        def y_pixel(value: float) -> int:
            if logarithmic:
                low = math.log10(y_min)
                high = math.log10(y_max)
                fraction = (math.log10(max(value, y_min)) - low) / (high - low)
            else:
                fraction = (value - y_min) / (y_max - y_min)
            return round(top + plot_h - min(1.0, max(0.0, fraction)) * plot_h)

        y_ticks = (
            tuple(
                value
                for value in (1, 2, 3, 5, 10, 20, 30, 50, 100, 200)
                if value <= y_max
            )
            if logarithmic
            else (0, 25, 50, 75, 100)
        )
        for tick in y_ticks:
            py = y_pixel(float(tick))
            draw.line((left, py, left + plot_w, py), fill=(225, 228, 232), width=1)
            draw.text((origin_x + 20, py - 8), f"{tick:g}", fill=INK, font=font(13))
        for angle in angles:
            px = x_pixel(angle)
            draw.line((px, top, px, top + plot_h), fill=(240, 242, 244), width=1)
            draw.text((px - 8, top + plot_h + 8), f"{angle:g}", fill=INK, font=font(12))
        draw.text((left + plot_w // 2 - 38, top + plot_h + 34), "angle (deg)", fill=INK, font=font(14))

        for index, thickness in enumerate(thicknesses):
            color = SERIES_COLORS[index % len(SERIES_COLORS)]
            series = []
            for row in rows:
                if float(row["eyelid_thickness_mm"]) != thickness:
                    continue
                if logarithmic and row["ae_over_ac"] in ("", None):
                    continue
                value = (
                    float(row["ae_over_ac"])
                    if logarithmic
                    else 100.0 * float(row["outer_coverage_fraction"])
                )
                series.append((float(row["angle_deg"]), value))
            series.sort()
            points = [(x_pixel(angle), y_pixel(value)) for angle, value in series]
            if len(points) > 1:
                draw.line(points, fill=color, width=3)
            for px, py in points:
                draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color)

    legend_y = 548
    for index, thickness in enumerate(thicknesses):
        x = 44 + index * 178
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        draw.line((x, legend_y + 8, x + 28, legend_y + 8), fill=color, width=4)
        draw.text((x + 36, legend_y), f"t={thickness:.2f} mm", fill=INK, font=font(14))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--angles", type=float, nargs="+", default=(0.5, 1.0, 2.0, 3.0))
    cli = parser.parse_args()
    if cli.workers < 1 or any(angle <= 0 for angle in cli.angles):
        parser.error("workers and flatness angles must be positive")
    root = cli.run_root.expanduser().resolve()
    output_base = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures"
    )
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    jobs: list[tuple[Path, dict[str, str]]] = []
    for row in manifest:
        attempt = root / row["attempt_dir"]
        required = tuple(attempt / f"{name}_{state}_faces.csv" for name in ("inner", "outer")
                         for state in ("preload", "final"))
        if all(path.is_file() for path in required):
            jobs.append((attempt, row))
    if not jobs:
        print("no complete cases with surface face data", file=sys.stderr)
        return 1

    all_rows: list[dict[str, str | float | int]] = []
    for angle_deg in dict.fromkeys(cli.angles):
        slug = angle_slug(angle_deg)
        output_dir = output_base / f"flat_region_{slug}deg"
        rows: list[dict[str, str | float | int]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
            futures = [
                pool.submit(
                    render_case,
                    attempt,
                    output_dir / f"{row['case']}_flat_region_{slug}deg.png",
                    row["case"],
                    float(row["eyelid_thickness_mm"]),
                    float(row["indent_mm"]),
                    angle_deg,
                )
                for attempt, row in jobs
            ]
            for future in concurrent.futures.as_completed(futures):
                rows.append(future.result())
        rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
        all_rows.extend(rows)
        write_manifest(output_dir / f"flat_region_{slug}deg_manifest.csv", rows)
        write_matrix(output_base / f"flat_region_{slug}deg_matrix.png", rows)
        write_matrix(
            output_base / f"flat_region_{slug}deg_multiview_matrix.png",
            rows,
            image_field="multiview_image",
        )
        print(f"angle={angle_text(angle_deg)} rendered={len(rows)} output={output_dir}")
    write_angle_sweep_summary(output_base / "flat_region_angle_sweep.csv", all_rows)
    render_angle_sweep_trend(output_base / "flat_region_angle_sweep.png", all_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
