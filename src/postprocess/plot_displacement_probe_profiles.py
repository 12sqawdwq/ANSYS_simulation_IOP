#!/usr/bin/env python3
"""Probe radial inner/outer displacement distributions from saved face states."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (
    PROBE_RADIUS_M,
    _surface_records,
    read_faces,
    select_displacement_support,
)

OUTER = (207, 57, 49)
INNER = (43, 95, 178)
GRID = (218, 222, 228)
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


def probe_surface(
    attempt: Path,
    surface: str,
    case: str,
    thickness_mm: float,
    bin_width_mm: float,
) -> tuple[dict[str, str | float | int], list[dict[str, str | float | int]]]:
    preload = read_faces(attempt / f"{surface}_preload_faces.csv")
    final = read_faces(attempt / f"{surface}_final_faces.csv")
    support, _ = select_displacement_support(preload, final)
    records = _surface_records(preload, final)
    radii_mm = np.asarray([record.radius * 1e3 for record in records], dtype=float)
    downward_um = np.asarray([record.downward * 1e6 for record in records], dtype=float)
    local_um = np.maximum(downward_um - support.baseline * 1e6, 0.0)
    threshold_um = support.displacement_threshold * 1e6
    probe_mask = radii_mm <= PROBE_RADIUS_M * 1e3
    edge_mask = (
        (radii_mm >= PROBE_RADIUS_M * 1e3 - bin_width_mm)
        & (radii_mm <= PROBE_RADIUS_M * 1e3)
    )
    outside_mask = (
        (radii_mm > PROBE_RADIUS_M * 1e3)
        & (radii_mm <= PROBE_RADIUS_M * 1e3 + 2 * bin_width_mm)
    )

    rows: list[dict[str, str | float | int]] = []
    edges = np.arange(0.0, float(np.max(radii_mm)) + bin_width_mm, bin_width_mm)
    for start, end in zip(edges[:-1], edges[1:]):
        mask = (radii_mm >= start) & (radii_mm < end)
        count = int(np.count_nonzero(mask))
        if count == 0:
            continue
        values = local_um[mask]
        rows.append({
            "case": case,
            "eyelid_thickness_mm": thickness_mm,
            "surface": surface,
            "radius_start_mm": start,
            "radius_end_mm": end,
            "radius_center_mm": 0.5 * (start + end),
            "face_count": count,
            "raw_downward_median_um": float(np.median(downward_um[mask])),
            "local_downward_p10_um": float(np.quantile(values, 0.1)),
            "local_downward_median_um": float(np.median(values)),
            "local_downward_p90_um": float(np.quantile(values, 0.9)),
            "above_threshold_fraction": float(np.mean(values > threshold_um)),
            "threshold_um": threshold_um,
        })

    above_bins = [
        float(row["radius_end_mm"])
        for row in rows
        if float(row["local_downward_median_um"]) > threshold_um
    ]
    probe_values = local_um[probe_mask]
    summary: dict[str, str | float | int] = {
        "case": case,
        "eyelid_thickness_mm": thickness_mm,
        "surface": surface,
        "face_count": len(records),
        "surface_radius_max_mm": float(np.max(radii_mm)),
        "baseline_um": support.baseline * 1e6,
        "noise_sigma_um": support.noise_sigma * 1e6,
        "threshold_um": threshold_um,
        "local_max_um": support.local_max * 1e6,
        "probe_local_p10_um": float(np.quantile(probe_values, 0.1)),
        "probe_local_median_um": float(np.median(probe_values)),
        "probe_local_p90_um": float(np.quantile(probe_values, 0.9)),
        "probe_above_threshold_fraction": float(np.mean(probe_values > threshold_um)),
        "probe_edge_median_um": float(np.median(local_um[edge_mask])),
        "outside_edge_median_um": (
            float(np.median(local_um[outside_mask])) if np.any(outside_mask) else ""
        ),
        "radial_median_crossing_mm": max(above_bins, default=0.0),
    }
    return summary, rows


def write_csv(path: Path, rows: list[dict[str, str | float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_profiles(
    path: Path,
    summaries: list[dict[str, str | float | int]],
    profiles: list[dict[str, str | float | int]],
    x_max_mm: float,
) -> None:
    grouped: dict[tuple[float, str], list[dict[str, str | float | int]]] = defaultdict(list)
    for row in profiles:
        grouped[(float(row["eyelid_thickness_mm"]), str(row["surface"]))].append(row)
    thicknesses = sorted({float(row["eyelid_thickness_mm"]) for row in summaries})
    summary_by_key = {
        (float(row["eyelid_thickness_mm"]), str(row["surface"])): row
        for row in summaries
    }
    y_max_um = max(
        float(row["local_downward_p90_um"])
        for row in profiles
        if float(row["radius_center_mm"]) <= x_max_mm
    )
    y_max_um = math.ceil(y_max_um / 50.0) * 50.0
    columns = 3
    panel_width, panel_height = 520, 365
    rows_count = math.ceil(len(thicknesses) / columns)
    image = Image.new("RGB", (columns * panel_width, rows_count * panel_height), "white")
    draw = ImageDraw.Draw(image)
    for index, thickness in enumerate(thicknesses):
        left = (index % columns) * panel_width
        top = (index // columns) * panel_height
        plot_left, plot_top = left + 58, top + 38
        plot_width, plot_height = 430, 270
        draw.text((left + 12, top + 8), f"t={thickness:.2f} mm", fill=INK, font=font(19))

        def pixel(radius: float, value: float) -> tuple[int, int]:
            return (
                round(plot_left + radius / x_max_mm * plot_width),
                round(plot_top + plot_height - value / y_max_um * plot_height),
            )

        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = plot_top + plot_height - fraction * plot_height
            draw.line((plot_left, y, plot_left + plot_width, y), fill=GRID, width=1)
            draw.text(
                (left + 8, y - 8), f"{fraction * y_max_um:.0f}", fill=INK, font=font(12)
            )
        for radius in range(0, math.floor(x_max_mm) + 1):
            x = plot_left + radius / x_max_mm * plot_width
            draw.line((x, plot_top, x, plot_top + plot_height), fill=GRID, width=1)
            draw.text((x - 4, plot_top + plot_height + 5), str(radius), fill=INK, font=font(12))
        edge_x = plot_left + PROBE_RADIUS_M * 1e3 / x_max_mm * plot_width
        draw.line((edge_x, plot_top, edge_x, plot_top + plot_height), fill=INK, width=2)

        for surface, color in (("outer", OUTER), ("inner", INNER)):
            rows = [
                row for row in grouped[(thickness, surface)]
                if float(row["radius_center_mm"]) <= x_max_mm
            ]
            points = [
                pixel(
                    float(row["radius_center_mm"]),
                    float(row["local_downward_median_um"]),
                )
                for row in rows
            ]
            if len(points) > 1:
                draw.line(points, fill=color, width=4)
            threshold = float(summary_by_key[(thickness, surface)]["threshold_um"])
            threshold_y = pixel(0, threshold)[1]
            draw.line(
                (plot_left, threshold_y, plot_left + plot_width, threshold_y),
                fill=color,
                width=1,
            )
        draw.text((plot_left, top + 328), "radius (mm)", fill=INK, font=font(13))
        draw.text((plot_left + 128, top + 328), "black: probe edge 2.16 mm", fill=INK, font=font(13))
        draw.line((plot_left + 294, top + 18, plot_left + 322, top + 18), fill=OUTER, width=4)
        draw.text((plot_left + 328, top + 10), "outer", fill=INK, font=font(13))
        draw.line((plot_left + 390, top + 18, plot_left + 418, top + 18), fill=INNER, width=4)
        draw.text((plot_left + 424, top + 10), "inner", fill=INK, font=font(13))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--bin-width-mm", type=float, default=0.15)
    parser.add_argument("--x-max-mm", type=float, default=5.0)
    cli = parser.parse_args()
    if cli.bin_width_mm <= 0 or cli.x_max_mm <= PROBE_RADIUS_M * 1e3:
        parser.error("bin width must be positive and x max must exceed the probe radius")
    root = cli.run_root.expanduser().resolve()
    output_dir = (
        cli.output_dir.expanduser().resolve()
        if cli.output_dir else root / "figures" / "displacement_probes"
    )
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    summaries: list[dict[str, str | float | int]] = []
    profiles: list[dict[str, str | float | int]] = []
    for row in manifest:
        attempt = root / row["attempt_dir"]
        required = tuple(
            attempt / f"{surface}_{state}_faces.csv"
            for surface in ("outer", "inner")
            for state in ("preload", "final")
        )
        if not all(path.is_file() for path in required):
            continue
        for surface in ("outer", "inner"):
            summary, radial = probe_surface(
                attempt,
                surface,
                row["case"],
                float(row["eyelid_thickness_mm"]),
                cli.bin_width_mm,
            )
            summaries.append(summary)
            profiles.extend(radial)
    if not summaries:
        print("no complete cases with surface face data", file=sys.stderr)
        return 1
    summaries.sort(key=lambda row: (float(row["eyelid_thickness_mm"]), str(row["surface"])))
    profiles.sort(key=lambda row: (
        float(row["eyelid_thickness_mm"]),
        str(row["surface"]),
        float(row["radius_center_mm"]),
    ))
    write_csv(output_dir / "displacement_probe_summary.csv", summaries)
    write_csv(output_dir / "displacement_probe_profiles.csv", profiles)
    plot_profiles(
        output_dir / "displacement_probe_profiles.png",
        summaries,
        profiles,
        cli.x_max_mm,
    )
    print(f"cases={len(summaries) // 2} output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
