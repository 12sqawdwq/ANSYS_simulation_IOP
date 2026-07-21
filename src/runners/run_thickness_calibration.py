#!/usr/bin/env python3
"""Calibrate eyelid/cornea material scales against thickness-area targets."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.runners.run_indentation_sweep import atomic_json, label

PRIMARY_THICKNESSES = (0.8, 1.0, 1.2, 1.25)
SECONDARY_THICKNESSES = (1.5, 2.0)
FINAL_THICKNESSES = (0.8, 1.0, 1.2, 1.25, 1.4, 1.5, 1.6, 1.8, 2.0)
MESH_VALIDATION_THICKNESSES = (0.8, 1.2, 2.0)
PRIMARY_RANGE = (1.5, 2.0)
SECONDARY_RANGES = {1.5: (2.0, 3.0), 2.0: (4.0, 8.0)}
SCORE_FIELDS = (
    "variant", "eyelid_material_scale", "cornea_material_scale", "stage",
    "complete_primary", "primary_pass_count", "primary_mean_error",
    "primary_score", "secondary_score", "trend_penalty", "total_score",
    "eligible", "failure_reason",
)


@dataclass(frozen=True)
class Variant:
    eyelid_scale: float
    cornea_scale: float
    stage: str = "initial"

    @property
    def name(self) -> str:
        return (
            f"eyelid_s{label(self.eyelid_scale)}_"
            f"cornea_s{label(self.cornea_scale)}"
        )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    temporary.replace(path)


def interval_error(value: float, lower: float, upper: float) -> float:
    if value < lower:
        return (lower - value) / lower
    if value > upper:
        return (value - upper) / upper
    return 0.0


def rows_by_thickness(rows: list[dict[str, str]]) -> dict[float, dict[str, str]]:
    return {round(float(row["eyelid_thickness_mm"]), 6): row for row in rows}


def primary_metrics(rows: list[dict[str, str]]) -> tuple[int, float, float]:
    indexed = rows_by_thickness(rows)
    errors: list[float] = []
    for thickness in PRIMARY_THICKNESSES:
        row = indexed.get(thickness)
        if row is None:
            return 0, math.inf, math.inf
        ratio = float(row["ae_over_ac_smooth_2deg"])
        errors.append(interval_error(ratio, *PRIMARY_RANGE))
    return sum(error <= 0.2 + 1e-12 for error in errors), sum(errors) / len(errors), (
        sum(error * error for error in errors) / len(errors)
    )


def secondary_metrics(
    primary_rows: list[dict[str, str]], secondary_rows: list[dict[str, str]]
) -> tuple[float, float]:
    indexed = rows_by_thickness([*primary_rows, *secondary_rows])
    errors: list[float] = []
    for thickness, target in SECONDARY_RANGES.items():
        row = indexed.get(thickness)
        if row is None:
            return math.inf, math.inf
        errors.append(interval_error(float(row["ae_over_ac_smooth_2deg"]), *target))
    secondary_score = sum(error * error for error in errors) / len(errors)
    k_125 = float(indexed[1.25]["ae_over_ac_smooth_2deg"])
    k_15 = float(indexed[1.5]["ae_over_ac_smooth_2deg"])
    k_20 = float(indexed[2.0]["ae_over_ac_smooth_2deg"])
    trend_penalty = 0.0 if k_20 >= k_125 and k_15 >= 0.9 * k_125 else 1.0
    return secondary_score, trend_penalty


def proximity(variant: Variant) -> float:
    return abs(math.log(variant.eyelid_scale)) + abs(math.log(variant.cornea_scale))


def run_command(command: list[str], *, allow_failure: bool = True) -> int:
    print("COMMAND " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode and not allow_failure:
        raise RuntimeError(f"command failed with exit code {completed.returncode}")
    return completed.returncode


def prune_primary_results(source: Path, keep_thicknesses: set[float]) -> None:
    removed: list[dict[str, int | str]] = []
    for row in read_csv(source / "run_manifest.csv"):
        if row.get("status") != "complete":
            continue
        thickness = round(float(row["eyelid_thickness_mm"]), 6)
        if thickness in keep_thicknesses:
            continue
        paths = [
            source / row["attempt_dir"] / f"{row['case']}.db",
            source / row["result_rst"],
        ]
        for path in paths:
            if path.is_file():
                size = path.stat().st_size
                path.unlink()
                removed.append({"path": str(path.relative_to(source)), "bytes": size})
    atomic_json(source / "calibration_artifact_cleanup.json", {
        "policy": "remove screening DB/RST after successful 0.26 mm extraction",
        "kept_thicknesses_mm": sorted(keep_thicknesses),
        "removed_files": removed,
        "removed_bytes": sum(int(item["bytes"]) for item in removed),
    })


def run_variant_phase(
    root: Path,
    variant: Variant,
    phase: str,
    thicknesses: tuple[float, ...],
    cli: argparse.Namespace,
    *,
    mesh_size_mm: float = 0.3,
    view_policy: str = "none",
    keep_primary_thicknesses: set[float] | None = None,
) -> list[dict[str, str]]:
    variant_root = root / "candidates" / variant.name
    source = variant_root / f"{phase}_source"
    state = variant_root / f"{phase}_state_0p26"
    summary = state / "summary.csv"
    if summary.is_file():
        return read_csv(summary)

    runner = [
        sys.executable, str(REPO_ROOT / "src/runners/run_indentation_sweep.py"),
        "--eyelid-thicknesses", *(f"{value:g}" for value in thicknesses),
        "--thickness-indent-mm", f"{cli.source_indent_mm:g}",
        "--run-root", str(source), "--workers", str(cli.workers),
        "--np", str(cli.np), "--timeout-seconds", str(cli.timeout_seconds),
        "--mesh-size-mm", f"{mesh_size_mm:g}", "--iop-mmhg", "20",
        "--eyelid-material-scale", f"{variant.eyelid_scale:.12g}",
        "--cornea-material-scale", f"{variant.cornea_scale:.12g}",
        "--view-policy", view_policy,
    ]
    run_command(runner)
    extractor = [
        sys.executable, str(REPO_ROOT / "src/postprocess/extract_thickness_state.py"),
        str(source), str(state), "--target-indent-mm", f"{cli.target_indent_mm:g}",
        "--source-indent-mm", f"{cli.source_indent_mm:g}",
        "--workers", str(cli.workers), "--np", "1", "--view-policy", view_policy,
    ]
    run_command(extractor)
    rows = read_csv(summary)
    if rows:
        prune_primary_results(source, keep_primary_thicknesses or set())
    return rows


def initial_variants(stage: str = "initial") -> list[Variant]:
    return [
        Variant(eyelid, cornea, stage)
        for eyelid in (0.5, 1.0, 2.0)
        for cornea in (0.75, 1.0, 1.25)
    ]


def refinement_variants(best: Variant) -> list[Variant]:
    eyelids = {
        max(0.25, min(4.0, value))
        for value in (best.eyelid_scale / math.sqrt(2), best.eyelid_scale,
                      best.eyelid_scale * math.sqrt(2))
    }
    corneas = {
        max(0.5, min(2.0, value))
        for value in (best.cornea_scale / 1.2, best.cornea_scale,
                      best.cornea_scale * 1.2)
    }
    return [Variant(eyelid, cornea, "refinement") for eyelid in sorted(eyelids)
            for cornea in sorted(corneas)]


def evaluate_primary(root: Path, variants: list[Variant], cli: argparse.Namespace) -> list[dict]:
    scores: list[dict] = []
    for variant in variants:
        rows = run_variant_phase(root, variant, "primary", PRIMARY_THICKNESSES, cli)
        passed, mean_error, score = primary_metrics(rows)
        scores.append({
            "variant": variant.name,
            "eyelid_material_scale": variant.eyelid_scale,
            "cornea_material_scale": variant.cornea_scale,
            "stage": variant.stage,
            "complete_primary": len(rows),
            "primary_pass_count": passed,
            "primary_mean_error": mean_error,
            "primary_score": score,
            "secondary_score": "",
            "trend_penalty": "",
            "total_score": score,
            "eligible": math.isfinite(score),
            "failure_reason": "" if math.isfinite(score) else "missing primary results",
            "_variant": variant,
            "_primary_rows": rows,
        })
        write_csv(root / "candidate_scores.csv", SCORE_FIELDS, scores)
    return scores


def rank_primary(scores: list[dict]) -> list[dict]:
    return sorted(scores, key=lambda item: (
        not item["eligible"], -int(item["primary_pass_count"]),
        float(item["primary_score"]), proximity(item["_variant"]), item["variant"],
    ))


def add_secondary(root: Path, scores: list[dict], cli: argparse.Namespace) -> None:
    for item in rank_primary(scores)[:3]:
        if not item["eligible"]:
            continue
        rows = run_variant_phase(
            root, item["_variant"], "secondary", SECONDARY_THICKNESSES, cli
        )
        secondary_score, trend_penalty = secondary_metrics(item["_primary_rows"], rows)
        item["secondary_score"] = secondary_score
        item["trend_penalty"] = trend_penalty
        item["total_score"] = (
            float(item["primary_score"]) + 0.25 * secondary_score + trend_penalty
        )
        if not math.isfinite(secondary_score):
            item["eligible"] = False
            item["failure_reason"] = "missing secondary results"
        write_csv(root / "candidate_scores.csv", SCORE_FIELDS, scores)


def select_best(scores: list[dict]) -> dict:
    eligible = [item for item in scores if item["eligible"] and item["secondary_score"] != ""]
    if not eligible:
        raise RuntimeError("no eligible calibration candidate")
    return min(eligible, key=lambda item: (
        -int(item["primary_pass_count"]), float(item["total_score"]),
        proximity(item["_variant"]), item["variant"],
    ))


def run_final(root: Path, best: dict, cli: argparse.Namespace) -> None:
    variant = best["_variant"]
    final_root = root / "final"
    original_candidates = root / "candidates"
    # Reuse the phase runner while publishing final data under a stable directory.
    temporary_candidates = final_root / "candidates"
    temporary_candidates.mkdir(parents=True, exist_ok=True)
    rows = run_variant_phase(
        final_root, variant, "full", FINAL_THICKNESSES, cli, view_policy="all",
        keep_primary_thicknesses=set(MESH_VALIDATION_THICKNESSES),
    )
    mesh_rows = run_variant_phase(
        final_root, variant, "mesh_0p15", MESH_VALIDATION_THICKNESSES, cli,
        mesh_size_mm=0.15, view_policy="none",
        keep_primary_thicknesses=set(MESH_VALIDATION_THICKNESSES),
    )
    primary_pass, primary_mean, _ = primary_metrics(rows)
    mesh_index = rows_by_thickness(mesh_rows)
    coarse_index = rows_by_thickness(rows)
    mesh_validation = []
    for thickness in MESH_VALIDATION_THICKNESSES:
        coarse = float(coarse_index[thickness]["ae_over_ac_smooth_2deg"])
        fine = float(mesh_index[thickness]["ae_over_ac_smooth_2deg"])
        mesh_validation.append({
            "eyelid_thickness_mm": thickness,
            "coarse_ratio": coarse,
            "fine_ratio": fine,
            "relative_change": abs(fine - coarse) / coarse,
            "passed": abs(fine - coarse) / coarse <= 0.15,
        })
    write_csv(
        root / "mesh_validation.csv",
        ("eyelid_thickness_mm", "coarse_ratio", "fine_ratio", "relative_change", "passed"),
        mesh_validation,
    )
    atomic_json(root / "selected_parameters.json", {
        "iop_mmhg": 20.0,
        "eyelid_material_scale": variant.eyelid_scale,
        "cornea_material_scale": variant.cornea_scale,
        "primary_pass_count": primary_pass,
        "primary_mean_error": primary_mean,
        "mesh_validation_passed": all(item["passed"] for item in mesh_validation),
        "source_indent_mm": cli.source_indent_mm,
        "target_indent_mm": cli.target_indent_mm,
        "area_metric": "ae_over_ac_smooth_2deg",
        "candidate_data_root": str(original_candidates),
    })
    report_lines = [
        "# 眼睑厚度材料校准计算报告",
        "",
        "## 参数",
        "",
        f"- IOP：20 mmHg",
        f"- 眼睑材料倍率：{variant.eyelid_scale:.6g}",
        f"- 角膜材料倍率：{variant.cornea_scale:.6g}",
        f"- 校准状态：沿 {cli.source_indent_mm:g} mm 加载路径提取 {cli.target_indent_mm:g} mm",
        "- 主指标：平滑法向 Ae/Ac(2°)",
        "",
        "## 完整厚度结果",
        "",
        "| 厚度 (mm) | 平滑 Ae/Ac(2°) | 原始 Ae/Ac(2°) | 反力 (N) |",
        "|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: float(item["eyelid_thickness_mm"])):
        report_lines.append(
            f"| {float(row['eyelid_thickness_mm']):.2f} | "
            f"{float(row['ae_over_ac_smooth_2deg']):.3f} | "
            f"{float(row['ae_over_ac_2deg']):.3f} | "
            f"{float(row['probe_force_n']):.4f} |"
        )
    report_lines.extend([
        "",
        "## 网格验证",
        "",
        "| 厚度 (mm) | 0.30 mm网格 | 0.15 mm网格 | 相对变化 | 通过 |",
        "|---:|---:|---:|---:|:---:|",
    ])
    for item in mesh_validation:
        report_lines.append(
            f"| {item['eyelid_thickness_mm']:.2f} | {item['coarse_ratio']:.3f} | "
            f"{item['fine_ratio']:.3f} | {item['relative_change'] * 100:.1f}% | "
            f"{'是' if item['passed'] else '否'} |"
        )
    report_lines.extend([
        "",
        "主区间要求为0.8-1.25 mm四个点中至少三个相对实验区间误差不超过20%。",
        "原始面片2°结果保留用于追溯，材料选择只使用平滑2°结果。",
        "",
    ])
    (root / "calibration_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--np", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=7200)
    parser.add_argument("--source-indent-mm", type=float, default=0.8)
    parser.add_argument("--target-indent-mm", type=float, default=0.26)
    parser.add_argument("--skip-final", action="store_true")
    return parser


def main() -> int:
    cli = build_parser().parse_args()
    if cli.workers < 1 or cli.np < 1 or cli.timeout_seconds <= 0:
        raise SystemExit("workers, np, and timeout must be positive")
    root = cli.run_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / "calibration_spec.json", {
        "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "iop_mmhg": 20.0,
        "primary_thicknesses_mm": PRIMARY_THICKNESSES,
        "primary_target": PRIMARY_RANGE,
        "secondary_targets": {str(key): value for key, value in SECONDARY_RANGES.items()},
        "primary_acceptance": "at least 3 of 4 points within 20% interval error",
        "source_indent_mm": cli.source_indent_mm,
        "target_indent_mm": cli.target_indent_mm,
    })

    scores = evaluate_primary(root, initial_variants(), cli)
    add_secondary(root, scores, cli)
    best = select_best(scores)
    if int(best["primary_pass_count"]) < 3 or float(best["primary_mean_error"]) > 0.2:
        refined = evaluate_primary(root, refinement_variants(best["_variant"]), cli)
        scores.extend(refined)
        add_secondary(root, refined, cli)
        write_csv(root / "candidate_scores.csv", SCORE_FIELDS, scores)
        best = select_best(scores)
    if int(best["primary_pass_count"]) < 3 or float(best["primary_mean_error"]) > 0.2:
        atomic_json(root / "calibration_status.json", {
            "status": "model_form_insufficient",
            "best_variant": best["variant"],
            "primary_pass_count": best["primary_pass_count"],
            "primary_mean_error": best["primary_mean_error"],
        })
        return 2
    if not cli.skip_final:
        run_final(root, best, cli)
    atomic_json(root / "calibration_status.json", {
        "status": "complete" if not cli.skip_final else "screening_complete",
        "best_variant": best["variant"],
        "primary_pass_count": best["primary_pass_count"],
        "primary_mean_error": best["primary_mean_error"],
        "total_score": best["total_score"],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
