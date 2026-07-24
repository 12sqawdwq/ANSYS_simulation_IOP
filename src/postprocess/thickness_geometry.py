#!/usr/bin/env python3
"""Compute diagnostic angle-threshold and radial-breakpoint area metrics."""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import minimize_scalar


ANGLE_LIMITS_DEG = (1.0, 2.0, 3.0)
DISPLACEMENT_FRACTION = 0.05
PROBE_RADIUS_M = 2.16e-3
PROBE_AREA_M2 = math.pi * PROBE_RADIUS_M**2
RADIAL_BIN_M = 0.15e-3
ABSOLUTE_NOISE_M = 1.0e-6
RELATIVE_NOISE = 0.02
FIT_WINDOW_SCALES = (0.90, 0.95, 1.00)
BREAK_METHOD_CODES = {"inflection": 1, "segmented_fit": 2, "probe_edge": 3}
GEOMETRY_FIELDS = (
    # Legacy angle-threshold fields retained for traceability.
    "inner_max_downward_m",
    "inner_effect_area_m2",
    "inner_area_1deg_m2",
    "inner_area_2deg_m2",
    "inner_area_3deg_m2",
    "inner_face_count",
    "inner_area_smooth_2deg_m2",
    "inner_smooth_2deg_face_count",
    # Diagnostic central connected angle-threshold regions.
    "outer_flat_projected_area_1deg_m2",
    "outer_flat_projected_area_2deg_m2",
    "outer_flat_projected_area_3deg_m2",
    "outer_flat_surface_area_2deg_m2",
    "outer_flat_face_count_2deg",
    "outer_flat_displacement_threshold_m",
    "inner_flat_projected_area_1deg_m2",
    "inner_flat_projected_area_2deg_m2",
    "inner_flat_projected_area_3deg_m2",
    "inner_flat_surface_area_2deg_m2",
    "inner_flat_face_count_2deg",
    "inner_flat_displacement_threshold_m",
    # Breakpoint-based outer and inner surface metrics.
    "outer_local_max_downward_m",
    "outer_surface_area_m2",
    "outer_projected_area_m2",
    "outer_break_radius_m",
    "outer_break_method_code",
    "outer_threshold_m",
    "outer_area_sensitivity_fraction",
    "outer_diameter_sensitivity_m",
    "outer_face_count",
    "inner_local_max_downward_m",
    "inner_surface_area_m2",
    "inner_projected_area_m2",
    "inner_break_radius_m",
    "inner_break_method_code",
    "inner_threshold_m",
    "inner_area_sensitivity_fraction",
    "inner_diameter_sensitivity_m",
)


@dataclass(frozen=True)
class Face:
    element: int
    nodes: tuple[int, int, int]
    points: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class SurfaceRecord:
    radius: float
    downward: float
    final_height: float
    surface_area: float
    projected_area: float
    face: Face


@dataclass(frozen=True)
class BreakpointResult:
    radius: float
    method: str
    threshold: float
    local_max: float
    surface_area: float
    projected_area: float


@dataclass(frozen=True)
class FlatAreaResult:
    projected_area: float
    surface_area: float
    face_count: int
    displacement_threshold: float


@dataclass(frozen=True)
class DisplacementSupportResult:
    """Diagnostic support selected only by robust local displacement."""

    projected_area: float
    surface_area: float
    face_count: int
    displacement_threshold: float
    baseline: float
    noise_sigma: float
    local_max: float


def _vector(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return b[0] - a[0], b[1] - a[1], b[2] - a[2]


def _cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def read_faces(path: Path) -> dict[int, Face]:
    faces: dict[int, Face] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.reader(handle), 1):
            values = [item.strip() for item in row if item.strip()]
            if not values:
                continue
            if len(values) != 13:
                raise ValueError(
                    f"{path.name}:{line_number}: expected 13 values, found {len(values)}"
                )
            parsed = [float(item) for item in values]
            if not all(math.isfinite(item) for item in parsed):
                raise ValueError(f"{path.name}:{line_number}: non-finite value")
            identifiers = tuple(int(round(item)) for item in parsed[:4])
            if any(abs(parsed[index] - identifiers[index]) > 1e-6 for index in range(4)):
                raise ValueError(
                    f"{path.name}:{line_number}: non-integral element or node identifier"
                )
            element, n1, n2, n3 = identifiers
            if element in faces:
                raise ValueError(f"{path.name}:{line_number}: duplicate element {element}")
            points = tuple(tuple(parsed[start:start + 3]) for start in (4, 7, 10))
            faces[element] = Face(element, (n1, n2, n3), points)
    if not faces:
        raise ValueError(f"{path.name}: no interface faces")
    return faces


