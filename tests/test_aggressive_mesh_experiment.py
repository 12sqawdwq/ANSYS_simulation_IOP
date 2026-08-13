from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
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
    assert config["git_branch"] == "l010-baseline-t1p25-experiment-20260813"
    assert config["status"] == "t1p25_iop20_resource_abort_archived_out_of_core_rerun_ready"
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
    guard = config["session_guard_validation"]
    assert guard["status"] == "formal_clean_commit_session_guard_validation_complete"
    assert guard["source_commit"] == "c62987d795711052170f3538517e38fff5c0aa18"
    assert guard["ansys_started"] is False
    assert guard["nested_setsid_tested"] is True
    assert guard["term_to_kill_escalation_tested"] is True
    assert guard["launcher_signal_returncode"] == 143
    assert guard["residual_processes"] == 0
    accepted = config["accepted_h2p00_iop0_endpoint"]
    assert accepted["status"] == "accepted_complete_l010_h2p00_iop0_endpoint"
    assert accepted["source_commit"] == "abf4175de29eb2237f84b4151e362559d5634b85"
    assert accepted["eyelid_thickness_mm"] == pytest.approx(2.0)
    assert accepted["three_load_steps_converged"] is True
    assert accepted["ansys_error_count"] == 0
    assert accepted["residual_processes"] == 0
    baseline = config["baseline_t1p25_campaign"]
    assert baseline["eyelid_thickness_mm"] == pytest.approx(1.25)
    assert baseline["mesh_preflight"]["status"] == "formal_t1p25_mesh_only_preflight_complete"
    assert baseline["mesh_preflight"]["mapdl_error_count"] == 0
    assert baseline["mesh_preflight"]["shape_error_elements"] == 0
    assert baseline["iop0"]["status"] == "user_requested_priority_switch_abort_complete"
    assert baseline["iop0"]["completed_substeps_at_stop"] == 8
    assert baseline["iop0"]["run_completed"] is False
    assert baseline["iop0"]["scientific_result_available"] is False
    assert baseline["iop0"]["q_calculable"] is False
    assert baseline["iop20"]["authorized"] is True
    assert baseline["iop20"]["status"] == "resource_guard_abort_near_endpoint_archived_out_of_core_rerun_ready"
    assert baseline["iop20"]["source_commit"] == "5d3ece4bccf67e382bdfa639b0da80711c8008b8"
    assert baseline["iop20"]["completed_substeps"] == 28
    assert baseline["iop20"]["last_converged_indentation_mm"] == pytest.approx(0.259875)
    assert baseline["iop20"]["scientific_result_available"] is False
    assert baseline["iop20"]["formal_f20_available"] is False
    assert baseline["iop20"]["q_calculable"] is False
    assert baseline["iop20"]["restart_from_old_binary_possible"] is False
    readiness = config["restart_readiness"]
    assert readiness["old_campaign_reusable"] is False
    assert readiness["iop0_new_campaign_eligible"] is True
    assert readiness["iop20_authorized"] is True
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
    source_commit = "8768e6ec6afb41225d729c21aac80b467c266897"
    source = subprocess.run(
        ["git", "show", f"{source_commit}:models/apdl/param_eye_sweep.mac"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if source.returncode != 0:
        pytest.skip("historical source macro is unavailable in this checkout")
    assert hashlib.sha256(source.stdout).hexdigest() == manifest["source_macro"]["sha256"]
    assert len(source.stdout) == manifest["source_macro"]["size_bytes"]
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
    assert 'EYELID_THICKNESS_MM="${EYELID_THICKNESS_MM:-}"' in preflight
    assert 'EYELID_THICKNESS_MM="${EYELID_THICKNESS_MM:-$global_baseline_eyelid_thickness_mm}"' in preflight
    assert "model_baseline.json" in preflight
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
    assert "--solver-memory-mode out-of-core" in solve
    assert "--result-output-frequency last" in solve
    assert "solver_mode_verified" in solve
    assert "out-of-core memory mode" in solve
    assert 'THICKNESSES="${THICKNESSES:-}"' in solve
    assert 'THICKNESSES="${THICKNESSES:-$global_baseline_eyelid_thickness_mm}"' in solve
    assert "model_baseline.json" in solve
    assert 'thickness_mode=global_baseline' in solve
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


def test_accepted_h2p00_iop0_is_hash_complete_and_not_a_baseline_endpoint():
    root = EXPERIMENT / "results" / "accepted_iop0_h2p00"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "accepted_complete_l010_h2p00_iop0_endpoint"
    assert manifest["source_git_commit"] == "abf4175de29eb2237f84b4151e362559d5634b85"
    assert manifest["condition"] == {
        "eyelid_thickness_mm": 2.0,
        "iop_mmhg": 0.0,
        "indent_mm": 0.28,
        "background_mesh_mm": 0.2,
        "local_refine_level": 1,
        "nominal_local_target_mm": 0.1,
        "np": 4,
    }
    assert all(manifest["qc"].values())
    assert manifest["result"]["probe_fy_n"] == pytest.approx(-0.27251723724402)
    assert manifest["result"]["maximum_penetration_mm"] == pytest.approx(0.0071246231527766)
    assert manifest["result"]["ansys_warning_count"] == 9
    assert "not a 1.25-mm baseline endpoint" in manifest["acceptance"]
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]
    external = {item["role"]: item for item in manifest["external_artifacts"]}
    assert set(external) == {
        "rst", "db", "solve_out", "run_manifest", "run_metadata",
        "resource_monitor", "campaign_status",
    }
    assert external["rst"]["size_bytes"] == 18945146880
    assert external["rst"]["sha256"] == "b373ec7a912479c5ef2fe9b8b8fbc38e70af72ebe7e0ee215136ec45162f9ff2"


def test_t1p25_preflight_is_hash_complete_and_solver_free():
    root = EXPERIMENT / "results" / "t1p25_preflight"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "formal_t1p25_mesh_only_preflight_complete"
    assert manifest["source_git_commit"] == "011c77e74e08fd7619cb9cda3d834cfe3b8506dd"
    assert manifest["global_baseline_eyelid_thickness_mm"] == pytest.approx(1.25)
    assert manifest["nonlinear_solution_started"] is False
    l010 = manifest["cases"]["L010"]
    assert l010["eyelid_thickness_mm"] == pytest.approx(1.25)
    assert l010["solid_elements_after"] == 655574
    assert l010["solid_nodes_after"] == 940688
    assert l010["mapdl_error_count"] == 0
    assert l010["shape_error_elements"] == 0
    assert l010["run_completed"] is True
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]


