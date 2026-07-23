#!/usr/bin/env python3
"""Render binary 2-degree objective flat-region maps for a thickness run."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (
    PROBE_AREA_M2,
    PROBE_RADIUS_M,
    Face,
    FlatAreaResult,
    read_faces,
    select_flat_surface,
)

RED = (211, 55, 48)
BLUE = (42, 91, 176)
EDGE = (235, 238, 242)
INK = (28, 31, 35)


def font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def panel(
    title: str,
    faces: dict[int, Face],
    selected: set[int],
    result: FlatAreaResult,
) -> Image.Image:
    width, height = 650, 650
    margin, plot_size = 44, 550
    extent = 1.12 * PROBE_RADIUS_M
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((margin, 12), title, fill=INK, font=font(22))

    def pixel(point: tuple[float, float, float]) -> tuple[int, int]:
        return (
            round(margin + plot_size / 2 + point[0] / extent * plot_size / 2),
            round(48 + plot_size / 2 - point[2] / extent * plot_size / 2),
        )

    for element, face in sorted(faces.items()):
        center_x = sum(point[0] for point in face.points) / 3.0
        center_z = sum(point[2] for point in face.points) / 3.0
        if math.hypot(center_x, center_z) > 1.18 * PROBE_RADIUS_M:
            continue
        draw.polygon(
            [pixel(point) for point in face.points],
            fill=RED if element in selected else BLUE,
            outline=EDGE,
            width=1,
        )

    center_x = margin + plot_size / 2
    center_y = 48 + plot_size / 2
    radius_px = PROBE_RADIUS_M / extent * plot_size / 2
    draw.ellipse(
        (center_x - radius_px, center_y - radius_px,
         center_x + radius_px, center_y + radius_px),
        outline=INK,
        width=3,
    )
    area_mm2 = result.projected_area * 1e6
    draw.text(
        (margin, 610),
        f"2 deg area={area_mm2:.3f} mm2   faces={result.face_count}",
        fill=INK,
        font=font(16),
    )
    return image


def render_case(
    attempt: Path,
    output: Path,
    case: str,
    thickness_mm: float,
    indent_mm: float,
) -> dict[str, str | float | int]:
    inner_preload = read_faces(attempt / "inner_preload_faces.csv")
    inner_final = read_faces(attempt / "inner_final_faces.csv")
    outer_preload = read_faces(attempt / "outer_preload_faces.csv")
    outer_final = read_faces(attempt / "outer_final_faces.csv")
    outer, outer_selected = select_flat_surface(
        outer_preload, outer_final, angle_limit_deg=2.0
    )
    inner, inner_selected = select_flat_surface(
        inner_preload, inner_final, angle_limit_deg=2.0
    )

    canvas = Image.new("RGB", (1320, 735), (246, 247, 249))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (24, 12),
        f"2 DEG OBJECTIVE FLAT REGION   t={thickness_mm:.2f} mm   indent={indent_mm:.2f} mm",
        fill=INK,
        font=font(24),
    )
    canvas.paste(panel("OUTER AE", outer_final, outer_selected, outer), (10, 52))
    canvas.paste(panel("INNER AC", inner_final, inner_selected, inner), (660, 52))
    draw.rectangle((32, 707, 54, 727), fill=RED)
    draw.text((62, 707), "effective: displaced, central-connected, normal angle <= 2 deg",
              fill=INK, font=font(14))
    draw.rectangle((760, 707, 782, 727), fill=BLUE)
    draw.text((790, 707), "not included", fill=INK, font=font(14))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    return {
        "case": case,
        "eyelid_thickness_mm": thickness_mm,
        "indent_mm": indent_mm,
        "outer_flat_area_2deg_mm2": outer.projected_area * 1e6,
        "outer_coverage_fraction": outer.projected_area / PROBE_AREA_M2,
        "outer_selected_faces": outer.face_count,
        "inner_flat_area_2deg_mm2": inner.projected_area * 1e6,
        "inner_selected_faces": inner.face_count,
        "ae_over_ac_flat_2deg": (
            outer.projected_area / inner.projected_area if inner.projected_area > 0 else ""
        ),
        "image": str(output),
    }


def write_manifest(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    fields = tuple(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    columns = 3
    tile_width, tile_height = 440, 270
    rows_count = math.ceil(len(rows) / columns)
    matrix = Image.new("RGB", (columns * tile_width, rows_count * (tile_height + 30)), "white")
    draw = ImageDraw.Draw(matrix)
    for index, row in enumerate(rows):
        source = Image.open(str(row["image"])).convert("RGB")
        source.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (index % columns) * tile_width
        y = (index // columns) * (tile_height + 30)
        matrix.paste(source, (x + (tile_width - source.width) // 2, y))
        draw.text(
            (x + 10, y + tile_height + 4),
            f"t={float(row['eyelid_thickness_mm']):.2f} mm  coverage={float(row['outer_coverage_fraction'])*100:.1f}%",
            fill=INK,
            font=font(15),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    matrix.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    cli = parser.parse_args()
    if cli.workers < 1:
        parser.error("workers must be positive")
    root = cli.run_root.expanduser().resolve()
    output_dir = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures" / "flat_region_2deg"
    )
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    jobs = []
    for row in manifest:
        attempt = root / row["attempt_dir"]
        required = tuple(attempt / f"{name}_{state}_faces.csv" for name in ("inner", "outer")
                         for state in ("preload", "final"))
        if all(path.is_file() for path in required):
            jobs.append((attempt, output_dir / f"{row['case']}_flat_region_2deg.png", row))
    if not jobs:
        print("no complete cases with surface face data", file=sys.stderr)
        return 1

    rows: list[dict[str, str | float | int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                render_case,
                attempt,
                output,
                row["case"],
                float(row["eyelid_thickness_mm"]),
                float(row["indent_mm"]),
            )
            for attempt, output, row in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    write_manifest(output_dir / "flat_region_2deg_manifest.csv", rows)
    write_matrix(output_dir.parent / "flat_region_2deg_matrix.png", rows)
    print(f"rendered={len(rows)} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
