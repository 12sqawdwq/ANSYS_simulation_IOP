#!/usr/bin/env python3
"""Decompose the direct area-ratio IOP error without fitting."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-summary", type=Path, required=True)
    parser.add_argument("--area-results", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    full = json.loads(args.full_summary.read_text(encoding="utf-8"))
    area = json.loads(args.area_results.read_text(encoding="utf-8"))
    pa_per_mmhg = 133.32236842105263
    probe_area = float(area["probe_area_mm2"])
    full_index = {
        (row["state"], float(row["input_iop_mmhg"])): row for row in full["rows"]
    }
    positive_by_state = {}
    for row in area["rows"]:
        if float(row["input_iop_mmhg"]) > 0:
            positive_by_state.setdefault(row["state"], []).append(row)
    output_rows = []
    summaries = {}
    for state, selected in positive_by_state.items():
        selected.sort(key=lambda row: float(row["input_iop_mmhg"]))
        transfer20 = float(selected[0]["iop_calc_from_area_ratio_mmhg"]) / 20.0
        for row in selected:
            pressure = float(row["input_iop_mmhg"])
            ac = float(row["inner_ac_5deg_mm2"])
            calculated = float(row["iop_calc_from_area_ratio_mmhg"])
            source = full_index[state, pressure]
            delta_force = float(source["delta_force_n"])
            ideal_force = pressure * pa_per_mmhg * ac * 1e-6
            transfer = calculated / pressure
            required_ac = probe_area * float(source["delta_probe_pressure_mmhg"]) / pressure
            baseline_component = pressure * (1.0 - transfer20)
            pressure_dependent_component = pressure * (transfer20 - transfer)
            output_rows.append({
                "state": state,
                "input_iop_mmhg": pressure,
                "actual_delta_force_n": delta_force,
                "ideal_force_if_deltaF_equals_iop_times_ac_n": ideal_force,
                "missing_force_n": ideal_force - delta_force,
                "area_transfer_factor_iopcalc_over_iop": transfer,
                "area_transfer_loss_percent": 100.0 * (1.0 - transfer),
                "current_ac_5deg_mm2": ac,
                "required_ac_for_exact_area_conversion_mm2": required_ac,
                "required_ac_reduction_percent": 100.0 * (1.0 - required_ac / ac),
                "total_area_iop_underestimate_mmhg": pressure - calculated,
                "low_pressure_offset_component_mmhg_anchored_at_20": baseline_component,
                "pressure_dependent_transfer_component_mmhg": pressure_dependent_component,
            })
        row20, row40 = selected[0], selected[-1]
        source20 = full_index[state, 20.0]
        source40 = full_index[state, 40.0]
        ac20 = float(row20["inner_ac_5deg_mm2"])
        ac40 = float(row40["inner_ac_5deg_mm2"])
        linear_growth = 2.0
        area_adjusted_growth = 2.0 * ac40 / ac20
        actual_force_growth = float(source40["delta_force_n"]) / float(source20["delta_force_n"])
        total_shortfall = linear_growth - actual_force_growth
        area_share = (linear_growth - area_adjusted_growth) / total_shortfall
        summaries[state] = {
            "ac_change_20_to_40_percent": 100.0 * (ac40 / ac20 - 1.0),
            "karea_change_20_to_40_percent": 100.0 * (
                float(row40["k_area_ae_over_ac5"]) / float(row20["k_area_ae_over_ac5"]) - 1.0
            ),
            "ksensor_response_change_20_to_40_percent": 100.0 * (
                float(source40["ksensor_delta"]) / float(source20["ksensor_delta"]) - 1.0
            ),
            "delta_force_growth_ratio_20_to_40": actual_force_growth,
            "ideal_growth_ratio_without_area_change": linear_growth,
            "ideal_growth_ratio_with_ac_change": area_adjusted_growth,
            "heuristic_share_of_force_growth_shortfall_from_ac_change": area_share,
            "heuristic_share_of_force_growth_shortfall_from_non_area_transfer": 1.0 - area_share,
            "transfer_factor_at_20": float(row20["iop_calc_from_area_ratio_mmhg"]) / 20.0,
            "transfer_factor_at_40": float(row40["iop_calc_from_area_ratio_mmhg"]) / 40.0,
        }
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fit_parameters": 0,
        "identity_under_test": "deltaF = IOP * Ac5deg",
        "interpretation": {
            "transfer_factor": "deltaF / (IOP*Ac5deg) = IOP_area/IOP_input",
            "anchored_decomposition": "Total error is split arithmetically into the 20 mmHg offset and the additional pressure-dependent decline. It is diagnostic, not a fitted causal model.",
            "growth_decomposition": "The 20-to-40 force-growth shortfall is split heuristically into Ac shrinkage and remaining non-area load-transfer change; these shares must not be added to the anchored decomposition.",
        },
        "summaries": summaries,
        "rows": output_rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(json.dumps({"summaries": summaries, "output": str(args.output_json)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
