from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import least_squares
import statsmodels.api as sm

from common import load_config, output_dir, read_csv, write_csv


def rational_forward(p_iop: np.ndarray, g0: float, lam: float) -> np.ndarray:
    p_iop = np.asarray(p_iop, dtype=float)
    return g0 * p_iop / (1.0 + lam * p_iop)


def rational_inverse(p_probe: np.ndarray, g0: float, lam: float) -> np.ndarray:
    p_probe = np.asarray(p_probe, dtype=float)
    denominator = g0 - lam * p_probe
    with np.errstate(divide="ignore", invalid="ignore"):
        return p_probe / denominator


def fit_core(x: np.ndarray, y: np.ndarray, max_nfev: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    nonzero = x > 0
    gain_guess = np.median(y[nonzero] / x[nonzero]) if np.any(nonzero) else 0.2
    gain_guess = max(float(gain_guess), 1e-4)
    result = least_squares(
        lambda theta: rational_forward(x, theta[0], theta[1]) - y,
        x0=np.array([gain_guess, 0.03]),
        bounds=(np.array([1e-10, 0.0]), np.array([10.0, 10.0])),
        max_nfev=max_nfev,
        method="trf",
    )
    if not result.success:
        raise RuntimeError(result.message)
    residual = result.fun
    dof = max(len(x) - 2, 1)
    sigma2 = float(np.sum(residual**2) / dof)
    covariance = np.linalg.pinv(result.jac.T @ result.jac) * sigma2
    return result.x, covariance, residual


def transformed(theta: np.ndarray) -> dict[str, float]:
    g0, lam = theta
    return {
        "g0_1_over_b": float(g0),
        "lambda_a_over_b_per_mmhg": float(lam),
        "a_per_mmhg": float(lam / g0),
        "b_dimensionless": float(1.0 / g0),
        "pstar_b_over_a_mmhg": float(1.0 / lam) if lam > 0 else np.inf,
    }


def transformed_covariance(theta: np.ndarray, covariance: np.ndarray) -> tuple[dict[str, float], float]:
    g0, lam = theta
    gradients = {
        "g0_1_over_b": np.array([1.0, 0.0]),
        "lambda_a_over_b_per_mmhg": np.array([0.0, 1.0]),
        "a_per_mmhg": np.array([-lam / g0**2, 1.0 / g0]),
        "b_dimensionless": np.array([-1.0 / g0**2, 0.0]),
        "pstar_b_over_a_mmhg": np.array([0.0, -1.0 / lam**2]) if lam > 0 else np.array([np.nan, np.nan]),
    }
    se = {
        key: float(np.sqrt(max(gradient @ covariance @ gradient, 0.0)))
        for key, gradient in gradients.items()
    }
    jac_ab = np.vstack([gradients["a_per_mmhg"], gradients["b_dimensionless"]])
    cov_ab = jac_ab @ covariance @ jac_ab.T
    denom = np.sqrt(cov_ab[0, 0] * cov_ab[1, 1])
    corr_ab = float(cov_ab[0, 1] / denom) if denom > 0 else np.nan
    return se, corr_ab


def bootstrap_fit(
    x: np.ndarray,
    y: np.ndarray,
    replicates: int,
    seed: int,
    max_nfev: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    nonzero_idx = np.flatnonzero(x > 0)
    origin_idx = np.flatnonzero(x == 0)
    rows: list[dict] = []
    for bootstrap_id in range(replicates):
        sampled = rng.choice(nonzero_idx, size=len(nonzero_idx), replace=True)
        if len(origin_idx):
            sampled = np.concatenate([origin_idx[:1], sampled])
        try:
            theta, _, _ = fit_core(x[sampled], y[sampled], max_nfev)
            rows.append({"bootstrap_id": bootstrap_id, "fit_status": "success", **transformed(theta)})
        except Exception as exc:  # deterministic audit row for failed resamples
            rows.append({"bootstrap_id": bootstrap_id, "fit_status": f"failed:{type(exc).__name__}"})
    return pd.DataFrame(rows)


def residual_diagnostics(residual: np.ndarray) -> dict[str, float]:
    residual = np.asarray(residual, dtype=float)
    if len(residual) >= 8 and not np.allclose(residual, residual[0]):
        shapiro_p = float(stats.shapiro(residual).pvalue)
    else:
        shapiro_p = np.nan
    if len(residual) >= 3:
        skewness = float(stats.skew(residual, bias=False))
        kurtosis = float(stats.kurtosis(residual, fisher=True, bias=False))
    else:
        skewness = kurtosis = np.nan
    return {"residual_skewness": skewness, "residual_excess_kurtosis": kurtosis, "shapiro_p": shapiro_p}


def linearized_crosscheck(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    mask = (x > 0) & (y > 0)
    response = x[mask] / y[mask]
    design = sm.add_constant(x[mask])
    result = sm.OLS(response, design).fit()
    return {
        "linearized_b_dimensionless": float(result.params[0]),
        "linearized_a_per_mmhg": float(result.params[1]),
        "linearized_r2": float(result.rsquared),
    }


def fit_state(frame: pd.DataFrame, state: str, config: dict) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = frame[frame["state"] == state].sort_values("p_iop_mmhg").copy()
    x = data["p_iop_mmhg"].to_numpy(float)
    y = data["p_probe_delta_mmhg"].to_numpy(float)
    max_nfev = int(config["fit"]["max_nfev"])
    theta, covariance, residual = fit_core(x, y, max_nfev)
    params = transformed(theta)
    se, corr_ab = transformed_covariance(theta, covariance)
    bootstrap = bootstrap_fit(
        x,
        y,
        int(config["fit"]["bootstrap_replicates"]),
        int(config["project"]["random_seed"]) + (0 if state == "primary_0p26" else 10000),
        max_nfev,
    )
    successful = bootstrap[bootstrap["fit_status"] == "success"].copy()
    predictions = rational_forward(x, *theta)
    inverse_predictions = rational_inverse(y, *theta)
    sse = float(np.sum((y - predictions) ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))

    scaled_jacobian = np.column_stack(
        [
            x / (1.0 + theta[1] * x),
            -theta[0] * x**2 / (1.0 + theta[1] * x) ** 2,
        ]
    )
    norms = np.linalg.norm(scaled_jacobian, axis=0)
    scaled_jacobian = scaled_jacobian / np.where(norms == 0, 1, norms)
    jac_condition = float(np.linalg.cond(scaled_jacobian))
    threshold = config["fit"]["identifiability_correlation_threshold"]
    identifiable = bool(
        len(np.unique(x)) >= config["analysis_policy"]["minimum_distinct_pressures_for_residual_dof"]
        and abs(corr_ab) < threshold
        and np.isfinite(jac_condition)
    )
    status = "identifiable" if identifiable else "weakly_identified_parameter_pair"

    row = {
        "eyelid_thickness_mm": float(data["eyelid_thickness_mm"].iloc[0]),
        "state": state,
        "fit_status": "success",
        "identifiability_status": status,
        "n_points": len(data),
        "n_distinct_pressures": int(data["p_iop_mmhg"].nunique()),
        "fit_range_min_mmhg": float(x.min()),
        "fit_range_max_mmhg": float(x.max()),
        **params,
        **{f"se_{key}": value for key, value in se.items()},
        "parameter_correlation_a_b": corr_ab,
        "scaled_jacobian_condition_number": jac_condition,
        "r2_probe_space": float(1.0 - sse / sst),
        "rmse_probe_mmhg": float(np.sqrt(np.mean((y - predictions) ** 2))),
        "mae_probe_mmhg": float(np.mean(np.abs(y - predictions))),
        "rmse_inverse_iop_mmhg": float(np.sqrt(np.nanmean((inverse_predictions - x) ** 2))),
        "mae_inverse_iop_mmhg": float(np.nanmean(np.abs(inverse_predictions - x))),
        "bootstrap_requested": int(config["fit"]["bootstrap_replicates"]),
        "bootstrap_successful": int(len(successful)),
        **residual_diagnostics(residual),
        **linearized_crosscheck(x, y),
        "limitation": "deterministic FE pressure states are not independent experimental replicates",
    }
    for key in params:
        if len(successful):
            row[f"ci95_low_{key}"] = float(successful[key].quantile(0.025))
            row[f"ci95_high_{key}"] = float(successful[key].quantile(0.975))
        else:
            row[f"ci95_low_{key}"] = np.nan
            row[f"ci95_high_{key}"] = np.nan

    bootstrap.insert(0, "state", state)
    for pressure in x:
        if len(successful):
            boot_pred = rational_forward(
                np.full(len(successful), pressure),
                successful["g0_1_over_b"].to_numpy(float),
                successful["lambda_a_over_b_per_mmhg"].to_numpy(float),
            )
            low, high = np.quantile(boot_pred, [0.025, 0.975])
        else:
            low = high = np.nan
        idx = np.flatnonzero(x == pressure)[0]
        data.loc[data["p_iop_mmhg"] == pressure, "p_probe_fitted_mmhg"] = predictions[idx]
        data.loc[data["p_iop_mmhg"] == pressure, "p_probe_fit_ci95_low_mmhg"] = low
        data.loc[data["p_iop_mmhg"] == pressure, "p_probe_fit_ci95_high_mmhg"] = high
        data.loc[data["p_iop_mmhg"] == pressure, "residual_probe_mmhg"] = y[idx] - predictions[idx]
        data.loc[data["p_iop_mmhg"] == pressure, "p_iop_inverse_fitted_mmhg"] = inverse_predictions[idx]
        data.loc[data["p_iop_mmhg"] == pressure, "inverse_error_mmhg"] = inverse_predictions[idx] - pressure
    return row, data, bootstrap, successful


def insufficient_rows(config: dict, fitted_states: list[str]) -> pd.DataFrame:
    endpoints = read_csv(config, "thickness_pressure_endpoints")
    reference = float(config["geometry"]["reference_thickness_mm"])
    rows = []
    for thickness in sorted(endpoints["eyelid_thickness_mm"].unique()):
        if np.isclose(thickness, reference):
            continue
        rows.append(
            {
                "eyelid_thickness_mm": thickness,
                "state": "sensitivity_0p28",
                "fit_status": "not_fitted",
                "identifiability_status": "not_identifiable_one_nonzero_pressure",
                "n_points": 2,
                "n_distinct_pressures": 2,
                "fit_range_min_mmhg": 0.0,
                "fit_range_max_mmhg": float(endpoints.loc[endpoints["eyelid_thickness_mm"] == thickness, "actual_iop_mmhg"].iloc[0]),
                "limitation": "one nonzero pressure gives zero residual degrees of freedom for the two-parameter model",
            }
        )
    return pd.DataFrame(rows)


def run(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    out = output_dir(config)
    tidy = pd.read_csv(out / "tidy_data.csv")
    pressure = tidy[tidy["record_type"] == "pressure_scan"].copy()
    parameter_rows: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    bootstrap_frames: list[pd.DataFrame] = []
    for state in config["fit"]["states"]:
        row, predictions, bootstrap, _ = fit_state(pressure, state, config)
        parameter_rows.append(row)
        prediction_frames.append(predictions)
        bootstrap_frames.append(bootstrap)
    fitted = pd.DataFrame(parameter_rows)
    unavailable = insufficient_rows(config, config["fit"]["states"])
    fitted = pd.concat([fitted, unavailable], ignore_index=True, sort=False).sort_values(
        ["state", "eyelid_thickness_mm"], ignore_index=True
    )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    bootstraps = pd.concat(bootstrap_frames, ignore_index=True)
    write_csv(fitted, out / "fitted_parameters.csv")
    write_csv(predictions, out / "pressure_fit_predictions.csv")
    write_csv(bootstraps, out / "pressure_fit_bootstrap.csv")
    return {"parameters": fitted, "predictions": predictions, "bootstrap": bootstraps}


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    run()