def _face_normal(face: Face) -> tuple[tuple[float, float, float], float]:
    edge1 = _vector(face.points[0], face.points[1])
    edge2 = _vector(face.points[0], face.points[2])
    normal = _cross(edge1, edge2)
    magnitude = math.sqrt(sum(component * component for component in normal))
    if magnitude <= 0:
        raise ValueError(f"element {face.element} has zero deformed area")
    if normal[1] < 0:
        normal = tuple(-component for component in normal)
    return normal, magnitude


def _normal_angle(normal: tuple[float, float, float]) -> float:
    magnitude = math.sqrt(sum(component * component for component in normal))
    if magnitude <= 0:
        raise ValueError("smoothed surface normal has zero magnitude")
    axis_cosine = min(1.0, max(0.0, abs(normal[1]) / magnitude))
    return math.degrees(math.acos(axis_cosine))


def _face_geometry(face: Face) -> tuple[float, float, float]:
    normal, magnitude = _face_normal(face)
    return 0.5 * magnitude, 0.5 * abs(normal[1]), _normal_angle(normal)


def _smoothed_face_angles(faces: dict[int, Face]) -> dict[int, float]:
    node_normals: dict[int, list[float]] = {}
    for face in faces.values():
        normal, _ = _face_normal(face)
        for node in face.nodes:
            accumulated = node_normals.setdefault(node, [0.0, 0.0, 0.0])
            for index, component in enumerate(normal):
                accumulated[index] += component

    unit_node_normals: dict[int, tuple[float, float, float]] = {}
    for node, normal in node_normals.items():
        magnitude = math.sqrt(sum(component * component for component in normal))
        if magnitude <= 0:
            raise ValueError(f"node {node} has zero smoothed normal")
        unit_node_normals[node] = tuple(component / magnitude for component in normal)

    angles: dict[int, float] = {}
    for element, face in faces.items():
        normal = tuple(
            sum(unit_node_normals[node][index] for node in face.nodes)
            for index in range(3)
        )
        angles[element] = _normal_angle(normal)
    return angles


def analyze_faces(
    preload: dict[int, Face],
    final: dict[int, Face],
    displacement_fraction: float = DISPLACEMENT_FRACTION,
) -> dict[str, float | int]:
    """Return the legacy angle-threshold metrics for the inner interface."""
    _validate_face_sets(preload, final)
    if not 0 < displacement_fraction < 1:
        raise ValueError("displacement_fraction must be between 0 and 1")

    smooth_angles = _smoothed_face_angles(final)
    records: list[tuple[float, float, float, float]] = []
    for element in sorted(preload):
        before = preload[element]
        after = final[element]
        preload_y = sum(point[1] for point in before.points) / 3.0
        final_y = sum(point[1] for point in after.points) / 3.0
        downward = preload_y - final_y
        _, projected_area, angle_deg = _face_geometry(after)
        records.append((downward, projected_area, angle_deg, smooth_angles[element]))

    max_downward = max(record[0] for record in records)
    if max_downward <= 0:
        raise ValueError("interface has no positive indentation-induced downward displacement")
    displacement_limit = displacement_fraction * max_downward
    affected = [record for record in records if record[0] >= displacement_limit]
    if not affected:
        raise ValueError("geometric effect-region selection is empty")

    metrics: dict[str, float | int] = {
        "inner_max_downward_m": max_downward,
        "inner_effect_area_m2": sum(record[1] for record in affected),
        "inner_face_count": len(records),
    }
    for angle in ANGLE_LIMITS_DEG:
        metrics[f"inner_area_{int(angle)}deg_m2"] = sum(
            projected_area
            for _, projected_area, angle_deg, _ in affected
            if angle_deg <= angle
        )
    smooth_2deg = [
        projected_area
        for _, projected_area, _, smooth_angle_deg in affected
        if smooth_angle_deg <= 2.0
    ]
    metrics["inner_area_smooth_2deg_m2"] = sum(smooth_2deg)
    metrics["inner_smooth_2deg_face_count"] = len(smooth_2deg)
    return metrics


