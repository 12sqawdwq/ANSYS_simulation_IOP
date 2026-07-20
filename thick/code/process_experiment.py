#!/usr/bin/env python3
"""Validate and summarize the controlled-phantom thickness experiment."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REQUIRED_COLUMNS = {
    "run_id", "assembly_id", "repeat_id", "eyelid_thickness_mm",
    "cornea_thickness_mm", "reference_iop_mmhg", "probe_advance_mm",
    "probe_force_n", "outer_area_mm2", "inner_area_mm2", "image_id_outer",
    "image_id_inner", "qc_status", "operator", "timestamp",
}
NUMERIC_COLUMNS = {
    "repeat_id", "eyelid_thickness_mm", "cornea_thickness_mm",
    "reference_iop_mmhg", "probe_advance_mm", "probe_force_n",
    "outer_area_mm2", "inner_area_mm2",
}
T_CRITICAL_95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571,
                 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 15: 2.145,
                 20: 2.086, 30: 2.042}


def t_critical(n: int) -> float:
    """Return a conservative two-sided 95% critical value without SciPy."""
    if n < 2:
        return float("nan")
    for limit in sorted(T_CRITICAL_95):
        if n <= limit:
            return T_CRITICAL_95[limit]
    return 1.96


def validate(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if frame["run_id"].duplicated().any():
        raise ValueError("run_id must be unique.")
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if not set(frame["qc_status"].dropna().unique()).issubset({"pass", "fail"}):
        raise ValueError("qc_status must contain only pass or fail.")
    valid = frame.loc[frame["qc_status"] == "pass"].copy()
    if valid.empty:
        raise ValueError("No qc_status=pass records available.")
    if (valid[["outer_area_mm2", "inner_area_mm2", "probe_force_n"]] <= 0).any().any():
        raise ValueError("Passing records require positive force and contact areas.")
    valid["ae_over_ac"] = valid["outer_area_mm2"] / valid["inner_area_mm2"]
    valid["ac_over_ae"] = valid["inner_area_mm2"] / valid["outer_area_mm2"]
    valid["probe_pressure_mmhg"] = (
        valid["probe_force_n"] / (valid["outer_area_mm2"] * 1e-6) / 133.322
    )
    valid["pressure_error_mmhg"] = (
        valid["probe_pressure_mmhg"] - valid["reference_iop_mmhg"]
    )
    return valid


def summarize(valid: pd.DataFrame) -> pd.DataFrame:
    keys = ["eyelid_thickness_mm", "cornea_thickness_mm", "reference_iop_mmhg"]
    measures = ["outer_area_mm2", "inner_area_mm2", "ae_over_ac", "ac_over_ae",
                "probe_force_n", "probe_pressure_mmhg", "pressure_error_mmhg"]
    assembly_means = (
        valid.groupby(keys + ["assembly_id"], as_index=False)[measures]
        .mean()
    )
    rows: list[dict[str, float]] = []
    for condition, group in assembly_means.groupby(keys, sort=True):
        row = dict(zip(keys, condition))
        mask = np.ones(len(valid), dtype=bool)
        for key, value in zip(keys, condition):
            mask &= np.isclose(valid[key], value)
        row["n_measurements"] = int(mask.sum())
        row["n_assemblies"] = group["assembly_id"].nunique()
        for measure in measures:
            values = group[measure].to_numpy(float)
            mean = float(np.mean(values))
            sem = float(np.std(values, ddof=1) / math.sqrt(len(values))) if len(values) > 1 else float("nan")
            ci = t_critical(len(values)) * sem if len(values) > 1 else float("nan")
            row[f"{measure}_mean"] = mean
            row[f"{measure}_ci95_low"] = mean - ci
            row[f"{measure}_ci95_high"] = mean + ci
        rows.append(row)
    return pd.DataFrame(rows)


def isotonic_increasing(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators fit for the expected nondecreasing Ae/Ac curve."""
    order = np.argsort(x)
    values = y[order].astype(float)
    blocks = [[value, 1] for value in values]
    index = 0
    while index < len(blocks) - 1:
        if blocks[index][0] <= blocks[index + 1][0]:
            index += 1
            continue
        total = blocks[index][1] + blocks[index + 1][1]
        blocks[index:index + 2] = [[
            (blocks[index][0] * blocks[index][1] + blocks[index + 1][0] * blocks[index + 1][1]) / total,
            total,
        ]]
        index = max(index - 1, 0)
    fitted = np.concatenate([np.full(count, value) for value, count in blocks])
    result = np.empty_like(fitted)
    result[order] = fitted
    return result


def write_outputs(valid: pd.DataFrame, summary: pd.DataFrame, output: Path, dataset_id: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    study = output.parents[2]
    figures = study / "figures" / "experiment" / dataset_id
    figures.mkdir(parents=True, exist_ok=True)
    valid.to_csv(output / "valid_measurements.csv", index=False)
    summary.to_csv(output / "condition_summary.csv", index=False)

    nominal = summary.loc[np.isclose(summary["cornea_thickness_mm"], 0.55) &
                          np.isclose(summary["reference_iop_mmhg"], 20.0)].copy()
    if not nominal.empty:
        nominal = nominal.sort_values("eyelid_thickness_mm")
        x = nominal["eyelid_thickness_mm"].to_numpy()
        y = nominal["ae_over_ac_mean"].to_numpy()
        nominal["ae_over_ac_monotonic"] = isotonic_increasing(x, y)
        nominal.to_csv(output / "nominal_thickness_correction.csv", index=False)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.errorbar(x, y,
                    yerr=[y - nominal["ae_over_ac_ci95_low"], nominal["ae_over_ac_ci95_high"] - y],
                    fmt="o", capsize=4, label="Experiment mean and 95% CI")
        ax.plot(x, nominal["ae_over_ac_monotonic"], "-", label="Monotonic correction fit")
        ax.set(xlabel="Eyelid thickness (mm)", ylabel="Ae/Ac", title="Thickness correction at 0.55 mm cornea and 20 mmHg")
        ax.grid(alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures / "ae_over_ac_correction.png", dpi=200)
        plt.close(fig)

    report = study / "docs" / "真实仿体实验结果.md"
    report.write_text(
        "# 真实仿体厚度实验结果\n\n"
        f"数据集：`{dataset_id}`。本报告由 `thick/code/process_experiment.py` 自动生成。\n\n"
        f"有效记录：{len(valid)}；独立装配体：{valid['assembly_id'].nunique()}。\n\n"
        "正式条件汇总见 `../data/processed/" + dataset_id + "/condition_summary.csv`。"
        "95% CI 基于有效重复记录计算；占位参数扫描不参与本报告统计。\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_csv", type=Path)
    parser.add_argument("--dataset-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    valid = validate(pd.read_csv(args.raw_csv))
    summary = summarize(valid)
    write_outputs(valid, summary, root / "data" / "processed" / args.dataset_id, args.dataset_id)


if __name__ == "__main__":
    main()
