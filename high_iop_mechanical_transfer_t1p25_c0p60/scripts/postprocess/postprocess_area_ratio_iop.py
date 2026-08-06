#!/usr/bin/env python3
"""Calculate IOP strictly from the directly measured FE geometric area ratio."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.input_json.read_text(encoding="utf-8"))
    area_probe = 14.65741468458854
    rows = []
    summaries = {}
    for item in source["rows"]:
        pressure = float(item["input_iop_mmhg"])
        ae = float(item["outer_ae_lower_mm2"])
        ac = float(item["inner_ac_5deg_mm2"])
        delta_probe = float(item["delta_probe_pressure_mmhg"])
        k_area = ae / ac
        delta_pressure_over_ae = delta_probe * area_probe / ae
        iop_area = k_area * delta_pressure_over_ae
        equivalent = area_probe / ac * delta_probe
        if not math.isclose(iop_area, equivalent, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError("area-consistent formulas disagree")
        row = {
            "state": item["state"],
            "input_iop_mmhg": pressure,
            "outer_ae_mm2": ae,
            "inner_ac_5deg_mm2": ac,
            "k_area_ae_over_ac5": k_area,
            "delta_probe_pressure_over_full_probe_mmhg": delta_probe,
            "delta_pressure_renormalized_over_ae_mmhg": delta_pressure_over_ae,
            "iop_calc_from_area_ratio_mmhg": iop_area,
            "iop_error_mmhg": iop_area - pressure,
            "naive_k_area_times_full_probe_pressure_mmhg_not_area_consistent": k_area * delta_probe,
        }
        rows.append(row)
    for state in sorted({str(row["state"]) for row in rows}):
        selected = [row for row in rows if row["state"] == state and row["input_iop_mmhg"] > 0]
        errors = [float(row["iop_error_mmhg"]) for row in selected]
        summaries[state] = {
            "mae_mmhg": mean(abs(error) for error in errors),
            "rmse_mmhg": math.sqrt(mean(error * error for error in errors)),
            "mape_percent": 100.0 * mean(
                abs(float(row["iop_error_mmhg"])) / float(row["input_iop_mmhg"])
                for row in selected
            ),
            "maximum_absolute_error_mmhg": max(abs(error) for error in errors),
        }
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(args.input_json),
        "definition": {
            "k_area": "Ae/Ac5deg",
            "outer_pressure": "deltaF/Ae = (Aprobe/Ae)*deltaPprobe",
            "iop_calc": "Karea*(deltaF/Ae) = deltaF/Ac5deg = (Aprobe/Ac5deg)*deltaPprobe",
            "fit_parameters": 0,
            "warning": "Karea*deltaPprobe is not area-consistent because deltaPprobe uses Aprobe, not Ae.",
        },
        "probe_area_mm2": area_probe,
        "summaries": summaries,
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"summaries": summaries, "output_json": str(args.output_json)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
