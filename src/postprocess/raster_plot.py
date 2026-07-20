"""Pillow-backed line plots for solver quality-control reports."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


COLORS = (
    (36, 99, 176),
    (220, 70, 54),
    (46, 139, 87),
    (143, 89, 169),
    (227, 145, 45),
    (33, 158, 188),
)


def _font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _tick(value: float) -> str:
    if abs(value) >= 1000 or (0 < abs(value) < 0.01):
        return f"{value:.2E}"
    return f"{value:.3G}"


def plot_lines(
    path: Path,
    title: str,
    series: list[tuple[str, list[tuple[float, float]]]],
) -> None:
    width, height = 1200, 720
    left, right, top, bottom = 120, 1160, 120, 635
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(24)
    label_font = _font(16)
    tick_font = _font(13)
    draw.text((35, 25), title, fill=(25, 25, 25), font=title_font)

    all_points = [point for _, points in series for point in points]
    if not all_points:
        draw.text((35, 85), "No complete case data", fill=(90, 90, 90), font=label_font)
        image.save(path, format="PNG", optimize=True)
        return

    xmin = min(point[0] for point in all_points)
    xmax = max(point[0] for point in all_points)
    ymin = min(0.0, min(point[1] for point in all_points))
    ymax = max(0.0, max(point[1] for point in all_points))
    if xmax <= xmin:
        xmax = xmin + 1.0
    if ymax <= ymin:
        ymax = ymin + 1.0
    ypad = 0.05 * (ymax - ymin)
    ymin -= ypad
    ymax += ypad

    def px(value: float) -> int:
        return round(left + (value - xmin) / (xmax - xmin) * (right - left))

    def py(value: float) -> int:
        return round(bottom - (value - ymin) / (ymax - ymin) * (bottom - top))

    grid = (220, 225, 230)
    for index in range(6):
        xvalue = xmin + index * (xmax - xmin) / 5
        yvalue = ymin + index * (ymax - ymin) / 5
        x, y = px(xvalue), py(yvalue)
        draw.line((x, top, x, bottom), fill=grid, width=1)
        draw.line((left, y, right, y), fill=grid, width=1)
        draw.text((x - 18, bottom + 10), _tick(xvalue), fill=(60, 60, 60), font=tick_font)
        draw.text((8, y - 8), _tick(yvalue), fill=(60, 60, 60), font=tick_font)

    draw.line((left, top, left, bottom), fill=(30, 30, 30), width=2)
    draw.line((left, bottom, right, bottom), fill=(30, 30, 30), width=2)
    draw.text((520, 680), "Indentation (mm)", fill=(35, 35, 35), font=label_font)

    legend_x, legend_y = 500, 35
    for index, (name, _) in enumerate(series):
        row, column = divmod(index, 3)
        x = legend_x + column * 210
        y = legend_y + row * 28
        color = COLORS[index % len(COLORS)]
        draw.line((x, y + 8, x + 30, y + 8), fill=color, width=4)
        draw.text((x + 40, y), name, fill=(35, 35, 35), font=label_font)

    for index, (_, points) in enumerate(series):
        color = COLORS[index % len(COLORS)]
        mapped = [(px(x), py(y)) for x, y in points]
        if len(mapped) > 1:
            draw.line(mapped, fill=color, width=4, joint="curve")
        for x, y in mapped:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color, outline="white", width=1)

    image.save(path, format="PNG", optimize=True)
