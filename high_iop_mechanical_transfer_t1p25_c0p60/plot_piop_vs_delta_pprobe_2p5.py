#!/usr/bin/env python3
"""Plot actual FE P_IOP versus baseline-subtracted P_probe on a 2.5 mmHg grid."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def find_font(filename: str) -> str:
    for directory in (
        Path("/usr/share/fonts/noto-cjk"),
        Path("/usr/share/fonts/opentype/noto"),
    ):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(filename)


def load_points(path: Path) -> tuple[list[tuple[float, float, bool]], float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("campaign_pass"):
        raise ValueError("dense FE campaign did not pass")
    expected = [float(value) for value in payload["final_pressure_grid_mmhg"]]
    if len(expected) < 2:
        raise ValueError("pressure grid requires at least two points")
    step = expected[1] - expected[0]
    if step <= 0.0 or any(not math.isclose(right - left, step, abs_tol=1e-12) for left, right in zip(expected, expected[1:])):
        raise ValueError(f"nonuniform pressure grid: {expected}")
    rows = {
        float(row["input_iop_mmhg"]): row
        for row in payload["rows"]
        if row["state"] == "primary_0p26"
    }
    if sorted(rows) != expected:
        raise ValueError(f"expected pressure grid {expected}, found {sorted(rows)}")
    return ([
        (
            pressure,
            float(rows[pressure]["delta_probe_pressure_mmhg"]),
            rows[pressure]["source_kind"] == "new_supplemental_solver",
        )
        for pressure in expected
    ], step)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    points, pressure_step = load_points(args.input_json)

    regular = find_font("NotoSansCJK-Regular.ttc")
    bold = find_font("NotoSansCJK-Bold.ttc")
    font = lambda path, size: ImageFont.truetype(path, size=size)

    width, height = 1800, 1100
    left, right, top, bottom = 210, 100, 175, 190
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum_pressure = max(point[0] for point in points)
    maximum_probe = max(point[1] for point in points)
    x_min, x_max = 0.0, float(math.ceil(maximum_probe + 1.0))
    y_min, y_max = 0.0, maximum_pressure + pressure_step
    xp = lambda value: left + (value - x_min) / (x_max - x_min) * plot_width
    yp = lambda value: top + (y_max - value) / (y_max - y_min) * plot_height

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(bold, 48)
    subtitle_font = font(regular, 27)
    axis_font = font(bold, 30)
    tick_font = font(regular, 23)
    label_font = font(bold, 17)
    legend_font = font(regular, 22)

    title = "扣除后 P_probe 与 P_IOP 的有限元散点关系"
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (box[2] - box[0])) / 2, 34), title, fill="#111827", font=title_font)
    subtitle = f"0–{maximum_pressure:g} mmHg，步长 {pressure_step:g} mmHg；0.259875 mm 主工作点；无插值"
    box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(((width - (box[2] - box[0])) / 2, 102), subtitle, fill="#4b5563", font=subtitle_font)

    y_tick_count = round(y_max / pressure_step)
    for y_index in range(y_tick_count + 1):
        y = y_index * pressure_step
        py = yp(y)
        major = y_index % 2 == 0
        draw.line((left, py, width - right, py), fill="#dbe3ec" if major else "#eff3f7", width=2 if major else 1)
        if major:
            text = f"{y:g}"
            box = draw.textbbox((0, 0), text, font=tick_font)
            draw.text((left - 22 - (box[2] - box[0]), py - (box[3] - box[1]) / 2), text, fill="#374151", font=tick_font)
    for x in range(math.ceil(x_max) + 1):
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
    layer = Image.new("RGBA", (620, 70), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    box = layer_draw.textbbox((0, 0), ylabel, font=axis_font)
    layer_draw.text(((620 - (box[2] - box[0])) / 2, (70 - (box[3] - box[1])) / 2), ylabel, fill="#111827", font=axis_font)
    layer = layer.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    image.paste(layer, (30, top + (plot_height - layer.height) // 2), layer)

    new_pressures = [pressure for pressure, _, is_new in points if is_new]
    new_label = (
        f"新增 {min(new_pressures):g}–{max(new_pressures):g} mmHg"
        if new_pressures else "新增求解点"
    )
    legend_y = 145
    for legend_x, color, text in (
        (width - 720, "#2563eb", "复用的已通过FE点"),
        (width - 380, "#f97316", new_label),
    ):
        draw.ellipse((legend_x, legend_y - 8, legend_x + 20, legend_y + 12), fill=color, outline="white", width=2)
        draw.text((legend_x + 30, legend_y - 14), text, fill="#374151", font=legend_font)

    for index, (pressure, probe, is_new) in enumerate(points):
        px, py = xp(probe), yp(pressure)
        color = "#f97316" if is_new else "#2563eb"
        draw.ellipse((px - 11, py - 11, px + 11, py + 11), fill=color, outline="white", width=3)
        text = f"{probe:.4f}"
        box = draw.textbbox((0, 0), text, font=label_font)
        text_width = box[2] - box[0]
        text_height = box[3] - box[1]
        dx = -text_width - 17 if index % 2 == 0 else 17
        tx, ty = px + dx, py - text_height / 2
        pad = 4
        draw.rounded_rectangle(
            (tx - pad, ty - pad, tx + text_width + pad, ty + text_height + pad),
            radius=6,
            fill="#fff7ed" if is_new else "#eff6ff",
            outline="#fdba74" if is_new else "#93c5fd",
            width=1,
        )
        draw.text((tx, ty), text, fill="#c2410c" if is_new else "#1d4ed8", font=label_font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
