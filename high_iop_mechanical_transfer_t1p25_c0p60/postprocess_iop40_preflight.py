#!/usr/bin/env python3
"""Summarize the 40 mmHg convergence preflight at 0.26 and 0.28 mm.

The same-campaign zero-IOP case is intentionally not available in phase 1.
Consequently, Ksensor values use the frozen historical F0 only as a provisional
convergence diagnostic and are explicitly marked as non-formal.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def number(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite {name}: {value!r}")
    return result


def flag(value: object) -> bool:
    return number(value, "boolean flag") >= 0.5


def load_single_manifest_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected one manifest row in {path}, found {len(rows)}")
    return rows[0]


def observation(
    *,
    label: str,
    indent_mm: float,
    force_n: float,
    model: dict[str, float],
    pressure_factor_mmhg_per_n: float,
    input_iop_mmhg: float,
) -> dict[str, float | str | bool]:
    zero_force_n = number(model["historical_zero_iop_force_n_for_preflight_only"], "F0")
    delta_force_n = force_n - zero_force_n
    total_pressure_mmhg = force_n * pressure_factor_mmhg_per_n
    zero_pressure_mmhg = zero_force_n * pressure_factor_mmhg_per_n
    delta_pressure_mmhg = delta_force_n * pressure_factor_mmhg_per_n
    alpha = number(model["alpha"], "alpha")
    beta = number(model["beta_per_mmhg"], "beta")
    denominator = 1.0 - beta * delta_pressure_mmhg
    if delta_pressure_mmhg <= 0 or denominator <= 0:
        raise ValueError(
            f"invalid provisional inversion at {label}: q={delta_pressure_mmhg}, denominator={denominator}"
        )
    ksensor = input_iop_mmhg / delta_pressure_mmhg
    iop_calc = alpha * delta_pressure_mmhg / denominator
    expected_force = number(model["expected_force_n"], "expected force")
    return {
        "state": label,
        "indent_mm": indent_mm,
        "probe_force_n": force_n,
        "probe_total_equivalent_pressure_mmhg": total_pressure_mmhg,
        "historical_zero_reference_force_n_preflight_only": zero_force_n,
        "historical_zero_reference_pressure_mmhg_preflight_only": zero_pressure_mmhg,
        "delta_force_n_preflight_only": delta_force_n,
        "delta_probe_pressure_mmhg_preflight_only": delta_pressure_mmhg,
        "provisional_ksensor": ksensor,
        "provisional_iop_calc_mmhg": iop_calc,
        "provisional_iop_error_mmhg": iop_calc - input_iop_mmhg,
        "expected_force_n": expected_force,
        "force_relative_error_vs_prediction": (force_n - expected_force) / expected_force,
        "formal_ksensor_ready": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--state-json", type=Path, required=True)
    parser.add_argument("--run-spec", type=Path, required=True)
    args = parser.parse_args()

    root = args.run_root.expanduser().resolve()
    manifest_path = root / "run" / "run_manifest.csv"
    row = load_single_manifest_row(manifest_path)
    state = json.loads(args.state_json.expanduser().resolve().read_text(encoding="utf-8"))
    spec = json.loads(args.run_spec.expanduser().resolve().read_text(encoding="utf-8"))

    area_mm2 = number(spec["geometry"]["probe_area_mm2"], "probe area")
    pa_per_mmhg = number(spec["pressure"]["pa_per_mmhg"], "Pa per mmHg")
    input_iop = number(spec["pressure"]["iop_mmhg"], "input IOP")
    pressure_factor = 1e6 / (area_mm2 * pa_per_mmhg)
    models = spec["frozen_sensor_models"]

    primary = observation(
        label="primary_0p26",
        indent_mm=number(state["actual_indent_mm"], "actual primary indent"),
        force_n=number(state["probe_force_n"], "primary force"),
        model=models["primary_0p259875_mm"],
        pressure_factor_mmhg_per_n=pressure_factor,
        input_iop_mmhg=input_iop,
    )
    sensitivity = observation(
        label="sensitivity_0p28",
        indent_mm=number(row["indent_mm"], "final indent"),
        force_n=abs(number(row["probe_fy_n"], "final probe force")),
        model=models["sensitivity_0p28_mm"],
        pressure_factor_mmhg_per_n=pressure_factor,
        input_iop_mmhg=input_iop,
    )

    criteria = spec["preflight_acceptance"]
    checks = {
        "manifest_status_complete": row.get("status") == criteria["required_status"],
        "returncode_zero": int(number(row.get("returncode"), "return code")) == 0,
        "ansys_error_count_zero": int(number(row.get("ansys_error_count"), "error count"))
        <= int(criteria["maximum_ansys_error_count"]),
        "preload_converged": flag(row.get("preload_converged")),
        "approach_converged": flag(row.get("approach_converged")),
        "indentation_converged": flag(row.get("indentation_converged")),
        "preload_contact_zero": int(number(row.get("preload_contact_count"), "preload contact count"))
        <= int(criteria["maximum_preload_contact_count"]),
        "preload_clearance_positive": number(row.get("preload_clearance_m"), "preload clearance") > 0,
        "approach_force_within_limit": abs(number(row.get("approach_probe_fy_n"), "approach force"))
        <= number(criteria["maximum_absolute_approach_force_n"], "approach limit"),
        "penetration_within_limit": number(row.get("max_penetration_m"), "penetration") * 1e3
        <= number(criteria["maximum_penetration_mm"], "penetration limit"),
        "primary_indent_within_limit": abs(number(state["indent_error_mm"], "indent error"))
        <= number(criteria["maximum_primary_indent_error_mm"], "indent limit"),
        "primary_result_is_load_step_3": int(round(number(state["result_load_step"], "load step"))) == 3,
        "primary_provisional_iop_within_expected_range": (
            number(criteria["expected_iop_calc_range_mmhg"][0], "IOP lower")
            <= number(primary["provisional_iop_calc_mmhg"], "primary IOP result")
            <= number(criteria["expected_iop_calc_range_mmhg"][1], "IOP upper")
        ),
    }
    passed = all(checks.values())

    attempt_dir = root / "run" / row["attempt_dir"]
    result_rst = root / "run" / row["result_rst"]
    result_db = attempt_dir / f"{result_rst.stem}.db"
    files = {
        "manifest": str(manifest_path),
        "attempt_dir": str(attempt_dir),
        "result_rst": str(result_rst),
        "result_db": str(result_db),
        "rst_exists": result_rst.is_file(),
        "db_exists": result_db.is_file(),
    }
    checks["primary_rst_and_db_retained"] = bool(files["rst_exists"] and files["db_exists"])
    passed = all(checks.values())

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_id": spec["experiment_id"],
        "phase": spec["phase"],
        "input_iop_mmhg": input_iop,
        "input_iop_pa": number(spec["pressure"]["iop_pa"], "input IOP Pa"),
        "git_commit": row.get("git_commit"),
        "attempt_count": int(number(row.get("attempt_count"), "attempt count")),
        "elapsed_seconds": number(row.get("elapsed_seconds"), "elapsed time"),
        "preflight_pass": passed,
        "checks": checks,
        "files": files,
        "absolute_material_parameters": spec["absolute_material_parameters"],
        "observations": [primary, sensitivity],
        "warning": (
            "Ksensor and IOP_calc are provisional because phase 1 uses historical F0. "
            "Recompute with the same-campaign zero-IOP case before formal interpretation."
        ),
    }

    analysis = root / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "iop40_preflight_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = list(primary.keys())
    with (analysis / "iop40_preflight_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([primary, sensitivity])
    print(json.dumps({
        "preflight_pass": passed,
        "attempt_count": payload["attempt_count"],
        "elapsed_seconds": payload["elapsed_seconds"],
        "primary": primary,
        "sensitivity": sensitivity,
        "analysis": str(analysis),
    }, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
