#!/usr/bin/env python3
"""Evaluate the targeted eyelid-thickness mesh-refinement campaign."""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASELINE = REPO_ROOT / "analysis" / "outputs" / "thickness_iop_predictions.csv"
DEFAULT_BASELINE_INVENTORY = REPO_ROOT / "thickness_mesh_independence" / "results" / "baseline_mesh_inventory.csv"
EXPECTED_THICKNESSES = (1.6, 1.8, 2.0)
PROBE_AREA_MM2 = 14.65741468458854
PA_PER_MMHG = 133.322
SCREENING_LIMIT_PERCENT = 2.0


def portable_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def normalize_svg(path: Path) -> None:
    """Remove generator-only trailing whitespace and force portable LF endings."""
    text = path.read_text(encoding="utf-8")
    normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty mesh comparison")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finite(row: dict[str, str], key: str) -> float:
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key}: {row.get(key)!r}")
    return value


def select_rows(rows: list[dict[str, str]], expected_iop: float, mesh_size: float) -> dict[float, dict[str, str]]:
    selected: dict[float, dict[str, str]] = {}
    for row in rows:
        thickness = finite(row, "eyelid_thickness_mm")
        if not any(math.isclose(thickness, item, abs_tol=1e-9) for item in EXPECTED_THICKNESSES):
            continue
        if not math.isclose(finite(row, "iop_mmhg"), expected_iop, abs_tol=1e-9):
            continue
        if not math.isclose(finite(row, "mesh_size_mm"), mesh_size, abs_tol=1e-9):
            continue
        if thickness in selected:
            raise ValueError(f"duplicate t={thickness:g}, IOP={expected_iop:g}")
        selected[thickness] = row
    if tuple(sorted(selected)) != EXPECTED_THICKNESSES:
        raise ValueError(
            f"expected thicknesses {EXPECTED_THICKNESSES} at IOP={expected_iop:g}; "
            f"found {tuple(sorted(selected))}"
        )
    return selected


def row_qc_pass(row: dict[str, str]) -> bool:
    checks = (
        row.get("status") == "complete",
        int(float(row.get("returncode", "-1"))) == 0,
        int(float(row.get("ansys_error_count", "-1"))) == 0,
        int(float(row.get("preload_converged", "0"))) == 1,
        int(float(row.get("approach_converged", "0"))) == 1,
        int(float(row.get("indentation_converged", "0"))) == 1,
        finite(row, "max_penetration_m") <= 0.03e-3,
        abs(finite(row, "approach_probe_fy_n")) <= 1e-3,
        row.get("git_dirty", "").strip().lower() in {"false", "0"},
    )
    return all(checks)


