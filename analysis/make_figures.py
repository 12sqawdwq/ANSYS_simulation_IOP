from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_config, output_dir, write_csv
from fit_pressure_model import rational_forward, rational_inverse


COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 120,
            "savefig.dpi": 250,
            "svg.fonttype": "none",
        }
    )


def save(fig: plt.Figure, figures: Path, stem: str, manifest: list[dict], description: str) -> None:
    fig.tight_layout()
    for extension in ["svg", "png"]:
        path = figures / f"{stem}.{extension}"
        fig.savefig(path, bbox_inches="tight")
        manifest.append(
            {
                "figure": stem,
                "format": extension,
                "relative_path": f"figures/{path.name}",
                "description": description,
            }
        )
    plt.close(fig)


def figure_pressure_curves(out: Path, manifest: list[dict]) -> None:
    pred = pd.read_csv(out / "pressure_fit_predictions.csv")
    boot = pd.read_csv(out / "pressure_fit_bootstrap.csv")
    states = ["primary_0p26", "sensitivity_0p28"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), sharex=True, sharey=True)
    grid = np.linspace(0, pred["p_iop_mmhg"].max(), 250)
    for ax, state, color in zip(axes, states, COLORS):
        data = pred[pred["state"] == state].sort_values("p_iop_mmhg")
        samples = boot[(boot["state"] == state) & (boot["fit_status"] == "success")]
        curves = np.array(
            [
                rational_forward(grid, row.g0_1_over_b, row.lambda_a_over_b_per_mmhg)
                for row in samples.itertuples()
            ]
        )
        low, median, high = np.quantile(curves, [0.025, 0.5, 0.975], axis=0)
        ax.scatter(data["p_iop_mmhg"], data["p_probe_delta_mmhg"], s=18, color=color, label="FE state", zorder=3)
        ax.plot(grid, median, color="black", lw=1.6, label="direct nonlinear fit")
        ax.fill_between(grid, low, high, color=color, alpha=0.20, label="bootstrap 95% CI")
        ax.set_title(state.replace("_", " "))
        ax.set_xlabel(r"Applied $P_{IOP}$ (mmHg)")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel(r"Zero-referenced $P_{probe}$ (mmHg)")
    axes[1].legend(frameon=False, loc="lower right")
    fig.suptitle("FE pressure-transfer curves and direct rational fits", y=1.02)
    save(fig, out / "figures", "fig01_pressure_curves", manifest, "Pressure curves, direct fits and bootstrap intervals")


def figure_parameters(out: Path, manifest: list[dict]) -> None:
    fitted = pd.read_csv(out / "fitted_parameters.csv")
    fitted = fitted[fitted["fit_status"] == "success"]
    specs = [
        ("a_per_mmhg", "a (1/mmHg)"),
        ("b_dimensionless", "b (-)"),
        ("g0_1_over_b", "G0 = 1/b (-)"),
        ("lambda_a_over_b_per_mmhg", "lambda = a/b (1/mmHg)"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), sharex=True)
    for ax, (column, ylabel) in zip(axes.flat, specs):
        for idx, row in fitted.reset_index(drop=True).iterrows():
            low = row[f"ci95_low_{column}"]
            high = row[f"ci95_high_{column}"]
            x = row["eyelid_thickness_mm"] + (-0.012 if idx == 0 else 0.012)
            ax.errorbar(
                x,
                row[column],
                yerr=[[row[column] - low], [high - row[column]]],
                fmt="o",
                color=COLORS[idx],
                capsize=3,
                label=row["state"].replace("_", " "),
            )
        ax.axvspan(0.8, 2.0, color="0.9", alpha=0.35)
        ax.text(0.82, 0.07, "No multi-IOP curves\nfor other thicknesses", transform=ax.get_xaxis_transform(), color="0.35")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.2)
    for ax in axes[-1]:
        ax.set_xlabel("Eyelid thickness (mm)")
    axes[0, 0].legend(frameon=False)
    fig.suptitle("Rational parameters versus eyelid thickness: identifiable data only")
    save(fig, out / "figures", "fig02_parameters_vs_thickness", manifest, "Only h=1.25 mm has identifiable rational parameters")


