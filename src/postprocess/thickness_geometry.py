#!/usr/bin/env python3
"""Compute inner applanation areas from preload and indented interface faces."""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


ANGLE_LIMITS_DEG = (1.0, 2.0, 3.0)
DISPLACEMENT_FRACTION = 0.05
GEOMETRY_FIELDS = (
    "inner_max_downward_m",
    "inner_effect_area_m2",
    "inner_area_1deg_m2",
    "inner_area_2deg_m2",
    "inner_area_3deg_m2",
    "inner_face_count",
)


@dataclass(frozen=True)
class Face:
    element: int
    nodes: tuple[int, int, int]
    points: tuple[tuple[float, float, float], ...]


def _vector(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
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
                raise ValueError(f"{path.name}:{line_number}: expected 13 values, found {len(values)}")
            parsed = [float(item) for item in values]
            if not all(math.isfinite(item) for item in parsed):
                raise ValueError(f"{path.name}:{line_number}: non-finite value")
            identifiers = tuple(int(round(item)) for item in parsed[:4])
            if any(abs(parsed[index] - identifiers[index]) > 1e-6 for index in range(4)):
                raise ValueError(f"{path.name}:{line_number}: non-integral element or node identifier")
            element, n1, n2, n3 = identifiers
            if element in faces:
                raise ValueError(f"{path.name}:{line_number}: duplicate element {element}")
            points = tuple(
                tuple(parsed[start:start + 3])
                for start in (4, 7, 10)
            )
            faces[element] = Face(element, (n1, n2, n3), points)
    if not faces:
        raise ValueError(f"{path.name}: no interface faces")
    return faces


def _face_geometry(face: Face) -> tuple[float, float]:
    edge1 = _vector(face.points[0], face.points[1])
    edge2 = _vector(face.points[0], face.points[2])
    normal = _cross(edge1, edge2)
    magnitude = math.sqrt(sum(component * component for component in normal))
    if magnitude <= 0:
        raise ValueError(f"element {face.element} has zero deformed area")
    projected_area = 0.5 * abs(normal[1])
    axis_cosine = min(1.0, max(0.0, abs(normal[1]) / magnitude))
    angle_deg = math.degrees(math.acos(axis_cosine))
    return projected_area, angle_deg


def analyze_faces(
    preload: dict[int, Face],
    final: dict[int, Face],
    displacement_fraction: float = DISPLACEMENT_FRACTION,
) -> dict[str, float | int]:
    if preload.keys() != final.keys():
        missing_preload = sorted(final.keys() - preload.keys())
        missing_final = sorted(preload.keys() - final.keys())
        raise ValueError(
            "preload/final element sets differ: "
            f"missing_preload={missing_preload[:5]} missing_final={missing_final[:5]}"
        )
    if not 0 < displacement_fraction < 1:
        raise ValueError("displacement_fraction must be between 0 and 1")

    records: list[tuple[float, float, float]] = []
    for element in sorted(preload):
        before = preload[element]
        after = final[element]
        if before.nodes != after.nodes:
            raise ValueError(f"element {element} node ordering differs between result sets")
        preload_y = sum(point[1] for point in before.points) / 3.0
        final_y = sum(point[1] for point in after.points) / 3.0
        downward = preload_y - final_y
        projected_area, angle_deg = _face_geometry(after)
        records.append((downward, projected_area, angle_deg))

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
            for _, projected_area, angle_deg in affected
            if angle_deg <= angle
        )
    return metrics


def analyze_files(preload_path: Path, final_path: Path) -> dict[str, float | int]:
    return analyze_faces(read_faces(preload_path), read_faces(final_path))


def write_results(output_dir: Path, metrics: dict[str, float | int]) -> None:
    numeric_path = output_dir / "thickness_geometry.csv"
    numeric_path.write_text(
        ",".join(f"{float(metrics[field]):.14e}" for field in GEOMETRY_FIELDS) + ",\n",
        encoding="ascii",
    )
    payload = {
        "definition": {
            "reference_state": "end of IOP preload (load step 1)",
            "final_state": "end of probe indentation (load step 2)",
            "effect_region": (
                "face centroid downward displacement is at least 5% of the maximum "
                "indentation-induced downward displacement"
            ),
            "area": "face area projected onto the plane normal to the global Y probe axis",
            "flatness": "absolute face-normal angle to the global Y probe axis",
            "angle_limits_deg": list(ANGLE_LIMITS_DEG),
        },
        "metrics": metrics,
    }
    (output_dir / "thickness_geometry.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt_dir", type=Path)
    cli = parser.parse_args()
    attempt_dir = cli.attempt_dir.expanduser().resolve()
    metrics = analyze_files(
        attempt_dir / "inner_preload_faces.csv",
        attempt_dir / "inner_final_faces.csv",
    )
    write_results(attempt_dir, metrics)
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