def load_metadata(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pair_metadata(left: dict[str, object], right: dict[str, object], mesh_size: float) -> None:
    for metadata in (left, right):
        if not math.isclose(float(metadata["mesh_size_mm"]), mesh_size, abs_tol=1e-9):
            raise ValueError("unexpected mesh size in run metadata")
        if metadata.get("git_dirty") is not False:
            raise ValueError("formal mesh screen must use a clean Git worktree")
        if not math.isclose(float(metadata["cornea_material_scale"]), 0.75, abs_tol=1e-12):
            raise ValueError("unexpected cornea material scale")
        if not math.isclose(float(metadata["eyelid_material_scale"]), 1.0, abs_tol=1e-12):
            raise ValueError("unexpected eyelid material scale")
    for key in ("git_commit", "apdl_sha256", "ansys_version"):
        if left.get(key) != right.get(key):
            raise ValueError(f"0/20-mmHg metadata mismatch: {key}")


def solver_counts(screening_root: Path, pressure_dir: str, row: dict[str, str]) -> dict[str, int]:
    solve_output = screening_root / pressure_dir / row["attempt_dir"] / "solve.out"
    text = solve_output.read_text(errors="replace")
    patterns = {
        "solver_elements": r"\.\.\.Number of elements:\s*(\d+)",
        "solver_nodes": r"\.\.\.Number of nodes:\s*(\d+)",
        "solver_equations": r"Number of equations\s*=\s*(\d+)",
    }
    counts: dict[str, int] = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if not matches:
            raise ValueError(f"cannot find {key} in {solve_output}")
        counts[key] = int(matches[-1])
    return counts


def baseline_rows(path: Path) -> dict[float, dict[str, float]]:
    selected: dict[float, dict[str, float]] = {}
    for row in read_csv(path):
        thickness = finite(row, "eyelid_thickness_mm")
        if not any(math.isclose(thickness, item, abs_tol=1e-9) for item in EXPECTED_THICKNESSES):
            continue
        selected[thickness] = {
            "force_zero_n": finite(row, "force_zero_baseline_n"),
            "force_20_n": finite(row, "force_iop_n"),
            "delta_force_n": finite(row, "delta_force_n"),
            "q_mmhg": finite(row, "delta_probe_pressure_mmhg"),
        }
    if tuple(sorted(selected)) != EXPECTED_THICKNESSES:
        raise ValueError("baseline does not contain the complete thick-end grid")
    return selected


def load_baseline_inventory(path: Path) -> dict[tuple[float, float], dict[str, str]]:
    indexed: dict[tuple[float, float], dict[str, str]] = {}
    for row in read_csv(path):
        key = (finite(row, "eyelid_thickness_mm"), finite(row, "iop_mmhg"))
        if key in indexed:
            raise ValueError(f"duplicate baseline inventory state: {key}")
        indexed[key] = row
    expected = {(h, p) for h in EXPECTED_THICKNESSES for p in (0.0, 20.0)}
    if set(indexed) != expected:
        raise ValueError("baseline solver inventory is incomplete")
    return indexed


def build_figure(rows: list[dict[str, object]], output: Path) -> None:
    by_mesh: dict[float, list[dict[str, object]]] = {}
    for row in rows:
        by_mesh.setdefault(float(row["mesh_size_mm"]), []).append(row)
    colors = {0.30: "#8A929D", 0.24: "#0072B2", 0.20: "#D55E00"}
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.7))
    for mesh, mesh_rows in sorted(by_mesh.items(), reverse=True):
        mesh_rows.sort(key=lambda item: float(item["eyelid_thickness_mm"]))
        h = np.array([float(item["eyelid_thickness_mm"]) for item in mesh_rows])
        color = colors.get(round(mesh, 2), None)
        axes[0].plot(h, [float(item["force_zero_n"]) for item in mesh_rows], marker="o",
                     color=color, linestyle="--", label=f"0 mmHg, mesh {mesh:.2f} mm")
        axes[0].plot(h, [float(item["force_20_n"]) for item in mesh_rows], marker="s",
                     color=color, label=f"20 mmHg, mesh {mesh:.2f} mm")
        axes[1].plot(h, [float(item["q_mmhg"]) for item in mesh_rows], marker="o",
                     color=color, label=f"mesh {mesh:.2f} mm")
    latest_mesh = min(by_mesh)
    latest = by_mesh[latest_mesh]
    latest.sort(key=lambda item: float(item["eyelid_thickness_mm"]))
    if len(by_mesh) > 1:
        axes[2].axhline(0, color="#59636F", linewidth=0.8)
        axes[2].bar(
            [float(item["eyelid_thickness_mm"]) for item in latest],
            [float(item["q_change_from_previous_mesh_percent"]) for item in latest],
            width=0.11,
            color="#009E73" if math.isclose(latest_mesh, 0.24) else "#D55E00",
        )
        axes[2].axhline(SCREENING_LIMIT_PERCENT, color="#CC3311", linestyle="--", linewidth=0.9)
        axes[2].axhline(-SCREENING_LIMIT_PERCENT, color="#CC3311", linestyle="--", linewidth=0.9)
    axes[0].set_title("A  Paired total forces")
    axes[0].set_ylabel("Probe force (N)")
    axes[1].set_title("B  Zero-referenced output")
    axes[1].set_ylabel(r"$q(20)$ (mmHg)")
    axes[2].set_title("C  Change after latest refinement")
    axes[2].set_ylabel(r"Change in $q$ from previous mesh (%)")
    for ax in axes:
        ax.set_xlabel("Eyelid thickness (mm)")
        ax.set_xticks(EXPECTED_THICKNESSES)
        ax.grid(True, color="#D9DEE5", linewidth=0.65)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].legend(fontsize=7.2)
    axes[1].legend(fontsize=8)
    fig.suptitle("Targeted thick-end mesh-refinement screen", fontweight="bold")
    fig.tight_layout()
    fig.savefig(output / "mesh_independence_screening.png", dpi=300, bbox_inches="tight")
    svg_output = output / "mesh_independence_screening.svg"
    fig.savefig(svg_output, bbox_inches="tight",
                metadata={"Date": None, "Creator": "evaluate_mesh_independence.py"})
    normalize_svg(svg_output)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening-root", type=Path, required=True)
    parser.add_argument(
        "--screening-source-label",
        help="Provenance label written to outputs when screening-root is a temporary local snapshot.",
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--baseline-inventory", type=Path, default=DEFAULT_BASELINE_INVENTORY)
    parser.add_argument(
        "--intermediate-comparison",
        type=Path,
        help="Prior mesh_comparison.csv; required to make a three-mesh confirmation table.",
    )
    parser.add_argument("--mesh-size-mm", type=float, default=0.24)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.screening_root.expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    screening_source = args.screening_source_label or str(root)
    metadata0 = load_metadata(root / "iop0" / "run_metadata.json")
    metadata20 = load_metadata(root / "iop20" / "run_metadata.json")
    validate_pair_metadata(metadata0, metadata20, args.mesh_size_mm)
    rows0 = select_rows(read_csv(root / "iop0" / "run_manifest.csv"), 0.0, args.mesh_size_mm)
    rows20 = select_rows(read_csv(root / "iop20" / "run_manifest.csv"), 20.0, args.mesh_size_mm)
    baseline = baseline_rows(args.baseline.expanduser().resolve())
    inventory = load_baseline_inventory(args.baseline_inventory.expanduser().resolve())

    comparison: list[dict[str, object]] = []
    baseline_all_qc = True
    for thickness in EXPECTED_THICKNESSES:
        values = baseline[thickness]
        inventory0 = inventory[(thickness, 0.0)]
        inventory20 = inventory[(thickness, 20.0)]
        if not math.isclose(abs(finite(inventory0, "probe_fy_n")), values["force_zero_n"], abs_tol=1e-12):
            raise ValueError(f"baseline 0-mmHg force mismatch at h={thickness:g}")
        if not math.isclose(abs(finite(inventory20, "probe_fy_n")), values["force_20_n"], abs_tol=1e-12):
            raise ValueError(f"baseline 20-mmHg force mismatch at h={thickness:g}")
        baseline_pair_qc = (
            inventory0["status"] == "complete"
            and inventory20["status"] == "complete"
            and int(float(inventory0["ansys_error_count"])) == 0
            and int(float(inventory20["ansys_error_count"])) == 0
            and int(float(inventory0["solver_nodes"])) == int(float(inventory20["solver_nodes"]))
            and int(float(inventory0["solver_elements"])) == int(float(inventory20["solver_elements"]))
        )
        baseline_all_qc = baseline_all_qc and baseline_pair_qc
        comparison.append({
            "mesh_size_mm": 0.30,
            "eyelid_thickness_mm": thickness,
            **values,
            "q_change_from_0p30_percent": 0.0,
            "q_change_from_previous_mesh_percent": 0.0,
            "contact_area_iop0_m2": finite(inventory0, "contact_area_m2"),
            "contact_area_iop20_m2": finite(inventory20, "contact_area_m2"),
            "pmax_iop0_pa": finite(inventory0, "pmax_pa"),
            "pmax_iop20_pa": finite(inventory20, "pmax_pa"),
            "max_penetration_iop0_m": finite(inventory0, "max_penetration_m"),
            "max_penetration_iop20_m": finite(inventory20, "max_penetration_m"),
            "active_contact_nodes_iop0": int(finite(inventory0, "active_contact_nodes")),
            "active_contact_nodes_iop20": int(finite(inventory20, "active_contact_nodes")),
            "preload_apex_uy_iop20_m": finite(inventory20, "preload_apex_uy_m"),
            "solver_elements": int(finite(inventory0, "solver_elements")),
            "solver_nodes": int(finite(inventory0, "solver_nodes")),
            "solver_equations_iop0": int(finite(inventory0, "solver_equations")),
            "solver_equations_iop20": int(finite(inventory20, "solver_equations")),
            "pair_qc_pass": baseline_pair_qc,
            "source": portable_path(args.baseline_inventory),
        })

    previous_q = {thickness: baseline[thickness]["q_mmhg"] for thickness in EXPECTED_THICKNESSES}
    mesh_sizes = [0.30]
    if args.intermediate_comparison:
        intermediate_all = read_csv(args.intermediate_comparison.expanduser().resolve())
        intermediate_meshes = sorted({finite(row, "mesh_size_mm") for row in intermediate_all if finite(row, "mesh_size_mm") < 0.30}, reverse=True)
        if len(intermediate_meshes) != 1:
            raise ValueError(f"expected one intermediate mesh below 0.30 mm; found {intermediate_meshes}")
        intermediate_mesh = intermediate_meshes[0]
        if not (args.mesh_size_mm < intermediate_mesh < 0.30):
            raise ValueError("current mesh must be finer than the intermediate mesh")
        intermediate_rows = [row for row in intermediate_all if math.isclose(finite(row, "mesh_size_mm"), intermediate_mesh, abs_tol=1e-9)]
        if len(intermediate_rows) != len(EXPECTED_THICKNESSES):
            raise ValueError("intermediate comparison is incomplete")
        for row in sorted(intermediate_rows, key=lambda item: finite(item, "eyelid_thickness_mm")):
            thickness = finite(row, "eyelid_thickness_mm")
            row["q_change_from_previous_mesh_percent"] = 100.0 * (
                finite(row, "q_mmhg") / baseline[thickness]["q_mmhg"] - 1.0
            )
            comparison.append(row)
            previous_q[thickness] = finite(row, "q_mmhg")
            baseline_all_qc = baseline_all_qc and row.get("pair_qc_pass", "").lower() in {"true", "1"}
        mesh_sizes.append(intermediate_mesh)

    screening_q: list[float] = []
    changes: list[float] = []
    previous_changes: list[float] = []
    all_qc = baseline_all_qc
    for thickness in EXPECTED_THICKNESSES:
        row0, row20 = rows0[thickness], rows20[thickness]
        counts0 = solver_counts(root, "iop0", row0)
        counts20 = solver_counts(root, "iop20", row20)
        same_discretization = (
            counts0["solver_elements"] == counts20["solver_elements"]
            and counts0["solver_nodes"] == counts20["solver_nodes"]
        )
        pair_qc = row_qc_pass(row0) and row_qc_pass(row20) and same_discretization
        all_qc = all_qc and pair_qc
        force0 = abs(finite(row0, "probe_fy_n"))
        force20 = abs(finite(row20, "probe_fy_n"))
        delta_force = force20 - force0
        q_mmhg = delta_force / (PROBE_AREA_MM2 * 1e-6 * PA_PER_MMHG)
        change = 100.0 * (q_mmhg / baseline[thickness]["q_mmhg"] - 1.0)
        previous_change = 100.0 * (q_mmhg / previous_q[thickness] - 1.0)
        screening_q.append(q_mmhg)
        changes.append(change)
        previous_changes.append(previous_change)
        comparison.append({
            "mesh_size_mm": args.mesh_size_mm,
            "eyelid_thickness_mm": thickness,
            "force_zero_n": force0,
            "force_20_n": force20,
            "delta_force_n": delta_force,
            "q_mmhg": q_mmhg,
            "q_change_from_0p30_percent": change,
            "q_change_from_previous_mesh_percent": previous_change,
            "contact_area_iop0_m2": finite(row0, "contact_area_m2"),
            "contact_area_iop20_m2": finite(row20, "contact_area_m2"),
            "pmax_iop0_pa": finite(row0, "pmax_pa"),
            "pmax_iop20_pa": finite(row20, "pmax_pa"),
            "max_penetration_iop0_m": finite(row0, "max_penetration_m"),
            "max_penetration_iop20_m": finite(row20, "max_penetration_m"),
            "active_contact_nodes_iop0": int(finite(row0, "n_outer")),
            "active_contact_nodes_iop20": int(finite(row20, "n_outer")),
            "preload_apex_uy_iop20_m": finite(row20, "preload_apex_uy_m"),
            "solver_elements": counts0["solver_elements"],
            "solver_nodes": counts0["solver_nodes"],
            "solver_equations_iop0": counts0["solver_equations"],
            "solver_equations_iop20": counts20["solver_equations"],
            "pair_qc_pass": pair_qc,
            "source": screening_source,
        })

    mesh_sizes.append(args.mesh_size_mm)
    order_preserved = screening_q[0] > screening_q[1] > screening_q[2]
    max_change = max(abs(value) for value in changes)
    max_previous_change = max(abs(value) for value in previous_changes)
    within_limit = max_previous_change <= SCREENING_LIMIT_PERCENT
    rows_by_mesh = {
        mesh: {
            float(row["eyelid_thickness_mm"]): row
            for row in comparison
            if math.isclose(float(row["mesh_size_mm"]), mesh, abs_tol=1e-9)
        }
        for mesh in mesh_sizes
    }
    previous_mesh = mesh_sizes[-2]
    direction_consistent = None
    if len(mesh_sizes) == 3:
        direction_consistent = all(
            (
                float(rows_by_mesh[mesh_sizes[1]][thickness]["q_mmhg"])
                - float(rows_by_mesh[mesh_sizes[0]][thickness]["q_mmhg"])
            )
            * (
                float(rows_by_mesh[mesh_sizes[2]][thickness]["q_mmhg"])
                - float(rows_by_mesh[mesh_sizes[1]][thickness]["q_mmhg"])
            )
            >= 0.0
            for thickness in EXPECTED_THICKNESSES
        )
    if not all_qc:
        decision = "do_not_interpret_failed_cases"
    elif len(mesh_sizes) == 2:
        decision = "proceed_to_0p20_for_three_mesh_confirmation"
    elif not order_preserved:
        decision = "thick_end_order_not_robust_under_three_mesh_refinement"
    elif within_limit:
        decision = "three_mesh_order_robust_and_finest_q_change_within_2_percent"
    else:
        decision = "thick_end_order_robust_but_amplitude_not_mesh_independent"
    q_drop = {}
    q_contrast = {}
    for mesh in mesh_sizes:
        q_at_1p6 = float(rows_by_mesh[mesh][1.6]["q_mmhg"])
        q_at_2p0 = float(rows_by_mesh[mesh][2.0]["q_mmhg"])
        key = f"mesh_{mesh:.2f}".replace(".", "p")
        q_drop[key] = 100.0 * (q_at_2p0 / q_at_1p6 - 1.0)
        q_contrast[key] = q_at_1p6 - q_at_2p0
    latest_q_shifts = {
        f"h_{thickness:.1f}": float(rows_by_mesh[args.mesh_size_mm][thickness]["q_mmhg"])
        - float(rows_by_mesh[previous_mesh][thickness]["q_mmhg"])
        for thickness in EXPECTED_THICKNESSES
    }
    latest_contrast_change = 100.0 * (
        q_contrast[f"mesh_{args.mesh_size_mm:.2f}".replace(".", "p")]
        / q_contrast[f"mesh_{previous_mesh:.2f}".replace(".", "p")]
        - 1.0
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": (
            "mesh_evaluation_qc_failed"
            if not all_qc
            else "three_mesh_confirmation_complete" if len(mesh_sizes) == 3
            else "screening_complete_not_final_mesh_independence"
        ),
        "screening_root": screening_source,
        "baseline": portable_path(args.baseline),
        "baseline_solver_inventory": portable_path(args.baseline_inventory),
        "intermediate_comparison": portable_path(args.intermediate_comparison) if args.intermediate_comparison else None,
        "source_git_commit": metadata0["git_commit"],
        "mesh_sizes_mm": mesh_sizes,
        "eyelid_thicknesses_mm": list(EXPECTED_THICKNESSES),
        "all_pairs_qc_pass": all_qc,
        "thick_end_order_preserved": order_preserved,
        "refinement_direction_consistent_at_each_thickness": direction_consistent,
        "maximum_absolute_q_change_from_0p30_percent": max_change,
        "maximum_absolute_q_change_from_previous_mesh_percent": max_previous_change,
        "screening_limit_percent": SCREENING_LIMIT_PERCENT,
        "latest_mesh_change_within_limit": within_limit,
        "mesh_refinement_ratios_from_previous_mesh": {
            f"h_{thickness:.1f}_elements": float(rows_by_mesh[args.mesh_size_mm][thickness]["solver_elements"])
            / float(rows_by_mesh[previous_mesh][thickness]["solver_elements"])
            for thickness in EXPECTED_THICKNESSES
        } | {
            f"h_{thickness:.1f}_nodes": float(rows_by_mesh[args.mesh_size_mm][thickness]["solver_nodes"])
            / float(rows_by_mesh[previous_mesh][thickness]["solver_nodes"])
            for thickness in EXPECTED_THICKNESSES
        },
        "q_drop_1p6_to_2p0_percent": q_drop,
        "post_hoc_shape_diagnostic": {
            "q_contrast_1p6_minus_2p0_mmhg": q_contrast,
            "latest_contrast_change_percent": latest_contrast_change,
            "latest_refinement_q_shift_mmhg": latest_q_shifts,
            "latest_refinement_q_shift_range_mmhg": max(latest_q_shifts.values())
            - min(latest_q_shifts.values()),
            "interpretation_boundary": "Exploratory common-mode/shape diagnostic only; it was not the preregistered 2% absolute-q decision criterion.",
        },
        "decision": decision,
        "claim_boundary": (
            "The three tested meshes preserve the sampled thick-end order, but the absolute q amplitude does not meet the 2% mesh-independence criterion; neither a converged magnitude nor a physical threshold in real tissue is established."
            if len(mesh_sizes) == 3 and not within_limit
            else "Three-mesh convergence can establish robustness only within this FE model; it does not prove a physical threshold in real tissue."
            if len(mesh_sizes) == 3
            else "The 0.24-mm result is a screen only; it cannot establish mesh independence without the third mesh."
        ),
    }
    write_csv(output / "mesh_comparison.csv", comparison)
    (output / "screening_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build_figure(comparison, output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all_qc else 1


if __name__ == "__main__":
    raise SystemExit(main())
