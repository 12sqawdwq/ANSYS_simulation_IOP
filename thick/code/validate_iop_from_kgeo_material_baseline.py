#!/usr/bin/env python3
"""Independently validate nine-point IOP conversion after zero-IOP baseline removal.

Frozen equation:
    IOP_calc = K_geo,5deg * DeltaP_Ae
             = (Ae / Ac5deg) * ((|F_iop| - |F_0|) / Ae)
             = (|F_iop| - |F_0|) / Ac5deg

The script never infers a zero-IOP baseline from the known applied IOP.  A
completed, independently solved zero-IOP run manifest is required for each
thickness.  Missing baselines remain explicit pending rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

PA_PER_MMHG = 133.322
PROBE_DIAMETER_MM = 4.32
PROBE_AREA_MM2 = math.pi * (PROBE_DIAMETER_MM / 2.0) ** 2
EXPECTED_THICKNESSES_MM = (0.80, 1.00, 1.20, 1.25, 1.40, 1.50, 1.60, 1.80, 2.00)

OUTPUT_FIELDS = (
    "case",
    "eyelid_thickness_mm",
    "indent_mm",
    "actual_iop_mmhg",
    "outer_ae_lower_mm2",
    "inner_ac_5deg_mm2",
    "approved_kgeo_5deg",
    "probe_area_mm2",
    "effective_k_for_full_probe_pressure",
    "force_iop_n",
    "force_zero_baseline_n",
    "probe_pressure_iop_mmhg",
    "probe_pressure_zero_baseline_mmhg",
    "delta_force_n",
    "delta_probe_pressure_mmhg",
    "delta_ae_pressure_mmhg",
    "calculated_iop_mmhg",
    "signed_error_mmhg",
    "absolute_error_mmhg",
    "relative_error_percent",
    "status",
    "zero_manifest",
    "zero_attempt_dir",
    "zero_git_commit",
)


def finite_float(value: str | float | int, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite {field}: {value!r}")
    return result


def close(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV has no data rows: {path}")
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def discover_zero_rows(zero_root: Path) -> list[dict[str, str]]:
    if not zero_root.exists():
        return []
    discovered: list[dict[str, str]] = []
    for manifest in sorted(zero_root.rglob("run_manifest.csv")):
        for row in read_csv(manifest):
            copied = dict(row)
            copied["_manifest_path"] = str(manifest.resolve())
            discovered.append(copied)
    return discovered


def completed_zero_candidate(
    row: dict[str, str],
    geometry: dict[str, str],
    expected_mesh_size_mm: float,
) -> bool:
    required_flags = ("preload_converged", "approach_converged", "indentation_converged")
    if row.get("status") != "complete":
        return False
    if not close(finite_float(row.get("iop_mmhg", "nan"), "zero iop_mmhg"), 0.0):
        return False
    if any(finite_float(row.get(field, "nan"), field) < 0.5 for field in required_flags):
        return False
    comparisons = (
        ("eyelid_thickness_mm", "eyelid_thickness_mm"),
        ("indent_mm", "indent_mm"),
        ("eyelid_material_scale", "eyelid_material_scale"),
        ("cornea_material_scale", "cornea_material_scale"),
    )
    for zero_field, geometry_field in comparisons:
        if not close(
            finite_float(row.get(zero_field, "nan"), zero_field),
            finite_float(geometry[geometry_field], geometry_field),
            tolerance=1e-7,
        ):
            return False
    # The solver manifest stores this load-path quantity in metres, while the
    # frozen geometry table stores it in millimetres.
    zero_gap_mm = finite_float(row.get("initial_gap_m", "nan"), "initial_gap_m") * 1000.0
    if not close(
        zero_gap_mm,
        finite_float(geometry["initial_gap_mm"], "initial_gap_mm"),
        tolerance=1e-7,
    ):
        return False
    if not close(
        finite_float(row.get("mesh_size_mm", "nan"), "mesh_size_mm"),
        expected_mesh_size_mm,
        tolerance=1e-7,
    ):
        return False
    if finite_float(row.get("result_load_step", "nan"), "result_load_step") < 2.5:
        return False
    if finite_float(row.get("result_time", "nan"), "result_time") < 2.999999:
        return False
    return True


def newest_candidate(rows: Sequence[dict[str, str]]) -> dict[str, str] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: (row.get("ended_at_utc", ""), row["_manifest_path"]))


def blank_result(geometry: dict[str, str], actual_iop_mmhg: float) -> dict[str, object]:
    ae = finite_float(geometry["outer_ae_lower_mm2"], "outer_ae_lower_mm2")
    ac = finite_float(geometry["inner_ac_5deg_mm2"], "inner_ac_5deg_mm2")
    stored_k = finite_float(geometry["approved_ae_over_ac"], "approved_ae_over_ac")
    calculated_k = ae / ac
    if not close(stored_k, calculated_k, tolerance=1e-10):
        raise ValueError(
            f"stored K mismatch for {geometry['case']}: {stored_k} != {calculated_k}"
        )
    force_iop = abs(finite_float(geometry["probe_force_n"], "probe_force_n"))
    pressure_iop = force_iop / (PROBE_AREA_MM2 * 1e-6) / PA_PER_MMHG
    return {
        "case": geometry["case"],
        "eyelid_thickness_mm": finite_float(
            geometry["eyelid_thickness_mm"], "eyelid_thickness_mm"
        ),
        "indent_mm": finite_float(geometry["indent_mm"], "indent_mm"),
        "actual_iop_mmhg": actual_iop_mmhg,
        "outer_ae_lower_mm2": ae,
        "inner_ac_5deg_mm2": ac,
        "approved_kgeo_5deg": stored_k,
        "probe_area_mm2": PROBE_AREA_MM2,
        "effective_k_for_full_probe_pressure": PROBE_AREA_MM2 / ac,
        "force_iop_n": force_iop,
        "force_zero_baseline_n": "",
        "probe_pressure_iop_mmhg": pressure_iop,
        "probe_pressure_zero_baseline_mmhg": "",
        "delta_force_n": "",
        "delta_probe_pressure_mmhg": "",
        "delta_ae_pressure_mmhg": "",
        "calculated_iop_mmhg": "",
        "signed_error_mmhg": "",
        "absolute_error_mmhg": "",
        "relative_error_percent": "",
        "status": "missing_zero_baseline",
        "zero_manifest": "",
        "zero_attempt_dir": "",
        "zero_git_commit": "",
    }


def calculate_result(
    geometry: dict[str, str],
    zero: dict[str, str],
    actual_iop_mmhg: float,
) -> dict[str, object]:
    result = blank_result(geometry, actual_iop_mmhg)
    force_iop = float(result["force_iop_n"])
    force_zero = abs(finite_float(zero["probe_fy_n"], "zero probe_fy_n"))
    delta_force = force_iop - force_zero
    if delta_force <= 0:
        result.update(
            {
                "force_zero_baseline_n": force_zero,
                "status": "nonpositive_delta_force",
                "zero_manifest": zero["_manifest_path"],
                "zero_attempt_dir": zero.get("attempt_dir", ""),
                "zero_git_commit": zero.get("git_commit", ""),
            }
        )
        return result

    ae = float(result["outer_ae_lower_mm2"])
    ac = float(result["inner_ac_5deg_mm2"])
    kgeo = float(result["approved_kgeo_5deg"])
    pressure_zero = force_zero / (PROBE_AREA_MM2 * 1e-6) / PA_PER_MMHG
    delta_probe_pressure = delta_force / (PROBE_AREA_MM2 * 1e-6) / PA_PER_MMHG
    delta_ae_pressure = delta_force / (ae * 1e-6) / PA_PER_MMHG
    calculated_iop = kgeo * delta_ae_pressure
    direct_check = delta_force / (ac * 1e-6) / PA_PER_MMHG
    if not close(calculated_iop, direct_check, tolerance=1e-11):
        raise ValueError(f"area cancellation check failed for {geometry['case']}")
    signed_error = calculated_iop - actual_iop_mmhg

    result.update(
        {
            "force_zero_baseline_n": force_zero,
            "probe_pressure_zero_baseline_mmhg": pressure_zero,
            "delta_force_n": delta_force,
            "delta_probe_pressure_mmhg": delta_probe_pressure,
            "delta_ae_pressure_mmhg": delta_ae_pressure,
            "calculated_iop_mmhg": calculated_iop,
            "signed_error_mmhg": signed_error,
            "absolute_error_mmhg": abs(signed_error),
            "relative_error_percent": signed_error / actual_iop_mmhg * 100.0,
            "status": "validated",
            "zero_manifest": zero["_manifest_path"],
            "zero_attempt_dir": zero.get("attempt_dir", ""),
            "zero_git_commit": zero.get("git_commit", ""),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geometry-csv", type=Path, required=True)
    parser.add_argument("--zero-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--actual-iop-mmhg", type=float, default=20.0)
    parser.add_argument("--expected-mesh-size-mm", type=float, default=0.30)
    parser.add_argument("--require-complete-nine", action="store_true")
    args = parser.parse_args()

    if args.actual_iop_mmhg <= 0 or args.expected_mesh_size_mm <= 0:
        parser.error("actual IOP and expected mesh size must be positive")

    geometry_rows = read_csv(args.geometry_csv)
    geometry_rows.sort(key=lambda row: finite_float(row["eyelid_thickness_mm"], "thickness"))
    thicknesses = tuple(
        round(finite_float(row["eyelid_thickness_mm"], "thickness"), 8)
        for row in geometry_rows
    )
    expected = tuple(round(value, 8) for value in EXPECTED_THICKNESSES_MM)
    if thicknesses != expected:
        raise ValueError(f"geometry CSV thicknesses are not the frozen nine points: {thicknesses}")

    zero_rows = discover_zero_rows(args.zero_root)
    output_rows: list[dict[str, object]] = []
    for geometry in geometry_rows:
        candidates = [
            row
            for row in zero_rows
            if completed_zero_candidate(row, geometry, args.expected_mesh_size_mm)
        ]
        selected = newest_candidate(candidates)
        if selected is None:
            output_rows.append(blank_result(geometry, args.actual_iop_mmhg))
        else:
            output_rows.append(calculate_result(geometry, selected, args.actual_iop_mmhg))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_dir / "iop_from_kgeo_material_baseline_full9.csv"
    write_csv(output_csv, output_rows)

    validated = [row for row in output_rows if row["status"] == "validated"]
    missing = [row for row in output_rows if row["status"] == "missing_zero_baseline"]
    invalid = [
        row
        for row in output_rows
        if row["status"] not in {"validated", "missing_zero_baseline"}
    ]
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "formula": "IOP_calc = Kgeo,5deg * ((abs(F_iop)-abs(F_0))/Ae)",
        "equivalent_formula": "IOP_calc = (abs(F_iop)-abs(F_0))/Ac5deg",
        "pressure_unit_conversion_pa_per_mmhg": PA_PER_MMHG,
        "probe_diameter_mm": PROBE_DIAMETER_MM,
        "probe_area_mm2": PROBE_AREA_MM2,
        "actual_iop_mmhg": args.actual_iop_mmhg,
        "expected_mesh_size_mm": args.expected_mesh_size_mm,
        "geometry_csv": str(args.geometry_csv.resolve()),
        "geometry_csv_sha256": sha256(args.geometry_csv),
        "zero_root": str(args.zero_root.resolve()),
        "discovered_zero_manifest_rows": len(zero_rows),
        "validated_count": len(validated),
        "missing_zero_baseline_count": len(missing),
        "invalid_count": len(invalid),
        "nine_point_status": (
            "complete" if len(validated) == 9 and not invalid else "incomplete"
        ),
        "mean_signed_error_mmhg": (
            sum(float(row["signed_error_mmhg"]) for row in validated) / len(validated)
            if validated
            else None
        ),
        "mean_absolute_error_mmhg": (
            sum(float(row["absolute_error_mmhg"]) for row in validated) / len(validated)
            if validated
            else None
        ),
        "rmse_mmhg": (
            math.sqrt(
                sum(float(row["signed_error_mmhg"]) ** 2 for row in validated)
                / len(validated)
            )
            if validated
            else None
        ),
        "missing_thicknesses_mm": [row["eyelid_thickness_mm"] for row in missing],
        "invalid_cases": [row["case"] for row in invalid],
        "independence_rule": (
            "Zero baselines are read only from completed iop_mmhg=0 run manifests; "
            "the known applied IOP is never used to infer a baseline."
        ),
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(output_csv)
    print(
        f"validated={len(validated)} missing={len(missing)} invalid={len(invalid)} "
        f"nine_point_status={metadata['nine_point_status']}"
    )
    for row in validated:
        print(
            f"t={float(row['eyelid_thickness_mm']):.2f} mm "
            f"IOP_calc={float(row['calculated_iop_mmhg']):.6f} mmHg "
            f"error={float(row['signed_error_mmhg']):+.6f} mmHg"
        )

    if args.require_complete_nine and metadata["nine_point_status"] != "complete":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
