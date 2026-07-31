#!/usr/bin/env python3
"""Combine newly solved pressures with an accepted FE pressure grid."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

STATE_NAMES = ("primary_0p26", "sensitivity_0p28")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def num(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite {name}: {value!r}")
    return result


def close(left: object, right: object, tolerance: float = 1e-12) -> bool:
    return math.isclose(num(left, "left"), num(right, "right"), rel_tol=0.0, abs_tol=tolerance)


def manifest_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected one manifest row in {path}, found {len(rows)}")
    return rows[0]


def pressure_key(pressure: float) -> str:
    return f"{pressure:g}".replace(".", "p")


def state_path(root: Path, pressure: float, state_name: str) -> Path:
    return root / "states" / f"iop{pressure_key(pressure)}" / state_name / "geometry_state.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-spec", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_root.expanduser().resolve()
    spec = load_json(args.run_spec.expanduser().resolve())
    source_spec = spec.get("reused_pressure_grid", spec.get("reused_formal_matrix"))
    if not source_spec:
        raise ValueError("run specification is missing a reused pressure grid")
    source_summary_path = Path(source_spec["summary_json"])
    source = load_json(source_summary_path)
    if not source.get("campaign_pass"):
        raise ValueError("reused formal campaign did not pass")

    final_grid = tuple(num(value, "final pressure") for value in spec["final_pressure_grid_mmhg"])
    step = num(spec.get("pressure_step_mmhg", 5.0), "pressure step")
    if step <= 0.0 or not final_grid or not close(final_grid[0], 0.0):
        raise ValueError(f"invalid final pressure grid for step {step:g}: {final_grid}")
    maximum_pressure = final_grid[-1]
    interval_count = round(maximum_pressure / step)
    expected_grid = tuple(index * step for index in range(interval_count + 1))
    if not close(interval_count * step, maximum_pressure) or final_grid != expected_grid:
        raise ValueError(f"unexpected final pressure grid for step {step:g}: {final_grid}")
    new_pressures = tuple(num(value, "new pressure") for value in spec["new_solver_pressures_mmhg"])
    reused_pressures = tuple(num(value, "reused pressure") for value in source_spec["pressures_mmhg"])
    old_rows = {
        (row["state"], num(row["input_iop_mmhg"], "old pressure")): row
        for row in source["rows"]
    }
    for state_name in STATE_NAMES:
        for pressure in reused_pressures:
            if (state_name, pressure) not in old_rows:
                raise ValueError(f"missing reused row: {state_name}, {pressure:g}")

    criteria = spec["acceptance"]
    expected_materials = spec["absolute_material_parameters"]
    reference_metadata_path = Path(
        spec.get("reference_apdl_run_metadata", source_spec.get("reference_apdl_run_metadata", ""))
    )
    if not reference_metadata_path.is_file():
        fallback_root = source_spec.get("data_root")
        reference_metadata_path = Path(fallback_root) / "iop0" / "run" / "run_metadata.json" if fallback_root else reference_metadata_path
    reference_metadata = load_json(reference_metadata_path)
    reference_apdl_hash = reference_metadata["apdl_sha256"]
    qc: dict[str, bool] = {"reused_formal_campaign_pass": True}
    new_states: dict[tuple[str, float], dict] = {}
    source_manifests: dict[str, str] = {}
    for pressure in new_pressures:
        key = pressure_key(pressure)
        case_root = root / f"iop{key}"
        mpath = case_root / "run" / "run_manifest.csv"
        row = manifest_row(mpath)
        metadata = load_json(case_root / "run" / "run_metadata.json")
        prefix = f"iop{key}"
        source_manifests[prefix] = str(mpath)
        qc[f"{prefix}_complete"] = row.get("status") == criteria["required_status"]
        qc[f"{prefix}_returncode_zero"] = int(num(row.get("returncode"), "returncode")) == int(criteria["required_returncode"])
        qc[f"{prefix}_ansys_errors_zero"] = int(num(row.get("ansys_error_count"), "error count")) <= int(criteria["maximum_ansys_error_count"])
        qc[f"{prefix}_three_steps_converged"] = all(
            num(row.get(field), field) >= 0.5
            for field in ("preload_converged", "approach_converged", "indentation_converged")
        )
        qc[f"{prefix}_preload_contact_zero"] = int(num(row.get("preload_contact_count"), "preload contact")) <= int(criteria["maximum_preload_contact_count"])
        qc[f"{prefix}_approach_force_ok"] = abs(num(row.get("approach_probe_fy_n"), "approach force")) <= num(criteria["maximum_absolute_approach_force_n"], "approach limit")
        qc[f"{prefix}_penetration_ok"] = num(row.get("max_penetration_m"), "penetration") * 1e3 <= num(criteria["maximum_penetration_mm"], "penetration limit")
        qc[f"{prefix}_apdl_hash_match"] = metadata["apdl_sha256"] == reference_apdl_hash
        for tissue in ("eyelid", "cornea"):
            for parameter in ("c10_mpa", "c01_mpa", "d1_pa_inv"):
                field = f"{tissue}_{parameter}"
                qc[f"{prefix}_{field}_match"] = close(row.get(field), expected_materials[tissue][parameter])
        for state_name in STATE_NAMES:
            state = load_json(state_path(root, pressure, state_name))
            new_states[state_name, pressure] = state
            target = 0.26 if state_name == "primary_0p26" else 0.28
            tolerance = num(criteria["maximum_primary_indent_error_mm"], "indent tolerance") if target == 0.26 else 1e-6
            qc[f"{prefix}_{state_name}_indent_ok"] = abs(num(state["actual_indent_mm"], "indent") - target) <= tolerance
            qc[f"{prefix}_{state_name}_load_step3"] = int(round(num(state["result_load_step"], "load step"))) == 3

    area_mm2 = num(spec["geometry"]["probe_area_mm2"], "probe area")
    pa_per_mmhg = num(spec["pressure_conversion"]["pa_per_mmhg"], "pressure conversion")
    factor = 1e6 / (area_mm2 * pa_per_mmhg)
    rows: list[dict[str, object]] = []
    state_summaries: dict[str, dict[str, object]] = {}
    for state_name in STATE_NAMES:
        zero_force = num(old_rows[state_name, 0.0]["probe_force_n"], "zero force")
        model = spec["frozen_sensor_models_for_diagnostic_only"][state_name]
        alpha = num(model["alpha"], "alpha")
        beta = num(model["beta_per_mmhg"], "beta")
        state_rows: list[dict[str, object]] = []
        for pressure in final_grid:
            if (state_name, pressure) in old_rows:
                old = old_rows[state_name, pressure]
                force = num(old["probe_force_n"], "old force")
                indent = num(old["actual_indent_mm"], "old indent")
                ae = num(old["outer_ae_lower_mm2"], "old Ae")
                ac = num(old["inner_ac_5deg_mm2"], "old Ac")
                kgeo = num(old["kgeo_5deg"], "old Kgeo")
                source_kind = "reused_formal_matrix"
                source_commit = old.get("source_git_commit", "")
            else:
                state = new_states[state_name, pressure]
                force = num(state["probe_force_n"], "new force")
                indent = num(state["actual_indent_mm"], "new indent")
                ae = num(state["outer_ae_lower_mm2"], "new Ae")
                ac = num(state["inner_ac_5deg_mm2"], "new Ac")
                kgeo = num(state["kgeo_5deg"], "new Kgeo")
                source_kind = "new_supplemental_solver"
                source_commit = state.get("source_git_commit", "")
            delta_force = force - zero_force
            delta_pressure = delta_force * factor
            if pressure == 0.0:
                ksensor: float | str = ""
                iop_calc = 0.0
                iop_error = 0.0
            else:
                if delta_pressure <= 0.0:
                    raise ValueError(f"non-positive delta probe pressure at {pressure:g} mmHg")
                ksensor = pressure / delta_pressure
                denominator = 1.0 - beta * delta_pressure
                iop_calc = alpha * delta_pressure / denominator if denominator > 0 else float("nan")
                iop_error = iop_calc - pressure
            item: dict[str, object] = {
                "state": state_name,
                "input_iop_mmhg": pressure,
                "actual_indent_mm": indent,
                "probe_force_n": force,
                "zero_reference_force_n": zero_force,
                "delta_force_n": delta_force,
                "delta_probe_pressure_mmhg": delta_pressure,
                "ksensor_delta": ksensor,
                "frozen_model_iop_calc_diagnostic_mmhg": iop_calc,
                "frozen_model_iop_error_diagnostic_mmhg": iop_error,
                "outer_ae_lower_mm2": ae,
                "inner_ac_5deg_mm2": ac,
                "kgeo_5deg": kgeo,
                "source_kind": source_kind,
                "source_git_commit": source_commit,
            }
            rows.append(item)
            state_rows.append(item)
        forces = [num(row["probe_force_n"], "force") for row in state_rows]
        deltas = [num(row["delta_probe_pressure_mmhg"], "delta pressure") for row in state_rows]
        force_monotonic = all(right > left for left, right in zip(forces, forces[1:]))
        delta_monotonic = all(right > left for left, right in zip(deltas, deltas[1:]))
        qc[f"{state_name}_probe_force_monotonic"] = force_monotonic
        qc[f"{state_name}_delta_pressure_monotonic"] = delta_monotonic
        interval_gains = []
        for left, right in zip(state_rows, state_rows[1:]):
            dp = num(right["input_iop_mmhg"], "right pressure") - num(left["input_iop_mmhg"], "left pressure")
            interval_gains.append({
                "from_iop_mmhg": left["input_iop_mmhg"],
                "to_iop_mmhg": right["input_iop_mmhg"],
                "delta_probe_pressure_gain_per_mmhg": (
                    num(right["delta_probe_pressure_mmhg"], "right delta")
                    - num(left["delta_probe_pressure_mmhg"], "left delta")
                ) / dp,
            })
        state_summaries[state_name] = {
            "zero_reference_force_n": zero_force,
            "probe_force_monotonic_increasing": force_monotonic,
            "delta_probe_pressure_monotonic_increasing": delta_monotonic,
            "interval_gains": interval_gains,
        }

    campaign_pass = all(qc.values())
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_id": spec["experiment_id"],
        "phase": spec["phase"],
        "campaign_pass": campaign_pass,
        "pressure_factor_mmhg_per_n": factor,
        "final_pressure_grid_mmhg": list(final_grid),
        "plotted_pressure_grid_mmhg": spec["plotted_pressure_grid_mmhg"],
        "qc": qc,
        "state_summaries": state_summaries,
        "rows": rows,
        "new_source_manifests": source_manifests,
        "reused_formal_summary": str(source_summary_path),
        "interpretation": spec["interpretation"],
    }
    analysis = root / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    output_stem = spec.get("analysis_output_stem", "iop_5_to_50_summary")
    output_json = analysis / f"{output_stem}.json"
    output_csv = analysis / f"{output_stem}.csv"
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "campaign_pass": campaign_pass,
        "output_json": str(output_json),
        "output_csv": str(output_csv),
        "state_summaries": state_summaries,
    }, ensure_ascii=False, indent=2))
    return 0 if campaign_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