def _validate_face_sets(preload: dict[int, Face], final: dict[int, Face]) -> None:
    if preload.keys() != final.keys():
        missing_preload = sorted(final.keys() - preload.keys())
        missing_final = sorted(preload.keys() - final.keys())
        raise ValueError(
            "preload/final element sets differ: "
            f"missing_preload={missing_preload[:5]} missing_final={missing_final[:5]}"
        )
    for element in preload:
        if preload[element].nodes != final[element].nodes:
            raise ValueError(f"element {element} node ordering differs between result sets")


def _surface_records(
    preload: dict[int, Face], final: dict[int, Face]
) -> list[SurfaceRecord]:
    _validate_face_sets(preload, final)
    records: list[SurfaceRecord] = []
    for element in sorted(preload):
        before = preload[element]
        after = final[element]
        preload_y = sum(point[1] for point in before.points) / 3.0
        final_y = sum(point[1] for point in after.points) / 3.0
        center_x = sum(point[0] for point in after.points) / 3.0
        center_z = sum(point[2] for point in after.points) / 3.0
        surface_area, projected_area, _ = _face_geometry(after)
        records.append(SurfaceRecord(
            math.hypot(center_x, center_z),
            preload_y - final_y,
            final_y,
            surface_area,
            projected_area,
            after,
        ))
    return records


def _weighted_radial_profile(
    records: list[SurfaceRecord], bin_width: float, relative_noise: float
) -> tuple[np.ndarray, np.ndarray, float, float]:
    radii = np.asarray([record.radius for record in records], dtype=float)
    downward = np.asarray([record.downward for record in records], dtype=float)
    weights = np.asarray([record.surface_area for record in records], dtype=float)
    outer_mask = radii >= 0.8 * float(np.max(radii))
    if int(np.count_nonzero(outer_mask)) < 3:
        outer_mask = radii >= float(np.quantile(radii, 0.8))
    baseline = float(np.median(downward[outer_mask]))
    outer_residual = downward[outer_mask] - baseline
    noise_sigma = 1.4826 * float(np.median(np.abs(
        outer_residual - np.median(outer_residual)
    )))
    local = np.maximum(downward - baseline, 0.0)
    local_max = float(np.max(local))
    if local_max <= 0:
        raise ValueError("surface has no positive local indentation displacement")
    threshold = max(3.0 * noise_sigma, relative_noise * local_max, ABSOLUTE_NOISE_M)

    indices = np.floor(radii / bin_width).astype(int)
    count = int(np.max(indices)) + 1
    area_by_bin = np.bincount(indices, weights=weights, minlength=count)
    displacement_by_bin = np.bincount(indices, weights=weights * local, minlength=count)
    valid = area_by_bin > 0
    bin_centers = (np.arange(count, dtype=float) + 0.5) * bin_width
    return (
        bin_centers[valid],
        displacement_by_bin[valid] / area_by_bin[valid],
        threshold,
        local_max,
    )


def _support_end(radii: np.ndarray, values: np.ndarray, threshold: float) -> int:
    peak = int(np.argmax(values))
    seen_high = False
    low_run = 0
    end = len(values) - 1
    for index in range(peak, len(values)):
        if values[index] >= threshold:
            seen_high = True
            low_run = 0
        elif seen_high:
            low_run += 1
            if low_run >= 2:
                end = max(peak + 2, index - 2)
                break
    return min(end, len(radii) - 1)