def test_t1p25_iop0_launch_record_freezes_baseline_and_single_pressure():
    root = EXPERIMENT / "results" / "t1p25_iop0_launch"
    metadata = json.loads((root / "run_metadata_at_launch.json").read_text(encoding="utf-8"))
    assert metadata["git_commit"] == "011c77e74e08fd7619cb9cda3d834cfe3b8506dd"
    assert metadata["git_dirty"] is False
    assert metadata["iop_mmhg"] == pytest.approx(0.0)
    assert metadata["np"] == 4
    assert metadata["retry_count"] == 0
    assert metadata["local_refine_level"] == 1
    assert [case["eyelid_thickness_mm"] for case in metadata["cases"]] == [1.25]
    status = (root / "campaign_status_at_launch.csv").read_text(encoding="utf-8")
    assert "global_baseline_eyelid_thickness_mm,1.25" in status
    assert "thickness_mode,global_baseline" in status
    assert "pressures_mmhg,0" in status
    assert "pressures_mmhg,20" not in status


def test_t1p25_iop0_user_abort_is_hash_complete_and_not_an_endpoint():
    root = EXPERIMENT / "results" / "t1p25_iop0_user_aborted"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "user_requested_priority_switch_abort_complete"
    assert manifest["classification"] == "user_requested_priority_switch_abort"
    assert manifest["source_git_commit"] == "011c77e74e08fd7619cb9cda3d834cfe3b8506dd"
    assert manifest["condition"]["eyelid_thickness_mm"] == pytest.approx(1.25)
    assert manifest["condition"]["iop_mmhg"] == pytest.approx(0.0)
    assert manifest["stop"]["launcher_exit_code"] == 143
    assert manifest["stop"]["token_processes_after"] == 0
    assert manifest["stop"]["solver_processes_after"] == 0
    assert manifest["stop"]["active_blueknow_units_after"] == 0
    numerical = manifest["numerical_state_at_stop"]
    assert numerical["mapdl_error_count"] == 0
    assert numerical["completed_substeps"] == 8
    assert numerical["run_completed"] is False
    assert numerical["accepted_endpoint"] is False
    assert numerical["q_calculable"] is False
    cleanup = manifest["cleanup"]
    assert cleanup["files_deleted"] == 46
    assert cleanup["apparent_bytes_deleted"] == 9372703404
    assert cleanup["remaining_manifest_entries"] == 0
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]


