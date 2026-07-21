#!/usr/bin/env python3
"""Build a labeled matrix from one fixed view across eyelid thicknesses."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


THICKNESSES_MM = (0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0)


def label(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def source_paths(views_root: Path, indent_mm: float, suffix: int) -> list[tuple[float, Path]]:
    paths: list[tuple[float, Path]] = []
    indent = label(indent_mm)
    for thickness in THICKNESSES_MM:
        case = f"eyelid_{label(thickness)}mm_indent_{indent}mm"
        path = views_root / case / f"{case}{suffix:03d}.png"
        if not path.is_file():
            raise FileNotFoundError(path)
        paths.append((thickness, path))
    return paths


def build_matrix(
    sources: list[tuple[float, Path]],
    output: Path,
    columns: int = 4,
    image_width: int = 800,
    label_height: int = 58,
    gap: int = 12,
    margin: int = 16,
) -> None:
    if not sources or columns < 1 or image_width < 1:
        raise ValueError("sources, columns, and image width must be positive")
    with Image.open(sources[0][1]) as first:
        image_height = round(image_width * first.height / first.width)
    rows = math.ceil(len(sources) / columns)
    tile_height = label_height + image_height
    canvas_width = margin * 2 + columns * image_width + (columns - 1) * gap
    canvas_height = margin * 2 + rows * tile_height + (rows - 1) * gap
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)
    font = load_font(30)

    for index, (thickness, path) in enumerate(sources):
        row, column = divmod(index, columns)
        x = margin + column * (image_width + gap)
        y = margin + row * (tile_height + gap)
        with Image.open(path) as source:
            image = source.convert("RGB").resize(
                (image_width, image_height), Image.Resampling.LANCZOS
            )
        canvas.paste(image, (x, y + label_height))
        text = f"{thickness:.1f} mm"
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        draw.text(
            (x + (image_width - (right - left)) / 2, y + (label_height - (bottom - top)) / 2 - top),
            text,
            fill="black",
            font=font,
        )
        draw.rectangle((x, y, x + image_width - 1, y + tile_height - 1), outline="#b7b7b7")

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("views_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--indent-mm", type=float, default=0.26)
    parser.add_argument("--suffix", type=int, default=7)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--image-width", type=int, default=800)
    cli = parser.parse_args()
    build_matrix(
        source_paths(cli.views_root, cli.indent_mm, cli.suffix),
        cli.output,
        columns=cli.columns,
        image_width=cli.image_width,
    )
    print(cli.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
