#!/usr/bin/env python3
"""Estimate inner load-bearing area from incremental bonded-interface pressure."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.plot_inner_planarity_trial import BACKGROUND, BLUE, EDGE, INK, RED, font
from src.postprocess.thickness_geometry import PROBE_RADIUS_M


@dataclass(frozen=True)
class PressureFace:
    element: int
    nodes: tuple[int, int, int]
    status: float
    pressure_pa: float
    area_m2: float
    center: tuple[float, float, float]


@dataclass(frozen=True)
class PressureAreaResult:
    selected: frozenset[int]
    baseline_pa: float
    noise_pa: float
    threshold_pa: float
    support_area_mm2: float
    participation_area_mm2: float
    incremental_force_n: float
    centroid_x_mm: float
    centroid_z_mm: float
    selected_faces: int


def read_pressure_faces(path: Path) -> dict[int, PressureFace]:
    faces: dict[int, PressureFace] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.reader(handle), 1):
            values = [float(item) for item in row if item.strip()]
            if not values:
                continue
            if len(values) != 10 or not all(math.isfinite(value) for value in values):
                raise ValueError(f"{path.name}:{line_number}: invalid pressure row")
            identifiers = tuple(int(round(value)) for value in values[:4])
            if any(abs(values[index] - identifiers[index]) > 1e-6 for index in range(4)):
                raise ValueError(f"{path.name}:{line_number}: invalid identifier")
            element, n1, n2, n3 = identifiers
            if element in faces or values[6] < 0:
                raise ValueError(f"{path.name}:{line_number}: duplicate element or area")
            faces[element] = PressureFace(
                element=element,
                nodes=(n1, n2, n3),
                status=values[4],
                pressure_pa=values[5],
                area_m2=values[6],
                center=(values[7], values[8], values[9]),
            )
    if not faces:
        raise ValueError(f"{path}: no pressure faces")
    return faces


def central_component(
    faces: dict[int, PressureFace], candidates: set[int]
) -> set[int]:
    if not candidates:
        return set()
    edge_owners: dict[tuple[int, int], list[int]] = {}
    for element in candidates:
        nodes = faces[element].nodes
        for first, second in (
            (nodes[0], nodes[1]),
            (nodes[1], nodes[2]),
            (nodes[2], nodes[0]),
        ):
            edge_owners.setdefault(tuple(sorted((first, second))), []).append(element)
    adjacency = {element: set() for element in candidates}
    for owners in edge_owners.values():
        for element in owners:
            adjacency[element].update(other for other in owners if other != element)
    seed = min(
        candidates,
        key=lambda element: math.hypot(
            faces[element].center[0], faces[element].center[2]
        ),
    )
    connected = {seed}
    stack = [seed]
    while stack:
        element = stack.pop()
        for neighbor in adjacency[element] - connected:
            connected.add(neighbor)
            stack.append(neighbor)
    return connected


def pressure_area(
    preload: dict[int, PressureFace],
    final: dict[int, PressureFace],
    *,
    annulus_inner_m: float,
    annulus_outer_m: float,
    sigma_factor: float,
) -> PressureAreaResult:
    if set(preload) != set(final):
        raise ValueError("preload and final pressure element sets differ")
    if not 0 < annulus_inner_m < annulus_outer_m or sigma_factor <= 0:
        raise ValueError("invalid annulus or sigma factor")
    elements = sorted(final)
    radii = np.asarray([
        math.hypot(final[element].center[0], final[element].center[2])
        for element in elements
    ])
    delta = np.asarray([
        final[element].pressure_pa - preload[element].pressure_pa
        for element in elements
    ])
    annulus = (radii >= annulus_inner_m) & (radii <= annulus_outer_m)
    if int(np.count_nonzero(annulus)) < 30:
        raise ValueError("pressure reference annulus contains fewer than 30 faces")
    baseline = float(np.median(delta[annulus]))
    residual = delta[annulus] - baseline
    noise = 1.4826 * float(np.median(np.abs(residual - np.median(residual))))
    threshold = sigma_factor * max(noise, 1e-9)
    local = {element: float(delta[index] - baseline) for index, element in enumerate(elements)}
    candidates = {
        element for element in elements
        if local[element] > threshold and final[element].area_m2 > 0
    }
    selected = central_component(final, candidates)
    support_area = sum(final[element].area_m2 for element in selected)
    force = sum(local[element] * final[element].area_m2 for element in selected)
    square_integral = sum(
        local[element] ** 2 * final[element].area_m2 for element in selected
    )
    participation_area = force * force / square_integral if square_integral > 0 else 0.0
    first_x = sum(
        final[element].center[0] * local[element] * final[element].area_m2
        for element in selected
    )
    first_z = sum(
        final[element].center[2] * local[element] * final[element].area_m2
        for element in selected
    )
    return PressureAreaResult(
        selected=frozenset(selected),
        baseline_pa=baseline,
        noise_pa=noise,
        threshold_pa=threshold,
        support_area_mm2=support_area * 1e6,
        participation_area_mm2=participation_area * 1e6,
        incremental_force_n=force,
        centroid_x_mm=first_x / force * 1e3 if force > 0 else math.nan,
        centroid_z_mm=first_z / force * 1e3 if force > 0 else math.nan,
        selected_faces=len(selected),
    )


def render_panel(
    final: dict[int, PressureFace], result: PressureAreaResult, thickness_mm: float
) -> Image.Image:
    width, height = 470, 500
    margin, plot_size = 35, 390
    radius = max(math.hypot(face.center[0], face.center[2]) for face in final.values())
    extent = min(radius, 3.2e-3)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 8), f"t={thickness_mm:.2f} mm", fill=INK, font=font(20))
    for element, face in final.items():
        x, _, z = face.center
        if math.hypot(x, z) > extent:
            continue
        px = round(margin + plot_size / 2 + x / extent * plot_size / 2)
        py = round(42 + plot_size / 2 - z / extent * plot_size / 2)
        area_radius = max(1, round(math.sqrt(face.area_m2 / math.pi) / extent * plot_size / 2))
        color = RED if element in result.selected else BLUE
        draw.ellipse(
            (px - area_radius, py - area_radius, px + area_radius, py + area_radius),
            fill=color,
            outline=EDGE,
        )
    center_x = margin + plot_size / 2
    center_y = 42 + plot_size / 2
    probe_px = PROBE_RADIUS_M / extent * plot_size / 2
    draw.ellipse(
        (center_x - probe_px, center_y - probe_px,
         center_x + probe_px, center_y + probe_px),
        outline=INK,
        width=2,
    )
    draw.text(
        (margin, 440),
        f"support={result.support_area_mm2:.2f}  effective={result.participation_area_mm2:.2f} mm2",
        fill=INK,
        font=font(14),
    )
    draw.text(
        (margin, 466),
        f"threshold={result.threshold_pa / 1e3:.2f} kPa  faces={result.selected_faces}",
        fill=INK,
        font=font(13),
    )
    return image


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_trend(
    path: Path,
    selected: list[dict[str, float | int | str]],
    sensitivity: list[dict[str, float | int | str]],
) -> None:
    width, height = 1280, 520
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((24, 14), "INNER PRESSURE AREA - THICKNESS TREND", fill=INK, font=font(23))
    thicknesses = [float(row["eyelid_thickness_mm"]) for row in selected]
    x_min, x_max = min(thicknesses), max(thicknesses)

    def panel(
        origin_x: int,
        title: str,
        y_min: float,
        y_max: float,
    ) -> tuple[Callable[[float, float], tuple[int, int]], tuple[int, int, int, int]]:
        left, top, plot_w, plot_h = origin_x + 70, 82, 500, 350
        draw.text((origin_x + 18, 50), title, fill=INK, font=font(17))
        for fraction in np.linspace(0, 1, 5):
            y = top + plot_h - fraction * plot_h
            value = y_min + fraction * (y_max - y_min)
            draw.line((left, y, left + plot_w, y), fill=(224, 228, 233), width=1)
            draw.text((origin_x + 22, y - 8), f"{value:.1f}", fill=INK, font=font(12))
        for thickness in thicknesses:
            x = left + (thickness - x_min) / max(x_max - x_min, 1e-9) * plot_w
            draw.text((x - 12, top + plot_h + 8), f"{thickness:g}", fill=INK, font=font(12))

        def pixel(x_value: float, y_value: float) -> tuple[int, int]:
            return (
                round(left + (x_value - x_min) / max(x_max - x_min, 1e-9) * plot_w),
                round(top + plot_h - (y_value - y_min) / (y_max - y_min) * plot_h),
            )

        return pixel, (left, top, plot_w, plot_h)

    area_pixel, _ = panel(0, "Curved area integral (mm2)", 0.0, 9.0)
    area_series = (
        ("outer_contact_area_mm2", (45, 95, 175), "outer contact"),
        ("inner_pressure_support_area_mm2", (130, 135, 145), "inner support"),
        ("inner_pressure_participation_area_mm2", RED, "inner effective"),
    )
    for index, (field, color, label) in enumerate(area_series):
        points = [
            area_pixel(float(row["eyelid_thickness_mm"]), float(row[field]))
            for row in selected
        ]
        draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
        legend_x = 80 + index * 165
        draw.line((legend_x, 466, legend_x + 25, 466), fill=color, width=3)
        draw.text((legend_x + 31, 458), label, fill=INK, font=font(12))

    ratio_pixel, _ = panel(640, "Ae/Ac pressure candidate", 0.8, 1.5)
    grouped: dict[float, list[float]] = {}
    for row in sensitivity:
        grouped.setdefault(float(row["eyelid_thickness_mm"]), []).append(
            float(row["ae_over_ac_pressure"])
        )
    for thickness in thicknesses:
        values = grouped[thickness]
        x1, y1 = ratio_pixel(thickness, min(values))
        _, y2 = ratio_pixel(thickness, max(values))
        draw.line((x1, y1, x1, y2), fill=(175, 180, 188), width=7)
    ratio_points = [
        ratio_pixel(
            float(row["eyelid_thickness_mm"]),
            float(row["ae_over_ac_pressure"]),
        )
        for row in selected
    ]
    draw.line(ratio_points, fill=RED, width=3)
    for x, y in ratio_points:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=RED)
    draw.text((720, 458), "gray: 9-setting sensitivity range", fill=INK, font=font(13))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sigma-factors", type=float, nargs="+", default=(2.0, 3.0, 4.0))
    parser.add_argument(
        "--annuli-probe-radius",
        type=str,
        nargs="+",
        default=("1.1:1.5", "1.2:1.6", "1.3:1.7"),
    )
    cli = parser.parse_args()
    root = cli.run_root.expanduser().resolve()
    output = cli.output_dir.expanduser().resolve()
    annuli = []
    for value in cli.annuli_probe_radius:
        first, second = (float(item) for item in value.split(":", 1))
        if not 1.0 <= first < second:
            parser.error("annulus factors must be formatted inner:outer and lie outside 1.0")
        annuli.append((first, second))
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    cases = []
    for row in manifest:
        attempt = root / row["attempt_dir"]
        preload_path = attempt / "inner_contact_preload.csv"
        final_path = attempt / "inner_contact_final.csv"
        if preload_path.is_file() and final_path.is_file():
            cases.append((
                row,
                read_pressure_faces(preload_path),
                read_pressure_faces(final_path),
            ))
    if not cases:
        parser.error("no complete cases with bonded-interface pressure states")
    cases.sort(key=lambda item: float(item[0]["eyelid_thickness_mm"]))

    sensitivity: list[dict[str, float | int | str]] = []
    selected_results: list[tuple[float, dict[int, PressureFace], PressureAreaResult]] = []
    for row, preload, final in cases:
        thickness = float(row["eyelid_thickness_mm"])
        outer_area = float(row["contact_area_m2"]) * 1e6
        for inner_factor, outer_factor in annuli:
            for sigma_factor in cli.sigma_factors:
                result = pressure_area(
                    preload,
                    final,
                    annulus_inner_m=inner_factor * PROBE_RADIUS_M,
                    annulus_outer_m=outer_factor * PROBE_RADIUS_M,
                    sigma_factor=sigma_factor,
                )
                item = {
                    "case": row["case"],
                    "eyelid_thickness_mm": thickness,
                    "annulus_inner_probe_radius": inner_factor,
                    "annulus_outer_probe_radius": outer_factor,
                    "sigma_factor": sigma_factor,
                    "baseline_pa": result.baseline_pa,
                    "noise_pa": result.noise_pa,
                    "threshold_pa": result.threshold_pa,
                    "inner_pressure_support_area_mm2": result.support_area_mm2,
                    "inner_pressure_participation_area_mm2": result.participation_area_mm2,
                    "outer_contact_area_mm2": outer_area,
                    "ae_over_ac_pressure": (
                        outer_area / result.participation_area_mm2
                        if result.participation_area_mm2 > 0 else ""
                    ),
                    "incremental_force_n": result.incremental_force_n,
                    "centroid_x_mm": result.centroid_x_mm,
                    "centroid_z_mm": result.centroid_z_mm,
                    "selected_faces": result.selected_faces,
                    "status": "candidate_not_approved",
                }
                sensitivity.append(item)
                if (
                    abs(inner_factor - 1.2) < 1e-9
                    and abs(outer_factor - 1.6) < 1e-9
                    and abs(sigma_factor - 3.0) < 1e-9
                ):
                    selected_results.append((thickness, final, result))
    write_csv(output / "inner_pressure_area_sensitivity.csv", sensitivity)
    selected_rows = [
        row for row in sensitivity
        if float(row["annulus_inner_probe_radius"]) == 1.2
        and float(row["annulus_outer_probe_radius"]) == 1.6
        and float(row["sigma_factor"]) == 3.0
    ]
    write_csv(output / "inner_pressure_area_candidate.csv", selected_rows)
    render_trend(
        output / "inner_pressure_area_trend.png",
        selected_rows,
        sensitivity,
    )

    columns = 4
    rows = math.ceil(len(selected_results) / columns)
    canvas = Image.new("RGB", (columns * 470, 52 + rows * 500), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (18, 12),
        "INNER INCREMENTAL PRESSURE AREA   annulus=1.2a-1.6a   threshold=3 sigma",
        fill=INK,
        font=font(23),
    )
    for index, (thickness, final, result) in enumerate(selected_results):
        canvas.paste(render_panel(final, result, thickness), (
            index % columns * 470,
            52 + index // columns * 500,
        ))
    output.mkdir(parents=True, exist_ok=True)
    canvas.save(output / "inner_pressure_area_matrix.png", format="PNG", optimize=True)
    print(f"cases={len(cases)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
