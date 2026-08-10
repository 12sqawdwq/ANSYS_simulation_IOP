#!/usr/bin/env python3
"""Project aggressive-mesh size, storage, and wall-time envelopes.

The projections are planning bounds, not a solver-speed calibration.  Global
counts use a log-log fit to the accepted 0.30/0.24/0.20 mm 2.00-mm cases.
The local estimate scales accepted 0.20-mm observations by the measured
mesh-only node/element ratios recorded in the experiment config.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG = (
    REPO_ROOT
    / "thickness_mesh_independence"
    / "aggressive_refinement"
    / "config"
    / "experiment.json"
)
DEFAULT_TIMING = (
    REPO_ROOT
    / "thickness_mesh_independence"
    / "results"
    / "visual_evidence"
    / "simulation_timing.csv"
)


def fit_power_law(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Return coefficient and exponent for y = coefficient * h**exponent."""
    xs = [math.log(item[0]) for item in points]
    ys = [math.log(item[1]) for item in points]
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    exponent = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sum(
        (x - xbar) ** 2 for x in xs
    )
    return math.exp(ybar - exponent * xbar), exponent


def read_timing(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--timing", type=Path, default=DEFAULT_TIMING)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    global_data = config["existing_global_mesh_evidence_2mm_20mmhg"]
    fits: dict[str, dict[str, float]] = {}
    for field in ("elements", "nodes", "equations", "rst_gib"):
        coefficient, exponent = fit_power_law(
            [(float(row["mesh_mm"]), float(row[field])) for row in global_data]
        )
        fits[field] = {"coefficient": coefficient, "exponent": exponent}

    timing = [
        row
        for row in read_timing(args.timing)
        if math.isclose(float(row["mesh_size_mm"]), 0.20, abs_tol=1e-12)
        and row["accepted_endpoint"].lower() == "true"
    ]
    if len(timing) != 6:
        raise ValueError(f"expected six accepted 0.20-mm endpoints, found {len(timing)}")
    baseline_six_hours = sum(float(row["elapsed_seconds"]) for row in timing) / 3600
    baseline_anchor_hours = sum(
        float(row["elapsed_seconds"])
        for row in timing
        if math.isclose(float(row["eyelid_thickness_mm"]), 2.0, abs_tol=1e-12)
    ) / 3600
    baseline = next(row for row in global_data if math.isclose(row["mesh_mm"], 0.2))
    exploratory = config["exploratory_mesh_only_observation"]
    local_element_ratio = exploratory["solid_elements_after"] / exploratory["solid_elements_before"]
    local_node_ratio = exploratory["solid_nodes_after"] / exploratory["solid_nodes_before"]
    local_equations = float(baseline["equations"]) * local_node_ratio
    local_rst = float(baseline["rst_gib"]) * local_node_ratio

    rows: list[dict[str, object]] = []
    for mesh in (0.15, 0.12, 0.10):
        predicted = {
            field: fits[field]["coefficient"] * mesh ** fits[field]["exponent"]
            for field in fits
        }
        ratio = predicted["equations"] / float(baseline["equations"])
        rows.append({
            "strategy": f"global_{mesh:.2f}",
            "background_mesh_mm": mesh,
            "nominal_local_target_mm": mesh,
            "predicted_elements": round(predicted["elements"]),
            "predicted_nodes": round(predicted["nodes"]),
            "predicted_equations": round(predicted["equations"]),
            "predicted_rst_gib_per_endpoint": round(predicted["rst_gib"], 3),
            "predicted_anchor_pair_wall_hours_lower": round(baseline_anchor_hours * ratio, 2),
            "predicted_anchor_pair_wall_hours_upper": round(
                baseline_anchor_hours * ratio ** 1.6, 2
            ),
            "predicted_six_endpoint_wall_hours_lower": round(baseline_six_hours * ratio, 2),
            "predicted_six_endpoint_wall_hours_upper": round(
                baseline_six_hours * ratio ** 1.6, 2
            ),
            "evidence": "log-log count fit; wall time is an unvalidated planning envelope",
        })
    rows.append({
        "strategy": "layered_local_0.10",
        "background_mesh_mm": 0.20,
        "nominal_local_target_mm": 0.10,
        "predicted_elements": exploratory["solid_elements_after"],
        "predicted_nodes": exploratory["solid_nodes_after"],
        "predicted_equations": round(local_equations),
        "predicted_rst_gib_per_endpoint": round(local_rst, 3),
        "predicted_anchor_pair_wall_hours_lower": round(
            baseline_anchor_hours * local_node_ratio, 2
        ),
        "predicted_anchor_pair_wall_hours_upper": round(
            baseline_anchor_hours * local_node_ratio ** 1.6, 2
        ),
        "predicted_six_endpoint_wall_hours_lower": round(
            baseline_six_hours * local_node_ratio, 2
        ),
        "predicted_six_endpoint_wall_hours_upper": round(
            baseline_six_hours * local_node_ratio ** 1.6, 2
        ),
        "evidence": "exploratory mesh-only count ratio; full solve not yet measured",
    })
    extreme = config["extreme_mesh_only_observation"]
    extreme_node_ratio = extreme["solid_nodes_after"] / extreme["solid_nodes_before"]
    rows.append({
        "strategy": "layered_local_0.05",
        "background_mesh_mm": 0.20,
        "nominal_local_target_mm": 0.05,
        "predicted_elements": extreme["solid_elements_after"],
        "predicted_nodes": extreme["solid_nodes_after"],
        "predicted_equations": round(float(baseline["equations"]) * extreme_node_ratio),
        "predicted_rst_gib_per_endpoint": round(
            float(baseline["rst_gib"]) * extreme_node_ratio, 3
        ),
        "predicted_anchor_pair_wall_hours_lower": round(
            baseline_anchor_hours * extreme_node_ratio, 2
        ),
        "predicted_anchor_pair_wall_hours_upper": round(
            baseline_anchor_hours * extreme_node_ratio ** 1.6, 2
        ),
        "predicted_six_endpoint_wall_hours_lower": round(
            baseline_six_hours * extreme_node_ratio, 2
        ),
        "predicted_six_endpoint_wall_hours_upper": round(
            baseline_six_hours * extreme_node_ratio ** 1.6, 2
        ),
        "evidence": "two-pass mesh-only count ratio; nonlinear solve rejected by resource gate",
    })

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "resource_projection.csv", rows)
    summary = {
        "schema_version": 1,
        "status": "planning_projection_not_solver_benchmark",
        "inputs": {
            "config": str(args.config.resolve()),
            "timing": str(args.timing.resolve()),
            "accepted_0p20_endpoints": len(timing),
            "baseline_six_endpoint_wall_hours": baseline_six_hours,
            "baseline_2mm_anchor_pair_wall_hours": baseline_anchor_hours,
        },
        "global_count_fits": fits,
        "local_mesh_only_ratios": {
            "L010_elements": local_element_ratio,
            "L010_nodes": local_node_ratio,
            "L005_nodes": extreme_node_ratio,
        },
        "rows": rows,
        "decision_boundary": {
            "global_0p10": "reject before nonlinear solve under the recorded 123-GiB RAM / 148-GiB free-disk snapshot",
            "layered_local_0p10": "eligible only for committed P0 mesh preflight and then a sequential 2.00-mm anchor pair",
            "layered_local_0p05": "mesh-only feasible but nonlinear anchor rejected under current memory, disk, and 72-hour limits",
            "full_six_endpoint_matrix": "conditional; upper wall-time and retained-RST storage can exceed the 72-hour / free-disk envelope",
        },
    }
    (output / "resource_projection.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
