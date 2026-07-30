#!/usr/bin/env python3
"""Plot the bivariate scatter of input IOP and baseline-subtracted probe reading."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


P_IOP = [0, 20, 25, 30, 35, 40]
P_PROBE = [0.000000, 6.542306, 7.266877, 7.878858, 8.428966, 8.936937]

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "figures" / "piop_vs_delta_pprobe_scatter_0p259875.png"


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
FONT_BOLD = find_font("NotoSansCJK-Bold.ttc")

W, H = 1600, 960
LEFT, RIGHT, TOP, BOTTOM = 190, 90, 150, 170
PLOT_W = W - LEFT - RIGHT
PLOT_H = H - TOP - BOTTOM
X_MIN, X_MAX = 0.0, 42.0
Y_MIN, Y_MAX = 0.0, 10.0


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def xp(value: float) -> float:
    return LEFT + (value - X_MIN) / (X_MAX - X_MIN) * PLOT_W


def yp(value: float) -> float:
    return TOP + (Y_MAX - value) / (Y_MAX - Y_MIN) * PLOT_H


image = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(image)
title_font = font(FONT_BOLD, 47)
subtitle_font = font(FONT_REGULAR, 27)
axis_font = font(FONT_BOLD, 30)
tick_font = font(FONT_REGULAR, 25)
label_font = font(FONT_BOLD, 23)

# Titles
headline = "P_IOP 与扣除后 P_probe 的二值散点分布"
bbox = draw.textbbox((0, 0), headline, font=title_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, 34), headline, fill="#111827", font=title_font)
subtitle = "0.259875 mm 主工作点"
bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, 99), subtitle, fill="#4b5563", font=subtitle_font)

# Grid and ticks
for y in [0, 2, 4, 6, 8, 10]:
    py = yp(y)
    draw.line((LEFT, py, W - RIGHT, py), fill="#dbe3ec", width=2)
    text = str(y)
    bbox = draw.textbbox((0, 0), text, font=tick_font)
    draw.text((LEFT - 22 - (bbox[2] - bbox[0]), py - (bbox[3] - bbox[1]) / 2), text, fill="#374151", font=tick_font)

for x in [0, 5, 10, 15, 20, 25, 30, 35, 40]:
    px = xp(x)
    draw.line((px, TOP, px, H - BOTTOM), fill="#eef2f7", width=2)
    text = str(x)
    bbox = draw.textbbox((0, 0), text, font=tick_font)
    draw.text((px - (bbox[2] - bbox[0]) / 2, H - BOTTOM + 18), text, fill="#374151", font=tick_font)

# Axes
draw.line((LEFT, TOP, LEFT, H - BOTTOM), fill="#1f2937", width=4)
draw.line((LEFT, H - BOTTOM, W - RIGHT, H - BOTTOM), fill="#1f2937", width=4)

xlabel = "眼内压 P_IOP（mmHg）"
bbox = draw.textbbox((0, 0), xlabel, font=axis_font)
draw.text(((W - (bbox[2] - bbox[0])) / 2, H - 78), xlabel, fill="#111827", font=axis_font)
ylabel = "扣除后探头读数 P_probe（mmHg）"
layer = Image.new("RGBA", (590, 70), (255, 255, 255, 0))
ldraw = ImageDraw.Draw(layer)
bbox = ldraw.textbbox((0, 0), ylabel, font=axis_font)
ldraw.text(((590 - (bbox[2] - bbox[0])) / 2, (70 - (bbox[3] - bbox[1])) / 2), ylabel, fill="#111827", font=axis_font)
layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
image.paste(layer, (28, TOP + (PLOT_H - layer.height) // 2), layer)

# Scatter points and exact pair labels
points = [(xp(x), yp(y)) for x, y in zip(P_IOP, P_PROBE)]
label_offsets = [(18, -47), (-130, -54), (-70, 28), (-70, 28), (-70, -56), (-164, -54)]
for (px, py), x, y, (dx, dy) in zip(points, P_IOP, P_PROBE, label_offsets):
    draw.ellipse((px - 13, py - 13, px + 13, py + 13), fill="#2563eb", outline="white", width=4)
    text = f"({x}, {y:.6f})"
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
