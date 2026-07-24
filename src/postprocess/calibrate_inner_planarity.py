#!/usr/bin/env python3
"""Calibrate inner planarity parameters against closed outer contact area."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.plot_inner_planarity_trial import (
    BACKGROUND,
    INK,
    PatchMetric,
    PlanarityResult,
    font,
    patch_metrics,
    render_panel,
    select_planarity_region,
)
from src.postprocess.thickness_geometry import (
    PROBE_RADIUS_M,
    Face,
    _projected_area_inside_circle,
    read_faces,
    select_displacement_support,
)


@dataclass(frozen=True)
class ContactState:
    status: float
    pressure_pa: float
    area_m2: float


@dataclass
class CaseData:
    case: str
    thickness_mm: float
    outer_preload: dict[int, Face]
    outer_final: dict[int, Face]
    inner_preload: dict[int, Face]
    inner_final: dict[int, Face]
    contact: dict[int, ContactState]
    contact_area_mm2: float
    outer_support: frozenset[int]
    inner_support: frozenset[int]
    metrics_by_window: dict[float, tuple[list[PatchMetric], list[PatchMetric]]]


@dataclass(frozen=True)
class CurvatureAreaResult:
    effective_area_mm2: float
    unweighted_area_mm2: float
    face_count: int
    curvature_baseline_per_mm: float
    curvature_noise_per_mm: float
    contact_overlap: float
    centroid_x_mm: float
    centroid_z_mm: float
    weights: dict[int, float]


def read_contact_state(path: Path) -> dict[int, ContactState]:
    states: dict[int, ContactState] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.reader(handle), 1):
            values = [item.strip() for item in row if item.strip()]
            if not values:
                continue
            if len(values) != 4:
                raise ValueError(f"{path.name}:{line_number}: expected four values")
            element_value, status, pressure, area = (float(value) for value in values)
            element = int(round(element_value))
            if abs(element_value - element) > 1e-6 or element in states:
                raise ValueError(f"{path.name}:{line_number}: invalid element identifier")
            if not all(math.isfinite(value) for value in (status, pressure, area)):
                raise ValueError(f"{path.name}:{line_number}: non-finite contact value")
            states[element] = ContactState(status, pressure, area)
    if not states:
        raise ValueError(f"{path.name}: no contact states")
    return states


def _adjacency(faces: dict[int, Face]) -> dict[int, set[int]]:
    owners: dict[tuple[int, int], list[int]] = {}
    for element, face in faces.items():
        for first, second in (
            (face.nodes[0], face.nodes[1]),
            (face.nodes[1], face.nodes[2]),
            (face.nodes[2], face.nodes[0]),
        ):
            owners.setdefault(tuple(sorted((first, second))), []).append(element)
    result = {element: set() for element in faces}
    for elements in owners.values():
        for element in elements:
            result[element].update(other for other in elements if other != element)
    return result


def contact_interior(
    faces: dict[int, Face], contact: dict[int, ContactState]
) -> set[int]:
    closed = {
        element for element, state in contact.items()
        if state.status >= 2.0 and state.area_m2 > 0 and element in faces
    }
    adjacency = _adjacency(faces)
    interior = {
        element for element in closed
        if adjacency[element] and adjacency[element].issubset(closed)
    }
    return interior or closed


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    if len(values) == 0 or values.shape != weights.shape or not 0 <= quantile <= 1:
        raise ValueError("invalid weighted quantile inputs")
    order = np.argsort(values)
    ordered_values = values[order]
    cumulative = np.cumsum(weights[order])
    target = quantile * float(cumulative[-1])
    return float(ordered_values[min(int(np.searchsorted(cumulative, target)), len(values) - 1)])


def numerical_plane_floor_um(
    cases: list[CaseData], window_mm: float
) -> tuple[float, float, float, int]:
    values: list[float] = []
    weights: list[float] = []
    for case in cases:
        outer_metrics = case.metrics_by_window[window_mm][0]
        by_element = {metric.element: metric for metric in outer_metrics}
        for element in contact_interior(case.outer_final, case.contact):
            if element not in by_element:
                continue
            values.append(by_element[element].final_plane_rms_mm * 1e3)
            weights.append(max(case.contact[element].area_m2, 1e-18))
    array = np.asarray(values, dtype=float)
    area_weights = np.asarray(weights, dtype=float)
    median = weighted_quantile(array, area_weights, 0.5)
    p95 = weighted_quantile(array, area_weights, 0.95)
    mad = 1.4826 * float(np.median(np.abs(array - np.median(array))))
    return median, p95, mad, len(array)


def curvature_reduction_area(
    final: dict[int, Face],
    metrics: list[PatchMetric],
    support: set[int] | frozenset[int],
    *,
    height_tolerance_um: float,
    measurement_radius_m: float = PROBE_RADIUS_M,
    closed_contact: set[int] | frozenset[int] = frozenset(),
) -> CurvatureAreaResult:
    """Integrate significant fractional curvature loss over the central support."""
    if height_tolerance_um <= 0 or measurement_radius_m <= 0:
        raise ValueError("height tolerance and measurement radius must be positive")
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
    centered = reduction[annulus] - baseline
    noise = 1.4826 * float(np.median(np.abs(centered - np.median(centered))))
    significance = max(3.0 * noise, 1e-6)
    height_limit_mm = height_tolerance_um * 1e-3

    effective_area = 0.0
    unweighted_area = 0.0
    contact_area = 0.0
    first_x = 0.0
    first_z = 0.0
    weights: dict[int, float] = {}
    for metric in metrics:
        element = metric.element
        delta = metric.curvature_reduction_per_mm - baseline
        if (
            element not in support
            or metric.final_plane_rms_mm > height_limit_mm
            or delta <= significance
        ):
            continue
        denominator = max(metric.preload_curvature_per_mm, significance)
        weight = min(1.0, max(0.0, delta / denominator))
        if weight <= 0:
            continue
        points = tuple((point[0], point[2]) for point in final[element].points)
        projected = _projected_area_inside_circle(points, measurement_radius_m)
        if projected <= 0:
            continue
        weighted = weight * projected
        center_x = sum(point[0] for point in final[element].points) / 3.0
        center_z = sum(point[2] for point in final[element].points) / 3.0
        effective_area += weighted
        unweighted_area += projected
        first_x += center_x * weighted
        first_z += center_z * weighted
        if element in closed_contact:
            contact_area += weighted
        weights[element] = weight
    centroid_x = first_x / effective_area if effective_area > 0 else math.nan
    centroid_z = first_z / effective_area if effective_area > 0 else math.nan
    return CurvatureAreaResult(
        effective_area_mm2=effective_area * 1e6,
        unweighted_area_mm2=unweighted_area * 1e6,
        face_count=len(weights),
        curvature_baseline_per_mm=baseline,
        curvature_noise_per_mm=noise,
        contact_overlap=contact_area / effective_area if effective_area > 0 else math.nan,
        centroid_x_mm=centroid_x * 1e3,
        centroid_z_mm=centroid_z * 1e3,
        weights=weights,
    )


def load_case(
    root: Path,
    row: dict[str, str],
    windows_mm: tuple[float, ...],
    analysis_radius_m: float,
) -> CaseData:
    attempt = root / row["attempt_dir"]
    outer_preload = read_faces(attempt / "outer_preload_faces.csv")
    outer_final = read_faces(attempt / "outer_final_faces.csv")
    inner_preload = read_faces(attempt / "inner_preload_faces.csv")
    inner_final = read_faces(attempt / "inner_final_faces.csv")
    contact = read_contact_state(attempt / "outer_contact_state.csv")
    closed = [state for state in contact.values() if state.status >= 2.0]
    contact_area = sum(state.area_m2 for state in closed) * 1e6
    _, outer_support = select_displacement_support(
        outer_preload, outer_final, maximum_radius=analysis_radius_m
    )
    _, inner_support = select_displacement_support(
        inner_preload, inner_final, maximum_radius=analysis_radius_m
    )
    metrics_by_window = {
        window: (
            patch_metrics(outer_preload, outer_final, window),
            patch_metrics(inner_preload, inner_final, window),
        )
        for window in windows_mm
    }
    return CaseData(
        case=row["case"],
        thickness_mm=float(row["eyelid_thickness_mm"]),
        outer_preload=outer_preload,
        outer_final=outer_final,
        inner_preload=inner_preload,
        inner_final=inner_final,
        contact=contact,
        contact_area_mm2=contact_area,
        outer_support=frozenset(outer_support),
        inner_support=frozenset(inner_support),
        metrics_by_window=metrics_by_window,
    )


def evaluate_pair(
    cases: list[CaseData],
    window_mm: float,
    tolerance_um: float,
    analysis_radius_m: float,
) -> tuple[
    dict[str, float | int],
    list[tuple[CaseData, PlanarityResult, CurvatureAreaResult]],
]:
    results: list[tuple[CaseData, PlanarityResult, CurvatureAreaResult]] = []
    binary_errors: list[float] = []
    curvature_errors: list[float] = []
    for case in cases:
        outer_metrics = case.metrics_by_window[window_mm][0]
        binary = select_planarity_region(
            case.outer_preload,
            case.outer_final,
            outer_metrics,
            height_tolerance_um=tolerance_um,
            window_diameter_mm=window_mm,
            analysis_radius_m=analysis_radius_m,
            displacement_support=case.outer_support,
        )
        closed = frozenset(
            element for element, state in case.contact.items()
            if state.status >= 2.0 and state.area_m2 > 0
        )
        curvature = curvature_reduction_area(
            case.outer_final,
            outer_metrics,
            case.outer_support,
            height_tolerance_um=tolerance_um,
            closed_contact=closed,
        )
        binary_errors.append(
            abs(binary.projected_area_mm2 - case.contact_area_mm2)
            / case.contact_area_mm2
        )
        curvature_errors.append(
            abs(curvature.effective_area_mm2 - case.contact_area_mm2)
            / case.contact_area_mm2
        )
        results.append((case, binary, curvature))
    floor_median, floor_p95, floor_mad, floor_count = numerical_plane_floor_um(
        cases, window_mm
    )
    row: dict[str, float | int] = {
        "window_diameter_mm": window_mm,
        "height_tolerance_um": tolerance_um,
        "outer_mean_absolute_relative_error": float(np.mean(curvature_errors)),
        "outer_rms_relative_error": math.sqrt(
            float(np.mean(np.square(curvature_errors)))
        ),
        "outer_max_relative_error": max(curvature_errors),
        "outer_binary_mean_relative_error": float(np.mean(binary_errors)),
        "outer_mean_contact_overlap": float(np.mean([
            result.contact_overlap for _, _, result in results
        ])),
        "outer_plane_floor_median_um": floor_median,
        "outer_plane_floor_p95_um": floor_p95,
        "outer_plane_floor_mad_um": floor_mad,
        "outer_plane_floor_face_count": floor_count,
        "above_numerical_floor": int(tolerance_um >= floor_p95),
    }
    return row, results


def render_heatmap(
    path: Path,
    rows: list[dict[str, float | int]],
    windows: tuple[float, ...],
    tolerances: tuple[float, ...],
    selected: tuple[float, float],
) -> None:
    cell_w, cell_h = 112, 62
    left, top = 150, 72
    image = Image.new(
        "RGB", (left + len(tolerances) * cell_w + 20, top + len(windows) * cell_h + 50),
        "white",
    )
    draw = ImageDraw.Draw(image)
    draw.text((18, 14), "OUTER CONTACT CALIBRATION - mean absolute relative error", fill=INK, font=font(22))
    indexed = {
        (float(row["window_diameter_mm"]), float(row["height_tolerance_um"])): row
        for row in rows
    }
    for column, tolerance in enumerate(tolerances):
        draw.text((left + column * cell_w + 26, 46), f"{tolerance:g} um", fill=INK, font=font(14))
    for row_index, window in enumerate(windows):
        y = top + row_index * cell_h
        draw.text((16, y + 20), f"window {window:g} mm", fill=INK, font=font(15))
        for column, tolerance in enumerate(tolerances):
            x = left + column * cell_w
            item = indexed[(window, tolerance)]
            error = float(item["outer_mean_absolute_relative_error"])
            strength = min(1.0, error / 0.5)
            color = (
                round(235 * strength + 220 * (1 - strength)),
                round(90 * strength + 238 * (1 - strength)),
                round(80 * strength + 225 * (1 - strength)),
            )
            draw.rectangle((x, y, x + cell_w - 4, y + cell_h - 4), fill=color)
            draw.text((x + 22, y + 18), f"{error * 100:.1f}%", fill=INK, font=font(16))
            if (window, tolerance) == selected:
                draw.rectangle((x, y, x + cell_w - 4, y + cell_h - 4), outline=INK, width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def render_area_chart(path: Path, rows: list[dict[str, float | int]]) -> None:
    width, height = 920, 560
    left, top, plot_w, plot_h = 85, 55, 785, 410
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((25, 14), "CURVATURE-REDUCTION AREA AND OUTER CONTACT", fill=INK, font=font(22))
    thicknesses = [float(row["eyelid_thickness_mm"]) for row in rows]
    max_area = math.ceil(max(
        max(
            float(row["inner_curvature_area_mm2"]),
            float(row["outer_curvature_area_mm2"]),
            float(row["outer_contact_area_mm2"]),
        )
        for row in rows
    ) / 2.0) * 2.0
    x_min, x_max = min(thicknesses), max(thicknesses)

    def pixel(x: float, y: float) -> tuple[int, int]:
        return (
            round(left + (x - x_min) / max(x_max - x_min, 1e-9) * plot_w),
            round(top + plot_h - y / max_area * plot_h),
        )

    for fraction in np.linspace(0, 1, 5):
        y = top + plot_h - fraction * plot_h
        draw.line((left, y, left + plot_w, y), fill=(220, 224, 230), width=1)
        draw.text((32, y - 8), f"{fraction * max_area:.1f}", fill=INK, font=font(13))
    colors = (
        ("outer_contact_area_mm2", (45, 95, 175), "outer contact"),
        ("outer_curvature_area_mm2", (22, 145, 122), "outer curvature"),
        ("inner_curvature_area_mm2", (211, 55, 48), "inner curvature"),
    )
    for field, color, label in colors:
        points = [pixel(float(row["eyelid_thickness_mm"]), float(row[field])) for row in rows]
        draw.line(points, fill=color, width=4)
        for point in points:
            draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=color)
        legend_x = {
            "outer_contact_area_mm2": 450,
            "outer_curvature_area_mm2": 610,
            "inner_curvature_area_mm2": 760,
        }[field]
        draw.line((legend_x, 30, legend_x + 26, 30), fill=color, width=4)
        draw.text((legend_x + 32, 21), label, fill=INK, font=font(13))
    for row in rows:
        x = pixel(float(row["eyelid_thickness_mm"]), 0)[0]
        draw.text((x - 13, top + plot_h + 10), f"{float(row['eyelid_thickness_mm']):g}", fill=INK, font=font(13))
    draw.text((left + 320, height - 46), "eyelid thickness (mm)", fill=INK, font=font(15))
    draw.text((12, top + 180), "area mm2", fill=INK, font=font(14))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--windows-mm", type=float, nargs="+", default=(0.6, 0.75, 0.9, 1.0))
    parser.add_argument("--tolerance-min-um", type=float, default=5.0)
    parser.add_argument("--tolerance-max-um", type=float, default=10.0)
    parser.add_argument("--tolerance-step-um", type=float, default=0.5)
    parser.add_argument("--analysis-radius-mm", type=float, default=3.0)
    parser.add_argument("--workers", type=int, default=4)
    cli = parser.parse_args()
    if (
        cli.workers < 1
        or any(window <= 0 for window in cli.windows_mm)
        or cli.tolerance_min_um <= 0
        or cli.tolerance_max_um < cli.tolerance_min_um
        or cli.tolerance_step_um <= 0
    ):
        parser.error("invalid positive calibration range")
    root = cli.run_root.expanduser().resolve()
    output_dir = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures" / "inner_planarity_calibration"
    )
    windows = tuple(dict.fromkeys(cli.windows_mm))
    tolerances = tuple(float(value) for value in np.arange(
        cli.tolerance_min_um,
        cli.tolerance_max_um + 0.5 * cli.tolerance_step_um,
        cli.tolerance_step_um,
    ))
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [
            row for row in csv.DictReader(handle)
            if row.get("status") == "complete"
            and all((root / row["attempt_dir"] / filename).is_file() for filename in (
                "outer_preload_faces.csv", "outer_final_faces.csv",
                "inner_preload_faces.csv", "inner_final_faces.csv",
                "outer_contact_state.csv",
            ))
        ]
    if not manifest:
        parser.error("no complete cases with face and contact-state data")
    analysis_radius_m = cli.analysis_radius_mm * 1e-3
    cases: list[CaseData] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(load_case, root, row, windows, analysis_radius_m)
            for row in manifest
        ]
        for future in concurrent.futures.as_completed(futures):
            cases.append(future.result())
    cases.sort(key=lambda case: case.thickness_mm)

    grid: list[dict[str, float | int]] = []
    outer_results: dict[
        tuple[float, float],
        list[tuple[CaseData, PlanarityResult, CurvatureAreaResult]],
    ] = {}
    for window in windows:
        for tolerance in tolerances:
            row, results = evaluate_pair(
                cases, window, tolerance, analysis_radius_m
            )
            grid.append(row)
            outer_results[(window, tolerance)] = results
    eligible = [row for row in grid if int(row["above_numerical_floor"]) == 1]
    if not eligible:
        raise ValueError("the requested tolerance range is below the outer numerical floor")
    best = min(eligible, key=lambda row: (
        float(row["outer_rms_relative_error"]),
        float(row["outer_max_relative_error"]),
        abs(float(row["window_diameter_mm"]) - 0.75),
    ))
    selected_window = float(best["window_diameter_mm"])
    selected_tolerance = float(best["height_tolerance_um"])

    rows: list[dict[str, float | int | str]] = []
    inner_results: list[tuple[CaseData, PlanarityResult]] = []
    selected_outer = {
        case.case: (binary, curvature)
        for case, binary, curvature
        in outer_results[(selected_window, selected_tolerance)]
    }
    for case in cases:
        result = select_planarity_region(
            case.inner_preload,
            case.inner_final,
            case.metrics_by_window[selected_window][1],
            height_tolerance_um=selected_tolerance,
            window_diameter_mm=selected_window,
            analysis_radius_m=analysis_radius_m,
            displacement_support=case.inner_support,
        )
        inner_results.append((case, result))
        inner_curvature = curvature_reduction_area(
            case.inner_final,
            case.metrics_by_window[selected_window][1],
            case.inner_support,
            height_tolerance_um=selected_tolerance,
        )
        outer_binary, outer_curvature = selected_outer[case.case]
        rows.append({
            "case": case.case,
            "eyelid_thickness_mm": case.thickness_mm,
            "selected_window_diameter_mm": selected_window,
            "selected_height_tolerance_um": selected_tolerance,
            "outer_contact_area_mm2": case.contact_area_mm2,
            "outer_binary_area_mm2": outer_binary.projected_area_mm2,
            "outer_curvature_area_mm2": outer_curvature.effective_area_mm2,
            "outer_relative_error": (
                abs(outer_curvature.effective_area_mm2 - case.contact_area_mm2)
                / case.contact_area_mm2
            ),
            "outer_contact_overlap": outer_curvature.contact_overlap,
            "inner_binary_area_mm2": result.projected_area_mm2,
            "inner_curvature_area_mm2": inner_curvature.effective_area_mm2,
            "inner_unweighted_candidate_area_mm2": inner_curvature.unweighted_area_mm2,
            "inner_selected_faces": inner_curvature.face_count,
            "ae_over_ac_curvature": (
                outer_curvature.effective_area_mm2
                / inner_curvature.effective_area_mm2
                if inner_curvature.effective_area_mm2 > 0 else ""
            ),
            "inner_centroid_x_mm": inner_curvature.centroid_x_mm,
            "inner_centroid_z_mm": inner_curvature.centroid_z_mm,
            "status": "candidate_not_approved",
        })
    write_csv(output_dir / "calibration_grid.csv", grid)
    write_csv(output_dir / "inner_planarity_candidate.csv", rows)
    render_heatmap(
        output_dir / "outer_contact_calibration_heatmap.png",
        grid,
        windows,
        tolerances,
        (selected_window, selected_tolerance),
    )
    render_area_chart(output_dir / "calibrated_area_vs_thickness.png", rows)

    representatives = [
        item for item in inner_results
        if any(abs(item[0].thickness_mm - value) < 1e-9 for value in (0.8, 1.25, 1.6))
    ]
    canvas = Image.new("RGB", (len(representatives) * 590, 678), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (18, 14),
        f"CONTACT-CALIBRATED INNER PLANARITY CANDIDATE   "
        f"window={selected_window:g} mm   h_tol={selected_tolerance:g} um",
        fill=INK,
        font=font(24),
    )
    for index, (case, result) in enumerate(representatives):
        canvas.paste(
            render_panel(case.inner_final, result, case.thickness_mm, analysis_radius_m),
            (index * 590, 58),
        )
    canvas.save(
        output_dir / "inner_planarity_candidate_matrix.png",
        format="PNG",
        optimize=True,
    )
    print(
        f"cases={len(cases)} selected_window_mm={selected_window:g} "
        f"selected_tolerance_um={selected_tolerance:g} "
        f"outer_mean_error={float(best['outer_mean_absolute_relative_error']):.6f} "
        f"output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