def _segmented_surface_break(
    records: list[SurfaceRecord], maximum_radius: float
) -> float:
    selected = [record for record in records if record.radius <= maximum_radius]
    if len(selected) < 12:
        raise ValueError("too few surface faces to identify an applanation breakpoint")
    radii = np.asarray([record.radius for record in selected], dtype=float)
    heights = np.asarray([record.final_height for record in selected], dtype=float)
    weights = np.asarray([record.surface_area for record in selected], dtype=float)
    lower = max(float(np.quantile(radii, 0.08)), 0.25e-3)
    upper = min(float(np.quantile(radii, 0.92)), maximum_radius - 0.25e-3)
    if upper <= lower:
        raise ValueError("surface support is too narrow for segmented breakpoint detection")

    # Radius columns are scaled to millimetres to keep the weighted least-squares
    # system well conditioned while preserving heights in model units.
    radius_scale = 1e3

    def fit(knot: float) -> tuple[float, np.ndarray]:
        matrix = np.column_stack((
            np.ones_like(radii),
            radii * radius_scale,
            np.maximum(0.0, radii - knot) * radius_scale,
        ))
        root_weight = np.sqrt(weights)
        coefficients, _, _, _ = np.linalg.lstsq(
            matrix * root_weight[:, None], heights * root_weight, rcond=None
        )
        residual = heights - matrix @ coefficients
        return float(np.dot(weights, residual * residual)), coefficients

    optimum = minimize_scalar(
        lambda knot: fit(float(knot))[0],
        bounds=(lower, upper),
        method="bounded",
        options={"xatol": 1e-9},
    )
    if not optimum.success or not math.isfinite(float(optimum.x)):
        raise ValueError("segmented breakpoint optimization failed")
    radius = float(optimum.x)
    _, coefficients = fit(radius)
    central_slope = float(coefficients[1])
    outer_slope = float(coefficients[1] + coefficients[2])
    if abs(outer_slope) < 1.2 * max(abs(central_slope), 1e-12):
        raise ValueError("surface does not contain a distinct central flat-to-curved transition")
    return radius


def _break_radius(
    records: list[SurfaceRecord],
    bin_width: float,
    relative_noise: float,
    maximum_radius: float | None,
) -> tuple[float, str, float, float]:
    radii, values, threshold, local_max = _weighted_radial_profile(
        records, bin_width, relative_noise
    )
    end = _support_end(radii, values, threshold)
    support_radius = float(radii[end]) + 0.5 * bin_width
    fitting_radius = min(
        support_radius,
        maximum_radius if maximum_radius is not None else PROBE_RADIUS_M,
    )
    if fitting_radius < 0.75e-3:
        raise ValueError("too few radial bins to identify an applanation breakpoint")
    try:
        radius = _segmented_surface_break(records, fitting_radius)
        if radius >= fitting_radius - 0.27e-3:
            radius = fitting_radius
            method = "probe_edge"
        else:
            method = "segmented_fit"
    except ValueError as error:
        if "distinct central flat-to-curved transition" not in str(error):
            raise
        radius = fitting_radius
        method = "probe_edge"
    if radius <= 0:
        raise ValueError("computed applanation breakpoint is non-positive")
    return radius, method, threshold, local_max


def _area2(points: tuple[tuple[float, float], ...]) -> float:
    (x1, z1), (x2, z2), (x3, z3) = points
    return 0.5 * abs((x2 - x1) * (z3 - z1) - (z2 - z1) * (x3 - x1))


