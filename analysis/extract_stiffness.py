from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from common import load_config, output_dir, write_csv


def local_stiffness(group: pd.DataFrame, window: tuple[float, float], target: float) -> dict:
    selected = group[group["probe_displacement_mm"].between(*window)].sort_values("probe_displacement_mm")
    x = selected["probe_displacement_mm"].to_numpy(float)
    y = selected["probe_force_n"].to_numpy(float)
    tangent = selected["tangent_stiffness_n_per_mm"].to_numpy(float)
    linear = sm.OLS(y, sm.add_constant(x)).fit()
    quadratic = sm.OLS(y, np.column_stack([np.ones(len(x)), x, x**2])).fit()
    slope = float(linear.params[1])
    slope_se = float(linear.bse[1])
    critical = float(stats.t.ppf(0.975, linear.df_resid))
    secant = float((y[-1] - y[0]) / (x[-1] - x[0]))
    tangent_target = float(np.interp(target, x, tangent))
    curvature_p = float(quadratic.pvalues[2]) if len(x) >= 4 else np.nan
    stiffness_variation = float((np.max(tangent) - np.min(tangent)) / np.mean(tangent))
    nonlinear = bool((np.isfinite(curvature_p) and curvature_p < 0.05) or stiffness_variation > 0.20)
    return {
        "eyelid_thickness_mm": float(group["eyelid_thickness_mm"].iloc[0]),
        "window_min_mm": window[0],
        "window_max_mm": window[1],
        "n_window_points": len(selected),
        "coupled_local_linear_stiffness_n_per_mm": slope,
        "coupled_local_linear_stiffness_se": slope_se,
        "coupled_local_linear_stiffness_ci95_low": slope - critical * slope_se,
        "coupled_local_linear_stiffness_ci95_high": slope + critical * slope_se,
        "coupled_secant_stiffness_n_per_mm": secant,
        "coupled_mean_tangent_stiffness_n_per_mm": float(np.mean(tangent)),
        "coupled_tangent_at_target_n_per_mm": tangent_target,
        "local_linear_r2": float(linear.rsquared),
        "quadratic_term_p": curvature_p,
        "relative_tangent_variation_in_window": stiffness_variation,
        "local_response_class": "nonlinear" if nonlinear else "approximately_linear",
        "k_l_n_per_mm": np.nan,
        "k_l_status": "not_identifiable_from_total_probe_force",
        "interpretation": "reported stiffness is the coupled probe-eyelid-cornea structural slope, not eyelid-only k_l",
    }


