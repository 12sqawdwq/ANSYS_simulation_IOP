#!/usr/bin/env python3
"""Evaluate frozen 0–50 mmHg rational models on unseen 52.5–60 mmHg FE points."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MODEL_LABELS = {
    "inverse_regression_0_to_50": ("逆向回归", "#dc2626"),
    "composite_proxy_0_to_50": ("综合代理", "#7c3aed"),
    "load_share_reparameterization_10_to_50": ("载荷分流", "#059669"),
}


def rational(q: float, a: float, b: float) -> float:
    denominator = 1.0 - a * q
    return b * q / denominator if denominator > 0.0 else math.nan


def implied_probe(p: float, a: float, b: float) -> float:
    return p / (b + a * p)


def metrics(rows: list[dict], model_name: str) -> dict[str, float | int]:
    errors = [row[f"{model_name}_error_mmhg"] for row in rows]
    return {
        "point_count": len(errors),
        "mae_mmhg": sum(abs(error) for error in errors) / len(errors),
        "rmse_mmhg": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "maximum_absolute_error_mmhg": max(abs(error) for error in errors),
    }


def font_path(filename: str) -> str:
    """Resolve a CJK font on Linux or Windows without a machine-specific path."""
    exact_directories = (
        Path("/usr/share/fonts/noto-cjk"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("C:/Windows/Fonts"),
    )
    for directory in exact_directories:
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)

    bold = "Bold" in filename
    fallbacks = (
        ("NotoSansSC-VF.ttf", "msyhbd.ttc", "msjhbd.ttc", "simhei.ttf")
        if bold
        else ("NotoSansSC-VF.ttf", "msyh.ttc", "msjh.ttc", "simsun.ttc")
    )
    for fallback in fallbacks:
        candidate = Path("C:/Windows/Fonts") / fallback
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(f"No CJK font found for {filename}")


def draw_figure(rows: list[dict], models: dict, payload: dict, output: Path) -> None:
    width, height = 1850, 1120
    left, right, top, bottom = 210, 90, 210, 190
    regular = font_path("NotoSansCJK-Regular.ttc")
    bold = font_path("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)
    title_font, subtitle_font = font(bold, 44), font(regular, 24)
    axis_font, tick_font, legend_font, box_font = font(bold, 29), font(regular, 22), font(regular, 21), font(bold, 20)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title = "冻结0–50 mmHg分式模型的52.5–60 mmHg外推检验"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (box[2] - box[0])) / 2, 25), title, fill="#111827", font=title_font)
    subtitle = "实际FE点；0.259875 mm主工作点；外推评估前不重新拟合"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (box[2] - box[0])) / 2, 90), subtitle, fill="#4b5563", font=subtitle_font)

    maximum_probe = max(row["delta_probe_pressure_mmhg"] for row in rows)
    x_max = float(math.ceil(maximum_probe + 1.0))
    y_max = 62.5
    xp = lambda value: left + value / x_max * (width - left - right)
    yp = lambda value: top + (y_max - value) / y_max * (height - top - bottom)
    for y in [index * 5.0 for index in range(round(y_max / 5.0) + 1)]:
        py = yp(y)
        draw.line((left, py, width - right, py), fill="#dbe3ec", width=2)
        text = f"{y:g}"
        tb = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((left - 18 - (tb[2] - tb[0]), py - (tb[3] - tb[1]) / 2), text, fill="#374151", font=tick_font)
    for x in range(math.ceil(x_max) + 1):
        px = xp(float(x))
        draw.line((px, top, px, height - bottom), fill="#edf2f7", width=2)
        text = str(x)
        tb = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (tb[2] - tb[0]) / 2, height - bottom + 14), text, fill="#374151", font=tick_font)
    draw.line((left, top, left, height - bottom), fill="#1f2937", width=4)
    draw.line((left, height - bottom, width - right, height - bottom), fill="#1f2937", width=4)

    q_curve_max = maximum_probe * 1.015
    for model_name, parameters in models.items():
        color = MODEL_LABELS[model_name][1]
        points = []
        for index in range(801):
            q = q_curve_max * index / 800.0
            prediction = rational(q, parameters["a_per_mmhg"], parameters["b_dimensionless"])
            if math.isfinite(prediction) and prediction <= y_max + 2.0:
                points.append((xp(q), yp(prediction)))
        draw.line(points, fill=color, width=5, joint="curve")

    for row in rows:
        is_new = row["is_unseen_extrapolation_point"]
        color = "#f97316" if is_new else "#2563eb"
        px, py = xp(row["delta_probe_pressure_mmhg"]), yp(row["input_iop_mmhg"])
        radius = 10 if is_new else 7
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color, outline="white", width=2)

    legend_items = [("#2563eb", "0–50 FE"), ("#f97316", "52.5–60 FE")]
    legend_items.extend((MODEL_LABELS[name][1], MODEL_LABELS[name][0]) for name in models)
    start_x = 640
    for index, (color, label) in enumerate(legend_items):
        lx = start_x + index * 220
        if index < 2:
            draw.ellipse((lx, 160, lx + 18, 178), fill=color)
        else:
            draw.line((lx, 169, lx + 28, 169), fill=color, width=5)
        draw.text((lx + 35, 152), label, fill="#374151", font=legend_font)

    inverse_metrics = payload["metrics"]["inverse_regression_0_to_50"]["unseen_52p5_to_60"]
    box_coords = (left + 25, top + 25, left + 590, top + 115)
    draw.rounded_rectangle(box_coords, radius=12, fill="#fff7ed", outline="#fdba74", width=2)
    draw.text((box_coords[0] + 18, box_coords[1] + 12), f"逆向冻结模型外推：MAE={inverse_metrics['mae_mmhg']:.3f} mmHg", fill="#9a3412", font=box_font)
    draw.text((box_coords[0] + 18, box_coords[1] + 49), f"RMSE={inverse_metrics['rmse_mmhg']:.3f}，最大误差={inverse_metrics['maximum_absolute_error_mmhg']:.3f} mmHg", fill="#9a3412", font=box_font)

    xlabel = "扣除后探头读数 Pprobe（mmHg）"
    tb = draw.textbbox((0, 0), xlabel, font=axis_font)
    draw.text(((width - (tb[2] - tb[0])) / 2, height - 78), xlabel, fill="#111827", font=axis_font)
    ylabel = "输入IOP（mmHg）"
    layer = Image.new("RGBA", (500, 65), (255, 255, 255, 0))
    ld = ImageDraw.Draw(layer)
    tb = ld.textbbox((0, 0), ylabel, font=axis_font)
    ld.text(((500 - (tb[2] - tb[0])) / 2, (65 - (tb[3] - tb[1])) / 2), ylabel, fill="#111827", font=axis_font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (28, top + (height - top - bottom - layer.height) // 2), layer)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-summary", type=Path, required=True)
    parser.add_argument("--run-spec", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-figure", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.input_summary.read_text(encoding="utf-8"))
    spec = json.loads(args.run_spec.read_text(encoding="utf-8"))
    if not summary.get("campaign_pass"):
        raise ValueError("extended FE campaign did not pass")
    models = spec["frozen_rational_models_for_extrapolation_only"]
    new_pressures = {float(value) for value in spec["new_solver_pressures_mmhg"]}
    source_rows = sorted(
        (row for row in summary["rows"] if row["state"] == "primary_0p26"),
        key=lambda row: float(row["input_iop_mmhg"]),
    )
    rows = []
    for source in source_rows:
        pressure = float(source["input_iop_mmhg"])
        q = float(source["delta_probe_pressure_mmhg"])
        row = {
            "input_iop_mmhg": pressure,
            "delta_probe_pressure_mmhg": q,
            "probe_force_n": float(source["probe_force_n"]),
            "actual_indent_mm": float(source["actual_indent_mm"]),
            "is_unseen_extrapolation_point": pressure in new_pressures,
            "source_kind": source["source_kind"],
        }
        for model_name, parameters in models.items():
            a = float(parameters["a_per_mmhg"])
            b = float(parameters["b_dimensionless"])
            prediction = rational(q, a, b)
            model_q = implied_probe(pressure, a, b)
            row[f"{model_name}_iop_prediction_mmhg"] = prediction
            row[f"{model_name}_error_mmhg"] = prediction - pressure
            row[f"{model_name}_implied_probe_mmhg"] = model_q
            row[f"{model_name}_probe_residual_mmhg"] = q - model_q
            row[f"{model_name}_denominator"] = 1.0 - a * q
        rows.append(row)

    reused = [row for row in rows if row["input_iop_mmhg"] <= 50.0]
    unseen = [row for row in rows if row["is_unseen_extrapolation_point"]]
    if [row["input_iop_mmhg"] for row in unseen] != sorted(new_pressures):
        raise ValueError("unseen extrapolation grid is incomplete")
    model_metrics = {
        name: {
            "reused_0_to_50": metrics(reused, name),
            "unseen_52p5_to_60": metrics(unseen, name),
            "extended_0_to_60": metrics(rows, name),
            "minimum_denominator_0_to_60": min(row[f"{name}_denominator"] for row in rows),
        }
        for name in models
    }
    interval_gains = []
    for left, right in zip(rows, rows[1:]):
        if right["input_iop_mmhg"] < 50.0:
            continue
        interval_gains.append({
            "from_iop_mmhg": left["input_iop_mmhg"],
            "to_iop_mmhg": right["input_iop_mmhg"],
            "delta_probe_pressure_gain_per_mmhg": (
                right["delta_probe_pressure_mmhg"] - left["delta_probe_pressure_mmhg"]
            ) / (right["input_iop_mmhg"] - left["input_iop_mmhg"]),
        })
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "frozen_models_evaluated_without_refit",
        "source_summary": str(args.input_summary.resolve()),
        "run_spec": str(args.run_spec.resolve()),
        "unseen_pressures_mmhg": sorted(new_pressures),
        "frozen_models": models,
        "metrics": model_metrics,
        "distribution_diagnostics": {
            "probe_reading_monotonic_0_to_60": all(
                right["delta_probe_pressure_mmhg"] > left["delta_probe_pressure_mmhg"]
                for left, right in zip(rows, rows[1:])
            ),
            "new_interval_gains": interval_gains,
        },
        "interpretation": {
            "independence": "The four 52.5-to-60 mmHg FE points were not used to identify the frozen 0-to-50 model parameters.",
            "no_refit": True,
            "scope": spec["interpretation"]["scope_policy"],
        },
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    draw_figure(rows, models, payload, args.output_figure)
    print(json.dumps({
        "unseen_pressures_mmhg": payload["unseen_pressures_mmhg"],
        "metrics": model_metrics,
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
        "output_figure": str(args.output_figure),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
