#!/usr/bin/env python3
"""Test whether one zero-IOP force baseline gives an affine multi-IOP response.

This is an interaction/linearity diagnostic, not a proof that material and IOP
forces are physically separable.  It compares independently solved states at
the same geometry-zero-relative indentation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PA_PER_MMHG = 133.322
PROBE_DIAMETER_MM = 4.32
PROBE_AREA_MM2 = math.pi * (PROBE_DIAMETER_MM / 2.0) ** 2
REQUIRED_IOPS = (0.0, 10.0, 20.0, 30.0)
CONSISTENCY_FIELDS = (
    "eyelid_thickness_mm",
    "indent_mm",
    "mesh_size_mm",
    "eyelid_material_scale",
    "cornea_material_scale",
    "cornea_thickness_mm",
)


def finite(value: str | float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(number):
        raise ValueError(f"non-finite {name}: {value!r}")
    return number


def close(left: float, right: float, tolerance: float = 1e-7) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def read_complete_row(
    path: Path,
    expected_iop: float,
    expected_thickness_mm: float,
    expected_indent_mm: float,
) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    matching = [
        row
        for row in rows
        if close(finite(row.get("iop_mmhg", "nan"), "iop_mmhg"), expected_iop)
        and close(
            finite(row.get("eyelid_thickness_mm", "nan"), "eyelid_thickness_mm"),
            expected_thickness_mm,
        )
        and close(finite(row.get("indent_mm", "nan"), "indent_mm"), expected_indent_mm)
    ]
    if len(matching) != 1:
        raise ValueError(
            f"expected one t={expected_thickness_mm:g} mm, d={expected_indent_mm:g} mm, "
            f"IOP={expected_iop:g} mmHg row in {path}, found {len(matching)}"
        )
    row = matching[0]
    if row.get("status") != "complete" or finite(row.get("returncode", "nan"), "returncode") != 0:
        raise ValueError(f"incomplete run at {expected_iop:g} mmHg: {path}")
    if finite(row.get("ansys_error_count", "nan"), "ansys_error_count") != 0:
        raise ValueError(f"ANSYS errors at {expected_iop:g} mmHg: {path}")
    for field in ("preload_converged", "approach_converged", "indentation_converged"):
        if finite(row.get(field, "nan"), field) < 0.5:
            raise ValueError(f"{field} failed at {expected_iop:g} mmHg: {path}")
    if finite(row.get("result_load_step", "nan"), "result_load_step") < 2.5:
        raise ValueError(f"final load step missing at {expected_iop:g} mmHg: {path}")
    copied = dict(row)
    copied["_manifest"] = str(path.resolve())
    return copied


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[index][:] + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= 1e-30:
            raise ValueError("singular least-squares system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * reference
                for value, reference in zip(augmented[row], augmented[column])
            ]
    return [augmented[index][-1] for index in range(size)]


def polynomial_fit(xs: Sequence[float], ys: Sequence[float], degree: int) -> list[float]:
    columns = degree + 1
    matrix = [
        [sum(x ** (row + column) for x in xs) for column in range(columns)]
        for row in range(columns)
    ]
    vector = [sum((x**power) * y for x, y in zip(xs, ys)) for power in range(columns)]
    return solve_linear_system(matrix, vector)


def evaluate(coefficients: Sequence[float], x: float) -> float:
    return sum(coefficient * x**power for power, coefficient in enumerate(coefficients))


def parse_manifest_argument(value: str) -> tuple[float, Path]:
    try:
        pressure, path = value.split("=", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use IOP=PATH") from error
    return finite(pressure, "manifest IOP"), Path(path).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        action="append",
        type=parse_manifest_argument,
        required=True,
        help="repeat as --manifest IOP_MMHG=/path/to/run_manifest.csv",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--eyelid-thickness-mm", type=float, default=1.25)
    parser.add_argument("--indent-mm", type=float, default=0.28)
    parser.add_argument("--engineering-gain-spread-limit-percent", type=float, default=5.0)
    args = parser.parse_args()

    supplied = {round(iop, 8): path for iop, path in args.manifest}
    if tuple(sorted(supplied)) != REQUIRED_IOPS:
        parser.error(f"exactly these IOP points are required: {REQUIRED_IOPS}")
    points = [
        (
            iop,
            read_complete_row(
                supplied[iop], iop, args.eyelid_thickness_mm, args.indent_mm
            ),
        )
        for iop in REQUIRED_IOPS
    ]

    reference = points[0][1]
    for iop, row in points[1:]:
        for field in CONSISTENCY_FIELDS:
            if not close(finite(row[field], field), finite(reference[field], field)):
                raise ValueError(f"configuration mismatch at {iop:g} mmHg: {field}")
        gap = finite(row["initial_gap_m"], "initial_gap_m")
        reference_gap = finite(reference["initial_gap_m"], "initial_gap_m")
        if not close(gap, reference_gap):
            raise ValueError(f"configuration mismatch at {iop:g} mmHg: initial_gap_m")

    iops = [point[0] for point in points]
    forces = [abs(finite(point[1]["probe_fy_n"], "probe_fy_n")) for point in points]
    force_zero = forces[0]
    probe_pressures = [
        force / (PROBE_AREA_MM2 * 1e-6) / PA_PER_MMHG for force in forces
    ]
    deltas = [force - force_zero for force in forces]
    secant_force_gains = [None if iop == 0 else delta / iop for iop, delta in zip(iops, deltas)]
    secant_probe_gains = [
        None if iop == 0 else (pressure - probe_pressures[0]) / iop
        for iop, pressure in zip(iops, probe_pressures)
    ]
    adjacent_force_gains = [
        None,
        *[
            (forces[index] - forces[index - 1]) / (iops[index] - iops[index - 1])
            for index in range(1, len(points))
        ],
    ]

    linear = polynomial_fit(iops, forces, 1)
    quadratic = polynomial_fit(iops, forces, 2)
    fixed_baseline_slope = sum(
        iop * delta for iop, delta in zip(iops[1:], deltas[1:])
    ) / sum(iop * iop for iop in iops[1:])
    fitted_forces = [force_zero + fixed_baseline_slope * iop for iop in iops]
    residuals = [force - fitted for force, fitted in zip(forces, fitted_forces)]
    nonzero_secants = [float(value) for value in secant_force_gains if value is not None]
    gain_mean = sum(nonzero_secants) / len(nonzero_secants)
    gain_spread_percent = (max(nonzero_secants) - min(nonzero_secants)) / gain_mean * 100.0
    max_residual_over_delta_percent = max(
        abs(residual) / delta * 100.0
        for residual, delta in zip(residuals[1:], deltas[1:])
    )

    # Hold out 20 mmHg; fit a fixed-zero-baseline slope using 10 and 30 only.
    holdout_indices = (1, 3)
    holdout_slope = sum(iops[i] * deltas[i] for i in holdout_indices) / sum(
        iops[i] ** 2 for i in holdout_indices
    )
    inferred_iop_20 = deltas[2] / holdout_slope
    holdout_error_mmhg = inferred_iop_20 - 20.0

    inferred_baselines = [
        force - linear[1] * iop for iop, force in zip(iops, forces)
    ]
    baseline_spread_n = max(inferred_baselines) - min(inferred_baselines)
    total_delta_30 = deltas[-1]
    quadratic_contribution_30_n = quadratic[2] * 30.0**2
    quadratic_fraction_30_percent = (
        quadratic_contribution_30_n / total_delta_30 * 100.0
        if total_delta_30 != 0
        else float("nan")
    )
    second_differences = [
        forces[index - 1] - 2.0 * forces[index] + forces[index + 1]
        for index in (1, 2)
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_rows: list[dict[str, object]] = []
    for index, ((iop, row), force, pressure, delta) in enumerate(
        zip(points, forces, probe_pressures, deltas)
    ):
        output_rows.append(
            {
                "iop_mmhg": iop,
                "probe_force_n": force,
                "probe_pressure_mmhg": pressure,
                "delta_force_from_zero_n": delta,
                "delta_probe_pressure_from_zero_mmhg": pressure - probe_pressures[0],
                "secant_force_gain_n_per_mmhg": "" if iop == 0 else secant_force_gains[index],
                "secant_probe_gain": "" if iop == 0 else secant_probe_gains[index],
                "adjacent_force_gain_n_per_mmhg": "" if index == 0 else adjacent_force_gains[index],
                "fixed_baseline_linear_fit_force_n": fitted_forces[index],
                "fixed_baseline_linear_residual_n": residuals[index],
                "inferred_baseline_from_free_linear_slope_n": inferred_baselines[index],
                "manifest": row["_manifest"],
                "attempt_dir": row.get("attempt_dir", ""),
                "git_commit": row.get("git_commit", ""),
            }
        )
    output_csv = args.output_dir / "iop_baseline_additivity_t1p25.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "interpretation": (
            "F(IOP)-F(0) is a total causal response difference. Near-affinity supports "
            "using one engineering baseline but does not prove physical separability of "
            "material, prestress, geometry, and contact contributions."
        ),
        "configuration": {
            field: finite(reference[field], field) for field in CONSISTENCY_FIELDS
        },
        "initial_gap_mm": finite(reference["initial_gap_m"], "initial_gap_m") * 1000.0,
        "probe_area_mm2": PROBE_AREA_MM2,
        "force_zero_n": force_zero,
        "free_linear_fit_intercept_n": linear[0],
        "free_linear_fit_slope_n_per_mmhg": linear[1],
        "fixed_zero_baseline_slope_n_per_mmhg": fixed_baseline_slope,
        "quadratic_fit_coefficients_n": {
            "intercept": quadratic[0],
            "linear_per_mmhg": quadratic[1],
            "quadratic_per_mmhg2": quadratic[2],
        },
        "quadratic_contribution_at_30_mmhg_n": quadratic_contribution_30_n,
        "quadratic_fraction_of_delta_at_30_percent": quadratic_fraction_30_percent,
        "second_differences_n_at_10_and_20_mmhg": second_differences,
        "secant_gain_spread_percent": gain_spread_percent,
        "maximum_fixed_baseline_residual_over_delta_percent": max_residual_over_delta_percent,
        "free_slope_inferred_baseline_spread_n": baseline_spread_n,
        "holdout_20_fit_points_mmhg": [10.0, 30.0],
        "holdout_20_inferred_iop_mmhg": inferred_iop_20,
        "holdout_20_error_mmhg": holdout_error_mmhg,
        "engineering_gain_spread_limit_percent": args.engineering_gain_spread_limit_percent,
        "engineering_fixed_baseline_check": (
            "pass" if gain_spread_percent <= args.engineering_gain_spread_limit_percent else "fail"
        ),
    }
    output_json = args.output_dir / "metadata.json"
    output_json.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output_csv)
    print(
        f"gain_spread={gain_spread_percent:.6f}% "
        f"quadratic_fraction_30={quadratic_fraction_30_percent:.6f}% "
        f"holdout20={inferred_iop_20:.6f} mmHg "
        f"check={metadata['engineering_fixed_baseline_check']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
