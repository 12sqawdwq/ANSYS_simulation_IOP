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
    assert config["schema_version"] == 2
    assert config["git_branch"] == "aggressive-contact-mesh-experiment-20260810"
    assert config["status"] == "failed_p1_audited_session_guard_implemented_formal_validation_pending"
    assert config["formal_preflight_source_commit"] == "8768e6ec6afb41225d729c21aac80b467c266897"
    assert config["hard_budget"]["wall_clock_hours"] == 72
    assert config["hard_budget"]["maximum_simultaneous_mapdl_cases"] == 1
    assert config["hard_budget"]["maximum_pressures_per_campaign"] == 1
    assert config["hard_budget"]["np_per_case"] == 4
    assert config["hard_budget"]["workers"] == 1
    assert config["hard_budget"]["retry_count"] == 0
    assert config["hard_budget"]["minimum_available_memory_gib_before_launch"] == 90
    assert config["hard_budget"]["abort_available_memory_gib"] == 30
    assert config["hard_budget"]["minimum_free_disk_gib_before_launch"] == 150
    assert config["hard_budget"]["abort_free_disk_gib"] == 100
    failed = config["failed_p1_resource_attempt"]
    assert failed["classification"] == "resource_guard_abort_with_orphan_process_cleanup"
    assert failed["source_commit"] == "d334fd124b768cbb53365fb19f383fa34ec9dbf7"
    assert failed["equations"] == 3370950
    assert failed["iop0_complete"] is False
    assert failed["iop20_started"] is False
    assert failed["partial_endpoint_accepted"] is False
    assert failed["restart_from_old_binary_possible"] is False
    assert failed["restart_authorized"] is False
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
    server = EXPERIMENT / "scripts" / "server"
    preflight = (server / "launch_mesh_preflight_5090d.sh").read_text()
    solve = (server / "launch_aggressive_anchor_5090d.sh").read_text()
    guard = (server / "session_guard.sh").read_text()
    guard_test = (server / "test_session_guard_5090d.sh").read_text()
    launcher_signal_test = (server / "test_anchor_launcher_signal_5090d.sh").read_text()
    for text in (preflight, solve):
        assert "EXPECTED_COMMIT:?" in text
        assert "status --porcelain" in text
        assert "Campaign root already exists" in text
    assert 'RUN_EXTREME="${RUN_EXTREME:-0}"' in preflight
    assert "L005:0.00020:120:1800" in preflight
    assert "*use,param_eye_sweep.mac" in preflight
    assert "--local-refine-level 1" in solve
    assert 'PRESSURES="${PRESSURES:-0}"' in solve
    assert "exactly one pressure" in solve
    assert 'MIN_AVAILABLE_MEMORY_GIB="${MIN_AVAILABLE_MEMORY_GIB:-90}"' in solve
    assert 'ABORT_AVAILABLE_MEMORY_GIB="${ABORT_AVAILABLE_MEMORY_GIB:-30}"' in solve
    assert 'MIN_FREE_DISK_GIB="${MIN_FREE_DISK_GIB:-150}"' in solve
    assert 'ABORT_FREE_DISK_GIB="${ABORT_FREE_DISK_GIB:-100}"' in solve
    assert 'MONITOR_INTERVAL_SECONDS="${MONITOR_INTERVAL_SECONDS:-10}"' in solve
    assert "NP_PER_CASE > 4" in solve
    assert "guard_start_unit" in solve
    assert "guard_stop_unit_tree" in solve
    assert "guard_finalize_unit" in solve
    assert 'kill -TERM -- "-$run_pid"' not in solve
    assert "resource_guard_abort" in solve
    assert "THICKNESSES:-2.0" in solve
    assert "systemd-run --user" in guard
    assert "KillMode=control-group" in guard
    assert "BLUEKNOW_CAMPAIGN_TOKEN" in guard
    assert "--kill-whom=all" in guard
    assert "guard_signal_all \"$unit\" \"$token\" TERM" in guard
    assert "guard_signal_all \"$unit\" \"$token\" KILL" in guard
    assert "residual_detected" in guard
    assert "setsid bash" in guard_test
    assert "mapdl-session-guard-test" in guard_test
    assert "hydra-pmi-session-guard-test" in guard_test
    assert "SESSION_GUARD_TEST_PASS" in guard_test
    assert "mapdl-anchor-launcher-test" in launcher_signal_test
    assert "hydra-anchor-launcher-test" in launcher_signal_test
    assert "kill -TERM \"$launcher_pid\"" in launcher_signal_test
    assert "launcher_rc\" -ne 143" in launcher_signal_test
    assert "CAMPAIGN_INCOMPLETE" in launcher_signal_test
    assert "ANCHOR_LAUNCHER_SIGNAL_TEST_PASS" in launcher_signal_test


def test_failed_p1_resource_abort_is_lightweight_hash_complete_and_not_an_endpoint():
    root = EXPERIMENT / "results" / "failed_p1_resource_guard"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "resource_guard_abort_with_orphan_process_cleanup"
    assert manifest["source_git_commit"] == "d334fd124b768cbb53365fb19f383fa34ec9dbf7"
    assert manifest["endpoint_acceptance"] == {
        "iop0_complete": False,
        "iop20_started": False,
        "partial_endpoint_accepted": False,
        "q_calculable": False,
        "restart_from_old_binary_possible": False,
    }
    assert manifest["solver"]["equations"] == 3370950
    assert manifest["solver"]["solver_mode"] == "out_of_core"
    assert manifest["solver"]["in_core_required_gb_all_ranks"] == pytest.approx(73.775)
    assert manifest["resource_abort"]["minimum_mem_available_gib"] == pytest.approx(11.50)
    assert manifest["orphan_cleanup"]["escaped_session_id"] == 439551
    assert manifest["orphan_cleanup"]["deleted_transient_files"] == 47
    assert manifest["orphan_cleanup"]["deleted_allocated_bytes"] == 83147467776
    assert manifest["restart_authorized"] is False
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]
        if "external_sha256" in item:
            assert item["external_sha256"] == item["sha256"]

    rows = list(csv.DictReader((root / "iop0" / "run_manifest.csv").open(encoding="utf-8")))
    assert rows == []
    status = (root / "FINAL_ABORT_STATUS.txt").read_text(encoding="utf-8")
    assert "partial_endpoint_accepted,false" in status
    assert "iop20_started,false" in status
    assert "restart_authorized,false" in status
    cleanup = (root / "ABORTED_TRANSIENT_CLEANUP.txt").read_text(encoding="utf-8")
    assert "files_selected,47" in cleanup
    assert "allocated_bytes_selected,83147467776" in cleanup
    extract = (root / "solver_resource_extract.txt").read_text(encoding="utf-8")
    assert "source_sha256,c8eb688d0b8a0367ad061f2b3661e86ce556b4b0f4a54d4454933504c9c43010" in extract
    assert "run_completed_observed,false" in extract
