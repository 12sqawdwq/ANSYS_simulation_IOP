#!/usr/bin/env python3
"""Compare outer and inner effective areas using pressure distributions."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.analyze_inner_pressure_area import (
    PressureAreaResult,
    PressureFace,
    pressure_area,
    read_pressure_faces,
)
from src.postprocess.plot_displacement_support import (
    BACKGROUND,
    BLUE,
    EDGE,
    INK,
    RED,
    font,
    map_pressure_selection_to_surface,
)
from src.postprocess.thickness_geometry import (
    PROBE_AREA_M2,
    PROBE_RADIUS_M,
    Face,
    conservative_projected_support,
    read_faces,
    select_displacement_support,
)

OUTER_COLOR = (212, 69, 52)
INNER_COLOR = (31, 132, 116)
SUPPORT_COLOR = (120, 126, 137)
HYBRID_COLOR = (49, 90, 168)
GRID = (224, 228, 233)


def comparison_metrics(
    outer: PressureAreaResult,
    inner: PressureAreaResult,
    outer_conservative_area_mm2: float,
) -> dict[str, float]:
    if inner.participation_area_mm2 <= 0 or inner.support_area_mm2 <= 0:
        raise ValueError("inner pressure area must be positive")
    effective_ratio = (
        outer.participation_area_mm2 / inner.participation_area_mm2
    )
    support_ratio = outer.support_area_mm2 / inner.support_area_mm2
    hybrid_ratio = outer_conservative_area_mm2 / inner.participation_area_mm2
    return {
        "pressure_effective_ratio": effective_ratio,
        "pressure_support_ratio": support_ratio,
        "current_hybrid_ratio": hybrid_ratio,
        "effective_ratio_change_percent": (
            effective_ratio / hybrid_ratio - 1.0
        ) * 100.0,
    }


def _surface_selection(
    surface: dict[int, Face],
    pressure: dict[int, PressureFace],
    selected: frozenset[int],
) -> set[int]:
    if selected.issubset(surface):
        return set(selected)
    mapped, _ = map_pressure_selection_to_surface(surface, pressure, selected)
    return mapped


def render_pressure_panel(
    title: str,
    surface: dict[int, Face],
    pressure: dict[int, PressureFace],
    result: PressureAreaResult,
    accent: tuple[int, int, int],
) -> Image.Image:
    width, height = 650, 650
    margin, plot_size = 44, 550
    extent = 1.12 * PROBE_RADIUS_M
    selected = _surface_selection(surface, pressure, result.selected)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), title, fill=INK, font=font(22))

    def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
        return (
            round(margin + plot_size / 2 + point[0] / extent * plot_size / 2),
            round(48 + plot_size / 2 - point[2] / extent * plot_size / 2),
        )

    for element, face in sorted(surface.items()):
        center_x = sum(point[0] for point in face.points) / 3.0
        center_z = sum(point[2] for point in face.points) / 3.0
        if math.hypot(center_x, center_z) > 1.18 * PROBE_RADIUS_M:
            continue
        draw.polygon(
            [pixel(point) for point in face.points],
            fill=accent if element in selected else BLUE,
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
    draw.rectangle((margin - 4, 582, width - 8, height), fill="white")
    draw.text(
        (margin, 592),
        f"support={result.support_area_mm2:.3f} mm2   "
        f"effective={result.participation_area_mm2:.3f} mm2",
        fill=INK,
        font=font(15),
    )
    draw.text(
        (margin, 618),
        f"T={result.threshold_pa / 1e3:.3f} kPa   "
        f"dF={result.incremental_force_n:.4f} N   faces={result.selected_faces}",
        fill=INK,
        font=font(14),
    )
    return image


def render_case(
    attempt: Path,
    output: Path,
    row: dict[str, str],
    annulus_inner: float,
    annulus_outer: float,
    sigma_factor: float,
) -> dict[str, str | float | int]:
    outer_preload_pressure = read_pressure_faces(
        attempt / "outer_contact_preload.csv"
    )
    outer_final_pressure = read_pressure_faces(attempt / "outer_contact_final.csv")
    inner_preload_pressure = read_pressure_faces(
        attempt / "inner_contact_preload.csv"
    )
    inner_final_pressure = read_pressure_faces(attempt / "inner_contact_final.csv")
    outer_preload = read_faces(attempt / "outer_preload_faces.csv")
    outer_final = read_faces(attempt / "outer_final_faces.csv")
    inner_final = read_faces(attempt / "inner_final_faces.csv")

    pressure_arguments = {
        "annulus_inner_m": annulus_inner * PROBE_RADIUS_M,
        "annulus_outer_m": annulus_outer * PROBE_RADIUS_M,
        "sigma_factor": sigma_factor,
        "minimum_status": 2.0,
    }
    outer_result = pressure_area(
        outer_preload_pressure,
        outer_final_pressure,
        **pressure_arguments,
    )
    inner_result = pressure_area(
        inner_preload_pressure,
        inner_final_pressure,
        **pressure_arguments,
    )
    _, outer_displacement_selection = select_displacement_support(
        outer_preload,
        outer_final,
    )
    outer_conservative, _, _, _ = conservative_projected_support(
        outer_final,
        outer_displacement_selection,
    )
    outer_conservative_mm2 = outer_conservative * 1e6
    ratios = comparison_metrics(
        outer_result,
        inner_result,
        outer_conservative_mm2,
    )

    thickness = float(row["eyelid_thickness_mm"])
    indent = float(row["indent_mm"])
    canvas = Image.new("RGB", (1320, 735), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 12),
        f"PRESSURE-DISTRIBUTION AREA COMPARISON   t={thickness:.2f} mm   "
        f"indent={indent:.2f} mm",
        fill=INK,
        font=font(24),
    )
    canvas.paste(
        render_pressure_panel(
            "OUTER: PROBE CONTACT PRESSURE",
            outer_final,
            outer_final_pressure,
            outer_result,
            OUTER_COLOR,
        ),
        (10, 52),
    )
    canvas.paste(
        render_pressure_panel(
            "INNER: BONDED PRESSURE INCREMENT",
            inner_final,
            inner_final_pressure,
            inner_result,
            INNER_COLOR,
        ),
        (660, 52),
    )
    draw.rectangle((30, 707, 52, 727), fill=OUTER_COLOR)
    draw.text((60, 707), "selected outer mesh", fill=INK, font=font(14))
    draw.rectangle((260, 707, 282, 727), fill=INNER_COLOR)
    draw.text((290, 707), "selected inner mesh", fill=INK, font=font(14))
    draw.rectangle((500, 707, 522, 727), fill=BLUE)
    draw.text((530, 707), "below threshold / disconnected", fill=INK, font=font(14))
    draw.text(
        (905, 707),
        f"Keff={ratios['pressure_effective_ratio']:.3f}   "
        f"Ksupport={ratios['pressure_support_ratio']:.3f}",
        fill=INK,
        font=font(14),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)

    return {
        "case": row["case"],
        "eyelid_thickness_mm": thickness,
        "indent_mm": indent,
        "annulus_inner_probe_radius": annulus_inner,
        "annulus_outer_probe_radius": annulus_outer,
        "sigma_factor": sigma_factor,
        "outer_pressure_baseline_pa": outer_result.baseline_pa,
        "outer_pressure_noise_pa": outer_result.noise_pa,
        "outer_pressure_threshold_pa": outer_result.threshold_pa,
        "outer_pressure_support_area_mm2": outer_result.support_area_mm2,
        "outer_pressure_effective_area_mm2": outer_result.participation_area_mm2,
        "outer_incremental_force_n": outer_result.incremental_force_n,
        "outer_selected_faces": outer_result.selected_faces,
        "inner_pressure_baseline_pa": inner_result.baseline_pa,
        "inner_pressure_noise_pa": inner_result.noise_pa,
        "inner_pressure_threshold_pa": inner_result.threshold_pa,
        "inner_pressure_support_area_mm2": inner_result.support_area_mm2,
        "inner_pressure_effective_area_mm2": inner_result.participation_area_mm2,
        "inner_incremental_force_n": inner_result.incremental_force_n,
        "inner_selected_faces": inner_result.selected_faces,
        "outer_conservative_area_mm2": outer_conservative_mm2,
        **ratios,
        "probe_area_mm2": PROBE_AREA_M2 * 1e6,
        "status": "diagnostic_not_approved",
        "image": output.name,
    }


def write_csv(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _chart_panel(
    draw: ImageDraw.ImageDraw,
    origin_x: int,
    title: str,
    x_values: list[float],
    y_values: list[float],
) -> tuple[Callable[[float, float], tuple[int, int]], tuple[int, int, int, int]]:
    left, top, width, height = origin_x + 78, 90, 540, 390
    x_min, x_max = min(x_values), max(x_values)
    y_min = min(0.0, math.floor(min(y_values) * 10.0) / 10.0)
    y_max = max(1.0, math.ceil(max(y_values) * 10.0) / 10.0)
    if y_max <= y_min:
        y_max = y_min + 1.0
    draw.text((origin_x + 24, 54), title, fill=INK, font=font(18))
    for fraction in np.linspace(0.0, 1.0, 6):
        y = top + height - fraction * height
        value = y_min + fraction * (y_max - y_min)
        draw.line((left, y, left + width, y), fill=GRID, width=1)
        draw.text((origin_x + 20, y - 8), f"{value:.1f}", fill=INK, font=font(12))
    for value in x_values:
        x = left + (value - x_min) / max(x_max - x_min, 1e-9) * width
        draw.text((x - 12, top + height + 10), f"{value:g}", fill=INK, font=font(12))

    def pixel(x_value: float, y_value: float) -> tuple[int, int]:
        return (
            round(left + (x_value - x_min) / max(x_max - x_min, 1e-9) * width),
            round(top + height - (y_value - y_min) / (y_max - y_min) * height),
        )

    return pixel, (left, top, width, height)


def render_trend(
    path: Path,
    rows: list[dict[str, str | float | int]],
) -> None:
    width, height = 1400, 585
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (24, 14),
        "OUTER / INNER EFFECTIVE MECHANICAL AREA - THICKNESS TREND",
        fill=INK,
        font=font(23),
    )
    thicknesses = [float(row["eyelid_thickness_mm"]) for row in rows]
    area_series = (
        ("outer_pressure_support_area_mm2", OUTER_COLOR, "outer support"),
        ("outer_pressure_effective_area_mm2", (235, 132, 111), "outer effective"),
        ("inner_pressure_support_area_mm2", INNER_COLOR, "inner support"),
        ("inner_pressure_effective_area_mm2", (91, 181, 166), "inner effective"),
    )
    area_values = [float(row[field]) for row in rows for field, _, _ in area_series]
    area_pixel, _ = _chart_panel(
        draw, 0, "Pressure-derived area (mm2)", thicknesses, area_values
    )
    for index, (field, color, label) in enumerate(area_series):
        points = [area_pixel(x, float(row[field])) for x, row in zip(thicknesses, rows)]
        draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
        legend_x = 72 + (index % 2) * 250
        legend_y = 525 + (index // 2) * 24
        draw.line((legend_x, legend_y, legend_x + 28, legend_y), fill=color, width=3)
        draw.text((legend_x + 36, legend_y - 8), label, fill=INK, font=font(13))

    ratio_series = (
        ("pressure_effective_ratio", RED, "pressure effective ratio"),
        ("pressure_support_ratio", SUPPORT_COLOR, "pressure support ratio"),
        ("current_hybrid_ratio", HYBRID_COLOR, "current mixed ratio"),
    )
    ratio_values = [float(row[field]) for row in rows for field, _, _ in ratio_series]
    ratio_pixel, _ = _chart_panel(
        draw, 700, "Outer / inner area ratio", thicknesses, ratio_values
    )
    for index, (field, color, label) in enumerate(ratio_series):
        points = [ratio_pixel(x, float(row[field])) for x, row in zip(thicknesses, rows)]
        draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)
        legend_x = 770 + index * 195
        draw.line((legend_x, 535, legend_x + 25, 535), fill=color, width=3)
        draw.text((legend_x + 31, 527), label, fill=INK, font=font(12))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def render_matrix(
    path: Path,
    rows: list[dict[str, str | float | int]],
    image_dir: Path,
) -> None:
    columns = 3
    tile_width, tile_height = 440, 270
    row_count = math.ceil(len(rows) / columns)
    canvas = Image.new(
        "RGB",
        (columns * tile_width, row_count * (tile_height + 42)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        with Image.open(image_dir / str(row["image"])) as opened:
            source = opened.convert("RGB")
        source.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = index % columns * tile_width
        y = index // columns * (tile_height + 42)
        canvas.paste(source, (x + (tile_width - source.width) // 2, y))
        draw.text(
            (x + 10, y + tile_height + 3),
            f"t={float(row['eyelid_thickness_mm']):.2f} mm   "
            f"AeP={float(row['outer_pressure_effective_area_mm2']):.3f}   "
            f"AcP={float(row['inner_pressure_effective_area_mm2']):.3f}   "
            f"K={float(row['pressure_effective_ratio']):.3f}",
            fill=INK,
            font=font(14),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--annulus-inner", type=float, default=1.2)
    parser.add_argument("--annulus-outer", type=float, default=1.6)
    parser.add_argument("--sigma-factor", type=float, default=3.0)
    cli = parser.parse_args()
    if (
        cli.workers < 1
        or not 1.0 <= cli.annulus_inner < cli.annulus_outer
        or cli.sigma_factor <= 0
    ):
        parser.error("invalid workers, annulus or sigma factor")
    root = cli.run_root.expanduser().resolve()
    output = cli.output_dir.expanduser().resolve()
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    required = (
        "outer_contact_preload.csv",
        "outer_contact_final.csv",
        "inner_contact_preload.csv",
        "inner_contact_final.csv",
        "outer_preload_faces.csv",
        "outer_final_faces.csv",
        "inner_final_faces.csv",
    )
    jobs = [
        (root / row["attempt_dir"], row)
        for row in manifest
        if all((root / row["attempt_dir"] / name).is_file() for name in required)
    ]
    if not jobs:
        parser.error("no complete cases with inner and outer pressure-face states")

    image_dir = output / "states"
    rows: list[dict[str, str | float | int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                render_case,
                attempt,
                image_dir / f"{row['case']}_mechanical_area.png",
                row,
                cli.annulus_inner,
                cli.annulus_outer,
                cli.sigma_factor,
            )
            for attempt, row in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    write_csv(output / "mechanical_area_comparison.csv", rows)
    render_trend(output / "mechanical_area_trend.png", rows)
    render_matrix(output / "mechanical_area_matrix.png", rows, image_dir)
    print(f"cases={len(rows)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