def figure_parameter_sensitivity(out: Path, manifest: list[dict]) -> None:
    sensitivity = pd.read_csv(out / "sensitivity_results.csv")
    exact = ["a", "b", "G0=1/b", "lambda=a/b"]
    proxy = sensitivity[sensitivity["output"] == "G_eff_at_20=P_probe/P_IOP"].iloc[0]
    labels = [*exact, "G_eff(20)\nproxy"]
    values = [np.nan] * 4 + [proxy["log_sensitivity"]]
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    for idx in range(4):
        ax.bar(idx, 0.02, width=0.68, facecolor="white", edgecolor="0.55", hatch="///")
        ax.text(idx, 0.035, "N/A", ha="center", va="bottom", color="0.35", fontweight="bold")
    error = np.array([[proxy["log_sensitivity"] - proxy["sensitivity_ci95_low"]], [proxy["sensitivity_ci95_high"] - proxy["log_sensitivity"]]])
    ax.bar(4, values[4], color=COLORS[2], width=0.68)
    ax.errorbar(4, values[4], yerr=error, fmt="none", color="black", capsize=4)
    ax.axhspan(-0.2, 0.2, color="#009E73", alpha=0.10, label="provisional |S| < 0.2")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(5), labels)
    ax.set_ylabel(r"Log sensitivity $\partial\ln(Y)/\partial\ln(h_l)$")
    ax.set_title("Thickness sensitivity: exact parameters are not identifiable")
    ax.legend(frameon=False)
    save(fig, out / "figures", "fig03_normalized_sensitivity", manifest, "Exact parameter sensitivities unavailable; 20-mmHg effective-gain proxy shown")


def figure_cv(out: Path, manifest: list[dict]) -> None:
    sensitivity = pd.read_csv(out / "sensitivity_results.csv")
    mapping = [
        ("a", "a"),
        ("b", "b"),
        ("G0=1/b", "G0"),
        ("lambda=a/b", "lambda"),
        ("zero_iop_baseline_force", "F0"),
        ("total_probe_force_at_20", "F20"),
        ("G_eff_at_20=P_probe/P_IOP", "G_eff(20)"),
    ]
    values = []
    for key, _ in mapping:
        row = sensitivity[sensitivity["output"] == key]
        values.append(np.nan if row.empty else float(row["coefficient_of_variation"].iloc[0]))
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    for idx, value in enumerate(values):
        if np.isfinite(value):
            ax.bar(idx, 100 * value, color=COLORS[(idx - 4) % len(COLORS)])
        else:
            ax.bar(idx, 0.8, facecolor="white", edgecolor="0.55", hatch="///")
            ax.text(idx, 1.15, "N/A", ha="center", color="0.35", fontweight="bold")
    ax.set_xticks(range(len(mapping)), [label for _, label in mapping])
    ax.set_ylabel("Coefficient of variation across thickness (%)")
    ax.set_title("Thickness-scan dispersion: requested parameters versus observable responses")
    ax.grid(axis="y", alpha=0.2)
    save(fig, out / "figures", "fig04_coefficient_of_variation", manifest, "CV comparison with non-identifiable exact parameters marked N/A")


