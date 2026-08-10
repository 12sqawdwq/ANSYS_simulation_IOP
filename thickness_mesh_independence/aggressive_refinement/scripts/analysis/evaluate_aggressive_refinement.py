#!/usr/bin/env python3
"""Evaluate paired 0/20-mmHg aggressive local-refinement endpoints."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

PROBE_AREA_MM2 = 14.65741468458854
PA_PER_MMHG = 133.322
ALLOWED_THICKNESSES = {1.6, 1.8, 2.0}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {row.get(key)!r}")
    return value


def index_manifest(path: Path, pressure: float) -> dict[float, dict[str, str]]:
    indexed: dict[float, dict[str, str]] = {}
    for row in read_csv(path):
        if not math.isclose(finite(row, "iop_mmhg"), pressure, abs_tol=1e-9):
            raise ValueError(f"unexpected pressure in {path}")
        thickness = finite(row, "eyelid_thickness_mm")
        if thickness not in ALLOWED_THICKNESSES or thickness in indexed:
            raise ValueError(f"unexpected or duplicate thickness {thickness:g} in {path}")
        indexed[thickness] = row
    if not indexed:
        raise ValueError(f"empty manifest: {path}")
    return indexed


def row_qc(row: dict[str, str]) -> bool:
    return all((
        row.get("status") == "complete",
        int(float(row.get("returncode", "-1"))) == 0,
        int(float(row.get("ansys_error_count", "-1"))) == 0,
        int(float(row.get("preload_converged", "0"))) == 1,
        int(float(row.get("approach_converged", "0"))) == 1,
        int(float(row.get("indentation_converged", "0"))) == 1,
        finite(row, "max_penetration_m") <= 0.03e-3,
        abs(finite(row, "approach_probe_fy_n")) <= 1e-3,
        int(float(row.get("result_load_step", "0"))) == 3,
        row.get("git_dirty", "").strip().lower() in {"false", "0"},
    ))


def solver_counts(root: Path, row: dict[str, str]) -> dict[str, int]:
    solve_out = root / row["attempt_dir"] / "solve.out"
    text = solve_out.read_text(errors="replace")
    patterns = {
        "solver_elements": r"\.\.\.Number of elements:\s*(\d+)",
        "solver_nodes": r"\.\.\.Number of nodes:\s*(\d+)",
        "solver_equations": r"Number of equations\s*=\s*(\d+)",
    }
    result: dict[str, int] = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if not matches:
            raise ValueError(f"missing {key} in {solve_out}")
        result[key] = int(matches[-1])
    return result


def load_metadata(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_metadata(left: dict[str, object], right: dict[str, object]) -> None:
    for metadata in (left, right):
        if not math.isclose(float(metadata["mesh_size_mm"]), 0.20, abs_tol=1e-12):
            raise ValueError("aggressive run must retain the 0.20-mm background")
        if int(metadata.get("local_refine_level", -1)) != 1:
            raise ValueError("aggressive run must use local refinement level 1")
        if not math.isclose(float(metadata.get("local_refine_halfwidth_mm", -1)), 1.8, abs_tol=1e-12):
            raise ValueError("unexpected local refinement half-width")
        if metadata.get("git_dirty") is not False:
            raise ValueError("formal aggressive run must use a clean worktree")
    for key in ("git_commit", "apdl_sha256", "ansys_version"):
        if left.get(key) != right.get(key):
            raise ValueError(f"paired metadata mismatch: {key}")
    left_cases = sorted(
        (case["eyelid_thickness_mm"], case["indent_mm"]) for case in left["cases"]
    )
    right_cases = sorted(
        (case["eyelid_thickness_mm"], case["indent_mm"]) for case in right["cases"]
    )
    if left_cases != right_cases:
        raise ValueError("paired thickness/indentation case sets differ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    metadata0 = load_metadata(root / "iop0" / "run_metadata.json")
    metadata20 = load_metadata(root / "iop20" / "run_metadata.json")
    validate_metadata(metadata0, metadata20)
    rows0 = index_manifest(root / "iop0" / "run_manifest.csv", 0.0)
    rows20 = index_manifest(root / "iop20" / "run_manifest.csv", 20.0)
    if set(rows0) != set(rows20):
        raise ValueError("0/20-mmHg thickness sets differ")
    reference = {
        finite(row, "eyelid_thickness_mm"): row
        for row in read_csv(args.reference)
        if math.isclose(finite(row, "mesh_size_mm"), 0.20, abs_tol=1e-12)
    }
    output_rows: list[dict[str, object]] = []
    for thickness in sorted(rows0):
        left, right = rows0[thickness], rows20[thickness]
        force0, force20 = abs(finite(left, "probe_fy_n")), abs(finite(right, "probe_fy_n"))
        q = (force20 - force0) / PROBE_AREA_MM2 * 1e6 / PA_PER_MMHG
        prior_q = finite(reference[thickness], "q_mmhg")
        counts0, counts20 = solver_counts(root / "iop0", left), solver_counts(root / "iop20", right)
        pair_same_mesh = counts0 == counts20
        qc = row_qc(left) and row_qc(right) and pair_same_mesh
        output_rows.append({
            "eyelid_thickness_mm": thickness,
            "background_mesh_mm": 0.20,
            "local_target_mesh_mm": 0.10,
            "local_refine_halfwidth_mm": 1.80,
            "force_zero_n": force0,
            "force_20_n": force20,
            "delta_force_n": force20 - force0,
            "q_mmhg": q,
            "global_0p20_q_mmhg": prior_q,
            "q_change_from_global_0p20_percent": (q / prior_q - 1) * 100,
            "contact_area_iop0_m2": finite(left, "contact_area_m2"),
            "contact_area_iop20_m2": finite(right, "contact_area_m2"),
            "pmax_iop0_pa": finite(left, "pmax_pa"),
            "pmax_iop20_pa": finite(right, "pmax_pa"),
            "max_penetration_iop0_m": finite(left, "max_penetration_m"),
            "max_penetration_iop20_m": finite(right, "max_penetration_m"),
            **counts0,
            "pair_same_mesh": pair_same_mesh,
            "pair_qc_pass": qc,
        })
    csv_path = out / "aggressive_mesh_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    changes = [abs(float(row["q_change_from_global_0p20_percent"])) for row in output_rows]
    ordered = len(output_rows) == 3 and all(
        float(output_rows[index]["q_mmhg"]) > float(output_rows[index + 1]["q_mmhg"])
        for index in range(2)
    )
    summary = {
        "schema_version": 1,
        "status": "complete" if all(row["pair_qc_pass"] for row in output_rows) else "qc_failed",
        "source_campaign": str(root),
        "source_git_commit": metadata0["git_commit"],
        "evaluated_thicknesses_mm": sorted(rows0),
        "all_pair_qc_pass": all(row["pair_qc_pass"] for row in output_rows),
        "maximum_absolute_q_change_from_global_0p20_percent": max(changes),
        "within_2_percent_strategy_screen": max(changes) <= 2.0,
        "complete_thick_end_order_available": len(output_rows) == 3,
        "thick_end_order_preserved": ordered if len(output_rows) == 3 else None,
        "claim_boundary": "L010 versus global 0.20 mm compares two discretization strategies. It cannot establish mesh independence without an accepted second local level.",
    }
    (out / "aggressive_mesh_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return 0 if summary["all_pair_qc_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
