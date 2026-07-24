#!/usr/bin/env python3
"""Render trial inner-surface planarity maps from saved thickness face states."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (
    PROBE_RADIUS_M,
    Face,
    _central_connected_elements,
    _face_geometry,
    _projected_area_inside_circle,
    _validate_face_sets,
    read_faces,
    select_displacement_support,
)

RED = (211, 55, 48)
BLUE = (42, 91, 176)
EDGE = (235, 238, 242)
INK = (28, 31, 35)
BACKGROUND = (246, 247, 249)


@dataclass(frozen=True)
class PatchMetric:
    element: int
    radius_m: float
    final_plane_rms_mm: float
    preload_curvature_per_mm: float
    final_curvature_per_mm: float
    curvature_reduction_per_mm: float


@dataclass(frozen=True)
class PlanarityResult:
    selected: frozenset[int]
    projected_area_mm2: float
    face_count: int
    height_tolerance_um: float
    curvature_tolerance_per_mm: float
    curvature_noise_per_mm: float
    curvature_baseline_per_mm: float


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


def _fit_patch_geometry(
    points_mm: np.ndarray, weights: np.ndarray
) -> tuple[float, float]:
    """Return plane RMS residual and quadratic curvature magnitude."""
    if points_mm.ndim != 2 or points_mm.shape[1] != 3 or len(points_mm) < 6:
        raise ValueError("at least six 3D patch points are required")
    if weights.shape != (len(points_mm),) or np.any(weights <= 0):
        raise ValueError("patch weights must be positive and match the points")
    center = np.average(points_mm, axis=0, weights=weights)
    x = points_mm[:, 0] - center[0]
    z = points_mm[:, 2] - center[2]
    y = points_mm[:, 1] - center[1]
    root_weight = np.sqrt(weights / np.mean(weights))

    plane = np.column_stack((np.ones_like(x), x, z))
    plane_coefficients, _, _, _ = np.linalg.lstsq(
        plane * root_weight[:, None], y * root_weight, rcond=None
    )
    plane_residual = y - plane @ plane_coefficients
    plane_rms = math.sqrt(float(np.average(plane_residual**2, weights=weights)))

    quadratic = np.column_stack((
        np.ones_like(x),
        x,
        z,
        0.5 * x**2,
        x * z,
        0.5 * z**2,
    ))
    coefficients, _, _, _ = np.linalg.lstsq(
        quadratic * root_weight[:, None], y * root_weight, rcond=None
    )
    fx, fz = float(coefficients[1]), float(coefficients[2])
    hessian = np.asarray([
        [coefficients[3], coefficients[4]],
        [coefficients[4], coefficients[5]],
    ], dtype=float)
    first_form = np.asarray([[1.0 + fx * fx, fx * fz],
                             [fx * fz, 1.0 + fz * fz]], dtype=float)
    second_form = hessian / math.sqrt(1.0 + fx * fx + fz * fz)
    principal = np.linalg.eigvals(np.linalg.solve(first_form, second_form)).real
    curvature = float(np.linalg.norm(principal))
    return plane_rms, curvature


def patch_metrics(
    preload: dict[int, Face],
    final: dict[int, Face],
    window_diameter_mm: float,
) -> list[PatchMetric]:
    _validate_face_sets(preload, final)
    elements = sorted(preload)

    def centers(faces: dict[int, Face]) -> np.ndarray:
        return np.asarray([
            [sum(point[axis] for point in faces[element].points) / 3.0 for axis in range(3)]
            for element in elements
        ], dtype=float)

    preload_centers = centers(preload)
    final_centers = centers(final)
    weights = np.asarray([_face_geometry(preload[element])[0] for element in elements])
    tree = cKDTree(preload_centers[:, (0, 2)] * 1e3)
    radius_mm = window_diameter_mm / 2.0
    metrics: list[PatchMetric] = []
    for index, element in enumerate(elements):
        neighbors = tree.query_ball_point(preload_centers[index, (0, 2)] * 1e3, radius_mm)
        if len(neighbors) < 12:
            _, nearest = tree.query(
                preload_centers[index, (0, 2)] * 1e3,
                k=min(12, len(elements)),
            )
            neighbors = np.atleast_1d(nearest).astype(int).tolist()
        neighbor_indices = np.asarray(neighbors, dtype=int)
        patch_weights = weights[neighbor_indices]
        _, preload_curvature = _fit_patch_geometry(
            preload_centers[neighbor_indices] * 1e3, patch_weights
        )
        final_rms, final_curvature = _fit_patch_geometry(
            final_centers[neighbor_indices] * 1e3, patch_weights
        )
        center = final_centers[index]
        metrics.append(PatchMetric(
            element=element,
            radius_m=math.hypot(float(center[0]), float(center[2])),
            final_plane_rms_mm=final_rms,
            preload_curvature_per_mm=preload_curvature,
            final_curvature_per_mm=final_curvature,
            curvature_reduction_per_mm=preload_curvature - final_curvature,
        ))
    return metrics


def select_planarity_region(
    preload: dict[int, Face],
    final: dict[int, Face],
    metrics: list[PatchMetric],
    *,
    height_tolerance_um: float,
    window_diameter_mm: float,
    analysis_radius_m: float,
) -> PlanarityResult:
    _, displacement_support = select_displacement_support(
        preload, final, maximum_radius=analysis_radius_m
    )
    radii = np.asarray([metric.radius_m for metric in metrics], dtype=float)
    reduction = np.asarray(
        [metric.curvature_reduction_per_mm for metric in metrics], dtype=float
    )
    annulus = (radii >= 0.65 * float(np.max(radii))) & (
        radii <= 0.82 * float(np.max(radii))
    )
    if int(np.count_nonzero(annulus)) < 12:
        annulus = radii >= float(np.quantile(radii, 0.7))
    baseline = float(np.median(reduction[annulus]))
    residual = reduction[annulus] - baseline
    noise = 1.4826 * float(np.median(np.abs(residual - np.median(residual))))
    reduction_threshold = max(3.0 * noise, 1e-6)
    curvature_tolerance = 8.0 * height_tolerance_um * 1e-3 / window_diameter_mm**2
    metric_by_element = {metric.element: metric for metric in metrics}
    candidates = {
        metric.element
        for metric in metrics
        if metric.element in displacement_support
        and metric.final_plane_rms_mm <= height_tolerance_um * 1e-3
        and metric.final_curvature_per_mm <= curvature_tolerance
        and metric.curvature_reduction_per_mm - baseline > reduction_threshold
    }
    connected = _central_connected_elements(final, candidates)
    if connected and min(metric_by_element[element].radius_m for element in connected) > (
        0.5 * window_diameter_mm * 1e-3
    ):
        connected = set()

    projected_area = 0.0
    for element in connected:
        points = tuple((point[0], point[2]) for point in final[element].points)
        projected_area += _projected_area_inside_circle(points, analysis_radius_m)
    return PlanarityResult(
        selected=frozenset(connected),
        projected_area_mm2=projected_area * 1e6,
        face_count=len(connected),
        height_tolerance_um=height_tolerance_um,
        curvature_tolerance_per_mm=curvature_tolerance,
        curvature_noise_per_mm=noise,
        curvature_baseline_per_mm=baseline,
    )


def render_panel(
    final: dict[int, Face],
    result: PlanarityResult,
    thickness_mm: float,
    analysis_radius_m: float,
) -> Image.Image:
    width, height = 590, 620
    margin, plot_size = 40, 500
    extent = 1.08 * analysis_radius_m
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (margin, 10),
        f"t={thickness_mm:.2f} mm   h_tol={result.height_tolerance_um:g} um",
        fill=INK,
        font=font(21),
    )

    def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
        return (
            round(margin + plot_size / 2 + point[0] / extent * plot_size / 2),
            round(46 + plot_size / 2 - point[2] / extent * plot_size / 2),
        )

    for element, face in sorted(final.items()):
        center_x = sum(point[0] for point in face.points) / 3.0
        center_z = sum(point[2] for point in face.points) / 3.0
        if math.hypot(center_x, center_z) > analysis_radius_m:
            continue
        draw.polygon(
            [pixel(point) for point in face.points],
            fill=RED if element in result.selected else BLUE,
            outline=EDGE,
            width=1,
        )
    center_x = margin + plot_size / 2
    center_y = 46 + plot_size / 2
    radius_px = PROBE_RADIUS_M / extent * plot_size / 2
    draw.ellipse(
        (center_x - radius_px, center_y - radius_px,
         center_x + radius_px, center_y + radius_px),
        outline=INK,
        width=3,
    )
    draw.text(
        (margin, 558),
        f"area={result.projected_area_mm2:.3f} mm2   faces={result.face_count}",
        fill=INK,
        font=font(16),
    )
    draw.text(
        (margin, 584),
        f"k_tol={result.curvature_tolerance_per_mm:.4f}/mm   "
        f"sigma_k={result.curvature_noise_per_mm:.4f}/mm",
        fill=INK,
        font=font(14),
    )
    return image


def analyze_case(
    attempt: Path,
    case: str,
    thickness_mm: float,
    height_tolerances_um: tuple[float, ...],
    window_diameter_mm: float,
    analysis_radius_m: float,
) -> tuple[list[dict[str, str | float | int]], list[Image.Image]]:
    preload = read_faces(attempt / "inner_preload_faces.csv")
    final = read_faces(attempt / "inner_final_faces.csv")
    metrics = patch_metrics(preload, final, window_diameter_mm)
    rows: list[dict[str, str | float | int]] = []
    panels: list[Image.Image] = []
    for tolerance in height_tolerances_um:
        result = select_planarity_region(
            preload,
            final,
            metrics,
            height_tolerance_um=tolerance,
            window_diameter_mm=window_diameter_mm,
            analysis_radius_m=analysis_radius_m,
        )
        rows.append({
            "case": case,
            "eyelid_thickness_mm": thickness_mm,
            "height_tolerance_um": tolerance,
            "window_diameter_mm": window_diameter_mm,
            "analysis_radius_mm": analysis_radius_m * 1e3,
            "projected_area_mm2": result.projected_area_mm2,
            "selected_faces": result.face_count,
            "curvature_tolerance_per_mm": result.curvature_tolerance_per_mm,
            "curvature_noise_per_mm": result.curvature_noise_per_mm,
            "curvature_baseline_per_mm": result.curvature_baseline_per_mm,
        })
        panels.append(render_panel(final, result, thickness_mm, analysis_radius_m))
    return rows, panels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--thicknesses", type=float, nargs="+", default=(0.8, 1.25, 1.6))
    parser.add_argument(
        "--height-tolerances-um", type=float, nargs="+", default=(5.0, 10.0, 15.0)
    )
    parser.add_argument("--window-diameter-mm", type=float, default=0.75)
    parser.add_argument("--analysis-radius-mm", type=float, default=3.0)
    parser.add_argument("--workers", type=int, default=3)
    cli = parser.parse_args()
    if (
        cli.workers < 1
        or cli.window_diameter_mm <= 0
        or cli.analysis_radius_mm <= PROBE_RADIUS_M * 1e3
        or any(value <= 0 for value in cli.height_tolerances_um)
    ):
        parser.error("workers, tolerances and dimensions must be positive")
    root = cli.run_root.expanduser().resolve()
    output_dir = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures" / "inner_planarity_trial"
    )
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    selected_rows = [
        row for row in manifest
        if any(abs(float(row["eyelid_thickness_mm"]) - value) < 1e-9
               for value in cli.thicknesses)
        and all((root / row["attempt_dir"] / f"inner_{state}_faces.csv").is_file()
                for state in ("preload", "final"))
    ]
    if len(selected_rows) != len(set(cli.thicknesses)):
        parser.error("not all requested thicknesses have complete inner face data")

    results: list[tuple[float, list[dict[str, str | float | int]], list[Image.Image]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                analyze_case,
                root / row["attempt_dir"],
                row["case"],
                float(row["eyelid_thickness_mm"]),
                tuple(dict.fromkeys(cli.height_tolerances_um)),
                cli.window_diameter_mm,
                cli.analysis_radius_mm * 1e-3,
            )
            for row in selected_rows
        ]
        for future in concurrent.futures.as_completed(futures):
            rows, panels = future.result()
            results.append((float(rows[0]["eyelid_thickness_mm"]), rows, panels))
    results.sort(key=lambda item: item[0])

    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows = [row for _, rows, _ in results for row in rows]
    with (output_dir / "inner_planarity_trial.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)

    tolerances = tuple(dict.fromkeys(cli.height_tolerances_um))
    canvas = Image.new(
        "RGB",
        (len(tolerances) * 590, len(results) * 620 + 58),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (20, 14),
        "INNER PLANARITY TRIAL - red: plane residual + curvature reduction; "
        "black: probe edge",
        fill=INK,
        font=font(24),
    )
    for row_index, (_, _, panels) in enumerate(results):
        for column_index, panel in enumerate(panels):
            canvas.paste(panel, (column_index * 590, 58 + row_index * 620))
    matrix = output_dir / "inner_planarity_trial_matrix.png"
    canvas.save(matrix, format="PNG", optimize=True)
    print(f"cases={len(results)} rows={len(all_rows)} matrix={matrix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
