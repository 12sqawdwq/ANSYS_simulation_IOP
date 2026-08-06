#!/usr/bin/env python3
"""Derive provisional rational parameters from FE area and transfer submodels."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "results" / "20260730_290d0544_iop_0_to_50_step2p5_summary.json"
DEFAULT_INVERSE = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
DEFAULT_JSON = ROOT / "results" / "20260731_forward_rational_parameters_ac5_proxy.json"
DEFAULT_CSV = ROOT / "results" / "20260731_forward_rational_parameters_ac5_proxy.csv"
DEFAULT_FIGURE = ROOT / "figures" / "forward_vs_inverse_rational_iop_0_to_50_step2p5.png"
PROBE_AREA_MM2 = 14.65741468458854
CORNEA_RADIUS_MM = 7.8
PRIMARY_INDENT_MM = 0.259875
PA_PER_MMHG = 133.32236842105263
PRESSURE_MPA_PER_MMHG = PA_PER_MMHG / 1e6
STABLE_MIN_IOP_MMHG = 10.0
REFERENCE_IOP_MMHG = 25.0


def find_font(filename: str) -> str:
    for directory in (Path("/usr/share/fonts/noto-cjk"), Path("/usr/share/fonts/opentype/noto")):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def linear_fit(xs: list[float], ys: list[float]) -> dict[str, float]:
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    sxx = sum((value - mean_x) ** 2 for value in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
    intercept = mean_y - slope * mean_x
    sse = sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - mean_y) ** 2 for y in ys)
    return {
        "intercept": intercept,
        "slope_per_mmhg": slope,
        "r_squared": 1.0 - sse / sst,
        "sse": sse,
    }


def rational(q: float, a: float, b: float) -> float:
    return b * q / (1.0 - a * q)


def metrics(rows: list[dict], field: str) -> dict[str, float]:
    errors = [float(row[field]) - float(row["input_iop_mmhg"]) for row in rows]
    pressures = [float(row["input_iop_mmhg"]) for row in rows]
    mean_pressure = sum(pressures) / len(pressures)
    sse = sum(value * value for value in errors)
    sst = sum((value - mean_pressure) ** 2 for value in pressures)
    return {
        "point_count": len(rows),
        "mae_mmhg": sum(abs(value) for value in errors) / len(errors),
        "rmse_mmhg": math.sqrt(sse / len(errors)),
        "maximum_absolute_error_mmhg": max(abs(value) for value in errors),
        "r_squared": 1.0 - sse / sst,
    }


def load_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("campaign_pass") or not all(payload["qc"].values()):
        raise ValueError("source FE campaign did not pass")
    rows = [dict(row) for row in payload["rows"] if row["state"] == "primary_0p26"]
    expected = [index * 2.5 for index in range(21)]
    if [float(row["input_iop_mmhg"]) for row in rows] != expected:
        raise ValueError("unexpected pressure grid")
    return rows


def derive(rows: list[dict], inverse: dict) -> tuple[dict, list[dict]]:
    enriched = []
    for row in rows:
        p = float(row["input_iop_mmhg"])
        q = float(row["delta_probe_pressure_mmhg"])
        ac = float(row["inner_ac_5deg_mm2"])
        area_ratio = PROBE_AREA_MM2 / ac
        eta = p / (q * area_ratio) if p > 0.0 else None
        enriched.append({
            "input_iop_mmhg": p,
            "delta_probe_pressure_mmhg": q,
            "inner_ac_5deg_mm2": ac,
            "area_ratio_ap_over_ac5": area_ratio,
            "eta_effective_ac5_proxy": eta,
            "source_kind": row["source_kind"],
        })

    stable = [row for row in enriched if float(row["input_iop_mmhg"]) >= STABLE_MIN_IOP_MMHG]
    pressures = [float(row["input_iop_mmhg"]) for row in stable]
    area_fit = linear_fit(pressures, [float(row["area_ratio_ap_over_ac5"]) for row in stable])
    eta_fit = linear_fit(pressures, [float(row["eta_effective_ac5_proxy"]) for row in stable])
    c0 = area_fit["intercept"]
    c1 = area_fit["slope_per_mmhg"]
    eta0 = eta_fit["intercept"]
    eta1 = eta_fit["slope_per_mmhg"]

    product_0 = eta0 * c0
    product_1 = eta0 * c1 + eta1 * c0
    product_2 = eta1 * c1
    p_ref = REFERENCE_IOP_MMHG
    forward_a = product_1 + 2.0 * product_2 * p_ref
    forward_b = product_0 - product_2 * p_ref**2

    eta_at_reference = eta0 + eta1 * p_ref
    constant_eta_a = eta_at_reference * c1
    constant_eta_b = eta_at_reference * c0
    inverse_a = float(inverse["parameters"]["a_per_mmhg"])
    inverse_b = float(inverse["parameters"]["b_dimensionless"])

    c1_per_mpa = c1 / PRESSURE_MPA_PER_MMHG
    alpha_over_kl_mm_per_n = c1_per_mpa * (2.0 * math.pi * PRIMARY_INDENT_MM / PROBE_AREA_MM2)
    kc0_over_kl = (
        c0 * 2.0 * math.pi * PRIMARY_INDENT_MM * CORNEA_RADIUS_MM / PROBE_AREA_MM2 - 1.0
    )

    for row in enriched:
        q = float(row["delta_probe_pressure_mmhg"])
        row["forward_rational_iop_mmhg"] = rational(q, forward_a, forward_b)
        row["inverse_regression_iop_mmhg"] = rational(q, inverse_a, inverse_b)
        row["forward_error_mmhg"] = row["forward_rational_iop_mmhg"] - float(row["input_iop_mmhg"])
        row["inverse_error_mmhg"] = row["inverse_regression_iop_mmhg"] - float(row["input_iop_mmhg"])

    stable_outputs = [row for row in enriched if float(row["input_iop_mmhg"]) >= STABLE_MIN_IOP_MMHG]
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "provisional forward derivation using Ac5 geometric proxy and FE-known IOP",
        "source_json": str(DEFAULT_SOURCE.resolve()),
        "inverse_regression_json": str(DEFAULT_INVERSE.resolve()),
        "constants": {
            "probe_area_mm2": PROBE_AREA_MM2,
            "cornea_radius_mm": CORNEA_RADIUS_MM,
            "primary_indent_mm": PRIMARY_INDENT_MM,
            "stable_min_iop_mmhg": STABLE_MIN_IOP_MMHG,
            "linearization_reference_iop_mmhg": REFERENCE_IOP_MMHG,
        },
        "area_model": {
            "equation": "K_A(p)=c0+c1*p, K_A=A_probe/A_c5deg",
            "c0": c0,
            "c1_per_mmhg": c1,
            "r_squared": area_fit["r_squared"],
            "derived_kc0_over_kl": kc0_over_kl,
            "derived_alpha_over_kl_mm_per_n": alpha_over_kl_mm_per_n,
        },
        "transfer_model": {
            "equation": "eta_eff(p)=eta0+eta1*p, eta_eff=p*A_c5/deltaF",
            "eta0": eta0,
            "eta1_per_mmhg": eta1,
            "eta_at_reference": eta_at_reference,
            "r_squared": eta_fit["r_squared"],
            "circularity_warning": "eta_eff uses known FE input IOP and is not an independent interface-force measurement.",
        },
        "product_model": {
            "equation": "eta_eff*K_A=d0+d1*p+d2*p^2",
            "d0": product_0,
            "d1_per_mmhg": product_1,
            "d2_per_mmhg2": product_2,
        },
        "constant_eta_diagnostic": {
            "a_per_mmhg": constant_eta_a,
            "b_dimensionless": constant_eta_b,
            "interpretation": "The original constant-eta area-only formula does not reproduce the inverse parameters.",
        },
        "forward_local_linearization": {
            "equation": "P_IOP=b*P_probe/(1-a*P_probe)",
            "a_per_mmhg": forward_a,
            "b_dimensionless": forward_b,
            "a_difference_from_inverse_percent": 100.0 * (forward_a / inverse_a - 1.0),
            "b_difference_from_inverse_percent": 100.0 * (forward_b / inverse_b - 1.0),
            "metrics_all_0_to_50": metrics(enriched, "forward_rational_iop_mmhg"),
            "metrics_stable_10_to_50": metrics(stable_outputs, "forward_rational_iop_mmhg"),
        },
        "inverse_regression_reference": {
            "a_per_mmhg": inverse_a,
            "b_dimensionless": inverse_b,
            "metrics_all_0_to_50": metrics(enriched, "inverse_regression_iop_mmhg"),
        },
        "limitations": [
            "A_c5deg is a frozen geometric proxy, not yet an independently validated mechanical effective area.",
            "eta_eff is inferred from known p, A_c5deg, and deltaF; direct eyelid-cornea interface force integration is still required.",
            "The stable submodels use 10–50 mmHg; low-pressure contact activation is outside their derivation range.",
            "The local linearization is centered at 25 mmHg and is not a universal hardware calibration.",
        ],
    }
    return payload, enriched


def draw_dashed(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: str, width: int) -> None:
    for start in range(0, len(points) - 1, 18):
        segment = points[start : min(start + 11, len(points))]
        if len(segment) >= 2:
            draw.line(segment, fill=fill, width=width, joint="curve")


def render(rows: list[dict], payload: dict, output: Path) -> None:
    regular = find_font("NotoSansCJK-Regular.ttc")
    bold = find_font("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)
    width, height = 1800, 1100
    left, right, top, bottom = 210, 100, 205, 190
    plot_width = width - left - right
    plot_height = height - top - bottom
    xp = lambda value: left + value / 11.0 * plot_width
    yp = lambda value: top + (55.0 - value) / 55.0 * plot_height
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(bold, 45)
    subtitle_font = font(regular, 25)
    axis_font = font(bold, 30)
    tick_font = font(regular, 23)
    legend_font = font(regular, 21)
    box_font = font(bold, 21)

    title = "P_probe–P_IOP 正向代理推导与逆向回归对比"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (box[2] - box[0])) / 2, 28), title, fill="#111827", font=title_font)
    subtitle = "Ac,5°代理；10–50 mmHg识别面积与传力子模型；25 mmHg局部线性化"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (box[2] - box[0])) / 2, 94), subtitle, fill="#4b5563", font=subtitle_font)

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

    forward = payload["forward_local_linearization"]
    inverse = payload["inverse_regression_reference"]
    observed_q_max = max(float(row["delta_probe_pressure_mmhg"]) for row in rows)
    inverse_curve = []
    forward_curve = []
    for index in range(801):
        q = observed_q_max * index / 800.0
        inverse_curve.append((xp(q), yp(rational(q, inverse["a_per_mmhg"], inverse["b_dimensionless"]))))
        forward_curve.append((xp(q), yp(rational(q, forward["a_per_mmhg"], forward["b_dimensionless"]))))
    draw.line(inverse_curve, fill="#dc2626", width=5, joint="curve")
    draw_dashed(draw, forward_curve, "#059669", 7)

    for row in rows:
        p = float(row["input_iop_mmhg"])
        q = float(row["delta_probe_pressure_mmhg"])
        color = "#f97316" if row["source_kind"] == "new_supplemental_solver" else "#2563eb"
        px, py = xp(q), yp(p)
        draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill=color, outline="white", width=3)

    x1, y1, x2, y2 = left + 35, top + 25, left + 880, top + 135
    draw.rounded_rectangle((x1, y1, x2, y2), radius=14, fill="#f0fdf4", outline="#86efac", width=2)
    draw.text((x1 + 18, y1 + 13), f"正向代理：a={forward['a_per_mmhg']:.7f}，b={forward['b_dimensionless']:.6f}", fill="#047857", font=box_font)
    draw.text((x1 + 18, y1 + 53), f"逆向回归：a={inverse['a_per_mmhg']:.7f}，b={inverse['b_dimensionless']:.6f}", fill="#991b1b", font=box_font)
    draw.text((x1 + 18, y1 + 88), f"差异：a {forward['a_difference_from_inverse_percent']:+.2f}%　b {forward['b_difference_from_inverse_percent']:+.2f}%", fill="#4b5563", font=legend_font)

    legend_y = 164
    for legend_x, color, text, line in (
        (width - 710, "#2563eb", "实际FE点", False),
        (width - 500, "#dc2626", "逆向回归", True),
        (width - 270, "#059669", "正向代理", True),
    ):
        if line:
            draw.line((legend_x, legend_y + 2, legend_x + 27, legend_y + 2), fill=color, width=6)
        else:
            draw.ellipse((legend_x, legend_y - 8, legend_x + 20, legend_y + 12), fill=color, outline="white", width=2)
        draw.text((legend_x + 35, legend_y - 14), text, fill="#374151", font=legend_font)

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
    parser.add_argument("--source-json", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--inverse-json", type=Path, default=DEFAULT_INVERSE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-figure", type=Path, default=DEFAULT_FIGURE)
    args = parser.parse_args()
    rows = load_rows(args.source_json)
    inverse = json.loads(args.inverse_json.read_text(encoding="utf-8"))
    payload, output_rows = derive(rows, inverse)
    payload["source_json"] = str(args.source_json.resolve())
    payload["inverse_regression_json"] = str(args.inverse_json.resolve())
    payload["rows"] = output_rows
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    render(output_rows, payload, args.output_figure)
    print(json.dumps({
        "area_model": payload["area_model"],
        "transfer_model": payload["transfer_model"],
        "constant_eta_diagnostic": payload["constant_eta_diagnostic"],
        "forward_local_linearization": payload["forward_local_linearization"],
        "inverse_regression_reference": payload["inverse_regression_reference"],
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
        "output_figure": str(args.output_figure),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