def fit_power_law(stiffness: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = np.log(stiffness["eyelid_thickness_mm"].to_numpy(float))
    y = np.log(stiffness["coupled_local_linear_stiffness_n_per_mm"].to_numpy(float))
    model = sm.OLS(y, sm.add_constant(x)).fit()
    exponent_m = float(model.params[1])
    n_definition = -exponent_m
    seed = int(config["project"]["random_seed"]) + 20000
    rng = np.random.default_rng(seed)
    boot_rows = []
    count = int(config["stiffness"]["power_law_bootstrap_replicates"])
    for bootstrap_id in range(count):
        idx = rng.choice(np.arange(len(x)), size=len(x), replace=True)
        if len(np.unique(x[idx])) < 2:
            continue
        fit = sm.OLS(y[idx], sm.add_constant(x[idx])).fit()
        boot_rows.append(
            {
                "bootstrap_id": bootstrap_id,
                "c_n_per_mm_per_mm_power": float(np.exp(fit.params[0])),
                "exponent_m_for_k_proportional_h_to_m": float(fit.params[1]),
                "n_for_k_proportional_h_to_minus_n": float(-fit.params[1]),
            }
        )
    bootstrap = pd.DataFrame(boot_rows)
    ci = bootstrap["n_for_k_proportional_h_to_minus_n"].quantile([0.025, 0.975]).to_numpy()
    hypothesis_t = float((n_definition - 1.0) / model.bse[1])
    hypothesis_p = float(2 * stats.t.sf(abs(hypothesis_t), model.df_resid))
    summary = pd.DataFrame(
        [
            {
                "observable": "coupled_local_linear_stiffness_n_per_mm",
                "c_n_per_mm_per_mm_power": float(np.exp(model.params[0])),
                "exponent_m_for_k_proportional_h_to_m": exponent_m,
                "n_for_k_proportional_h_to_minus_n": n_definition,
                "n_ci95_low": float(ci[0]),
                "n_ci95_high": float(ci[1]),
                "r2_log_space": float(model.rsquared),
                "p_value_test_n_equals_1": hypothesis_p,
                "supports_inverse_thickness_n_equals_1": bool(hypothesis_p >= 0.05 and n_definition > 0),
                "bootstrap_successful": len(bootstrap),
                "scope_warning": "This is k_probe,coupled(h), not independently extracted eyelid k_l(h).",
            }
        ]
    )
    return summary, bootstrap


def identifiability_audit() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "quantity": "k_l",
                "required_observation": "eyelid-only force versus eyelid-only displacement in the target window",
                "available_observation": "total probe force versus commanded probe displacement",
                "status": "not_identifiable",
                "reason": "cornea, bonded interface and whole-globe motion are included in the same reaction",
            },
            {
                "quantity": "k_c(P_IOP)",
                "required_observation": "corneal force-displacement slope at multiple displacements for every IOP",
                "available_observation": "one retained indentation state at each IOP",
                "status": "not_identifiable",
                "reason": "pressure derivative of endpoint force is not a displacement stiffness",
            },
            {
                "quantity": "k_c0",
                "required_observation": "intercept of independently measured k_c(P_IOP)",
                "available_observation": "no independent k_c curve",
                "status": "not_identifiable",
                "reason": "cannot separate corneal stiffness from eyelid/coupling stiffness",
            },
            {
                "quantity": "alpha",
                "required_observation": "slope beta/R_c from independently measured k_c(P_IOP)",
                "available_observation": "no independent k_c curve",
                "status": "not_identifiable",
                "reason": "single-displacement pressure scan measures transfer, not pressure-induced stiffness",
            },
            {
                "quantity": "k_c(P_IOP)/k_l",
                "required_observation": "both independently extracted structural stiffnesses",
                "available_observation": "neither component stiffness is independently available",
                "status": "not_identifiable",
                "reason": "material modulus values cannot substitute for structural equivalent stiffness",
            },
        ]
    )


def run(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    out = output_dir(config)
    tidy = pd.read_csv(out / "tidy_data.csv")
    curves = tidy[tidy["record_type"] == "force_displacement"].copy()
    window = tuple(float(value) for value in config["stiffness"]["target_window_mm"])
    target = float(config["stiffness"]["target_displacement_mm"])
    stiffness = pd.DataFrame(
        [local_stiffness(group, window, target) for _, group in curves.groupby("eyelid_thickness_mm")]
    ).sort_values("eyelid_thickness_mm")
    power_law, bootstrap = fit_power_law(stiffness, config)
    audit = identifiability_audit()
    corneal = pd.DataFrame(
        [
            {
                "k_c0_n_per_mm": np.nan,
                "beta_n_per_mm_per_mmhg": np.nan,
                "alpha_derived_unit": np.nan,
                "linear_fit_range_mmhg": np.nan,
                "fit_status": "not_identifiable",
                "reason": audit.loc[audit["quantity"] == "k_c(P_IOP)", "reason"].iloc[0],
            }
        ]
    )
    write_csv(stiffness, out / "stiffness_parameters.csv")
    write_csv(power_law, out / "stiffness_power_law.csv")
    write_csv(bootstrap, out / "stiffness_power_law_bootstrap.csv")
    write_csv(corneal, out / "corneal_stiffness_parameters.csv")
    write_csv(audit, out / "mechanical_identifiability.csv")
    return {"stiffness": stiffness, "power_law": power_law, "audit": audit, "corneal": corneal}


if __name__ == "__main__":
    run()
