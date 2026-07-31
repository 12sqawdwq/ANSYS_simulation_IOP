#!/usr/bin/env python3
"""Run RST contact-vector integrations for the 21-point pressure grid and summarize them."""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def pressure_key(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def linear_fit(xs: list[float], ys: list[float]) -> dict[str, float]:
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sum(
        (x - mean_x) ** 2 for x in xs
    )
    intercept = mean_y - slope * mean_x
    sse = sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - mean_y) ** 2 for y in ys)
    return {"intercept": intercept, "slope_per_mmhg": slope, "r_squared": 1.0 - sse / sst}


def rational(q: float, a: float, b: float) -> float:
    denominator = 1.0 - a * q
    return b * q / denominator if denominator > 0.0 else math.nan


def error_metrics(rows: list[dict], field: str) -> dict[str, float]:
    errors = [float(row[field]) - float(row["input_iop_mmhg"]) for row in rows]
    return {
        "mae_mmhg": sum(abs(value) for value in errors) / len(errors),
        "rmse_mmhg": math.sqrt(sum(value * value for value in errors) / len(errors)),
        "maximum_absolute_error_mmhg": max(abs(value) for value in errors),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run-spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    spec = load_json(args.run_spec.expanduser().resolve())
    output = args.output_root.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    extractor = repo / "src" / "postprocess" / "extract_contact_force_integrals.py"
    python_bin = Path(spec["postprocessor"]["python_executable"])
    ansys_bin = Path(spec["postprocessor"]["ansys_executable"])
    pressures = [float(value) for value in spec["pressure_grid_mmhg"]]
    roots = {name: Path(value) for name, value in spec["source_state_roots"].items()}
    root_pressures = {
        name: {float(value) for value in values}
        for name, values in spec["state_root_pressures_mmhg"].items()
    }
    state_overrides = {
        float(key): Path(value) for key, value in spec.get("state_json_overrides", {}).items()
    }
    source_summary = load_json(Path(spec["source_fe_summary"]))
    fe_rows = {
        float(row["input_iop_mmhg"]): row
        for row in source_summary["rows"]
        if row["state"] == "primary_0p26"
    }
    acceptance = spec["acceptance"]
    raw_rows = []
    source_states = {}
    for pressure in pressures:
        matching_roots = [name for name, values in root_pressures.items() if pressure in values]
        key = pressure_key(pressure)
        if pressure in state_overrides:
            if matching_roots:
                raise ValueError(f"override and regular root both defined for {pressure:g} mmHg")
            state_path = state_overrides[pressure]
        else:
            if len(matching_roots) != 1:
                raise ValueError(f"expected one source root for {pressure:g} mmHg; found {matching_roots}")
            state_path = roots[matching_roots[0]] / f"iop{key}" / "primary_0p26" / "geometry_state.json"
        if not state_path.is_file():
            raise FileNotFoundError(state_path)
        source_states[key] = str(state_path)
        case_output = output / "cases" / f"iop{key}"
        command = [
            str(python_bin),
            str(extractor),
            "--state-json",
            str(state_path),
            "--output-dir",
            str(case_output),
            "--ansys-bin",
            str(ansys_bin),
            "--np",
            str(spec["postprocessor"]["np"]),
            "--timeout-seconds",
            str(spec["postprocessor"]["timeout_seconds_per_case"]),
            "--maximum-probe-force-relative-error",
            str(acceptance["maximum_probe_contact_reaction_relative_error"]),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        (case_output / "extractor.log").write_text(
            completed.stdout + ("\nSTDERR:\n" + completed.stderr if completed.stderr else ""),
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"extractor failed for {pressure:g} mmHg: {completed.stderr}")
        raw = load_json(case_output / "contact_force_integrals.json")
        if int(raw["mapdl_error_count"]) != int(acceptance["required_mapdl_error_count"]):
            raise ValueError(f"MAPDL errors at {pressure:g} mmHg")
        if abs(float(raw["actual_indent_mm"]) - spec["geometry"]["primary_actual_indent_mm"]) > float(
            acceptance["maximum_actual_indent_error_mm"]
        ):
            raise ValueError(f"indent mismatch at {pressure:g} mmHg")
        raw_rows.append(raw)

    zero = next(row for row in raw_rows if float(row["iop_mmhg"]) == 0.0)
    zero_probe = abs(float(zero["probe_rf_y_n"]))
    zero_inner = abs(float(zero["inner_cnf_y_n"]))
    probe_area = float(spec["geometry"]["probe_area_mm2"])
    pa_per_mmhg = float(spec["pressure_conversion"]["pa_per_mmhg"])
    rows = []
    for raw in raw_rows:
        p = float(raw["iop_mmhg"])
        fe = fe_rows[p]
        q = float(fe["delta_probe_pressure_mmhg"])
        ac5 = float(fe["inner_ac_5deg_mm2"])
        ka = probe_area / ac5
        probe_force = abs(float(raw["probe_rf_y_n"]))
        interface_force = abs(float(raw["inner_cnf_y_n"]))
        delta_probe = probe_force - zero_probe
        delta_interface = interface_force - zero_inner
        pressure_area_force = p * pa_per_mmhg * ac5 * 1e-6
        if p > 0.0:
            tau = delta_interface / delta_probe
            chi = pressure_area_force / delta_interface
            eta = tau * chi
            direct_gain = tau * ka
            direct_iop = direct_gain * q
            factorization_error = eta - p / (ka * q)
        else:
            tau = chi = eta = direct_gain = factorization_error = math.nan
            direct_iop = 0.0
        rows.append({
            "input_iop_mmhg": p,
            "actual_indent_mm": float(raw["actual_indent_mm"]),
            "delta_probe_pressure_mmhg": q,
            "probe_force_n": probe_force,
            "probe_contact_force_n": abs(float(raw["outer_cnf_y_n"])),
            "probe_contact_reaction_relative_error": float(raw["probe_contact_reaction_relative_error"]),
            "eyelid_cornea_interface_force_n": interface_force,
            "eyelid_cornea_tangential_y_n": float(raw["inner_cnt_y_n"]),
            "support_reaction_y_n": float(raw["support_rf_y_n"]),
            "delta_probe_force_n": delta_probe,
            "delta_interface_force_n": delta_interface,
            "ac5_mm2": ac5,
            "ka_ap_over_ac5": ka,
            "pressure_times_ac5_force_n": pressure_area_force,
            "tau_interface_delta": tau,
            "chi_pressure_equivalence": chi,
            "eta_effective_factorized": eta,
            "direct_gain_tau_times_ka": direct_gain,
            "direct_area_interface_iop_mmhg": direct_iop,
            "factorization_error": factorization_error,
            "outer_contact_area_mm2": float(raw["outer_contact_area_m2"]) * 1e6,
            "inner_bonded_contact_area_mm2": float(raw["inner_contact_area_m2"]) * 1e6,
            "source_state_json": source_states[pressure_key(p)],
        })

    nonzero = rows[1:]
    stable = [row for row in rows if float(row["input_iop_mmhg"]) >= 10.0]
    direct_fit = linear_fit(
        [float(row["input_iop_mmhg"]) for row in stable],
        [float(row["direct_gain_tau_times_ka"]) for row in stable],
    )
    direct_b = direct_fit["intercept"]
    direct_a = direct_fit["slope_per_mmhg"]
    for row in rows:
        row["direct_rational_iop_mmhg"] = rational(
            float(row["delta_probe_pressure_mmhg"]), direct_a, direct_b
        )
        row["direct_rational_error_mmhg"] = (
            float(row["direct_rational_iop_mmhg"]) - float(row["input_iop_mmhg"])
        )
    qc = {
        "all_pressures_present": len(rows) == len(pressures),
        "all_mapdl_error_counts_zero": all(int(row["mapdl_error_count"]) == 0 for row in raw_rows),
        "all_probe_contact_reaction_checks_pass": all(
            float(row["probe_contact_reaction_relative_error"])
            <= float(acceptance["maximum_probe_contact_reaction_relative_error"])
            for row in raw_rows
        ),
        "probe_force_matches_fe_summary": all(
            abs(float(row["probe_force_n"]) - float(fe_rows[float(row["input_iop_mmhg"])]["probe_force_n"]))
            <= 1e-8
            for row in rows
        ),
        "factorization_identity_pass": all(abs(float(row["factorization_error"])) <= 1e-12 for row in nonzero),
    }
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_id": spec["experiment_id"],
        "phase": spec["phase"],
        "campaign_pass": all(qc.values()),
        "qc": qc,
        "zero_references": {
            "probe_force_n": zero_probe,
            "eyelid_cornea_interface_force_n": zero_inner,
        },
        "direct_interface_forward_model": {
            "definition": "tau_interface=delta_interface_force/delta_probe_force; gain=tau_interface*Aprobe/Ac5",
            "stable_fit_min_iop_mmhg": 10.0,
            "a_per_mmhg": direct_a,
            "b_dimensionless": direct_b,
            "gain_linear_r_squared": direct_fit["r_squared"],
            "metrics_all_points": error_metrics(rows, "direct_rational_iop_mmhg"),
        },
        "interpretation": spec["interpretation"],
        "source_states": source_states,
        "rows": rows,
    }
    analysis = output / "analysis"
    analysis.mkdir(exist_ok=True)
    json_path = analysis / "interface_force_integrals_summary.json"
    csv_path = analysis / "interface_force_integrals_summary.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "campaign_pass": payload["campaign_pass"],
        "qc": qc,
        "direct_interface_forward_model": payload["direct_interface_forward_model"],
        "output_json": str(json_path),
        "output_csv": str(csv_path),
    }, ensure_ascii=False, indent=2))
    return 0 if payload["campaign_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