def test_t1p25_iop20_launch_record_freezes_single_pressure_and_baseline():
    root = EXPERIMENT / "results" / "t1p25_iop20_launch"
    metadata = json.loads((root / "iop20" / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["git_commit"] == "5d3ece4bccf67e382bdfa639b0da80711c8008b8"
    assert metadata["git_dirty"] is False
    assert metadata["iop_mmhg"] == pytest.approx(20.0)
    assert metadata["np"] == 4
    assert metadata["retry_count"] == 0
    assert metadata["local_refine_level"] == 1
    assert [case["eyelid_thickness_mm"] for case in metadata["cases"]] == [1.25]
    status = (root / "campaign_status.csv").read_text(encoding="utf-8")
    assert "thickness_mode,global_baseline" in status
    assert "pressures_mmhg,20" in status
    assert "pressures_mmhg,0" not in status
    driver = (root / "iop20" / "eyelid_1p25mm_indent_0p28mm" / "attempt_1" / "driver.dat").read_text(encoding="utf-8")
    assert "eyelid_thickness=0.00125" in driver
    assert "iop_pa=2666.44736842" in driver


def test_t1p25_iop20_resource_abort_is_hash_complete_and_not_an_endpoint():
    root = EXPERIMENT / "results" / "t1p25_iop20_resource_aborted"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "resource_guard_abort_near_endpoint_with_converged_intermediate_states"
    assert manifest["source_git_commit"] == "5d3ece4bccf67e382bdfa639b0da80711c8008b8"
    assert manifest["condition"]["eyelid_thickness_mm"] == pytest.approx(1.25)
    assert manifest["condition"]["iop_mmhg"] == pytest.approx(20.0)
    assert manifest["condition"]["solver_mode"] == "in_core"
    abort = manifest["resource_abort"]
    assert abort["launcher_returncode"] == 143
    assert abort["trigger_mem_available_kib"] == 30237892
    numerical = manifest["numerical_state_at_abort"]
    assert numerical["load_step_completed_substeps"] == {"1": 8, "2": 8, "3": 12}
    assert numerical["completed_substeps_total"] == 28
    assert numerical["cumulative_equilibrium_iterations"] == 54
    assert numerical["last_converged_pseudotime"] == pytest.approx(2.928125)
    assert numerical["last_converged_indentation_mm"] == pytest.approx(0.259875)
    assert numerical["mapdl_error_count"] == 0
    assert numerical["run_completed"] is False
    assert numerical["formal_f20_available"] is False
    assert numerical["q_calculable"] is False
    containment = manifest["containment"]
    assert containment["solver_processes_after"] == 0
    assert containment["token_processes_after"] == 0
    assert containment["active_blueknow_units_after"] == 0
    cleanup = manifest["cleanup"]
    assert cleanup["files_deleted"] == 46
    assert cleanup["apparent_bytes_deleted"] == 21133517890
    assert cleanup["allocated_bytes_deleted"] == 14760343552
    assert cleanup["remaining_selected_files"] == 0
    assert manifest["restart_decision"]["old_binary_restart_authorized"] is False
    assert manifest["restart_decision"]["same_in_core_strategy_authorized"] is False
    assert manifest["restart_decision"]["new_root_required"] is True
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]


def test_t1p25_iop20_failed_dispatch_never_started_solver():
    root = EXPERIMENT / "results" / "t1p25_iop20_failed_dispatch"
    audit = (root / "FAILED_DISPATCH_AUDIT.csv").read_text(encoding="utf-8")
    assert "classification,dispatch_wrapper_failed_before_launcher" in audit
    assert "outer_exit_code,126" in audit
    assert "launcher_started,false" in audit
    assert "ansys_started,false" in audit
    assert "mpi_started,false" in audit
    assert "solver_processes_after,0" in audit
    assert "blueknow_running_units_after,0" in audit
    assert "corrected_launch_requires_new_root,true" in audit


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


def test_formal_session_guard_validation_is_clean_commit_hash_complete_and_non_numerical():
    root = EXPERIMENT / "results" / "session_guard_validation"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "formal_clean_commit_session_guard_validation_complete"
    assert manifest["source_git_commit"] == "c62987d795711052170f3538517e38fff5c0aa18"
    assert manifest["ansys_started"] is False
    assert manifest["numerical_endpoint_created"] is False
    assert manifest["tests"]["helper"] == {
        "pass": True,
        "contained_processes_before": 3,
        "nested_setsid": True,
        "term_to_kill": True,
        "residual_processes": 0,
    }
    assert manifest["tests"]["launcher_signal"]["pass"] is True
    assert manifest["tests"]["launcher_signal"]["expected_returncode"] == 143
    assert manifest["tests"]["launcher_signal"]["campaign_incomplete"] is True
    assert manifest["active_blueknow_units_after"] == 0
    for item in manifest["artifacts"]:
        path = root / item["path"]
        assert path.is_file()
        assert path.stat().st_size == item["size_bytes"]
        assert sha256(path) == item["sha256"]
        if "external_sha256" in item:
            assert item["external_sha256"] == item["sha256"]

    metadata = (root / "validation_metadata.csv").read_text(encoding="utf-8")
    assert "source_worktree_clean,true" in metadata
    assert "ansys_started,false" in metadata
    assert "helper_test_pass,true" in metadata
    assert "launcher_signal_test_pass,true" in metadata
    residual = (root / "final_residual_check.txt").read_text(encoding="utf-8")
    assert "remaining_fixture_processes=0" in residual
    assert "active_blueknow_units=0" in residual
    helper_events = (root / "helper" / "session_guard_events.csv").read_text(encoding="utf-8")
    launcher_events = (root / "launcher" / "session_guard_events.csv").read_text(encoding="utf-8")
    for text in (helper_events, launcher_events):
        assert ",term_sent," in text
        assert ",kill_sent," in text
        assert ",no_residual_processes," in text
    helper_processes = (root / "helper" / "session_guard_processes.tsv").read_text(encoding="utf-8")
    assert "mapdl-session-guard-test" in helper_processes
    assert "hydra-pmi-session-guard-test" in helper_processes
    launcher_stdout = (root / "launcher_test_stdout.txt").read_text(encoding="utf-8")
    assert "ANCHOR_LAUNCHER_SIGNAL_TEST_PASS launcher_rc=143" in launcher_stdout
