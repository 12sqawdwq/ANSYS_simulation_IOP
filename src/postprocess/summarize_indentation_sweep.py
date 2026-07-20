#!/usr/bin/env python3
"""Build pressure-proxy metrics from MAPDL sweep outputs."""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path


def nodes(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for line in path.read_text(errors="replace").splitlines():
        values = re.findall(r"[-+]?\\d*\\.?\\d+(?:[Ee][-+]?\\d+)?", line)
        if re.match(r"^\\s*\\d+\\s+", line) and len(values) >= 4:
            try:
                points.append((float(values[1]), float(values[3])))
            except ValueError:
                pass
    return points


def hull_area(points: list[tuple[float, float]]) -> float:
    unique = sorted(set(points))
    if len(unique) < 3:
        return 0.0
    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    lower = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(hull, hull[1:] + hull[:1]))) / 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    cli = parser.parse_args()
    rows = []
    for case in sorted(cli.run_root.glob("offset_*_indent_*")):
        match = re.fullmatch(r"offset_(.+)mm_indent_(.+)mm", case.name)
        if not match or not (case / "metrics.csv").exists():
            continue
        values = [float(item) for item in (case / "metrics.csv").read_text().strip().strip(",").split(",")]
        force, n_outer, n_inner, cornea, eyelid, pmax, uy = values
        outer = hull_area(nodes(case / "outer_nodes.txt"))
        inner = hull_area(nodes(case / "inner_nodes.txt"))
        p_read = abs(force) / outer if outer else math.nan
        k_area = outer / inner if inner else math.nan
        delta_p = abs(force) * (1 / inner - 1 / outer) if outer and inner else math.nan
        rows.append({"case": case.name, "force_N": abs(force), "outer_area_m2": outer,
                     "inner_area_m2": inner, "Pread_Pa": p_read, "Karea": k_area,
                     "DeltaParea_Pa": delta_p, "Parea_Pa": p_read * k_area if outer and inner else math.nan,
                     "outer_contact_elements": n_outer, "inner_contact_elements": n_inner,
                     "cornea_peak_Pa": cornea, "eyelid_peak_Pa": eyelid,
                     "contact_pressure_max_Pa": pmax, "probe_uy_m": uy})
    with (cli.run_root / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
