#!/usr/bin/env python3
"""Collect lightweight solver/QC inventory from retained baseline run manifests."""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

EXPECTED_THICKNESSES = (1.6, 1.8, 2.0)
EXPECTED_IOP = (0.0, 20.0)
FIELDS = (
    "eyelid_thickness_mm",
    "iop_mmhg",
    "mesh_size_mm",
    "status",
    "probe_fy_n",
    "contact_area_m2",
    "pmax_pa",
    "max_penetration_m",
    "active_contact_nodes",
    "preload_apex_uy_m",
    "solver_elements",
    "solver_nodes",
    "solver_equations",
    "git_commit",
    "ansys_error_count",
    "source_manifest",
    "attempt_dir",
)


def parse_counts(path: Path) -> dict[str, int]:
    text = path.read_text(errors="replace")
    patterns = {
        "solver_elements": r"\.\.\.Number of elements:\s*(\d+)",
        "solver_nodes": r"\.\.\.Number of nodes:\s*(\d+)",
        "solver_equations": r"Number of equations\s*=\s*(\d+)",
    }
    result: dict[str, int] = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if not matches:
            raise ValueError(f"cannot find {key} in {path}")
        result[key] = int(matches[-1])
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument(
        "--keep-first-overlap",
        action="store_true",
        help="For an overlapping state, retain the row from the first manifest in CLI order.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected: dict[tuple[float, float], dict[str, object]] = {}
    for manifest in args.manifest:
        manifest = manifest.expanduser().resolve()
        with manifest.open(newline="", encoding="utf-8-sig") as handle:
            for raw in csv.DictReader(handle):
                thickness = float(raw["eyelid_thickness_mm"])
                iop = float(raw["iop_mmhg"])
                indent = float(raw["indent_mm"])
                key = (thickness, iop)
                if (
                    thickness not in EXPECTED_THICKNESSES
                    or iop not in EXPECTED_IOP
                    or not math.isclose(indent, 0.28, abs_tol=1e-12)
                ):
                    continue
                attempt = manifest.parent / raw["attempt_dir"]
                counts = parse_counts(attempt / "solve.out")
                candidate: dict[str, object] = {
                    "eyelid_thickness_mm": thickness,
                    "iop_mmhg": iop,
                    "mesh_size_mm": float(raw["mesh_size_mm"]),
                    "status": raw["status"],
                    "probe_fy_n": float(raw["probe_fy_n"]),
                    "contact_area_m2": float(raw["contact_area_m2"]),
                    "pmax_pa": float(raw["pmax_pa"]),
                    "max_penetration_m": float(raw["max_penetration_m"]),
                    "active_contact_nodes": int(float(raw["n_outer"])),
                    "preload_apex_uy_m": float(raw["preload_apex_uy_m"]),
                    **counts,
                    "git_commit": raw["git_commit"],
                    "ansys_error_count": int(float(raw["ansys_error_count"])),
                    "source_manifest": str(manifest),
                    "attempt_dir": str(attempt),
                }
                if key in selected:
                    previous = selected[key]
                    exact_fields = ("probe_fy_n", "solver_elements", "solver_nodes", "git_commit")
                    if any(previous[field] != candidate[field] for field in exact_fields):
                        if not args.keep_first_overlap:
                            raise ValueError(f"conflicting duplicate baseline state: {key}")
                    continue
                selected[key] = candidate
    expected = {(h, p) for h in EXPECTED_THICKNESSES for p in EXPECTED_IOP}
    if set(selected) != expected:
        raise ValueError(f"baseline inventory mismatch; missing={sorted(expected - set(selected))}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for key in sorted(selected):
            writer.writerow(selected[key])
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