def figure_stiffness(out: Path, manifest: list[dict]) -> None:
    data = pd.read_csv(out / "stiffness_parameters.csv")
    model = pd.read_csv(out / "stiffness_power_law.csv").iloc[0]
    boot = pd.read_csv(out / "stiffness_power_law_bootstrap.csv")
    grid = np.linspace(data["eyelid_thickness_mm"].min(), data["eyelid_thickness_mm"].max(), 200)
    curves = np.array(
        [
            row.c_n_per_mm_per_mm_power * grid ** row.exponent_m_for_k_proportional_h_to_m
            for row in boot.itertuples()
        ]
    )
    low, high = np.quantile(curves, [0.025, 0.975], axis=0)
    fit = model["c_n_per_mm_per_mm_power"] * grid ** model["exponent_m_for_k_proportional_h_to_m"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    y = data["coupled_local_linear_stiffness_n_per_mm"]
    yerr = np.vstack([y - data["coupled_local_linear_stiffness_ci95_low"], data["coupled_local_linear_stiffness_ci95_high"] - y])
    ax.errorbar(data["eyelid_thickness_mm"], y, yerr=yerr, fmt="o", color=COLORS[0], capsize=3, label="FE local slope (95% CI)")
    ax.plot(grid, fit, color="black", label="power-law fit")
    ax.fill_between(grid, low, high, color=COLORS[0], alpha=0.18, label="bootstrap 95% CI")
    ax.set_xlabel("Eyelid thickness (mm)")
    ax.set_ylabel("Coupled probe-system stiffness (N/mm)")
    ax.set_title("Target-window coupled stiffness (not eyelid-only k_l)")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, out / "figures", "fig05_coupled_stiffness_power_law", manifest, "Coupled local stiffness and power-law fit")


def diagnostic_figure(out: Path, manifest: list[dict], stem: str, title: str, message: str, description: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.70, "NOT IDENTIFIABLE", ha="center", va="center", fontsize=15, color="#D55E00", fontweight="bold")
    ax.text(0.5, 0.42, message, ha="center", va="center", fontsize=10, wrap=True, linespacing=1.5)
    ax.set_title(title, pad=12)
    save(fig, out / "figures", stem, manifest, description)


def figure_theory_identity(out: Path, manifest: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 4.2))
    ax.plot([0, 1], [0, 1], ls="--", color="0.45", label="identity line")
    ax.text(0.5, 0.62, "0 theory-fit pairs", ha="center", fontsize=14, color="#D55E00", fontweight="bold")
    ax.text(0.5, 0.43, "Independent k_l, k_c0 and alpha\nare unavailable", ha="center", color="0.3")
    ax.set_xlabel("Theory value (normalized display axis)")
    ax.set_ylabel("Direct-fit value (normalized display axis)")
    ax.set_title("Theory–fit consistency audit")
    ax.legend(frameon=False, loc="lower right")
    save(fig, out / "figures", "fig08_theory_fit_identity", manifest, "Identity-line audit; no theory-fit pairs are computable")


def figure_iop_error(out: Path, manifest: list[dict]) -> None:
    data = pd.read_csv(out / "thickness_iop_predictions.csv")
    boot = pd.read_csv(out / "pressure_fit_bootstrap.csv")
    boot = boot[(boot["state"] == "sensitivity_0p28") & (boot["fit_status"] == "success")]
    intervals = []
    for q in data["delta_probe_pressure_mmhg"]:
        values = rational_inverse(q, boot["g0_1_over_b"].to_numpy(float), boot["lambda_a_over_b_per_mmhg"].to_numpy(float))
        values = values[np.isfinite(values) & (values > -100) & (values < 200)]
        intervals.append(np.quantile(values, [0.025, 0.975]))
    intervals = np.asarray(intervals)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    prediction = data["shared_calibration_iop_mmhg"].to_numpy(float)
    ax.errorbar(
        data["eyelid_thickness_mm"],
        prediction - data["actual_iop_mmhg"],
        yerr=np.vstack([prediction - intervals[:, 0], intervals[:, 1] - prediction]),
        fmt="o-",
        color=COLORS[1],
        capsize=3,
        label="shared-calibration error (bootstrap 95% CI)",
    )
    ax.axhline(0, color="black", lw=0.8)
    ax.axhspan(-1.5, 1.5, color=COLORS[2], alpha=0.10, label="±1.5 mmHg engineering band")
    ax.set_xlabel("Eyelid thickness (mm)")
    ax.set_ylabel("Predicted minus applied IOP (mmHg)")
    ax.set_title("Effect of thickness on shared-calibration IOP error at 20 mmHg")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, out / "figures", "fig09_iop_error_vs_thickness", manifest, "20-mmHg shared-calibration errors across thickness")


