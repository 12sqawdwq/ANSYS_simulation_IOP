#!/usr/bin/env python3
"""Plot actual FE P_IOP versus baseline-subtracted P_probe from 5 to 50 mmHg."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "results" / "20260730_440e44e5_iop_5_to_50_summary.json"
DEFAULT_OUTPUT = ROOT / "figures" / "piop_vs_delta_pprobe_scatter_5_to_50_step5.png"


def find_font(filename: str) -> str:
    for directory in (
        Path("/usr/share/fonts/noto-cjk"),
        Path("/usr/share/fonts/opentype/noto"),
    ):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def load_points(path: Path) -> list[tuple[float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = [float(value) for value in range(5, 51, 5)]
    rows = {
        float(row["input_iop_mmhg"]): float(row["delta_probe_pressure_mmhg"])
        for row in payload["rows"]
        if row["state"] == "primary_0p26" and float(row["input_iop_mmhg"]) > 0
    }
    if sorted(rows) != expected:
        raise ValueError(f"expected pressure grid {expected}, found {sorted(rows)}")
    return [(pressure, rows[pressure]) for pressure in expected]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    points = load_points(args.input_json)

    regular = find_font("NotoSansCJK-Regular.ttc")
    bold = find_font("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)

    width, height = 1700, 1000
    left, right, top, bottom = 200, 90, 165, 180
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_min, x_max = 0.0, 11.0
    y_min, y_max = 0.0, 55.0
    xp = lambda value: left + (value - x_min) / (x_max - x_min) * plot_width
    yp = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(bold, 48)
    subtitle_font = font(regular, 27)
    axis_font = font(bold, 30)
    tick_font = font(regular, 24)
    label_font = font(bold, 21)

    title = "扣除后 P_probe 与 P_IOP 的二值散点分布"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (box[2] - box[0])) / 2, 35), title, fill="#111827", font=title_font)
    subtitle = "5–50 mmHg，步长 5 mmHg；0.259875 mm 主工作点"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (box[2] - box[0])) / 2, 103), subtitle, fill="#4b5563", font=subtitle_font)

    for y in range(0, 56, 5):
        py = yp(y)
        draw.line((left, py, width - right, py), fill="#dbe3ec", width=2)
        text = str(y)
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((left - 22 - (box[2] - box[0]), py - (box[3] - box[1]) / 2), text, fill="#374151", font=tick_font)
    for x in range(0, 12):
        px = xp(x)
        draw.line((px, top, px, height - bottom), fill="#eef2f7", width=2)
        text = str(x)
        box = draw.textbbox((0, 0), text, font=tick_font)
        draw.text((px - (box[2] - box[0]) / 2, height - bottom + 18), text, fill="#374151", font=tick_font)

    draw.line((left, top, left, height - bottom), fill="#1f2937", width=4)
    draw.line((left, height - bottom, width - right, height - bottom), fill="#1f2937", width=4)

    xlabel = "扣除后探头读数 P_probe（mmHg）"
    box = draw.textbbox((0, 0), xlabel, font=axis_font)
    draw.text(((width - (box[2] - box[0])) / 2, height - 82), xlabel, fill="#111827", font=axis_font)
    ylabel = "眼内压 P_IOP（mmHg）"
    layer = Image.new("RGBA", (600, 70), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    box = layer_draw.textbbox((0, 0), ylabel, font=axis_font)
    layer_draw.text(((600 - (box[2] - box[0])) / 2, (70 - (box[3] - box[1])) / 2), ylabel, fill="#111827", font=axis_font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (29, top + (plot_height - layer.height) // 2), layer)

    for index, (pressure, probe) in enumerate(points):
        px, py = xp(probe), yp(pressure)
        draw.ellipse((px - 13, py - 13, px + 13, py + 13), fill="#2563eb", outline="white", width=4)
        text = f"{probe:.6f}"
        box = draw.textbbox((0, 0), text, font=label_font)
        text_width = box[2] - box[0]
        text_height = box[3] - box[1]
        dx = -text_width - 20 if index % 2 == 0 else 20
        dy = -text_height / 2
        tx, ty = px + dx, py + dy
        pad = 7
        draw.rounded_rectangle(
            (tx - pad, ty - pad, tx + text_width + pad, ty + (box[3] - box[1]) + pad),
            radius=8,
            fill="#eff6ff",
            outline="#93c5fd",
            width=2,
        )
        draw.text((tx, ty), text, fill="#1d4ed8", font=label_font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
