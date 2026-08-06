#!/usr/bin/env python3
"""Plot IOP versus K=Ae/Ac using the user-provided table values."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


IOP = [0, 20, 25, 30, 35, 40]
K_AE_AC = [2.454723, 2.630974, 2.758612, 2.797279, 3.403860, 4.297049]

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "figures" / "iop_vs_k_ae_over_ac_0p259875.png"


def find_font(filename: str) -> str:
    for directory in (
        Path("/usr/share/fonts/noto-cjk"),
        Path("/usr/share/fonts/opentype/noto"),
    ):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


FONT_REGULAR = find_font("NotoSansCJK-Regular.ttc")
FONT_MEDIUM = find_font("NotoSansCJK-Bold.ttc")

W, H = 1600, 960
LEFT, RIGHT, TOP, BOTTOM = 180, 90, 150, 170
PLOT_W = W - LEFT - RIGHT
PLOT_H = H - TOP - BOTTOM
Y_MIN, Y_MAX = 2.2, 4.6


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def xp(value: float) -> float:
    return LEFT + value / 40.0 * PLOT_W


def yp(value: float) -> float:
    return TOP + (Y_MAX - value) / (Y_MAX - Y_MIN) * PLOT_H


image = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(image)
title_font = font(FONT_MEDIUM, 48)
subtitle_font = font(FONT_REGULAR, 27)
axis_font = font(FONT_MEDIUM, 31)
tick_font = font(FONT_REGULAR, 25)
label_font = font(FONT_MEDIUM, 24)

# Titles
headline = "眼内压与面积比例 K（Ae/Ac5°）的关系"
bbox = draw.textbbox((0, 0), headline, font=title_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, 35), headline, fill="#111827", font=title_font)
subtitle = "0.259875 mm 主工作点"
bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, 98), subtitle, fill="#4b5563", font=subtitle_font)

# Grid and ticks
for y in [2.2, 2.6, 3.0, 3.4, 3.8, 4.2, 4.6]:
    py = yp(y)
    draw.line((LEFT, py, W - RIGHT, py), fill="#dbe3ec", width=2)
    text = f"{y:.1f}"
    bbox = draw.textbbox((0, 0), text, font=tick_font)
    draw.text((LEFT - 22 - (bbox[2] - bbox[0]), py - (bbox[3] - bbox[1]) / 2), text, fill="#374151", font=tick_font)

for x in IOP:
    px = xp(x)
    draw.line((px, TOP, px, H - BOTTOM), fill="#eef2f7", width=2)
    text = str(x)
    bbox = draw.textbbox((0, 0), text, font=tick_font)
    draw.text((px - (bbox[2] - bbox[0]) / 2, H - BOTTOM + 18), text, fill="#374151", font=tick_font)

# Axes
draw.line((LEFT, TOP, LEFT, H - BOTTOM), fill="#1f2937", width=4)
draw.line((LEFT, H - BOTTOM, W - RIGHT, H - BOTTOM), fill="#1f2937", width=4)

# Axis labels
xlabel = "眼内压 IOP（mmHg）"
bbox = draw.textbbox((0, 0), xlabel, font=axis_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, H - 78), xlabel, fill="#111827", font=axis_font)
ylabel = "面积比例 K = Ae / Ac5°"
layer = Image.new("RGBA", (520, 70), (255, 255, 255, 0))
ldraw = ImageDraw.Draw(layer)
bbox = ldraw.textbbox((0, 0), ylabel, font=axis_font)
ldraw.text(((520 - (bbox[2] - bbox[0])) / 2, (70 - (bbox[3] - bbox[1])) / 2), ylabel, fill="#111827", font=axis_font)
layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
image.paste(layer, (26, TOP + (PLOT_H - layer.height) // 2), layer)

# Relationship line
points = [(xp(x), yp(y)) for x, y in zip(IOP, K_AE_AC)]
draw.line(points, fill="#2563eb", width=6, joint="curve")
for px, py in points:
    draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill="white", outline="#2563eb", width=6)

# Point labels
positions = [(16, -48), (-58, -52), (-54, 26), (-54, 28), (-54, -52), (-128, -48)]
for (px, py), value, (dx, dy) in zip(points, K_AE_AC, positions):
    text = f"{value:.6f}"
    bbox = draw.textbbox((0, 0), text, font=label_font)
    tx, ty = px + dx, py + dy
    pad = 7
    draw.rounded_rectangle(
        (tx - pad, ty - pad, tx + (bbox[2] - bbox[0]) + pad, ty + (bbox[3] - bbox[1]) + pad),
        radius=8,
        fill="#eff6ff",
        outline="#93c5fd",
        width=2,
    )
    draw.text((tx, ty), text, fill="#1d4ed8", font=label_font)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
image.save(OUTPUT, format="PNG", optimize=True)
print(OUTPUT)