def _distance_to_segment(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    dx, dz = end[0] - start[0], end[1] - start[1]
    length2 = dx * dx + dz * dz
    if length2 <= 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    fraction = max(0.0, min(1.0, (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dz
    ) / length2))
    nearest = start[0] + fraction * dx, start[1] + fraction * dz
    return math.hypot(point[0] - nearest[0], point[1] - nearest[1])


def _origin_in_triangle(points: tuple[tuple[float, float], ...]) -> bool:
    signs = []
    for start, end in zip(points, (*points[1:], points[0])):
        signs.append(start[0] * end[1] - end[0] * start[1])
    return all(value >= -1e-18 for value in signs) or all(value <= 1e-18 for value in signs)


def _triangle_misses_circle(
    points: tuple[tuple[float, float], ...], radius: float
) -> bool:
    if _origin_in_triangle(points):
        return False
    distance = min(
        _distance_to_segment((0.0, 0.0), start, end)
        for start, end in zip(points, (*points[1:], points[0]))
    )
    return distance >= radius


def _subdivide(points: tuple[tuple[float, float], ...]) -> tuple[tuple[tuple[float, float], ...], ...]:
    a, b, c = points
    ab = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    bc = ((b[0] + c[0]) / 2.0, (b[1] + c[1]) / 2.0)
    ca = ((c[0] + a[0]) / 2.0, (c[1] + a[1]) / 2.0)
    return (a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)


def _projected_area_inside_circle(
    points: tuple[tuple[float, float], ...], radius: float, depth: int = 6
) -> float:
    area = _area2(points)
    if area <= 0:
        return 0.0
    inside = [x * x + z * z <= radius * radius for x, z in points]
    if all(inside):
        return area
    if not any(inside) and _triangle_misses_circle(points, radius):
        return 0.0
    if depth <= 0:
        samples = [*points, (
            sum(point[0] for point in points) / 3.0,
            sum(point[1] for point in points) / 3.0,
        )]
        fraction = sum(x * x + z * z <= radius * radius for x, z in samples) / len(samples)
        return fraction * area
    return sum(
        _projected_area_inside_circle(child, radius, depth - 1)
        for child in _subdivide(points)
    )


def _integrate_disk(records: list[SurfaceRecord], radius: float) -> tuple[float, float]:
    surface_area = 0.0
    projected_area = 0.0
    for record in records:
        points = tuple((point[0], point[2]) for point in record.face.points)
        total_projected = _area2(points)
        if total_projected <= 0:
            continue
        clipped_projected = _projected_area_inside_circle(points, radius)
        fraction = min(1.0, max(0.0, clipped_projected / total_projected))
        projected_area += clipped_projected
        surface_area += fraction * record.surface_area
    return surface_area, projected_area


def _central_connected_elements(
    faces: dict[int, Face], candidates: set[int]
) -> set[int]:
    """Return the candidate component nearest the probe axis."""
    if not candidates:
        return set()
    edge_owners: dict[tuple[int, int], list[int]] = {}
    for element in candidates:
        nodes = faces[element].nodes
        for first, second in ((nodes[0], nodes[1]), (nodes[1], nodes[2]), (nodes[2], nodes[0])):
            edge_owners.setdefault(tuple(sorted((first, second))), []).append(element)
    adjacency = {element: set() for element in candidates}
    for owners in edge_owners.values():
        if len(owners) < 2:
            continue
        for element in owners:
            adjacency[element].update(owner for owner in owners if owner != element)

    def center_radius(element: int) -> float:
        face = faces[element]
        x = sum(point[0] for point in face.points) / 3.0
        z = sum(point[2] for point in face.points) / 3.0
        return math.hypot(x, z)

    seed = min(candidates, key=center_radius)
    connected = {seed}
    pending = [seed]
    while pending:
        element = pending.pop()
        for neighbor in adjacency[element] - connected:
            connected.add(neighbor)
            pending.append(neighbor)
    return connected


def select_displacement_support(
    preload: dict[int, Face],
    final: dict[int, Face],
    *,
    maximum_radius: float = PROBE_RADIUS_M,
    absolute_noise: float = ABSOLUTE_NOISE_M,
) -> tuple[DisplacementSupportResult, set[int]]:
    """Return the central support above the robust displacement noise floor.

    This is a diagnostic participation map. It deliberately applies no surface
    normal or curvature criterion and therefore is not an applanation area.
    """
    _validate_face_sets(preload, final)
    if maximum_radius <= 0 or absolute_noise <= 0:
        raise ValueError("maximum radius and absolute noise must be positive")

    records = _surface_records(preload, final)
    radii = np.asarray([record.radius for record in records], dtype=float)
    downward = np.asarray([record.downward for record in records], dtype=float)
    outer_mask = radii >= 0.8 * float(np.max(radii))
    if int(np.count_nonzero(outer_mask)) < 3:
        outer_mask = radii >= float(np.quantile(radii, 0.8))
    baseline = float(np.median(downward[outer_mask]))
    outer_residual = downward[outer_mask] - baseline
    noise_sigma = 1.4826 * float(np.median(np.abs(
        outer_residual - np.median(outer_residual)
    )))
    local_downward = {
        record.face.element: max(record.downward - baseline, 0.0) for record in records
    }
    local_max = max(local_downward.values())
    if local_max <= 0:
        raise ValueError("surface has no positive local indentation displacement")
    displacement_threshold = max(3.0 * noise_sigma, absolute_noise)

    candidates: set[int] = set()
    clipped_projected: dict[int, float] = {}
    records_by_element = {record.face.element: record for record in records}
    for record in records:
        element = record.face.element
        if local_downward[element] <= displacement_threshold:
            continue
        points = tuple((point[0], point[2]) for point in record.face.points)
        area = _projected_area_inside_circle(points, maximum_radius)
        if area > 0:
            candidates.add(element)
            clipped_projected[element] = area

    connected = _central_connected_elements(final, candidates)
    projected_area = 0.0
    surface_area = 0.0
    for element in connected:
        record = records_by_element[element]
        if record.projected_area <= 0:
            continue
        projected = clipped_projected[element]
        fraction = min(1.0, max(0.0, projected / record.projected_area))
        projected_area += projected
        surface_area += fraction * record.surface_area
    projected_area = min(projected_area, math.pi * maximum_radius**2)
    return DisplacementSupportResult(
        projected_area=projected_area,
        surface_area=surface_area,
        face_count=len(connected),
        displacement_threshold=displacement_threshold,
        baseline=baseline,
        noise_sigma=noise_sigma,
        local_max=local_max,
    ), connected


def select_flat_surface(
    preload: dict[int, Face],
    final: dict[int, Face],
    *,
    angle_limit_deg: float = 2.0,
    maximum_radius: float = PROBE_RADIUS_M,
    displacement_fraction: float = DISPLACEMENT_FRACTION,
) -> tuple[FlatAreaResult, set[int]]:
    """Return diagnostic angle-threshold metrics and selected face IDs."""
    _validate_face_sets(preload, final)
    if angle_limit_deg <= 0 or maximum_radius <= 0:
        raise ValueError("flatness angle and maximum radius must be positive")
    if not 0 < displacement_fraction < 1:
        raise ValueError("displacement_fraction must be between zero and one")

    records = _surface_records(preload, final)
    radii = np.asarray([record.radius for record in records], dtype=float)
    downward = np.asarray([record.downward for record in records], dtype=float)
    outer_mask = radii >= 0.8 * float(np.max(radii))
    if int(np.count_nonzero(outer_mask)) < 3:
        outer_mask = radii >= float(np.quantile(radii, 0.8))
    baseline = float(np.median(downward[outer_mask]))
    outer_residual = downward[outer_mask] - baseline
    noise_sigma = 1.4826 * float(np.median(np.abs(
        outer_residual - np.median(outer_residual)
    )))
    local_downward = {
        record.face.element: max(record.downward - baseline, 0.0) for record in records
    }
    local_max = max(local_downward.values())
    if local_max <= 0:
        raise ValueError("surface has no positive local indentation displacement")
    displacement_threshold = max(
        3.0 * noise_sigma,
        displacement_fraction * local_max,
        ABSOLUTE_NOISE_M,
    )

    smooth_angles = _smoothed_face_angles(final)
    candidates: set[int] = set()
    clipped_projected: dict[int, float] = {}
    records_by_element = {record.face.element: record for record in records}
    for record in records:
        element = record.face.element
        if (
            local_downward[element] < displacement_threshold
            or smooth_angles[element] > angle_limit_deg
        ):
            continue
        points = tuple((point[0], point[2]) for point in record.face.points)
        area = _projected_area_inside_circle(points, maximum_radius)
        if area > 0:
            candidates.add(element)
            clipped_projected[element] = area

    connected = _central_connected_elements(final, candidates)
    projected_area = 0.0
    surface_area = 0.0
    for element in connected:
        record = records_by_element[element]
        total_projected = record.projected_area
        if total_projected <= 0:
            continue
        projected = clipped_projected[element]
        fraction = min(1.0, max(0.0, projected / total_projected))
        projected_area += projected
        surface_area += fraction * record.surface_area
    result = FlatAreaResult(
        projected_area=projected_area,
        surface_area=surface_area,
        face_count=len(connected),
        displacement_threshold=displacement_threshold,
    )
    return result, connected


def analyze_flat_surface(
    preload: dict[int, Face],
    final: dict[int, Face],
    *,
    angle_limit_deg: float = 2.0,
    maximum_radius: float = PROBE_RADIUS_M,
    displacement_fraction: float = DISPLACEMENT_FRACTION,
) -> FlatAreaResult:
    """Integrate the central, displaced and near-planar deformed surface region."""
    result, _ = select_flat_surface(
        preload,
        final,
        angle_limit_deg=angle_limit_deg,
        maximum_radius=maximum_radius,
        displacement_fraction=displacement_fraction,
    )
    return result


def _flat_surface_metrics(
    prefix: str, preload: dict[int, Face], final: dict[int, Face]
) -> dict[str, float | int]:
    results = {
        int(angle): analyze_flat_surface(
            preload, final, angle_limit_deg=angle, maximum_radius=PROBE_RADIUS_M
        )
        for angle in ANGLE_LIMITS_DEG
    }
    two_degree = results[2]
    return {
        **{
            f"{prefix}_flat_projected_area_{angle}deg_m2": results[angle].projected_area
            for angle in (1, 2, 3)
        },
        f"{prefix}_flat_surface_area_2deg_m2": two_degree.surface_area,
        f"{prefix}_flat_face_count_2deg": two_degree.face_count,
        f"{prefix}_flat_displacement_threshold_m": two_degree.displacement_threshold,
    }


def analyze_breakpoint_surface(
    preload: dict[int, Face],
    final: dict[int, Face],
    *,
    maximum_radius: float | None = None,
    bin_width: float = RADIAL_BIN_M,
    relative_noise: float = RELATIVE_NOISE,
) -> BreakpointResult:
    records = _surface_records(preload, final)
    return _analyze_breakpoint_records(
        records,
        maximum_radius=maximum_radius,
        bin_width=bin_width,
        relative_noise=relative_noise,
    )


def _analyze_breakpoint_records(
    records: list[SurfaceRecord],
    *,
    maximum_radius: float | None,
    bin_width: float,
    relative_noise: float,
) -> BreakpointResult:
    radius, method, threshold, local_max = _break_radius(
        records, bin_width, relative_noise, maximum_radius
    )
    surface_area, projected_area = _integrate_disk(records, radius)
    if surface_area <= 0 or projected_area <= 0:
        raise ValueError("breakpoint applanation area is empty")
    return BreakpointResult(
        radius, method, threshold, local_max, surface_area, projected_area
    )


def _surface_metrics(
    prefix: str,
    preload: dict[int, Face],
    final: dict[int, Face],
    maximum_radius: float | None,
) -> dict[str, float | int]:
    records = _surface_records(preload, final)
    primary = _analyze_breakpoint_records(
        records,
        maximum_radius=maximum_radius,
        bin_width=RADIAL_BIN_M,
        relative_noise=RELATIVE_NOISE,
    )
    variant_radii = [
        _break_radius(
            records,
            bin_width,
            relative_noise,
            maximum_radius=maximum_radius * fit_window_scale,
        )[0]
        for fit_window_scale in FIT_WINDOW_SCALES
        for bin_width in (0.10e-3, 0.15e-3, 0.20e-3)
        for relative_noise in (0.01, 0.02, 0.03)
    ]
    integrations = {
        radius: _integrate_disk(records, radius) for radius in set(variant_radii)
    }
    areas = [integrations[radius][0] for radius in variant_radii]
    diameters = [
        2.0 * math.sqrt(integrations[radius][1] / math.pi)
        for radius in variant_radii
    ]
    return {
        f"{prefix}_local_max_downward_m": primary.local_max,
        f"{prefix}_surface_area_m2": primary.surface_area,
        f"{prefix}_projected_area_m2": primary.projected_area,
        f"{prefix}_break_radius_m": primary.radius,
        f"{prefix}_break_method_code": BREAK_METHOD_CODES[primary.method],
        f"{prefix}_threshold_m": primary.threshold,
        f"{prefix}_area_sensitivity_fraction": (
            max(areas) - min(areas)
        ) / primary.surface_area,
        f"{prefix}_diameter_sensitivity_m": max(diameters) - min(diameters),
    }


def analyze_files(
    inner_preload_path: Path,
    inner_final_path: Path,
    outer_preload_path: Path | None = None,
    outer_final_path: Path | None = None,
) -> dict[str, float | int]:
    inner_preload = read_faces(inner_preload_path)
    inner_final = read_faces(inner_final_path)
    metrics = analyze_faces(inner_preload, inner_final)
    metrics.update(_flat_surface_metrics("inner", inner_preload, inner_final))
    metrics.update(_surface_metrics(
        "inner", inner_preload, inner_final, PROBE_RADIUS_M
    ))
    if outer_preload_path is None or outer_final_path is None:
        raise ValueError("outer preload and final face files are required")
    outer_preload = read_faces(outer_preload_path)
    outer_final = read_faces(outer_final_path)
    metrics.update(_flat_surface_metrics("outer", outer_preload, outer_final))
    metrics.update(_surface_metrics(
        "outer", outer_preload, outer_final, PROBE_RADIUS_M
    ))
    metrics["outer_face_count"] = len(outer_final)
    return metrics


def _plot_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_boundary_qc_plot(
    path: Path,
    outer_faces: dict[int, Face],
    inner_faces: dict[int, Face],
    metrics: dict[str, float | int],
) -> None:
    width, height = 1200, 620
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _plot_font(22)
    label_font = _plot_font(15)
    draw.text((30, 18), "Applanation breakpoint QC", fill=(25, 25, 25), font=title_font)

    for panel, (prefix, faces) in enumerate((
        ("outer", outer_faces), ("inner", inner_faces)
    )):
        left = 40 + panel * 590
        top, size = 75, 510
        radius = float(metrics[f"{prefix}_break_radius_m"])
        extent = max(1.35 * radius, 1.8e-3)

        def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
            x = left + size / 2 + point[0] / extent * size / 2
            y = top + size / 2 - point[2] / extent * size / 2
            return round(x), round(y)

        draw.rectangle((left, top, left + size, top + size), outline=(90, 90, 90), width=1)
        for face in faces.values():
            center = tuple(sum(point[index] for point in face.points) / 3.0 for index in range(3))
            if math.hypot(center[0], center[2]) > extent:
                continue
            color = (38, 126, 178) if math.hypot(center[0], center[2]) <= radius else (190, 195, 200)
            x, y = pixel(center)
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)
        center_x, center_y = left + size / 2, top + size / 2
        circle_radius = radius / extent * size / 2
        draw.ellipse(
            (center_x - circle_radius, center_y - circle_radius,
             center_x + circle_radius, center_y + circle_radius),
            outline=(220, 70, 54), width=3,
        )
        method = {1: "inflection", 2: "segmented fit", 3: "probe edge"}.get(
            int(round(float(metrics[f"{prefix}_break_method_code"]))), "unknown"
        )
        diameter = 2.0 * math.sqrt(
            float(metrics[f"{prefix}_projected_area_m2"]) / math.pi
        ) * 1e3
        draw.text(
            (left + 8, top + 8),
            f"{prefix.upper()}  break={radius * 1e3:.3f} mm  d_eq={diameter:.3f} mm  {method}",
            fill=(25, 25, 25), font=label_font,
        )
    image.save(path, format="PNG", optimize=True)


