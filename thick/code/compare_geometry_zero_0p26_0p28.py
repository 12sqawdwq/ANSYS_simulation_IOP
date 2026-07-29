#!/usr/bin/env python3
"""Aggregate retained 0.26-mm states and compare them with frozen 0.28-mm rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

PA_PER_MMHG = 133.322
PROBE_DIAMETER_MM = 4.32
PROBE_AREA_MM2 = math.pi * (PROBE_DIAMETER_MM / 2.0) ** 2
EXPECTED_THICKNESSES = (0.80, 1.00, 1.20, 1.25, 1.40, 1.50, 1.60, 1.80, 2.00)
CORNEA_RADIUS_MM = 7.8


def finite(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(number):
        raise ValueError(f"non-finite {name}: {value!r}")
    return number


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def pct_change(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def geometric_indent(thickness_mm: float) -> float:
    radius = CORNEA_RADIUS_MM + thickness_mm
    probe_radius = PROBE_DIAMETER_MM / 2.0
    return radius - math.sqrt(radius * radius - probe_radius * probe_radius)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--geometry-0p28-csv", type=Path, required=True)
    parser.add_argument("--iop-0p28-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    states: dict[tuple[float, float], dict[str, object]] = {}
    for path in sorted(args.state_root.rglob("geometry_state.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        key = (
            round(finite(row["eyelid_thickness_mm"], "thickness"), 8),
            round(finite(row["iop_mmhg"], "IOP"), 8),
        )
        if key in states:
            raise ValueError(f"duplicate retained state {key}: {path}")
        row["_state_json"] = str(path.resolve())
        states[key] = row

    geometry28 = {
        round(finite(row["eyelid_thickness_mm"], "thickness"), 8): row
        for row in read_csv(args.geometry_0p28_csv)
    }
    iop28 = {
        round(finite(row["eyelid_thickness_mm"], "thickness"), 8): row
        for row in read_csv(args.iop_0p28_csv)
    }

    output_rows: list[dict[str, object]] = []
    for thickness in EXPECTED_THICKNESSES:
        key = round(thickness, 8)
        missing = [item for item in ((key, 0.0), (key, 20.0)) if item not in states]
        if missing or key not in geometry28 or key not in iop28:
            raise ValueError(f"missing inputs for t={thickness:g}: {missing}")
        zero = states[(key, 0.0)]
        loaded = states[(key, 20.0)]
        old_geometry = geometry28[key]
        old_iop = iop28[key]

        actual_zero = finite(zero["actual_indent_mm"], "zero actual indent")
        actual_loaded = finite(loaded["actual_indent_mm"], "loaded actual indent")
        if abs(actual_zero - actual_loaded) > 1e-7:
            raise ValueError(f"0/20 indentation mismatch at t={thickness:g}")

        force0_26 = finite(zero["probe_force_n"], "force0 0.26")
        force20_26 = finite(loaded["probe_force_n"], "force20 0.26")
        delta_force26 = force20_26 - force0_26
        if delta_force26 <= 0:
            raise ValueError(f"non-positive 0.26 force increment at t={thickness:g}")
        ae0_26 = finite(zero["outer_ae_lower_mm2"], "Ae0 0.26")
        ac0_26 = finite(zero["inner_ac_5deg_mm2"], "Ac0 0.26")
        k0_26 = finite(zero["kgeo_5deg"], "K0 0.26")
        ae20_26 = finite(loaded["outer_ae_lower_mm2"], "Ae20 0.26")
        ac20_26 = finite(loaded["inner_ac_5deg_mm2"], "Ac20 0.26")
        k20_26 = finite(loaded["kgeo_5deg"], "K20 0.26")
        delta_probe26 = delta_force26 / (PROBE_AREA_MM2 * 1e-6) / PA_PER_MMHG
        calculated26 = delta_force26 / (ac20_26 * 1e-6) / PA_PER_MMHG
        error26 = calculated26 - 20.0

        force0_28 = finite(old_iop["force_zero_baseline_n"], "force0 0.28")
        force20_28 = finite(old_iop["force_iop_n"], "force20 0.28")
        delta_force28 = finite(old_iop["delta_force_n"], "delta force 0.28")
        ae20_28 = finite(old_geometry["outer_ae_lower_mm2"], "Ae20 0.28")
        ac20_28 = finite(old_geometry["inner_ac_5deg_mm2"], "Ac20 0.28")
        k20_28 = finite(old_geometry["approved_ae_over_ac"], "K20 0.28")
        calculated28 = finite(old_iop["calculated_iop_mmhg"], "calculated IOP 0.28")
        dgeo = geometric_indent(thickness)

        output_rows.append(
            {
                "eyelid_thickness_mm": thickness,
                "geometric_indent_mm": dgeo,
                "actual_indent_0p26_mm": actual_loaded,
                "indent_0p26_minus_geometric_um": (actual_loaded - dgeo) * 1000.0,
                "indent_0p26_over_geometric": actual_loaded / dgeo,
                "force_zero_0p26_n": force0_26,
                "force_20_0p26_n": force20_26,
                "delta_force_0p26_n": delta_force26,
                "delta_probe_pressure_0p26_mmhg": delta_probe26,
                "ae_zero_0p26_mm2": ae0_26,
                "ac5_zero_0p26_mm2": ac0_26,
                "kgeo_zero_0p26": k0_26,
                "ae_20_0p26_mm2": ae20_26,
                "ac5_20_0p26_mm2": ac20_26,
                "kgeo_20_0p26": k20_26,
                "kgeo_20_minus_zero_0p26": k20_26 - k0_26,
                "calculated_iop_0p26_mmhg": calculated26,
                "signed_error_0p26_mmhg": error26,
                "relative_error_0p26_percent": error26 / 20.0 * 100.0,
                "force_zero_0p28_n": force0_28,
                "force_20_0p28_n": force20_28,
                "delta_force_0p28_n": delta_force28,
                "ae_20_0p28_mm2": ae20_28,
                "ac5_20_0p28_mm2": ac20_28,
                "kgeo_20_0p28": k20_28,
                "calculated_iop_0p28_mmhg": calculated28,
                "force_zero_change_0p26_vs_0p28_percent": pct_change(force0_26, force0_28),
                "force_20_change_0p26_vs_0p28_percent": pct_change(force20_26, force20_28),
                "delta_force_change_0p26_vs_0p28_percent": pct_change(delta_force26, delta_force28),
                "ae_20_change_0p26_vs_0p28_percent": pct_change(ae20_26, ae20_28),
                "ac5_20_change_0p26_vs_0p28_percent": pct_change(ac20_26, ac20_28),
                "kgeo_20_change_0p26_vs_0p28_percent": pct_change(k20_26, k20_28),
                "calculated_iop_change_0p26_vs_0p28_percent": pct_change(calculated26, calculated28),
                "state_zero_json": zero["_state_json"],
                "state_20_json": loaded["_state_json"],
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_dir / "geometry_zero_0p26_vs_0p28_full9.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    primary_fields = (
        "eyelid_thickness_mm",
        "geometric_indent_mm",
        "actual_indent_0p26_mm",
        "indent_0p26_minus_geometric_um",
        "force_zero_0p26_n",
        "force_20_0p26_n",
        "delta_force_0p26_n",
        "delta_probe_pressure_0p26_mmhg",
        "ae_zero_0p26_mm2",
        "ac5_zero_0p26_mm2",
        "kgeo_zero_0p26",
        "ae_20_0p26_mm2",
        "ac5_20_0p26_mm2",
        "kgeo_20_0p26",
        "calculated_iop_0p26_mmhg",
        "signed_error_0p26_mmhg",
        "relative_error_0p26_percent",
    )
    primary_csv = args.output_dir / "geometry_zero_0p26_primary_full9.csv"
    with primary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=primary_fields)
        writer.writeheader()
        writer.writerows(
            {field: row[field] for field in primary_fields} for row in output_rows
        )

    errors26 = [finite(row["signed_error_0p26_mmhg"], "error26") for row in output_rows]
    errors28 = [
        finite(row["calculated_iop_0p28_mmhg"], "calc28") - 20.0 for row in output_rows
    ]
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete",
        "row_count": len(output_rows),
        "requested_indent_mm": 0.26,
        "actual_indent_mm_range": [
            min(finite(row["actual_indent_0p26_mm"], "actual indent") for row in output_rows),
            max(finite(row["actual_indent_0p26_mm"], "actual indent") for row in output_rows),
        ],
        "mean_signed_error_0p26_mmhg": sum(errors26) / len(errors26),
        "mean_absolute_error_0p26_mmhg": sum(abs(value) for value in errors26) / len(errors26),
        "rmse_0p26_mmhg": math.sqrt(sum(value * value for value in errors26) / len(errors26)),
        "mean_signed_error_0p28_mmhg": sum(errors28) / len(errors28),
        "mean_absolute_error_0p28_mmhg": sum(abs(value) for value in errors28) / len(errors28),
        "rmse_0p28_mmhg": math.sqrt(sum(value * value for value in errors28) / len(errors28)),
        "geometry_0p28_csv": str(args.geometry_0p28_csv.resolve()),
        "iop_0p28_csv": str(args.iop_0p28_csv.resolve()),
        "state_root": str(args.state_root.resolve()),
        "interpretation": (
            "0.26-mm values are independently read from retained 0- and 20-mmHg RST "
            "states; no force or area is interpolated from the 0.28-mm endpoint."
        ),
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(output_csv)
    print(
        f"0.26 MAE={metadata['mean_absolute_error_0p26_mmhg']:.6f} "
        f"RMSE={metadata['rmse_0p26_mmhg']:.6f}; "
        f"0.28 MAE={metadata['mean_absolute_error_0p28_mmhg']:.6f} "
        f"RMSE={metadata['rmse_0p28_mmhg']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
