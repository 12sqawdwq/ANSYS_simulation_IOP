from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "thickness_mesh_independence" / "aggressive_refinement"
CONFIG = EXPERIMENT / "config" / "experiment.json"
MODEL = ROOT / "models" / "apdl" / "param_eye_sweep.mac"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_aggressive_experiment_freezes_resource_and_claim_boundaries():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["git_branch"] == "aggressive-contact-mesh-experiment-20260810"
    assert config["status"] == "formal_p0_mesh_preflight_complete_p1_not_started"
    assert config["formal_preflight_source_commit"] == "8768e6ec6afb41225d729c21aac80b467c266897"
    assert config["hard_budget"]["wall_clock_hours"] == 72
    assert config["hard_budget"]["maximum_simultaneous_mapdl_cases"] == 1
    strategies = {item["id"]: item for item in config["candidate_strategies"]}
    assert strategies["G010"]["decision"].startswith("reject_before_solve")
    assert strategies["L010"]["background_mesh_mm"] == pytest.approx(0.20)
    assert strategies["L010"]["nominal_local_target_mm"] == pytest.approx(0.10)
    assert strategies["L005"]["nominal_local_target_mm"] == pytest.approx(0.05)
    assert "nonlinear solve rejected" in strategies["L005"]["decision"]
    assert config["acceptance"]["amplitude_screen_percent"] == pytest.approx(2.0)
    assert "not sufficient" in config["acceptance"]["convergence_claim_rule"]
    assert config["data_policy"]["no_automatic_deletion"].startswith("No accepted DB/RST")


def test_model_refines_before_contact_and_preserves_default_mode_encoding():
    text = MODEL.read_text(encoding="utf-8").lower()
    assert "units = solver retry mode" in text
    assert "local_refine_halfwidth = 1.8e-3" in text
    assert "refine_layer_halfheight = 0.40e-3" in text
    assert "*do,refine_pass,1,local_refine_level" in text
    assert "erefine,all,1,1" in text
    assert text.index("erefine,all,1,1") < text.index("! contact 1")
    assert text.index("erefine,all,1,1") < text.index("! bcs")
    assert "*if,mesh_only_preflight,eq,1,then" in text
    assert "aggressive_mesh_inventory,csv" in text


def test_runner_exposes_local_level_and_records_the_frozen_region():
    from src.runners import run_indentation_sweep as runner

    parser = runner.build_parser()
    args = parser.parse_args(["--profile", "thickness", "--local-refine-level", "1"])
    assert args.local_refine_level == 1
    assert runner.LOCAL_REFINE_HALFWIDTH_MM == pytest.approx(1.8)
    fields = set(runner.MANIFEST_FIELDS)
    assert {
        "local_refine_level",
        "local_refine_halfwidth_mm",
        "local_target_mesh_size_mm",
    } <= fields


def test_development_preflight_is_mesh_only_and_hash_complete():
    root = EXPERIMENT / "results" / "development_preflight"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "development_mesh_only_preflight_not_formal_numerical_endpoint"
    assert manifest["git_worktree_was_dirty"] is True
    assert manifest["condition"]["mesh_only"] is True
    assert manifest["condition"]["nonlinear_solution_started"] is False
    assert manifest["result"]["ansys_error_count"] == 0
    assert manifest["result"]["solid_elements_after"] == 817237
    assert manifest["result"]["solid_nodes_after"] == 1160408
    assert manifest["extreme_result"]["solid_elements_after"] == 2880653
    assert manifest["extreme_result"]["solid_nodes_after"] == 3986139
    assert manifest["extreme_result"]["condition"]["nonlinear_solution_started"] is False
    assert "nonlinear_solve_rejected" in manifest["extreme_result"]["decision"]
    assert sha256(MODEL) == manifest["source_macro"]["sha256"]
    assert MODEL.stat().st_size == manifest["source_macro"]["size_bytes"]
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]
    solve_text = (root / "L010_2p00mm" / "mesh_log.txt").read_text(errors="replace")
    assert "RUN COMPLETED" in solve_text
    assert "NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0" in solve_text
    assert "SOLUTION OPTIONS" not in solve_text