def figure_ranking(out: Path, manifest: list[dict]) -> None:
    data = pd.read_csv(out / "sensitivity_results.csv")
    data = data[data["status"] == "estimable_single_factor"].copy()
    data["abs_sensitivity"] = data["log_sensitivity"].abs()
    data = data.sort_values("abs_sensitivity")
    labels = {
        "zero_iop_baseline_force": "F0",
        "total_probe_force_at_20": "F20",
        "delta_probe_force_at_20": "Delta F20",
        "P_probe_delta_at_20": "Delta Pprobe20",
        "G_eff_at_20=P_probe/P_IOP": "G_eff(20)",
        "shared_calibration_iop_prediction": "P_IOP estimate",
    }
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    colors = [COLORS[2] if value < 0.2 else COLORS[1] for value in data["abs_sensitivity"]]
    ax.barh([labels.get(value, value) for value in data["output"]], data["abs_sensitivity"], color=colors)
    ax.axvline(0.2, color="black", ls="--", label="provisional threshold")
    ax.set_xlabel("Absolute single-factor log sensitivity")
    ax.set_title("Observable sensitivity ranking for eyelid thickness")
    ax.legend(frameon=False)
    ax.grid(axis="x", alpha=0.2)
    save(fig, out / "figures", "fig10_sensitivity_ranking", manifest, "Single-factor thickness sensitivity ranking; other factors were fixed")


def figure_residuals(out: Path, manifest: list[dict]) -> None:
    data = pd.read_csv(out / "pressure_fit_predictions.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, (state, group), color in zip(axes, data.groupby("state"), COLORS):
        ax.axhline(0, color="black", lw=0.8)
        ax.scatter(group["p_iop_mmhg"], group["residual_probe_mmhg"], color=color, s=18)
        ax.set_title(state.replace("_", " "))
        ax.set_xlabel(r"Applied $P_{IOP}$ (mmHg)")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Probe-space residual (mmHg)")
    fig.suptitle("Direct-fit residual distribution over pressure")
    save(fig, out / "figures", "fig11_pressure_fit_residuals", manifest, "Residuals reveal pressure-dependent model discrepancy")


def run(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    out = output_dir(config)
    setup_style()
    manifest: list[dict] = []
    figure_pressure_curves(out, manifest)
    figure_parameters(out, manifest)
    figure_parameter_sensitivity(out, manifest)
    figure_cv(out, manifest)
    figure_stiffness(out, manifest)
    diagnostic_figure(
        out,
        manifest,
        "fig06_corneal_stiffness_identifiability",
        "Corneal stiffness k_c(P_IOP), k_c0 and alpha",
        "Each pressure has only one retained displacement state.\nA force-displacement slope cannot be calculated at any pressure.",
        "Diagnostic showing why corneal stiffness cannot be extracted",
    )
    diagnostic_figure(
        out,
        manifest,
        "fig07_stiffness_ratio_identifiability",
        "Structural stiffness ratio k_c(P_IOP) / k_l",
        "Neither component stiffness is independently observed.\nMaterial modulus ratios are not substituted for structural stiffness ratios.",
        "Diagnostic showing why k_c/k_l cannot be calculated",
    )
    figure_theory_identity(out, manifest)
    figure_iop_error(out, manifest)
    figure_ranking(out, manifest)
    figure_residuals(out, manifest)
    frame = pd.DataFrame(manifest)
    write_csv(frame, out / "figure_manifest.csv")
    return frame


if __name__ == "__main__":
    run()
