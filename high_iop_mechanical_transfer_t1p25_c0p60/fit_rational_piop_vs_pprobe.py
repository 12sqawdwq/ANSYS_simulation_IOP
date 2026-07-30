#!/usr/bin/env python3
"""Fit P_IOP=b*P_probe/(1-a*P_probe) to the actual 2.5 mmHg FE grid."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"
DEFAULT_JSON = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
DEFAULT_CSV = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.csv"
DEFAULT_FIGURE = ROOT / "figures" / "piop_vs_delta_pprobe_rational_regression_0_to_50_step2p5.png"


def find_font(filename: str) -> str:
    for directory in (
        Path("/usr/share/fonts/noto-cjk"),
        Path("/usr/share/fonts/opentype/noto"),
    ):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def load_points(path: Path) -> list[dict[str, float | str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("campaign_pass") or not all(payload["qc"].values()):
        raise ValueError("source FE campaign did not pass all quality checks")
    rows = [row for row in payload["rows"] if row["state"] == "primary_0p26"]
    expected = [index * 2.5 for index in range(21)]
    if [float(row["input_iop_mmhg"]) for row in rows] != expected:
        raise ValueError("source does not contain the expected 0–50 mmHg grid")
    return [
        {
            "input_iop_mmhg": float(row["input_iop_mmhg"]),
            "delta_probe_pressure_mmhg": float(row["delta_probe_pressure_mmhg"]),
            "source_kind": str(row["source_kind"]),
        }
        for row in rows
    ]


def profile_solution(rows: list[dict[str, float | str]], a: float) -> tuple[float, float]:
    transformed = []
    pressures = []
    for row in rows:
        q = float(row["delta_probe_pressure_mmhg"])
        denominator = 1.0 - a * q
        if denominator <= 0.0:
            return math.inf, math.nan
        transformed.append(q / denominator)
        pressures.append(float(row["input_iop_mmhg"]))
    sum_x2 = sum(value * value for value in transformed)
    b = sum(p * value for p, value in zip(pressures, transformed)) / sum_x2
    sse = sum((b * value - p) ** 2 for p, value in zip(pressures, transformed))
    return sse, b


def fit_rational(rows: list[dict[str, float | str]]) -> tuple[float, float]:
    q_max = max(float(row["delta_probe_pressure_mmhg"]) for row in rows)
    lower = -2.0
    upper = 0.999 / q_max
    grid_count = 20000
    grid = [lower + (upper - lower) * index / grid_count for index in range(grid_count + 1)]
    scores = [profile_solution(rows, value)[0] for value in grid]
    best_index = min(range(len(grid)), key=scores.__getitem__)
    if best_index in (0, grid_count):
        raise ValueError("profile least-squares optimum reached a search boundary")
    left = grid[best_index - 1]
    right = grid[best_index + 1]
    ratio = (1.0 + math.sqrt(5.0)) / 2.0
    c = right - (right - left) / ratio
    d = left + (right - left) / ratio
    fc = profile_solution(rows, c)[0]
    fd = profile_solution(rows, d)[0]
    for _ in range(120):
        if fc < fd:
            right, d, fd = d, c, fc
            c = right - (right - left) / ratio
            fc = profile_solution(rows, c)[0]
        else:
            left, c, fc = c, d, fd
            d = left + (right - left) / ratio
            fd = profile_solution(rows, d)[0]
    a = (left + right) / 2.0
    _, b = profile_solution(rows, a)
    return a, b


def prediction(q: float, a: float, b: float) -> float:
    return b * q / (1.0 - a * q)


def analyze(rows: list[dict[str, float | str]], a: float, b: float) -> tuple[list[dict[str, float | str]], dict]:
    output_rows = []
    errors = []
    for row in rows:
        p = float(row["input_iop_mmhg"])
        q = float(row["delta_probe_pressure_mmhg"])
        calculated = prediction(q, a, b)
        error = calculated - p
        errors.append(error)
        output_rows.append({
            **row,
            "regression_iop_mmhg": calculated,
            "regression_error_mmhg": error,
            "absolute_error_mmhg": abs(error),
        })
    pressures = [float(row["input_iop_mmhg"]) for row in rows]
    mean_pressure = sum(pressures) / len(pressures)
    sse = sum(error * error for error in errors)
    sst = sum((value - mean_pressure) ** 2 for value in pressures)
    nonzero_errors = errors[1:]
    metrics = {
        "point_count_including_origin": len(rows),
        "informative_nonzero_point_count": len(rows) - 1,
        "mae_all_points_mmhg": sum(abs(value) for value in errors) / len(errors),
        "rmse_all_points_mmhg": math.sqrt(sse / len(errors)),
        "mae_nonzero_points_mmhg": sum(abs(value) for value in nonzero_errors) / len(nonzero_errors),
        "rmse_nonzero_points_mmhg": math.sqrt(sum(value * value for value in nonzero_errors) / len(nonzero_errors)),
        "maximum_absolute_error_mmhg": max(abs(value) for value in errors),
        "maximum_absolute_error_pressure_mmhg": pressures[max(range(len(errors)), key=lambda index: abs(errors[index]))],
        "r_squared_iop_space": 1.0 - sse / sst,
        "sse_iop_mmhg2": sse,
        "minimum_denominator_on_observed_grid": min(
            1.0 - a * float(row["delta_probe_pressure_mmhg"]) for row in rows
        ),
        "probe_pressure_asymptote_mmhg": 1.0 / a,
    }

    informative = rows[1:]
    jacobian = []
    for row in informative:
        q = float(row["delta_probe_pressure_mmhg"])
        denominator = 1.0 - a * q
        jacobian.append((b * q * q / denominator**2, q / denominator))
    j11 = sum(left * left for left, _ in jacobian)
    j12 = sum(left * right for left, right in jacobian)
    j22 = sum(right * right for _, right in jacobian)
    determinant = j11 * j22 - j12 * j12
    residual_variance = sse / (len(informative) - 2)
    variance_a = residual_variance * j22 / determinant
    variance_b = residual_variance * j11 / determinant
    covariance_ab = -residual_variance * j12 / determinant
    t_critical_95_df18 = 2.10092204024104
    se_a = math.sqrt(variance_a)
    se_b = math.sqrt(variance_b)
    metrics["nominal_parameter_uncertainty"] = {
        "residual_degrees_of_freedom": len(informative) - 2,
        "standard_error_a_per_mmhg": se_a,
        "standard_error_b": se_b,
        "covariance_a_b": covariance_ab,
        "correlation_a_b": covariance_ab / math.sqrt(variance_a * variance_b),
        "a_nominal_95_percent_interval_per_mmhg": [a - t_critical_95_df18 * se_a, a + t_critical_95_df18 * se_a],
        "b_nominal_95_percent_interval": [b - t_critical_95_df18 * se_b, b + t_critical_95_df18 * se_b],
        "caveat": "Nominal regression uncertainty only; deterministic FE points are not independent experimental replicates.",
    }
    return output_rows, metrics


def render_figure(rows: list[dict[str, float | str]], a: float, b: float, metrics: dict, output: Path) -> None:
    regular = find_font("NotoSansCJK-Regular.ttc")
    bold = find_font("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)
    width, height = 1800, 1100
    left, right, top, bottom = 210, 100, 195, 190
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_min, x_max = 0.0, 11.0
    y_min, y_max = 0.0, 55.0
    xp = lambda value: left + (value - x_min) / (x_max - x_min) * plot_width
    yp = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(bold, 47)
    subtitle_font = font(regular, 26)
    axis_font = font(bold, 30)
    tick_font = font(regular, 23)
    legend_font = font(regular, 21)
    equation_font = font(bold, 23)

    title = "P_probe–P_IOP 实际有限元散点与分式回归曲线"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (box[2] - box[0])) / 2, 30), title, fill="#111827", font=title_font)
    subtitle = "0–50 mmHg，步长2.5 mmHg；0.259875 mm主工作点；直接最小化IOP残差"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (box[2] - box[0])) / 2, 98), subtitle, fill="#4b5563", font=subtitle_font)

    for y in range(0, 56, 5):
        py = yp(y)
        draw.line((left, py, width - right, py), fill="#dbe3ec", width=2)
        text = str(y)
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((left - 22 - (box[2] - box[0]), py - (box[3] - box[1]) / 2), text, fill="#374151", font=tick_font)
    for x in range(12):
        px = xp(x)
        draw.line((px, top, px, height - bottom), fill="#edf2f7", width=2)
        text = str(x)
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (box[2] - box[0]) / 2, height - bottom + 18), text, fill="#374151", font=tick_font)
    draw.line((left, top, left, height - bottom), fill="#1f2937", width=4)
    draw.line((left, height - bottom, width - right, height - bottom), fill="#1f2937", width=4)

    curve = []
    observed_q_max = max(float(row["delta_probe_pressure_mmhg"]) for row in rows)
    for index in range(801):
        q = observed_q_max * index / 800.0
        curve.append((xp(q), yp(prediction(q, a, b))))
    draw.line(curve, fill="#dc2626", width=6, joint="curve")

    for row in rows:
        p = float(row["input_iop_mmhg"])
        q = float(row["delta_probe_pressure_mmhg"])
        is_new = row["source_kind"] == "new_supplemental_solver"
        color = "#f97316" if is_new else "#2563eb"
        px, py = xp(q), yp(p)
        draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=color, outline="white", width=3)

    equation = f"PIOP = {b:.6f} Pprobe / (1 − {a:.7f} Pprobe)"
    metric_text = (
        f"R² = {metrics['r_squared_iop_space']:.6f}    "
        f"MAE = {metrics['mae_all_points_mmhg']:.3f} mmHg    "
        f"RMSE = {metrics['rmse_all_points_mmhg']:.3f} mmHg"
    )
    box_x1, box_y1, box_x2, box_y2 = left + 35, top + 25, left + 850, top + 125
    draw.rounded_rectangle((box_x1, box_y1, box_x2, box_y2), radius=14, fill="#fff7ed", outline="#fdba74", width=2)
    draw.text((box_x1 + 20, box_y1 + 13), equation, fill="#991b1b", font=equation_font)
    draw.text((box_x1 + 20, box_y1 + 58), metric_text, fill="#4b5563", font=legend_font)

    legend_y = 157
    legend_entries = (
        (width - 740, "#2563eb", "复用5 mmHg点"),
        (width - 500, "#f97316", "新增中间点"),
        (width - 270, "#dc2626", "分式回归"),
    )
    for legend_x, color, text in legend_entries:
        if text == "分式回归":
            draw.line((legend_x, legend_y + 2, legend_x + 26, legend_y + 2), fill=color, width=5)
        else:
            draw.ellipse((legend_x, legend_y - 8, legend_x + 20, legend_y + 12), fill=color, outline="white", width=2)
        draw.text((legend_x + 34, legend_y - 14), text, fill="#374151", font=legend_font)

    xlabel = "扣除后探头读数 P_probe（mmHg）"
    box = draw.textbbox((0, 0), xlabel, font=axis_font)
    draw.text(((width - (box[2] - box[0])) / 2, height - 82), xlabel, fill="#111827", font=axis_font)
    ylabel = "眼内压 P_IOP（mmHg）"
    layer = Image.new("RGBA", (620, 70), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    box = layer_draw.textbbox((0, 0), ylabel, font=axis_font)
    layer_draw.text(((620 - (box[2] - box[0])) / 2, (70 - (box[3] - box[1])) / 2), ylabel, fill="#111827", font=axis_font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (30, top + (plot_height - layer.height) // 2), layer)

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-figure", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()
    rows = load_points(args.input_json)
    a, b = fit_rational(rows)
    output_rows, metrics = analyze(rows, a, b)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": "P_IOP=b*P_probe/(1-a*P_probe)",
        "fit_direction": "inverse calibration: input P_probe, target known FE P_IOP",
        "objective": "unweighted nonlinear least squares in P_IOP space",
        "source_json": str(args.input_json.resolve()),
        "pressure_grid_mmhg": [float(row["input_iop_mmhg"]) for row in rows],
        "parameters": {"a_per_mmhg": a, "b_dimensionless": b},
        "metrics": metrics,
        "rows": output_rows,
        "interpretation": {
            "status": "exploratory all-point inverse regression; not a production hardware calibration",
            "mechanistic_decomposition_not_used": True,
            "new_midpoint_holdout_consumed_by_this_fit": True,
            "known_limitation": "largest residuals occur in the low-pressure contact-activation region",
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    render_figure(output_rows, a, b, metrics, args.output_figure)
    print(json.dumps({
        "a_per_mmhg": a,
        "b_dimensionless": b,
        "metrics": metrics,
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
        "output_figure": str(args.output_figure),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
