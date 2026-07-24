#!/usr/bin/env python3
"""Analyze probe force curves extracted from completed thickness cases."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PROBE_DIAMETER_MM = 4.32
PROBE_AREA_MM2 = math.pi * (PROBE_DIAMETER_MM / 2.0) ** 2
PA_PER_MMHG = 133.322
RAW_FIELDS = (
    "target_indent_m",
    "result_time",
    "result_load_step",
    "probe_fy_n",
    "probe_uy_min_m",
    "probe_uy_max_m",
)
CURVE_FIELDS = (
    "source_case",
    "eyelid_thickness_mm",
    "cornea_thickness_mm",
    "indentation_mm",
    "actual_indentation_mm",
    "displacement_error_um",
    "probe_force_n",
    "probe_equivalent_pressure_kpa",
    "probe_equivalent_pressure_mmhg",
    "tangent_stiffness_n_per_mm",
    "result_time",
)
BREAKPOINT_FIELDS = (
    "eyelid_thickness_mm",
    "candidate_indent_mm",
    "pre_slope_n_per_mm",
    "post_slope_n_per_mm",
    "slope_change_fraction",
    "two_segment_sse_improvement",
    "evidence",
)


def thickness_from_name(path: Path) -> float:
    match = re.search(r"eyelid_(\d+)p(\d+)mm", path.stem)
    if not match:
        raise ValueError(f"cannot parse eyelid thickness from {path.name}")
    return float(f"{match.group(1)}.{match.group(2)}")


def read_raw(path: Path, gap_mm: float) -> list[dict[str, float | str]]:
    thickness = thickness_from_name(path)
    rows: list[dict[str, float | str]] = []
    with path.open(newline="", encoding="ascii") as handle:
        reader = csv.reader(handle)
        for line_number, values in enumerate(reader, 1):
            values = [value.strip() for value in values if value.strip()]
            if not values:
                continue
            if len(values) != len(RAW_FIELDS):
                raise ValueError(
                    f"{path}:{line_number}: expected {len(RAW_FIELDS)} values, got {len(values)}"
                )
            raw = dict(zip(RAW_FIELDS, map(float, values)))
            target_mm = raw["target_indent_m"] * 1e3
            mean_uy_mm = 0.5 * (
                raw["probe_uy_min_m"] + raw["probe_uy_max_m"]
            ) * 1e3
            actual_mm = max(0.0, abs(mean_uy_mm) - gap_mm)
            force_n = abs(raw["probe_fy_n"])
            pressure_kpa = force_n / PROBE_AREA_MM2 * 1e3
            rows.append({
                "source_case": path.stem,
                "eyelid_thickness_mm": thickness,
                "cornea_thickness_mm": 0.60,
                "indentation_mm": target_mm,
                "actual_indentation_mm": actual_mm,
                "displacement_error_um": (actual_mm - target_mm) * 1e3,
                "probe_force_n": force_n,
                "probe_equivalent_pressure_kpa": pressure_kpa,
                "probe_equivalent_pressure_mmhg": pressure_kpa * 1e3 / PA_PER_MMHG,
                "result_time": raw["result_time"],
            })
    if len(rows) < 7:
        raise ValueError(f"{path} has too few curve points: {len(rows)}")
    rows.sort(key=lambda row: float(row["indentation_mm"]))
    return rows


def tangent_stiffness(rows: list[dict[str, float | str]]) -> np.ndarray:
    x = np.asarray([float(row["indentation_mm"]) for row in rows])
    y = np.asarray([float(row["probe_force_n"]) for row in rows])
    stiffness = np.gradient(y, x)
    if len(stiffness) >= 5:
        stiffness = np.convolve(stiffness, np.ones(3) / 3.0, mode="same")
        stiffness[0] = (y[1] - y[0]) / (x[1] - x[0])
        stiffness[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
    return stiffness


def fit_breakpoint(rows: list[dict[str, float | str]]) -> dict[str, float | str]:
    x_all = np.asarray([float(row["indentation_mm"]) for row in rows])
    y_all = np.asarray([float(row["probe_force_n"]) for row in rows])
    mask = x_all >= 0.05
    x = x_all[mask]
    y = y_all[mask]
    linear = np.column_stack((np.ones_like(x), x))
    linear_beta, *_ = np.linalg.lstsq(linear, y, rcond=None)
    linear_residual = y - linear @ linear_beta
    linear_sse = float(linear_residual @ linear_residual)

    best: tuple[float, float, np.ndarray] | None = None
    for knot in x[4:-4]:
        design = np.column_stack((np.ones_like(x), x, np.maximum(0.0, x - knot)))
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual = y - design @ beta
        sse = float(residual @ residual)
        if best is None or sse < best[1]:
            best = (float(knot), sse, beta)
    if best is None:
        raise ValueError("not enough points for a two-segment fit")

    knot, segmented_sse, beta = best
    pre_slope = float(beta[1])
    post_slope = float(beta[1] + beta[2])
    slope_scale = max(abs(pre_slope), abs(post_slope), 1e-12)
    slope_change = abs(post_slope - pre_slope) / slope_scale
    improvement = 0.0 if linear_sse <= 1e-20 else 1.0 - segmented_sse / linear_sse
    if improvement >= 0.35 and slope_change >= 0.25:
        evidence = "strong"
    elif improvement >= 0.20 and slope_change >= 0.15:
        evidence = "weak"
    else:
        evidence = "none"
    return {
        "eyelid_thickness_mm": float(rows[0]["eyelid_thickness_mm"]),
        "candidate_indent_mm": knot,
        "pre_slope_n_per_mm": pre_slope,
        "post_slope_n_per_mm": post_slope,
        "slope_change_fraction": slope_change,
        "two_segment_sse_improvement": improvement,
        "evidence": evidence,
    }


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def plot_curves(
    path: Path,
    grouped: list[tuple[float, list[dict[str, float | str]]]],
    breakpoints: list[dict[str, float | str]],
) -> None:
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, len(grouped)))
    figure, (force_axis, stiffness_axis) = plt.subplots(
        2, 1, figsize=(12.8, 9.2), sharex=True,
        gridspec_kw={"height_ratios": (1.6, 1.0)},
    )
    for color, (thickness, rows), breakpoint in zip(colors, grouped, breakpoints):
        x = np.asarray([float(row["indentation_mm"]) for row in rows])
        force = np.asarray([float(row["probe_force_n"]) for row in rows])
        stiffness = np.asarray([float(row["tangent_stiffness_n_per_mm"]) for row in rows])
        label = f"eyelid {thickness:.1f} mm"
        force_axis.plot(x, force, color=color, linewidth=2.0, label=label)
        stiffness_axis.plot(x, stiffness, color=color, linewidth=1.8)
        if breakpoint["evidence"] != "none":
            knot = float(breakpoint["candidate_indent_mm"])
            stiffness_axis.scatter(
                [knot], [np.interp(knot, x, stiffness)], color=color,
                edgecolor="white", linewidth=0.7, s=42, zorder=4,
            )

    force_axis.set_ylabel("Probe force (N)")
    force_axis.grid(True, color="#D8DDE3", linewidth=0.7)
    force_axis.legend(ncol=2, frameon=False, fontsize=9, loc="upper left")
    pressure_axis = force_axis.secondary_yaxis(
        "right",
        functions=(
            lambda force: force / PROBE_AREA_MM2 * 1e3,
            lambda pressure: pressure * PROBE_AREA_MM2 / 1e3,
        ),
    )
    pressure_axis.set_ylabel("Equivalent pressure F/Aprobe (kPa)")

    stiffness_axis.axhline(0.0, color="#222222", linewidth=0.8)
    stiffness_axis.set_xlabel("Nominal indentation after gap closure (mm)")
    stiffness_axis.set_ylabel("Tangent stiffness dF/dd (N/mm)")
    stiffness_axis.grid(True, color="#D8DDE3", linewidth=0.7)
    figure.suptitle(
        "Probe response to 0.80 mm indentation\n"
        "Fixed cornea thickness 0.60 mm, IOP 20 mmHg, probe diameter 4.32 mm",
        fontsize=15,
    )
    figure.text(
        0.5, 0.015,
        "Equivalent pressure is probe force divided by nominal probe area; it is not IOP.",
        ha="center", fontsize=9, color="#4B5563",
    )
    figure.tight_layout(rect=(0.03, 0.04, 0.97, 0.94))
    figure.savefig(path, dpi=180)
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--gap-mm", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = sorted(args.input_dir.glob("eyelid_*mm.csv"))
    if not files:
        raise SystemExit(f"no eyelid curve files found in {args.input_dir}")
    grouped = [(thickness_from_name(path), read_raw(path, args.gap_mm)) for path in files]
    grouped.sort(key=lambda item: item[0])
    all_rows: list[dict] = []
    breakpoints: list[dict[str, float | str]] = []
    for _, rows in grouped:
        for row, stiffness in zip(rows, tangent_stiffness(rows)):
            row["tangent_stiffness_n_per_mm"] = float(stiffness)
            all_rows.append(row)
        breakpoints.append(fit_breakpoint(rows))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "probe_force_curve.csv", CURVE_FIELDS, all_rows)
    write_csv(args.output_dir / "breakpoint_analysis.csv", BREAKPOINT_FIELDS, breakpoints)
    max_error = max(abs(float(row["displacement_error_um"])) for row in all_rows)
    evidence_counts = {
        level: sum(row["evidence"] == level for row in breakpoints)
        for level in ("strong", "weak", "none")
    }
    metadata = {
        "probe_diameter_mm": PROBE_DIAMETER_MM,
        "probe_area_mm2": PROBE_AREA_MM2,
        "cornea_thickness_mm": 0.60,
        "eyelid_thicknesses_mm": [item[0] for item in grouped],
        "curve_points_per_thickness": [len(item[1]) for item in grouped],
        "maximum_displacement_error_um": max_error,
        "breakpoint_evidence_counts": evidence_counts,
        "breakpoint_rule": {
            "strong": "SSE improvement >= 0.35 and relative slope change >= 0.25",
            "weak": "SSE improvement >= 0.20 and relative slope change >= 0.15",
        },
    }
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    plot_curves(args.output_dir / "probe_force_curve.png", grouped, breakpoints)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
