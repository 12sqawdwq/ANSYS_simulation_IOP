#!/usr/bin/env python3
"""Plot direct RST interface-force forward model and its factor decomposition."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "20260731_3ce7c957_interface_force_integrals_summary.json"
DEFAULT_INVERSE = ROOT / "results" / "20260730_rational_regression_0_to_50_step2p5.json"
DEFAULT_MAIN = ROOT / "figures" / "interface_force_direct_forward_vs_inverse.png"
DEFAULT_FACTORS = ROOT / "figures" / "interface_force_factor_decomposition.png"


def font_path(filename: str) -> str:
    for directory in (Path("/usr/share/fonts/noto-cjk"), Path("/usr/share/fonts/opentype/noto")):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def rational(q: float, a: float, b: float) -> float:
    return b * q / (1.0 - a * q)


def axes(draw, width, height, left, right, top, bottom, x_max, y_max, x_step, y_step, tick_font):
    xp = lambda value: left + value / x_max * (width - left - right)
    yp = lambda value: top + (y_max - value) / y_max * (height - top - bottom)
    y = 0.0
    while y <= y_max + 1e-9:
        py = yp(y)
        draw.line((left, py, width - right, py), fill="#dbe3ec", width=2)
        text = f"{y:g}"
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((left - 20 - (box[2] - box[0]), py - (box[3] - box[1]) / 2), text, fill="#374151", font=tick_font)
        y += y_step
    x = 0.0
    while x <= x_max + 1e-9:
        px = xp(x)
        draw.line((px, top, px, height - bottom), fill="#edf2f7", width=2)
        text = f"{x:g}"
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (box[2] - box[0]) / 2, height - bottom + 17), text, fill="#374151", font=tick_font)
        x += x_step
    draw.line((left, top, left, height - bottom), fill="#1f2937", width=4)
    draw.line((left, height - bottom, width - right, height - bottom), fill="#1f2937", width=4)
    return xp, yp


def vertical_label(image, text, axis_font, x, top, plot_height):
    layer = Image.new("RGBA", (650, 70), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    box = layer_draw.textbbox((0, 0), text, font=axis_font)
    layer_draw.text(((650 - (box[2] - box[0])) / 2, (70 - (box[3] - box[1])) / 2), text, fill="#111827", font=axis_font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (x, top + (plot_height - layer.height) // 2), layer)


def draw_main(payload: dict, inverse: dict, output: Path) -> None:
    rows = payload["rows"]
    direct = payload["direct_interface_forward_model"]
    ai = float(inverse["parameters"]["a_per_mmhg"])
    bi = float(inverse["parameters"]["b_dimensionless"])
    ad = float(direct["a_per_mmhg"])
    bd = float(direct["b_dimensionless"])
    width, height = 1800, 1100
    left, right, top, bottom = 210, 100, 205, 190
    regular = font_path("NotoSansCJK-Regular.ttc")
    bold = font_path("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, subtitle_font = font(bold, 45), font(regular, 25)
    axis_font, tick_font, legend_font, box_font = font(bold, 30), font(regular, 23), font(regular, 21), font(bold, 21)
    title = "RST直接界面传力×面积正向计算与逆向回归"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - box[2] + box[0]) / 2, 28), title, fill="#111827", font=title_font)
    subtitle = "CONTA174全局接触力矢量积分；Ac,5°几何代理；0.259875 mm"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - box[2] + box[0]) / 2, 94), subtitle, fill="#4b5563", font=subtitle_font)
    xp, yp = axes(draw, width, height, left, right, top, bottom, 11.0, 55.0, 1.0, 5.0, tick_font)
    qmax = max(float(row["delta_probe_pressure_mmhg"]) for row in rows)
    inverse_curve, direct_curve = [], []
    for index in range(801):
        q = qmax * index / 800.0
        inverse_curve.append((xp(q), yp(rational(q, ai, bi))))
        direct_curve.append((xp(q), yp(rational(q, ad, bd))))
    draw.line(inverse_curve, fill="#dc2626", width=5, joint="curve")
    draw.line(direct_curve, fill="#059669", width=6, joint="curve")
    for row in rows:
        p = float(row["input_iop_mmhg"])
        q = float(row["delta_probe_pressure_mmhg"])
        draw.ellipse((xp(q) - 10, yp(p) - 10, xp(q) + 10, yp(p) + 10), fill="#2563eb", outline="white", width=3)
    x1, y1, x2, y2 = left + 35, top + 25, left + 920, top + 140
    draw.rounded_rectangle((x1, y1, x2, y2), radius=14, fill="#f8fafc", outline="#94a3b8", width=2)
    draw.text((x1 + 18, y1 + 12), f"直接正向：a={ad:.7f}，b={bd:.6f}", fill="#047857", font=box_font)
    draw.text((x1 + 18, y1 + 52), f"逆向回归：a={ai:.7f}，b={bi:.6f}", fill="#991b1b", font=box_font)
    metrics = direct["metrics_all_points"]
    draw.text((x1 + 18, y1 + 90), f"直接正向 MAE={metrics['mae_mmhg']:.3f}，RMSE={metrics['rmse_mmhg']:.3f} mmHg", fill="#4b5563", font=legend_font)
    for lx, color, text in ((width - 690, "#2563eb", "实际FE"), (width - 480, "#dc2626", "逆向回归"), (width - 250, "#059669", "直接正向")):
        if text == "实际FE": draw.ellipse((lx, 157, lx + 20, 177), fill=color)
        else: draw.line((lx, 168, lx + 28, 168), fill=color, width=6)
        draw.text((lx + 35, 151), text, fill="#374151", font=legend_font)
    xlabel = "扣除后探头读数 P_probe（mmHg）"
    box = draw.textbbox((0, 0), xlabel, font=axis_font)
    draw.text(((width - box[2] + box[0]) / 2, height - 82), xlabel, fill="#111827", font=axis_font)
    vertical_label(image, "眼内压 P_IOP（mmHg）", axis_font, 30, top, height - top - bottom)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def draw_factors(payload: dict, output: Path) -> None:
    rows = [row for row in payload["rows"] if float(row["input_iop_mmhg"]) > 0.0]
    width, height = 1800, 1050
    left, right, top, bottom = 210, 100, 175, 180
    regular = font_path("NotoSansCJK-Regular.ttc")
    bold = font_path("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, subtitle_font = font(bold, 45), font(regular, 25)
    axis_font, tick_font, legend_font = font(bold, 30), font(regular, 23), font(regular, 22)
    title = "RST界面传力分解：τ_interface、χ与η_eff"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - box[2] + box[0]) / 2, 27), title, fill="#111827", font=title_font)
    subtitle = "η_eff = τ_interface × χ；χ=p·Ac,5°/ΔF_interface"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - box[2] + box[0]) / 2, 92), subtitle, fill="#4b5563", font=subtitle_font)
    xp, yp = axes(draw, width, height, left, right, top, bottom, 50.0, 4.5, 5.0, 0.5, tick_font)
    series = (
        ("tau_interface_delta", "#2563eb", "直接界面传力比例 τ"),
        ("chi_pressure_equivalence", "#f97316", "压力等效修正 χ"),
        ("eta_effective_factorized", "#7c3aed", "综合修正 ηeff"),
    )
    for field, color, _ in series:
        points = [(xp(float(row["input_iop_mmhg"])), yp(float(row[field]))) for row in rows]
        draw.line(points, fill=color, width=5, joint="curve")
        for px, py in points: draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color, outline="white", width=2)
    for index, (_, color, text) in enumerate(series):
        lx = width - 820 + index * 270
        draw.line((lx, 145, lx + 30, 145), fill=color, width=6)
        draw.text((lx + 40, 130), text, fill="#374151", font=legend_font)
    xlabel = "输入IOP（mmHg）"
    box = draw.textbbox((0, 0), xlabel, font=axis_font)
    draw.text(((width - box[2] + box[0]) / 2, height - 76), xlabel, fill="#111827", font=axis_font)
    vertical_label(image, "无量纲修正或比例", axis_font, 30, top, height - top - bottom)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--inverse-json", type=Path, default=DEFAULT_INVERSE)
    parser.add_argument("--output-main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--output-factors", type=Path, default=DEFAULT_FACTORS)
    args = parser.parse_args()
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    inverse = json.loads(args.inverse_json.read_text(encoding="utf-8"))
    if not payload.get("campaign_pass"):
        raise ValueError("interface-force campaign did not pass")
    draw_main(payload, inverse, args.output_main)
    draw_factors(payload, args.output_factors)
    print(args.output_main)
    print(args.output_factors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
