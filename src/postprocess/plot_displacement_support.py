#!/usr/bin/env python3
"""Render outer-displacement and inner-pressure area comparison maps."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (
    PROBE_AREA_M2,
    PROBE_RADIUS_M,
    DisplacementSupportResult,
    Face,
    conservative_projected_support,
    read_faces,
    select_displacement_support,
)
from src.postprocess.analyze_inner_pressure_area import (
    PressureAreaResult,
    PressureFace,
    pressure_area,
    read_pressure_faces,
)

RED = (211, 55, 48)
AMBER = (226, 153, 44)
BLUE = (42, 91, 176)
EDGE = (235, 238, 242)
INK = (28, 31, 35)
BACKGROUND = (246, 247, 249)


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


def render_surface_panel(
    title: str,
    faces: dict[int, Face],
    strict: set[int],
    boundary: set[int],
    result: DisplacementSupportResult,
    strict_area: float,
    clipped_area: float,
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
            fill=(
                RED if element in strict
                else AMBER if element in boundary
                else BLUE
            ),
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
    draw.text(
        (margin, 595),
        f"lower={strict_area * 1e6:.3f} mm2   "
        f"clipped={clipped_area * 1e6:.3f} mm2",
        fill=INK,
        font=font(15),
    )
    draw.text(
        (margin, 620),
        f"T={result.displacement_threshold * 1e6:.2f} um   "
        f"core={len(strict)}   boundary={len(boundary)}",
        fill=INK,
        font=font(15),
    )
    return image


def render_pressure_panel(
    final: dict[int, PressureFace],
    result: PressureAreaResult,
) -> Image.Image:
    width, height = 650, 650
    margin, plot_size = 44, 550
    extent = 1.12 * PROBE_RADIUS_M
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), "INNER PRESSURE PARTICIPATION", fill=INK, font=font(22))

    def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
        return (
            round(margin + plot_size / 2 + point[0] / extent * plot_size / 2),
            round(48 + plot_size / 2 - point[2] / extent * plot_size / 2),
        )

    for element, face in sorted(final.items()):
        if math.hypot(face.center[0], face.center[2]) > 1.18 * PROBE_RADIUS_M:
            continue
        center_x, center_y = pixel(face.center)
        face_radius = max(
            1,
            round(math.sqrt(face.area_m2 / math.pi) / extent * plot_size / 2),
        )
        draw.ellipse(
            (
                center_x - face_radius,
                center_y - face_radius,
                center_x + face_radius,
                center_y + face_radius,
            ),
            fill=RED if element in result.selected else BLUE,
            outline=EDGE,
            width=1,
        )

    center_x = margin + plot_size / 2
    center_y = 48 + plot_size / 2
    radius_px = PROBE_RADIUS_M / extent * plot_size / 2
    draw.ellipse(
        (
            center_x - radius_px,
            center_y - radius_px,
            center_x + radius_px,
            center_y + radius_px,
        ),
        outline=INK,
        width=3,
    )
    draw.text(
        (margin, 595),
        f"support={result.support_area_mm2:.3f} mm2   "
        f"effective={result.participation_area_mm2:.3f} mm2",
        fill=INK,
        font=font(15),
    )
    draw.text(
        (margin, 620),
        f"T={result.threshold_pa / 1e3:.2f} kPa   "
        f"faces={result.selected_faces}",
        fill=INK,
        font=font(15),
    )
    return image


def render_case(
    attempt: Path,
    output: Path,
    case: str,
    thickness_mm: float,
    indent_mm: float,
) -> dict[str, str | float | int]:
    inner_preload = read_faces(attempt / "inner_preload_faces.csv")
    inner_final = read_faces(attempt / "inner_final_faces.csv")
    outer_preload = read_faces(attempt / "outer_preload_faces.csv")
    outer_final = read_faces(attempt / "outer_final_faces.csv")
    inner_pressure_preload = read_pressure_faces(
        attempt / "inner_contact_preload.csv"
    )
    inner_pressure_final = read_pressure_faces(attempt / "inner_contact_final.csv")
    outer, outer_selected = select_displacement_support(outer_preload, outer_final)
    inner, inner_selected = select_displacement_support(inner_preload, inner_final)
    inner_pressure = pressure_area(
        inner_pressure_preload,
        inner_pressure_final,
        annulus_inner_m=1.2 * PROBE_RADIUS_M,
        annulus_outer_m=1.6 * PROBE_RADIUS_M,
        sigma_factor=3.0,
    )
    outer_lower, outer_clipped, outer_strict, outer_boundary = (
        conservative_projected_support(outer_final, outer_selected)
    )
    inner_lower, inner_clipped, inner_strict, inner_boundary = (
        conservative_projected_support(inner_final, inner_selected)
    )

    canvas = Image.new("RGB", (1320, 735), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 12),
        f"OUTER / INNER AREA COMPARISON   t={thickness_mm:.2f} mm   "
        f"indent={indent_mm:.2f} mm",
        fill=INK,
        font=font(24),
    )
    canvas.paste(
        render_surface_panel(
            "OUTER SURFACE",
            outer_final,
            outer_strict,
            outer_boundary,
            outer,
            outer_lower,
            outer_clipped,
        ),
        (10, 52),
    )
    canvas.paste(
        render_pressure_panel(inner_pressure_final, inner_pressure),
        (660, 52),
    )
    draw.rectangle((32, 707, 54, 727), fill=RED)
    draw.text(
        (62, 707),
        "outer: strict inside / inner: selected pressure",
        fill=INK,
        font=font(14),
    )
    draw.rectangle((480, 707, 502, 727), fill=AMBER)
    draw.text((510, 707), "outer boundary (excluded)", fill=INK, font=font(14))
    draw.rectangle((760, 707, 782, 727), fill=BLUE)
    draw.text((790, 707), "not selected", fill=INK, font=font(14))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)

    return {
        "case": case,
        "eyelid_thickness_mm": thickness_mm,
        "indent_mm": indent_mm,
        "outer_baseline_um": outer.baseline * 1e6,
        "outer_noise_sigma_um": outer.noise_sigma * 1e6,
        "outer_threshold_um": outer.displacement_threshold * 1e6,
        "outer_local_max_um": outer.local_max * 1e6,
        "outer_support_area_mm2": outer.projected_area * 1e6,
        "outer_coverage_fraction": outer.projected_area / PROBE_AREA_M2,
        "outer_selected_faces": outer.face_count,
        "outer_conservative_area_mm2": outer_lower * 1e6,
        "outer_conservative_coverage_fraction": outer_lower / PROBE_AREA_M2,
        "outer_boundary_uncertainty_mm2": (outer_clipped - outer_lower) * 1e6,
        "outer_strict_faces": len(outer_strict),
        "outer_boundary_faces": len(outer_boundary),
        "inner_baseline_um": inner.baseline * 1e6,
        "inner_noise_sigma_um": inner.noise_sigma * 1e6,
        "inner_threshold_um": inner.displacement_threshold * 1e6,
        "inner_local_max_um": inner.local_max * 1e6,
        "inner_support_area_mm2": inner.projected_area * 1e6,
        "inner_coverage_fraction": inner.projected_area / PROBE_AREA_M2,
        "inner_selected_faces": inner.face_count,
        "inner_conservative_area_mm2": inner_lower * 1e6,
        "inner_conservative_coverage_fraction": inner_lower / PROBE_AREA_M2,
        "inner_boundary_uncertainty_mm2": (inner_clipped - inner_lower) * 1e6,
        "inner_strict_faces": len(inner_strict),
        "inner_boundary_faces": len(inner_boundary),
        "inner_pressure_baseline_pa": inner_pressure.baseline_pa,
        "inner_pressure_noise_pa": inner_pressure.noise_pa,
        "inner_pressure_threshold_pa": inner_pressure.threshold_pa,
        "inner_pressure_support_area_mm2": inner_pressure.support_area_mm2,
        "inner_pressure_participation_area_mm2": (
            inner_pressure.participation_area_mm2
        ),
        "inner_pressure_selected_faces": inner_pressure.selected_faces,
        "image": output.name,
    }


def write_manifest(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(
    path: Path,
    rows: list[dict[str, str | float | int]],
    image_dir: Path,
) -> None:
    columns = 3
    tile_width, tile_height = 440, 270
    rows_count = math.ceil(len(rows) / columns)
    matrix = Image.new(
        "RGB", (columns * tile_width, rows_count * (tile_height + 34)), "white"
    )
    draw = ImageDraw.Draw(matrix)
    for index, row in enumerate(rows):
        with Image.open(image_dir / str(row["image"])) as opened:
            source = opened.convert("RGB")
        source.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + 34)
        matrix.paste(source, (x + (tile_width - source.width) // 2, y))
        draw.text(
            (x + 10, y + tile_height + 4),
            f"t={float(row['eyelid_thickness_mm']):.2f} mm   "
            f"outer lower={float(row['outer_conservative_coverage_fraction']) * 100:.1f}%   "
            f"inner lower={float(row['inner_conservative_coverage_fraction']) * 100:.1f}%",
            fill=INK,
            font=font(15),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    cli = parser.parse_args()
    if cli.workers < 1:
        parser.error("workers must be positive")
    root = cli.run_root.expanduser().resolve()
    output_dir = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures" / "displacement_support"
    )
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    jobs: list[tuple[Path, dict[str, str]]] = []
    for row in manifest:
        attempt = root / row["attempt_dir"]
        required = tuple(
            attempt / f"{name}_{state}_faces.csv"
            for name in ("inner", "outer")
            for state in ("preload", "final")
        ) + tuple(
            attempt / f"inner_contact_{state}.csv"
            for state in ("preload", "final")
        )
        if all(path.is_file() for path in required):
            jobs.append((attempt, row))
    if not jobs:
        print("no complete cases with surface face data", file=sys.stderr)
        return 1

    rows: list[dict[str, str | float | int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                render_case,
                attempt,
                output_dir / f"{row['case']}_displacement_support.png",
                row["case"],
                float(row["eyelid_thickness_mm"]),
                float(row["indent_mm"]),
            )
            for attempt, row in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    write_manifest(output_dir / "displacement_support_manifest.csv", rows)
    matrix = output_dir.parent / "displacement_support_matrix.png"
    write_matrix(matrix, rows, output_dir)
    print(f"rendered={len(rows)} output={output_dir} matrix={matrix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