def write_results(output_dir: Path, metrics: dict[str, float | int]) -> None:
    numeric_path = output_dir / "thickness_geometry.csv"
    numeric_path.write_text(
        ",".join(f"{float(metrics[field]):.14e}" for field in GEOMETRY_FIELDS) + ",\n",
        encoding="ascii",
    )
    method_names = {value: key for key, value in BREAK_METHOD_CODES.items()}
    payload = {
        "definition": {
            "status": "diagnostic_only",
            "reference_state": "end of IOP preload (load step 1)",
            "final_state": "requested probe-indentation state",
            "angle_threshold_boundary": (
                "central edge-connected deformed faces within the probe radius, with smoothed face "
                "normal at most 2 degrees from the probe axis and indentation displacement above an "
                "outer-annulus noise floor"
            ),
            "angle_threshold_area": "diagnostic projected integral of the 2 degree region",
            "angle_threshold_area_is_forced_to_probe": False,
            "flatness_sensitivity_deg": list(ANGLE_LIMITS_DEG),
            "diagnostic_area": "contact-status and radial-breakpoint areas are independent checks",
            "radial_bin_m": RADIAL_BIN_M,
            "relative_noise": RELATIVE_NOISE,
            "absolute_noise_m": ABSOLUTE_NOISE_M,
            "probe_radius_m": PROBE_RADIUS_M,
            "fit_window_scales": list(FIT_WINDOW_SCALES),
            "legacy_definition": (
                "5% displacement effect region filtered by 1, 2, and 3 degree face-normal limits"
            ),
        },
        "breakpoint_methods": {
            "outer": method_names[int(metrics["outer_break_method_code"])],
            "inner": method_names[int(metrics["inner_break_method_code"])],
        },
        "metrics": metrics,
    }
    (output_dir / "thickness_geometry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    outer_final = output_dir / "outer_final_faces.csv"
    inner_final = output_dir / "inner_final_faces.csv"
    if outer_final.is_file() and inner_final.is_file():
        write_boundary_qc_plot(
            output_dir / "applanation_boundary_qc.png",
            read_faces(outer_final),
            read_faces(inner_final),
            metrics,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt_dir", type=Path)
    cli = parser.parse_args()
    attempt_dir = cli.attempt_dir.expanduser().resolve()
    metrics = analyze_files(
        attempt_dir / "inner_preload_faces.csv",
        attempt_dir / "inner_final_faces.csv",
        attempt_dir / "outer_preload_faces.csv",
        attempt_dir / "outer_final_faces.csv",
    )
    write_results(attempt_dir, metrics)
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