def test_formal_preflight_is_commit_pinned_mesh_only_and_hash_complete():
    root = EXPERIMENT / "results" / "formal_preflight"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "formal_committed_mesh_only_preflight_complete"
    assert manifest["source_git_commit"] == "8768e6ec6afb41225d729c21aac80b467c266897"
    assert manifest["nonlinear_solution_started"] is False
    assert set(manifest["cases"]) == {"G015", "L010"}
    g015, l010 = manifest["cases"]["G015"], manifest["cases"]["L010"]
    assert g015["solid_elements_after"] == 1292705
    assert g015["solid_nodes_after"] == 1813547
    assert l010["solid_elements_after"] == 817237
    assert l010["solid_nodes_after"] == 1160408
    for case in (g015, l010):
        assert case["status"] == "complete"
        assert case["mapdl_error_count"] == 0
        assert case["shape_error_elements"] == 0
        assert case["run_completed"] is True
        assert case["external_db"]["path"].startswith("/home/xuanyu/")
        assert len(case["external_db"]["sha256"]) == 64
    assert g015["solid_elements_after"] > l010["solid_elements_after"] * 1.5
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]
    conclusion = (root / "CONCLUSION.md").read_text(encoding="utf-8")
    assert "压力对尚未启动" in conclusion
    assert "不能计算 \\(q\\)" in conclusion


def test_resource_projection_is_reproducible(tmp_path: Path):
    script = load_module(
        "estimate_resource_envelope",
        EXPERIMENT / "scripts" / "analysis" / "estimate_resource_envelope.py",
    )
    rows = list(csv.DictReader((EXPERIMENT / "results" / "resource_projection.csv").open(encoding="utf-8")))
    indexed = {row["strategy"]: row for row in rows}
    assert int(indexed["global_0.10"]["predicted_equations"]) > 16_000_000
    assert float(indexed["global_0.10"]["predicted_rst_gib_per_endpoint"]) > 90
    assert int(indexed["layered_local_0.10"]["predicted_elements"]) == 817237
    assert float(indexed["layered_local_0.10"]["predicted_six_endpoint_wall_hours_upper"]) < 72
    assert int(indexed["layered_local_0.05"]["predicted_equations"]) > 11_000_000
    assert float(indexed["layered_local_0.05"]["predicted_rst_gib_per_endpoint"]) > 60
    assert float(indexed["layered_local_0.05"]["predicted_anchor_pair_wall_hours_lower"]) > 48

    # Exercise the pure fit helper independently of CLI path serialization.
    coefficient, exponent = script.fit_power_law([(0.3, 177278), (0.24, 343661), (0.2, 575211)])
    predicted = coefficient * 0.1**exponent
    assert exponent == pytest.approx(-2.90522200599)
    assert predicted == pytest.approx(4_331_491.763, rel=1e-10)


def test_mesh_preflight_collector_reads_development_fixture(tmp_path: Path):
    module = load_module(
        "collect_mesh_preflight",
        EXPERIMENT / "scripts" / "analysis" / "collect_mesh_preflight.py",
    )
    source = EXPERIMENT / "results" / "development_preflight" / "L010_2p00mm"
    case = tmp_path / "L010"
    shutil.copytree(source, case)
    (case / "PREFLIGHT_COMPLETE").write_text("complete\n", encoding="utf-8")
    row = module.parse_case(case)
    assert row["status"] == "complete"
    assert row["background_mesh_mm"] == pytest.approx(0.2)
    assert row["nominal_local_target_mm"] == pytest.approx(0.1)
    assert row["solid_elements_after"] == 817237
    assert row["solid_nodes_after"] == 1160408
    assert row["mapdl_error_count"] == 0
    assert row["shape_warning_elements"] == 32
    assert row["shape_error_elements"] == 0
    assert row["run_completed"] is True

    extreme_source = EXPERIMENT / "results" / "development_preflight" / "L005_2p00mm"
    extreme_case = tmp_path / "L005"
    shutil.copytree(extreme_source, extreme_case)
    (extreme_case / "PREFLIGHT_COMPLETE").write_text("complete\n", encoding="utf-8")
    extreme = module.parse_case(extreme_case)
    assert extreme["solid_elements_after"] == 2880653
    assert extreme["solid_nodes_after"] == 3986139
    assert extreme["shape_warning_elements"] == 50
    assert extreme["shape_error_elements"] == 0


def test_launchers_require_commit_pin_and_keep_extreme_mesh_only():
    preflight = (EXPERIMENT / "scripts" / "server" / "launch_mesh_preflight_5090d.sh").read_text()
    solve = (EXPERIMENT / "scripts" / "server" / "launch_aggressive_anchor_5090d.sh").read_text()
    for text in (preflight, solve):
        assert "EXPECTED_COMMIT:?" in text
        assert "status --porcelain" in text
        assert "Campaign root already exists" in text
    assert 'RUN_EXTREME="${RUN_EXTREME:-0}"' in preflight
    assert "L005:0.00020:120:1800" in preflight
    assert "*use,param_eye_sweep.mac" in preflight
    assert "--local-refine-level 1" in solve
    assert "maximum_simultaneous" not in solve
    assert "resource_guard_abort" in solve
    assert "THICKNESSES:-2.0" in solve
