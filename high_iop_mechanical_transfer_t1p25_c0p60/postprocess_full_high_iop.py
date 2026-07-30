#!/usr/bin/env python3
"""Aggregate the complete 0/20/25/30/35/40 mmHg high-IOP campaign."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

PRESSURES = (0.0, 20.0, 25.0, 30.0, 35.0, 40.0)
STATE_DEFS = (
    ("primary_0p26", "primary_0p259875_mm", "primary_0p26"),
    ("sensitivity_0p28", "sensitivity_0p28_mm", "sensitivity_0p28"),
)


def num(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite {name}: {value!r}")
    return result


def close(left: float, right: float, tolerance: float = 1e-10) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected one row in {path}, found {len(rows)}")
    return rows[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pearson(x: list[float], y: list[float]) -> float:
    xm, ym = mean(x), mean(y)
    numerator = sum((a - xm) * (b - ym) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - xm) ** 2 for a in x) * sum((b - ym) ** 2 for b in y))
    return numerator / denominator if denominator else float("nan")


def ranks(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    output = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][0] == ordered[start][0]:
            end += 1
        rank = 0.5 * (start + 1 + end)
        for _, index in ordered[start:end]:
            output[index] = rank
        start = end
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-spec", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_root.expanduser().resolve()
    spec = load_json(args.run_spec.expanduser().resolve())
    source40 = Path(spec["reused_iop40_preflight"]["data_root"])
    area_mm2 = num(spec["geometry"]["probe_area_mm2"], "probe area")
    pa_per_mmhg = num(spec["pressure_conversion"]["pa_per_mmhg"], "pressure conversion")
    factor = 1e6 / (area_mm2 * pa_per_mmhg)
    criteria = spec["acceptance"]

    manifests: dict[float, tuple[Path, dict[str, str]]] = {}
    states: dict[tuple[float, str], dict] = {}
    run_metadata: dict[float, dict] = {}
    for pressure in PRESSURES:
        case_root = source40 if pressure == 40.0 else root / f"iop{int(pressure)}"
        mpath = case_root / "run" / "run_manifest.csv"
        manifests[pressure] = mpath, manifest_row(mpath)
        run_metadata[pressure] = load_json(case_root / "run" / "run_metadata.json")
        if pressure == 40.0:
            state_base = root / "states" / "iop40"
            state_paths = {
                "primary_0p26": state_base / "primary_0p26_geometry_state.json",
                "sensitivity_0p28": state_base / "sensitivity_0p28_geometry_state.json",
            }
        else:
            state_base = root / "states" / f"iop{int(pressure)}"
            state_paths = {
                "primary_0p26": state_base / "primary_0p26" / "geometry_state.json",
                "sensitivity_0p28": state_base / "sensitivity_0p28" / "geometry_state.json",
            }
        for state_name, path in state_paths.items():
            states[pressure, state_name] = load_json(path)

    qc: dict[str, bool] = {}
    expected_materials = spec["absolute_material_parameters"]
    apdl_hash_reference = run_metadata[40.0]["apdl_sha256"]
    for pressure in PRESSURES:
        path, row = manifests[pressure]
        prefix = f"iop{int(pressure)}"
        qc[f"{prefix}_complete"] = row.get("status") == criteria["required_status"]
        qc[f"{prefix}_returncode_zero"] = int(num(row.get("returncode"), "returncode")) == 0
        qc[f"{prefix}_ansys_errors_zero"] = int(num(row.get("ansys_error_count"), "error count")) <= int(criteria["maximum_ansys_error_count"])
        qc[f"{prefix}_three_steps_converged"] = all(num(row.get(field), field) >= 0.5 for field in ("preload_converged", "approach_converged", "indentation_converged"))
        qc[f"{prefix}_preload_contact_zero"] = int(num(row.get("preload_contact_count"), "preload contact")) <= int(criteria["maximum_preload_contact_count"])
        qc[f"{prefix}_approach_force_ok"] = abs(num(row.get("approach_probe_fy_n"), "approach force")) <= num(criteria["maximum_absolute_approach_force_n"], "approach limit")
        qc[f"{prefix}_penetration_ok"] = num(row.get("max_penetration_m"), "penetration") * 1e3 <= num(criteria["maximum_penetration_mm"], "penetration limit")
        qc[f"{prefix}_apdl_hash_match"] = run_metadata[pressure]["apdl_sha256"] == apdl_hash_reference
        for tissue in ("eyelid", "cornea"):
            for parameter in ("c10_mpa", "c01_mpa", "d1_pa_inv"):
                field = f"{tissue}_{parameter}"
                qc[f"{prefix}_{field}_match"] = close(num(row.get(field), field), num(expected_materials[tissue][parameter], field))
        for state_name, _, _ in STATE_DEFS:
            state = states[pressure, state_name]
            target = 0.26 if state_name == "primary_0p26" else 0.28
            tolerance = num(criteria["maximum_primary_indent_error_mm"], "indent tolerance") if target == 0.26 else 1e-6
            qc[f"{prefix}_{state_name}_indent_ok"] = abs(num(state["actual_indent_mm"], "actual indent") - target) <= tolerance
            qc[f"{prefix}_{state_name}_load_step3"] = int(round(num(state["result_load_step"], "load step"))) == 3

    rst40 = Path(manifests[40.0][0].parent) / manifests[40.0][1]["result_rst"]
    qc["iop40_rst_sha256_match"] = sha256(rst40) == spec["reused_iop40_preflight"]["rst_sha256"]

    rows: list[dict[str, object]] = []
    state_summaries: dict[str, dict] = {}
    for state_name, model_name, _ in STATE_DEFS:
        model = spec["frozen_sensor_models"][model_name]
        alpha = num(model["alpha"], "alpha")
        beta = num(model["beta_per_mmhg"], "beta")
        zero_force = num(states[0.0, state_name]["probe_force_n"], "zero force")
        state_rows: list[dict[str, object]] = []
        for pressure in PRESSURES:
            state = states[pressure, state_name]
            force = num(state["probe_force_n"], "force")
            delta_force = force - zero_force
            delta_pressure = delta_force * factor
            if pressure == 0.0:
                ksensor: float | str = ""
                iop_calc = 0.0
                iop_error = 0.0
                expected_k: float | str = ""
                expected_delta_pressure = 0.0
            else:
                if delta_pressure <= 0 or 1.0 - beta * delta_pressure <= 0:
                    raise ValueError(f"invalid pressure response at {state_name}, {pressure:g} mmHg")
                ksensor = pressure / delta_pressure
                iop_calc = alpha * delta_pressure / (1.0 - beta * delta_pressure)
                iop_error = iop_calc - pressure
                expected_k = alpha + beta * pressure
                expected_delta_pressure = pressure / expected_k
            item: dict[str, object] = {
                "state": state_name,
                "input_iop_mmhg": pressure,
                "actual_indent_mm": num(state["actual_indent_mm"], "indent"),
                "probe_force_n": force,
                "probe_total_equivalent_pressure_mmhg": force * factor,
                "zero_reference_force_n": zero_force,
                "zero_reference_pressure_mmhg": zero_force * factor,
                "delta_force_n": delta_force,
                "delta_probe_pressure_mmhg": delta_pressure,
                "ksensor_delta": ksensor,
                "frozen_model_expected_ksensor": expected_k,
                "frozen_model_expected_delta_pressure_mmhg": expected_delta_pressure,
                "iop_calc_mmhg": iop_calc,
                "iop_error_mmhg": iop_error,
                "outer_ae_lower_mm2": num(state["outer_ae_lower_mm2"], "Ae"),
                "inner_ac_5deg_mm2": num(state["inner_ac_5deg_mm2"], "Ac5"),
                "kgeo_5deg": num(state["kgeo_5deg"], "Kgeo"),
                "source_git_commit": state.get("source_git_commit", ""),
            }
            rows.append(item)
            state_rows.append(item)

        positive = [row for row in state_rows if num(row["input_iop_mmhg"], "pressure") > 0]
        errors = [num(row["iop_error_mmhg"], "IOP error") for row in positive]
        pressures = [num(row["input_iop_mmhg"], "pressure") for row in positive]
        kvalues = [num(row["ksensor_delta"], "Ksensor") for row in positive]
        delta_values = [num(row["delta_probe_pressure_mmhg"], "delta pressure") for row in state_rows]
        forces = [num(row["probe_force_n"], "force") for row in state_rows]
        gains = []
        for left, right in zip(state_rows, state_rows[1:]):
            dp = num(right["input_iop_mmhg"], "pressure") - num(left["input_iop_mmhg"], "pressure")
            gains.append({
                "from_iop_mmhg": left["input_iop_mmhg"],
                "to_iop_mmhg": right["input_iop_mmhg"],
                "delta_probe_pressure_gain_per_mmhg": (
                    num(right["delta_probe_pressure_mmhg"], "q") - num(left["delta_probe_pressure_mmhg"], "q")
                ) / dp,
            })
        state_summaries[state_name] = {
            "iop_mae_mmhg": mean(abs(error) for error in errors),
            "iop_rmse_mmhg": math.sqrt(mean(error * error for error in errors)),
            "maximum_absolute_iop_error_mmhg": max(abs(error) for error in errors),
            "ksensor_pearson_vs_iop": pearson(pressures, kvalues),
            "ksensor_spearman_vs_iop": pearson(ranks(pressures), ranks(kvalues)),
            "force_monotonic_increasing": all(right > left for left, right in zip(forces, forces[1:])),
            "delta_pressure_monotonic_increasing": all(right > left for left, right in zip(delta_values, delta_values[1:])),
            "interval_gains": gains,
            "validation_errors_mmhg": {
                str(int(row["input_iop_mmhg"])): row["iop_error_mmhg"]
                for row in positive if row["input_iop_mmhg"] in (25.0, 35.0, 40.0)
            },
        }
        qc[f"{state_name}_iop_mae_ok"] = state_summaries[state_name]["iop_mae_mmhg"] <= num(criteria["maximum_iop_mae_mmhg"], "MAE limit")
        qc[f"{state_name}_single_iop_error_ok"] = state_summaries[state_name]["maximum_absolute_iop_error_mmhg"] <= num(criteria["maximum_single_iop_error_mmhg"], "error limit")
        qc[f"{state_name}_force_monotonic"] = bool(state_summaries[state_name]["force_monotonic_increasing"])
        qc[f"{state_name}_delta_pressure_monotonic"] = bool(state_summaries[state_name]["delta_pressure_monotonic_increasing"])

    campaign_pass = all(qc.values())
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_id": spec["experiment_id"],
        "phase": spec["phase"],
        "campaign_pass": campaign_pass,
        "formal_zero_reference_available": True,
        "pressure_factor_mmhg_per_n": factor,
        "qc": qc,
        "state_summaries": state_summaries,
        "rows": rows,
        "source_manifests": {str(int(p)): str(manifests[p][0]) for p in PRESSURES},
        "absolute_material_parameters": expected_materials,
    }
    analysis = root / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "high_iop_full_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (analysis / "high_iop_full_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "campaign_pass": campaign_pass,
        "state_summaries": state_summaries,
        "analysis": str(analysis),
    }, ensure_ascii=False, indent=2))
    return 0 if campaign_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
