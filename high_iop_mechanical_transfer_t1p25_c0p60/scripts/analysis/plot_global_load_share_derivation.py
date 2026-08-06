#!/usr/bin/env python3
"""Plot the global pressure-load-share derivation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "results" / "20260731_global_load_share_derivation.json"
DEFAULT_OUTPUT = ROOT / "figures" / "global_load_share_rational_derivation.png"


def font_path(filename: str) -> str:
    for directory in (Path("/usr/share/fonts/noto-cjk"), Path("/usr/share/fonts/opentype/noto")):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def rational(q: float, a: float, b: float) -> float:
    return b * q / (1.0 - a * q)


def panel_axes(draw, box, xmax, ymax, xstep, ystep, tick_font):
    left, top, right, bottom = box
    xp = lambda x: left + x / xmax * (right - left)
    yp = lambda y: bottom - y / ymax * (bottom - top)
    y = 0.0
    while y <= ymax + 1e-12:
        py = yp(y)
        draw.line((left, py, right, py), fill="#dbe3ec", width=2)
        text = f"{y:g}"
        tb = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((left - 14 - (tb[2] - tb[0]), py - (tb[3] - tb[1]) / 2), text, fill="#475569", font=tick_font)
        y += ystep
    x = 0.0
    while x <= xmax + 1e-12:
        px = xp(x)
        draw.line((px, top, px, bottom), fill="#edf2f7", width=2)
        text = f"{x:g}"
        tb = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (tb[2] - tb[0]) / 2, bottom + 12), text, fill="#475569", font=tick_font)
        x += xstep
    draw.line((left, top, left, bottom), fill="#1f2937", width=4)
    draw.line((left, bottom, right, bottom), fill="#1f2937", width=4)
    return xp, yp


def centered(draw, text, font, y, width, fill="#111827"):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


def vertical_label(image, text, font, x, top, height):
    layer = Image.new("RGBA", (500, 60), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    box = layer_draw.textbbox((0, 0), text, font=font)
    layer_draw.text(((500 - (box[2] - box[0])) / 2, (60 - (box[3] - box[1])) / 2), text, fill="#111827", font=font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (x, top + (height - layer.height) // 2), layer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    if not payload.get("derivation_pass"):
        raise ValueError("load-share derivation did not pass")

    regular = font_path("NotoSansCJK-Regular.ttc")
    bold = font_path("NotoSansCJK-Bold.ttc")
    f = lambda path, size: ImageFont.truetype(path, size=size)
    title_font, subtitle_font = f(bold, 43), f(regular, 23)
    panel_font, axis_font, tick_font, legend_font = f(bold, 29), f(bold, 24), f(regular, 20), f(regular, 20)
    width, height = 1900, 1080
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    centered(draw, "全模型压力载荷分流推导分式IOP模型", title_font, 25, width)
    cfg = payload["configuration"]
    val = payload["projected_area_validation"]
    subtitle = (
        f"几何投影面积={cfg['geometric_iop_projected_area_mm2']:.3f} mm²；"
        f"力平衡投影面积={val['balance_area_mean_stable_mm2']:.3f} mm²；稳定区10–50 mmHg"
    )
    centered(draw, subtitle, subtitle_font, 91, width, "#4b5563")

    left_box = (135, 225, 900, 845)
    right_box = (1085, 225, 1850, 845)
    centered(draw, "A. 进入探头的IOP总载荷份额", panel_font, 145, 950)
    title_b = "B. 载荷分流机制重建与实际FE"
    tb = draw.textbbox((0, 0), title_b, font=panel_font)
    draw.text((1085 + (765 - (tb[2] - tb[0])) / 2, 145), title_b, fill="#111827", font=panel_font)

    xpl, ypl = panel_axes(draw, left_box, 50.0, 0.10, 5.0, 0.01, tick_font)
    rows = payload["rows"]
    actual = [row for row in rows if row["input_iop_mmhg"] > 0.0]
    fit_points = []
    for index in range(501):
        pressure = 50.0 * index / 500.0
        capture = 1.0 / (
            payload["load_share_fit"]["c0_dimensionless"]
            + payload["load_share_fit"]["c1_per_mmhg"] * pressure
        )
        fit_points.append((xpl(pressure), ypl(capture)))
    draw.line(fit_points, fill="#059669", width=5, joint="curve")
    for row in actual:
        p = row["input_iop_mmhg"]
        value = row["probe_capture_fraction_lambda"]
        color = "#2563eb" if p >= 10.0 else "#f97316"
        draw.ellipse((xpl(p) - 7, ypl(value) - 7, xpl(p) + 7, ypl(value) + 7), fill=color, outline="white", width=2)
    draw.line((xpl(10), left_box[1], xpl(10), left_box[3]), fill="#94a3b8", width=3)
    draw.text((xpl(10) + 8, left_box[1] + 10), "稳定区起点", fill="#64748b", font=legend_font)
    draw.text((left_box[0] + 185, 912), "输入IOP（mmHg）", fill="#111827", font=axis_font)
    vertical_label(image, "载荷份额 λ", axis_font, 20, left_box[1], left_box[3] - left_box[1])
    draw.ellipse((left_box[0] + 28, 185, left_box[0] + 44, 201), fill="#2563eb")
    draw.text((left_box[0] + 52, 177), "稳定区FE", fill="#374151", font=legend_font)
    draw.ellipse((left_box[0] + 190, 185, left_box[0] + 206, 201), fill="#f97316")
    draw.text((left_box[0] + 214, 177), "低压启用段", fill="#374151", font=legend_font)
    draw.line((left_box[0] + 410, 193, left_box[0] + 440, 193), fill="#059669", width=5)
    draw.text((left_box[0] + 450, 177), "刚度分流模型", fill="#374151", font=legend_font)

    xpr, ypr = panel_axes(draw, right_box, 11.0, 55.0, 1.0, 5.0, tick_font)
    geom = payload["geometric_forward_parameters"]
    inv = payload["inverse_regression_reference"]
    qmax = max(row["delta_probe_pressure_mmhg"] for row in rows)
    direct_curve, inverse_curve = [], []
    for index in range(801):
        q = qmax * index / 800.0
        direct_curve.append((xpr(q), ypr(rational(q, geom["a_per_mmhg"], geom["b_dimensionless"]))))
        inverse_curve.append((xpr(q), ypr(rational(q, inv["a_per_mmhg"], inv["b_dimensionless"]))))
    draw.line(inverse_curve, fill="#dc2626", width=4, joint="curve")
    draw.line(direct_curve, fill="#059669", width=5, joint="curve")
    for row in rows:
        draw.ellipse((xpr(row["delta_probe_pressure_mmhg"]) - 7, ypr(row["input_iop_mmhg"]) - 7, xpr(row["delta_probe_pressure_mmhg"]) + 7, ypr(row["input_iop_mmhg"]) + 7), fill="#2563eb", outline="white", width=2)
    draw.text((right_box[0] + 180, 912), "Pprobe（mmHg）", fill="#111827", font=axis_font)
    vertical_label(image, "PIOP（mmHg）", axis_font, 966, right_box[1], right_box[3] - right_box[1])
    draw.ellipse((right_box[0] + 34, 185, right_box[0] + 50, 201), fill="#2563eb")
    draw.text((right_box[0] + 60, 177), "实际FE", fill="#374151", font=legend_font)
    draw.line((right_box[0] + 182, 193, right_box[0] + 212, 193), fill="#059669", width=5)
    draw.text((right_box[0] + 222, 177), "载荷分流推导", fill="#374151", font=legend_font)
    draw.line((right_box[0] + 435, 193, right_box[0] + 465, 193), fill="#dc2626", width=4)
    draw.text((right_box[0] + 475, 177), "逆向回归", fill="#374151", font=legend_font)

    fit = payload["load_share_fit"]
    footer = (
        f"1/λ={fit['c0_dimensionless']:.5f}+{fit['c1_per_mmhg']:.6f}·p（R²={fit['r_squared']:.5f}）   "
        f"→   a={geom['a_per_mmhg']:.7f}/mmHg，b={geom['b_dimensionless']:.6f}，"
        f"RMSE={geom['metrics_all_0_to_50']['rmse_mmhg']:.3f} mmHg"
    )
    centered(draw, footer, subtitle_font, 985, width, "#334155")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
