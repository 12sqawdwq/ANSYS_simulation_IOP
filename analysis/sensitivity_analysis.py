from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from common import cv, load_config, output_dir, read_csv, write_csv
from fit_pressure_model import rational_inverse


def log_sensitivity(thickness: np.ndarray, values: np.ndarray) -> dict[str, float]:
    thickness = np.asarray(thickness, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = np.isfinite(thickness) & np.isfinite(values) & (thickness > 0) & (values > 0)
    x = np.log(thickness[mask])
    y = np.log(values[mask])
    model = sm.OLS(y, sm.add_constant(x)).fit()
    critical = float(stats.t.ppf(0.975, model.df_resid))
    slope = float(model.params[1])
    se = float(model.bse[1])
    return {
        "log_sensitivity": slope,
        "sensitivity_se": se,
        "sensitivity_ci95_low": slope - critical * se,
        "sensitivity_ci95_high": slope + critical * se,
        "log_log_r2": float(model.rsquared),
        "log_log_p_value": float(model.pvalues[1]),
    }


def describe_thickness_effect(
    name: str,
    unit: str,
    thickness: np.ndarray,
    values: np.ndarray,
    reference_thickness: float,
    interpretation: str,
) -> dict:
    thickness = np.asarray(thickness, dtype=float)
    values = np.asarray(values, dtype=float)
    ref_idx = int(np.argmin(np.abs(thickness - reference_thickness)))
    reference = float(values[ref_idx])
    return {
        "output": name,
        "unit": unit,
        "status": "estimable_single_factor",
        "reference_thickness_mm": float(thickness[ref_idx]),
        "reference_value": reference,
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "relative_range_over_reference": float((np.max(values) - np.min(values)) / reference),
        "maximum_relative_deviation_from_reference": float(np.max(np.abs(values - reference) / abs(reference))),
        "coefficient_of_variation": cv(values),
        **log_sensitivity(thickness, values),
        "interpretation": interpretation,
    }


def metrics(frame: pd.DataFrame, error_column: str, true_column: str = "actual_iop_mmhg") -> dict:
    error = frame[error_column].to_numpy(float)
    true = frame[true_column].to_numpy(float)
    relative = np.abs(error) / np.where(true == 0, np.nan, np.abs(true))
    return {
        "n": len(frame),
        "mae_mmhg": float(np.nanmean(np.abs(error))),
        "rmse_mmhg": float(np.sqrt(np.nanmean(error**2))),
        "maximum_absolute_error_mmhg": float(np.nanmax(np.abs(error))),
        "mean_absolute_relative_error": float(np.nanmean(relative)),
        "maximum_absolute_relative_error": float(np.nanmax(relative)),
    }


def unavailable_parameter_rows(config: dict) -> pd.DataFrame:
    names = [
        ("a", "1/mmHg"),
        ("b", "1"),
        ("G0=1/b", "1"),
        ("lambda=a/b", "1/mmHg"),
    ]
    return pd.DataFrame(
        [
            {
                "output": name,
                "unit": unit,
                "status": "not_identifiable_across_thickness",
                "log_sensitivity": np.nan,
                "relative_range_over_reference": np.nan,
                "maximum_relative_deviation_from_reference": np.nan,
                "coefficient_of_variation": np.nan,
                "interpretation": "Only one nonzero pressure is available per non-reference thickness; two rational parameters cannot be separated.",
            }
            for name, unit in names
        ]
    )


def run(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    out = output_dir(config)
    endpoint = read_csv(config, "thickness_pressure_endpoints").sort_values("eyelid_thickness_mm").copy()
    fitted = pd.read_csv(out / "fitted_parameters.csv")
    state = "sensitivity_0p28"
    calibration = fitted[(fitted["state"] == state) & (fitted["fit_status"] == "success")].iloc[0]
    g0 = float(calibration["g0_1_over_b"])
    lam = float(calibration["lambda_a_over_b_per_mmhg"])

    endpoint["g_eff_at_20"] = endpoint["delta_probe_pressure_mmhg"] / endpoint["actual_iop_mmhg"]
    endpoint["shared_calibration_iop_mmhg"] = rational_inverse(
        endpoint["delta_probe_pressure_mmhg"].to_numpy(float), g0, lam
    )
    endpoint["shared_calibration_denominator"] = g0 - lam * endpoint["delta_probe_pressure_mmhg"]
    endpoint["shared_calibration_error_mmhg"] = (
        endpoint["shared_calibration_iop_mmhg"] - endpoint["actual_iop_mmhg"]
    )
    reference_thickness = float(config["geometry"]["reference_thickness_mm"])
    reference_prediction = float(
        endpoint.loc[np.isclose(endpoint["eyelid_thickness_mm"], reference_thickness), "shared_calibration_iop_mmhg"].iloc[0]
    )
    endpoint["thickness_attributable_iop_shift_mmhg"] = endpoint["shared_calibration_iop_mmhg"] - reference_prediction
    endpoint["absolute_relative_error"] = (
        endpoint["shared_calibration_error_mmhg"].abs() / endpoint["actual_iop_mmhg"]
    )
    endpoint["parameter_source"] = "shared G0 and lambda fitted only at h=1.25 mm, state sensitivity_0p28"

    h = endpoint["eyelid_thickness_mm"].to_numpy(float)
    descriptions = [
        describe_thickness_effect(
            "zero_iop_baseline_force",
            "N",
            h,
            endpoint["force_zero_baseline_n"].to_numpy(float),
            reference_thickness,
            "direct total-force baseline",
        ),
        describe_thickness_effect(
            "total_probe_force_at_20",
            "N",
            h,
            endpoint["force_iop_n"].to_numpy(float),
            reference_thickness,
            "direct total probe reaction",
        ),
        describe_thickness_effect(
            "delta_probe_force_at_20",
            "N",
            h,
            endpoint["delta_force_n"].to_numpy(float),
            reference_thickness,
            "zero-referenced IOP-induced force increment",
        ),
        describe_thickness_effect(
            "P_probe_delta_at_20",
            "mmHg",
            h,
            endpoint["delta_probe_pressure_mmhg"].to_numpy(float),
            reference_thickness,
            "direct zero-referenced pressure-like readout",
        ),
        describe_thickness_effect(
            "G_eff_at_20=P_probe/P_IOP",
            "1",
            h,
            endpoint["g_eff_at_20"].to_numpy(float),
            reference_thickness,
            "single-pressure effective gain G0/(1+20 lambda); it is not G0",
        ),
        describe_thickness_effect(
            "shared_calibration_iop_prediction",
            "mmHg",
            h,
            endpoint["shared_calibration_iop_mmhg"].to_numpy(float),
            reference_thickness,
            "20-mmHg prediction using the h=1.25-mm shared rational calibration",
        ),
    ]
    observed = pd.DataFrame(descriptions)
    sensitivity = pd.concat([unavailable_parameter_rows(config), observed], ignore_index=True, sort=False)

    thresholds = config["thresholds"]
    proxy = observed[observed["output"] == "G_eff_at_20=P_probe/P_IOP"].iloc[0]
    overall_error = metrics(endpoint, "shared_calibration_error_mmhg")
    thickness_error = metrics(endpoint, "thickness_attributable_iop_shift_mmhg")
    proxy_threshold = {
        "quantity": "G_eff_at_20 proxy",
        "is_exact_requested_parameter": False,
        "abs_log_sensitivity": abs(float(proxy["log_sensitivity"])),
        "max_relative_deviation": float(proxy["maximum_relative_deviation_from_reference"]),
        "iop_mae_mmhg": thickness_error["mae_mmhg"],
        "total_calibration_mae_mmhg": overall_error["mae_mmhg"],
        "mean_iop_relative_error": thickness_error["mean_absolute_relative_error"],
        "total_calibration_mean_relative_error": overall_error["mean_absolute_relative_error"],
        "passes_sensitivity_threshold": abs(float(proxy["log_sensitivity"])) < thresholds["max_abs_log_sensitivity"],
        "passes_relative_deviation_threshold": float(proxy["maximum_relative_deviation_from_reference"]) < thresholds["max_relative_deviation_fraction"],
        "passes_iop_error_threshold": (
            thickness_error["mae_mmhg"] < thresholds["max_iop_mae_mmhg"]
            or thickness_error["mean_absolute_relative_error"] < thresholds["max_iop_relative_error_fraction"]
        ),
        "decision": "proxy_only_not_sufficient_for_G0_or_lambda_claim",
    }
    exact_rows = [
        {
            "quantity": quantity,
            "is_exact_requested_parameter": True,
            "decision": "not_evaluable_due_to_nonidentifiability",
        }
        for quantity in ["G0=1/b", "lambda=a/b"]
    ]
    threshold_results = pd.DataFrame([*exact_rows, proxy_threshold])

    error_rows = [
        {"scope": "thickness_scan_at_20_mmhg_total_error", **overall_error},
        {
            "scope": "thickness_scan_at_20_mmhg_thickness_attributable_shift",
            **thickness_error,
        },
    ]
    predictions = pd.read_csv(out / "pressure_fit_predictions.csv")
    ref_curve = predictions[predictions["state"] == state].copy()
    normal_min, normal_max = config["pressure_ranges_mmhg"]["normal"]
    high_min, high_max = config["pressure_ranges_mmhg"]["high"]
    normal = ref_curve[ref_curve["p_iop_mmhg"].between(normal_min, normal_max, inclusive="both")]
    high = ref_curve[ref_curve["p_iop_mmhg"].between(high_min, high_max, inclusive="right")]
    error_rows.append({"scope": "reference_curve_normal_iop_model_error", **metrics(normal.rename(columns={"p_iop_mmhg": "actual_iop_mmhg"}), "inverse_error_mmhg")})
    error_rows.append({"scope": "reference_curve_high_iop_model_error", **metrics(high.rename(columns={"p_iop_mmhg": "actual_iop_mmhg"}), "inverse_error_mmhg")})
    error_summary = pd.DataFrame(error_rows)

    variance_rows = []
    for row in descriptions:
        variance_rows.append(
            {
                "output": row["output"],
                "factor": "eyelid_thickness",
                "effect_metric": "single-factor log-log R2",
                "effect_value": row["log_log_r2"],
                "standardized_log_coefficient": row["log_sensitivity"],
                "status": "unadjusted_single_factor_only",
                "reason": "material, radius, probe area and IOP are fixed in the thickness matrix",
            }
        )
    for factor in ["eyelid_modulus", "probe_displacement", "probe_area", "corneal_radius"]:
        variance_rows.append(
            {
                "output": "all",
                "factor": factor,
                "effect_metric": "partial R2/Sobol",
                "effect_value": np.nan,
                "standardized_log_coefficient": np.nan,
                "status": "not_estimable_no_independent_scan",
                "reason": "factor is fixed or not crossed with thickness in the selected FE matrix",
            }
        )
    variance = pd.DataFrame(variance_rows)

    write_csv(endpoint, out / "thickness_iop_predictions.csv")
    write_csv(sensitivity, out / "sensitivity_results.csv")
    write_csv(threshold_results, out / "threshold_evaluation.csv")
    write_csv(error_summary, out / "pressure_error_summary.csv")
    write_csv(variance, out / "variance_decomposition.csv")
    return {
        "endpoint": endpoint,
        "sensitivity": sensitivity,
        "thresholds": threshold_results,
        "errors": error_summary,
        "variance": variance,
    }


if __name__ == "__main__":
    run()
