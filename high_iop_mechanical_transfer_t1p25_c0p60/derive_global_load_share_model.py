#!/usr/bin/env python3
"""Derive a rational IOP model from global pressure-load sharing.

This is a mechanism derivation, not an independent validation: the stiffness/load-
share coefficients are identified from the retained FE pressure states.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "20260731_3ce7c957_interface_force_integrals_summary.json"
DEFAULT_INVERSE = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
DEFAULT_JSON = ROOT / "results" / "20260731_global_load_share_derivation.json"
DEFAULT_CSV = ROOT / "results" / "20260731_global_load_share_derivation.csv"
MMHG_TO_PA = 133.322387415
PROBE_AREA_MM2 = 14.6574147


def linear_fit(xs: list[float], ys: list[float]) -> dict[str, float]:
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("linear fit requires at least three paired points")
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx <= 0.0:
        raise ValueError("zero x variance")
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
    intercept = ybar - slope * xbar
    predictions = [intercept + slope * x for x in xs]
    ss_res = sum((y - prediction) ** 2 for y, prediction in zip(ys, predictions))
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    return {
        "intercept": intercept,
        "slope_per_mmhg": slope,
        "r_squared": 1.0 - ss_res / ss_tot,
    }


def rational(q: float, a: float, b: float) -> float:
    denominator = 1.0 - a * q
    if denominator <= 0.0:
        return math.nan
    return b * q / denominator


def metrics(rows: Iterable[dict], a: float, b: float, minimum_iop_mmhg: float) -> dict[str, float | int]:
    errors = []
    for row in rows:
        if row["input_iop_mmhg"] < minimum_iop_mmhg:
            continue
        prediction = rational(row["delta_probe_pressure_mmhg"], a, b)
        errors.append(prediction - row["input_iop_mmhg"])
    return {
        "point_count": len(errors),
        "mae_mmhg": sum(abs(error) for error in errors) / len(errors),
        "rmse_mmhg": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "maximum_absolute_error_mmhg": max(abs(error) for error in errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--inverse-json", type=Path, default=DEFAULT_INVERSE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--fit-min-iop", type=float, default=10.0)
    args = parser.parse_args()

    source = json.loads(args.input_json.read_text(encoding="utf-8"))
    inverse = json.loads(args.inverse_json.read_text(encoding="utf-8"))
    if not source.get("campaign_pass"):
        raise ValueError("source RST integration campaign did not pass")
    source_rows = source["rows"]
    if len(source_rows) != 21 or source_rows[0]["input_iop_mmhg"] != 0.0:
        raise ValueError("expected frozen 21-point grid beginning at zero")

    probe_area_mm2 = PROBE_AREA_MM2
    cornea_radius_mm = 7.8
    cornea_thickness_mm = 0.6
    outer_edge_radius_mm = 6.0
    inner_edge_radius_mm = outer_edge_radius_mm * (cornea_radius_mm - cornea_thickness_mm) / cornea_radius_mm
    geometric_projected_area_mm2 = math.pi * inner_edge_radius_mm**2

    zero = source_rows[0]
    # Signed global equilibrium in model Y: -Fprobe + Fsupport + Fpressure = 0.
    # Remove the tiny p=0 balance residual before calculating pressure force.
    zero_balance_residual_n = zero["probe_force_n"] - zero["support_reaction_y_n"]
    rows = []
    for source_row in source_rows:
        pressure = float(source_row["input_iop_mmhg"])
        pressure_force_n = (
            source_row["probe_force_n"]
            - source_row["support_reaction_y_n"]
            - zero_balance_residual_n
        )
        if pressure > 0.0:
            projected_area_mm2 = pressure_force_n / (pressure * MMHG_TO_PA) * 1.0e6
            capture_fraction = source_row["delta_probe_force_n"] / pressure_force_n
            inverse_capture = 1.0 / capture_fraction
            reconstructed_chi = source_row["ac5_mm2"] / (
                source_row["tau_interface_delta"] * capture_fraction * projected_area_mm2
            )
        else:
            pressure_force_n = 0.0
            projected_area_mm2 = None
            capture_fraction = None
            inverse_capture = None
            reconstructed_chi = None
        rows.append(
            {
                "input_iop_mmhg": pressure,
                "delta_probe_pressure_mmhg": source_row["delta_probe_pressure_mmhg"],
                "delta_probe_force_n": source_row["delta_probe_force_n"],
                "global_iop_projected_force_n": pressure_force_n,
                "global_iop_projected_area_mm2": projected_area_mm2,
                "probe_capture_fraction_lambda": capture_fraction,
                "inverse_capture_fraction": inverse_capture,
                "tau_interface_delta": source_row["tau_interface_delta"] if pressure > 0.0 else None,
                "chi_from_original_factorization": source_row["chi_pressure_equivalence"] if pressure > 0.0 else None,
                "chi_reconstructed_from_global_share": reconstructed_chi,
                "ac5_mm2": source_row["ac5_mm2"],
            }
        )

    stable = [row for row in rows if row["input_iop_mmhg"] >= args.fit_min_iop]
    share_fit = linear_fit(
        [row["input_iop_mmhg"] for row in stable],
        [row["inverse_capture_fraction"] for row in stable],
    )
    c0 = share_fit["intercept"]
    c1 = share_fit["slope_per_mmhg"]
    lambda_zero_extrapolated = 1.0 / c0
    pressure_stiffening_gamma = c1 / c0
    boundary_to_probe_stiffness_ratio_zero = c0 - 1.0

    positive_areas = [row["global_iop_projected_area_mm2"] for row in rows if row["input_iop_mmhg"] > 0.0]
    stable_areas = [row["global_iop_projected_area_mm2"] for row in stable]
    balance_area_mean_all = sum(positive_areas) / len(positive_areas)
    balance_area_mean_stable = sum(stable_areas) / len(stable_areas)

    def parameters(area_mm2: float) -> dict[str, float | dict]:
        a = probe_area_mm2 * c1 / area_mm2
        b = probe_area_mm2 * c0 / area_mm2
        return {
            "a_per_mmhg": a,
            "b_dimensionless": b,
            "asymptotic_probe_pressure_mmhg": 1.0 / a,
            "metrics_all_0_to_50": metrics(rows, a, b, 0.0),
            "metrics_stable_10_to_50": metrics(rows, a, b, args.fit_min_iop),
        }

    geometric_parameters = parameters(geometric_projected_area_mm2)
    balance_parameters = parameters(balance_area_mean_stable)
    ai = float(inverse["parameters"]["a_per_mmhg"])
    bi = float(inverse["parameters"]["b_dimensionless"])

    max_chi_identity_error = max(
        abs(row["chi_reconstructed_from_global_share"] - row["chi_from_original_factorization"])
        for row in rows
        if row["input_iop_mmhg"] > 0.0
    )
    for row in rows:
        pressure = row["input_iop_mmhg"]
        row["inverse_capture_fit"] = c0 + c1 * pressure
        row["capture_fraction_fit"] = 1.0 / row["inverse_capture_fit"]
        row["boundary_to_probe_stiffness_ratio_fit"] = row["inverse_capture_fit"] - 1.0
        row["geometric_forward_iop_mmhg"] = rational(
            row["delta_probe_pressure_mmhg"],
            geometric_parameters["a_per_mmhg"],
            geometric_parameters["b_dimensionless"],
        )
        row["geometric_forward_error_mmhg"] = row["geometric_forward_iop_mmhg"] - pressure

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "mechanism_derivation_not_independent_validation",
        "source_json": str(args.input_json.resolve()),
        "fit_range_mmhg": [args.fit_min_iop, 50.0],
        "definitions": {
            "global_pressure_force": "F_iop=Fprobe_reaction-Fsupport_reaction-zero_balance_residual",
            "capture_fraction": "lambda=delta_Fprobe/F_iop",
            "spring_load_share": "lambda=kp/(kp+kb)=1/(c0+c1*p)",
            "rational_forward": "p=b*q/(1-a*q)",
            "parameter_map": "b=Ap*c0/Aiop_proj; a=Ap*c1/Aiop_proj",
            "chi_identity": "chi=Ac5/(tau_interface*lambda*Aiop_proj)",
            "collapsed_total_model": "p=Ap/(lambda*Aiop_proj)*q",
        },
        "configuration": {
            "probe_area_mm2": probe_area_mm2,
            "cornea_radius_mm": cornea_radius_mm,
            "cornea_thickness_mm": cornea_thickness_mm,
            "outer_edge_radius_mm": outer_edge_radius_mm,
            "inner_pressure_edge_radius_mm": inner_edge_radius_mm,
            "geometric_iop_projected_area_mm2": geometric_projected_area_mm2,
            "zero_balance_residual_n": zero_balance_residual_n,
        },
        "projected_area_validation": {
            "balance_area_min_mm2": min(positive_areas),
            "balance_area_mean_all_mm2": balance_area_mean_all,
            "balance_area_mean_stable_mm2": balance_area_mean_stable,
            "balance_area_max_mm2": max(positive_areas),
            "geometric_vs_stable_balance_relative_difference": geometric_projected_area_mm2 / balance_area_mean_stable - 1.0,
        },
        "load_share_fit": {
            "c0_dimensionless": c0,
            "c1_per_mmhg": c1,
            "r_squared": share_fit["r_squared"],
            "lambda_zero_stable_extrapolation": lambda_zero_extrapolated,
            "gamma_per_mmhg": pressure_stiffening_gamma,
            "kb0_over_kp": boundary_to_probe_stiffness_ratio_zero,
            "d_kb_over_kp_per_mmhg": c1,
        },
        "geometric_forward_parameters": geometric_parameters,
        "balance_area_sensitivity_parameters": balance_parameters,
        "inverse_regression_reference": {
            "a_per_mmhg": ai,
            "b_dimensionless": bi,
            "geometric_a_relative_difference": geometric_parameters["a_per_mmhg"] / ai - 1.0,
            "geometric_b_relative_difference": geometric_parameters["b_dimensionless"] / bi - 1.0,
        },
        "qc": {
            "source_campaign_pass": bool(source["campaign_pass"]),
            "projected_area_geometry_agrees_with_balance_below_0p5pct": abs(geometric_projected_area_mm2 / balance_area_mean_stable - 1.0) < 0.005,
            "inverse_capture_linear_r_squared_above_0p99": share_fit["r_squared"] > 0.99,
            "chi_factorization_identity_below_1e_minus_6": max_chi_identity_error < 1.0e-6,
            "maximum_chi_identity_error": max_chi_identity_error,
        },
        "rows": rows,
    }
    payload["derivation_pass"] = all(value for key, value in payload["qc"].items() if key != "maximum_chi_identity_error")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "derivation_pass": payload["derivation_pass"],
        "geometric_projected_area_mm2": geometric_projected_area_mm2,
        "balance_projected_area_stable_mm2": balance_area_mean_stable,
        "load_share_fit": payload["load_share_fit"],
        "geometric_forward_parameters": geometric_parameters,
        "inverse_comparison": payload["inverse_regression_reference"],
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
    }, ensure_ascii=False, indent=2))
    return 0 if payload["derivation_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
