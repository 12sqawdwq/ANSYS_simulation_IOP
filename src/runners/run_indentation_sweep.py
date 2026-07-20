#!/usr/bin/env python3
"""Run validated MAPDL indentation sweeps with isolated per-case attempts."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.prune_solver_artifacts import POLICY as ARTIFACT_POLICY
from src.postprocess.prune_solver_artifacts import prune_attempt
from src.postprocess.thickness_geometry import GEOMETRY_FIELDS as THICKNESS_GEOMETRY_FIELDS
from src.postprocess.thickness_geometry import analyze_files, write_results as write_geometry_results

MODEL_DIR = REPO_ROOT / "models" / "apdl"
APDL_FILES = (
    "param_eye_sweep.mac",
    "post_sweep.mac",
    "post_thickness_geometry.mac",
    "plot_sweep_views.mac",
)
OFFSETS_MM = (0.0, 0.5, 1.0, 2.0)
MAX_INDENT_MM = 0.8
MIN_EYELID_THICKNESS_MM = 0.8
MAX_EYELID_THICKNESS_MM = 2.0
THICKNESS_MM = tuple(round(0.8 + 0.2 * index, 1) for index in range(7))
FULL_INDENTS_MM = tuple(i / 5 for i in range(5))
COARSE_INDENTS_MM = (0.0, 0.4, 0.8)
GAP_M = 0.05e-3
PROFILE_CASES = {
    "smoke": ((0.0, 0.0), (0.0, 0.8), (2.0, 0.4), (2.0, 0.8)),
    "coarse": tuple((offset, indent) for offset in OFFSETS_MM for indent in COARSE_INDENTS_MM),
    "full": tuple((offset, indent) for offset in OFFSETS_MM for indent in FULL_INDENTS_MM),
}
RAW_METRIC_FIELDS = (
    "probe_fx_n",
    "probe_fy_n",
    "contact_area_m2",
    "contact_x_center_m",
    "pmax_pa",
    "max_penetration_m",
    "n_outer",
    "cornea_peak_pa",
    "eyelid_peak_pa",
    "probe_uy_m",
    "probe_uy_max_m",
    "result_load_step",
    "result_time",
)
MANIFEST_FIELDS = (
    "case",
    "profile",
    "offset_mm",
    "indent_mm",
    "eyelid_thickness_mm",
    "cornea_thickness_mm",
    "mesh_size_mm",
    "status",
    "failure_reason",
    "attempt_count",
    "selected_attempt",
    "np_used",
    "returncode",
    "started_at_utc",
    "ended_at_utc",
    "elapsed_seconds",
    "timeout_seconds",
    "ansys_error_count",
    "views_count",
    "artifact_pruned_files",
    "artifact_pruned_bytes",
    "artifact_prune_error",
    "probe_fx_n",
    "probe_fy_n",
    "contact_area_m2",
    "contact_x_center_m",
    "pmax_pa",
    "max_penetration_m",
    "n_outer",
    "inner_max_downward_m",
    "inner_effect_area_m2",
    "inner_area_5deg_m2",
    "inner_area_10deg_m2",
    "inner_area_15deg_m2",
    "inner_face_count",
    "cornea_peak_pa",
    "eyelid_peak_pa",
    "probe_uy_m",
    "probe_uy_max_m",
    "commanded_push_m",
    "preload_converged",
    "indentation_converged",
    "result_load_step",
    "result_time",
    "result_rst",
    "attempt_dir",
    "git_commit",
    "git_dirty",
)
RETRYABLE_STATUSES = {"nonconverged", "ansys_error"}
NONCONVERGENCE_MARKERS = (
    "SOLUTION NOT CONVERGED",
    "THE SOLUTION WAS NOT CONVERGED",
    "CONVERGENCE FAILURE",
    "DOES NOT CONVERGE",
)
FATAL_MARKERS = ("ERROR TERMINATION", "FATAL ERROR")


@dataclass(frozen=True)
class CaseSpec:
    offset_mm: float
    indent_mm: float
    order: int
    eyelid_thickness_mm: float = 1.0
    kind: str = "indentation"

    @property
    def name(self) -> str:
        if self.kind == "thickness":
            return f"eyelid_{label(self.eyelid_thickness_mm)}mm_indent_{label(self.indent_mm)}mm"
        return f"offset_{label(self.offset_mm)}mm_indent_{label(self.indent_mm)}mm"


@dataclass(frozen=True)
class RunConfig:
    run_root: Path
    profile: str
    np: int
    timeout_seconds: float
    retry_count: int
    ansys_bin: Path
    mesh_size_mm: float
    git_commit: str
    git_dirty: bool


@dataclass
class AttemptOutcome:
    status: str
    reason: str
    returncode: int | None
    elapsed_seconds: float
    error_count: int
    views_count: int
    metrics: dict[str, float | int | str]
    rst_path: Path | None
    artifact_pruned_files: int = 0
    artifact_pruned_bytes: int = 0
    artifact_prune_error: str = ""


def label(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_provenance() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def find_ansys_binary(override: Path | None) -> Path:
    if override is not None:
        candidate = override.expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"ANSYS executable does not exist: {candidate}")
        return candidate
    command = shutil.which("ansys")
    if command:
        return Path(command)
    candidates = sorted(Path("/ansys_inc").glob("*/ansys/bin/ansys[0-9]*"), reverse=True)
    if not candidates:
        raise FileNotFoundError("ANSYS executable not found; set ANSYS_BIN or pass --ansys-bin")
    return candidates[0]


def ansys_version(ansys_bin: Path) -> str:
    completed = subprocess.run(
        [str(ansys_bin), "-v"], capture_output=True, text=True, timeout=30, check=False
    )
    text = (completed.stdout + completed.stderr).strip()
    return "\n".join(text.splitlines()[:8])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_manifest(path: Path, rows: list[dict], order: dict[str, int]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: order[item["case"]]):
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})
    temporary.replace(path)


def parse_numeric_csv(path: Path, expected: int) -> list[float]:
    values = [item.strip() for item in path.read_text(errors="replace").replace("\n", "").split(",")]
    values = [item for item in values if item]
    if len(values) != expected:
        raise ValueError(f"expected {expected} values in {path.name}, found {len(values)}")
    parsed = [float(item) for item in values]
    if not all(math.isfinite(value) for value in parsed):
        raise ValueError(f"non-finite value in {path.name}")
    return parsed


def terminate_process_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()


def execute_command(
    command: list[str], cwd: Path, env: dict[str, str], timeout_seconds: float
) -> tuple[int | None, bool, float]:
    started = time.monotonic()
    with (cwd / "launcher.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=(os.name == "posix"),
            text=True,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            terminate_process_group(process)
            returncode = process.returncode
            timed_out = True
    return returncode, timed_out, time.monotonic() - started


def validate_attempt(
    attempt_dir: Path,
    case: CaseSpec,
    returncode: int | None,
    timed_out: bool,
    elapsed_seconds: float,
) -> AttemptOutcome:
    solve_path = attempt_dir / "solve.out"
    launcher_path = attempt_dir / "launcher.log"
    output = ""
    for path in (solve_path, launcher_path):
        if path.exists():
            output += path.read_text(errors="replace")
    upper_output = output.upper()
    error_count = upper_output.count("*** ERROR ***")
    if timed_out:
        return AttemptOutcome("timeout", "case exceeded timeout", returncode, elapsed_seconds,
                              error_count, 0, {}, None)
    if returncode != 0 or any(marker in upper_output for marker in FATAL_MARKERS):
        status = "nonconverged" if any(marker in upper_output for marker in NONCONVERGENCE_MARKERS) else "ansys_error"
        return AttemptOutcome(status, "ANSYS terminated before a valid final result", returncode,
                              elapsed_seconds, error_count, 0, {}, None)
    if "RUN COMPLETED" not in upper_output:
        status = "nonconverged" if any(marker in upper_output for marker in NONCONVERGENCE_MARKERS) else "ansys_error"
        return AttemptOutcome(status, "RUN COMPLETED marker is missing", returncode,
                              elapsed_seconds, error_count, 0, {}, None)

    metrics_path = attempt_dir / "metrics.csv"
    solution_status_path = attempt_dir / "solution_status.csv"
    rst_candidates = sorted(attempt_dir.glob(f"{case.name}.rst"))
    if not metrics_path.is_file() or not solution_status_path.is_file() or not rst_candidates:
        return AttemptOutcome("missing_results", "metrics, solution status, or RST is missing",
                              returncode, elapsed_seconds, error_count, 0, {}, None)
    views = [path for path in attempt_dir.glob("*.png") if path.stat().st_size > 0]
    if len(views) != 9:
        return AttemptOutcome("missing_results", f"expected 9 non-empty views, found {len(views)}",
                              returncode, elapsed_seconds, error_count, len(views), {}, rst_candidates[0])

    try:
        raw_metrics = parse_numeric_csv(metrics_path, len(RAW_METRIC_FIELDS))
        convergence = parse_numeric_csv(solution_status_path, 2)
        thickness_metrics = (
            parse_numeric_csv(
                attempt_dir / "thickness_geometry.csv", len(THICKNESS_GEOMETRY_FIELDS)
            )
            if case.kind == "thickness" else []
        )
    except (OSError, ValueError) as error:
        return AttemptOutcome("invalid_metrics", str(error), returncode, elapsed_seconds,
                              error_count, len(views), {}, rst_candidates[0])
    metrics = dict(zip(RAW_METRIC_FIELDS, raw_metrics))
    metrics.update(zip(THICKNESS_GEOMETRY_FIELDS, thickness_metrics))
    metrics["preload_converged"] = int(round(convergence[0]))
    metrics["indentation_converged"] = int(round(convergence[1]))
    metrics["n_outer"] = int(round(float(metrics["n_outer"])))
    if metrics["preload_converged"] != 1 or metrics["indentation_converged"] != 1:
        return AttemptOutcome("nonconverged", "one or both load steps are not converged",
                              returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])
    if round(float(metrics["result_load_step"])) != 2 or not math.isclose(
        float(metrics["result_time"]), 2.0, rel_tol=0.0, abs_tol=1e-6
    ):
        return AttemptOutcome("invalid_metrics", "final result is not load step 2 at time 2",
                              returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])
    if (float(metrics["contact_area_m2"]) < 0 or float(metrics["pmax_pa"]) < 0
            or float(metrics["max_penetration_m"]) < 0 or metrics["n_outer"] < 0):
        return AttemptOutcome("invalid_metrics", "contact metrics contain negative values",
                              returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])

    commanded_push = GAP_M + case.indent_mm / 1000.0
    displacement_tolerance = max(1e-8, 0.005 * commanded_push)
    for field in ("probe_uy_m", "probe_uy_max_m"):
        if abs(float(metrics[field]) + commanded_push) > displacement_tolerance:
            return AttemptOutcome("invalid_metrics", f"{field} does not match commanded displacement",
                                  returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])
    if float(metrics["contact_area_m2"]) == 0:
        metrics["contact_x_center_m"] = ""
    if case.kind == "thickness":
        inner_areas = [
            float(metrics[field])
            for field in ("inner_area_5deg_m2", "inner_area_10deg_m2", "inner_area_15deg_m2")
        ]
        if (
            float(metrics["inner_max_downward_m"]) <= 0
            or float(metrics["inner_effect_area_m2"]) <= 0
            or any(area <= 0 for area in inner_areas)
            or int(round(float(metrics["inner_face_count"]))) <= 0
        ):
            return AttemptOutcome("invalid_metrics", "inner geometric metrics are not positive",
                                  returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])
        if not (
            inner_areas[0] <= inner_areas[1] <= inner_areas[2]
            <= float(metrics["inner_effect_area_m2"])
        ):
            return AttemptOutcome("invalid_metrics", "inner geometric areas violate angle ordering",
                                  returncode, elapsed_seconds, error_count, len(views), metrics, rst_candidates[0])
    return AttemptOutcome("complete", "", returncode, elapsed_seconds, error_count,
                          len(views), metrics, rst_candidates[0])


def run_attempt(case: CaseSpec, config: RunConfig, attempt_number: int) -> AttemptOutcome:
    attempt_dir = config.run_root / case.name / f"attempt_{attempt_number}"
    attempt_dir.mkdir(parents=True, exist_ok=False)
    for filename in APDL_FILES:
        shutil.copy2(MODEL_DIR / filename, attempt_dir / filename)
    retry_mode = 1 if attempt_number > 1 else 0
    driver = attempt_dir / "driver.dat"
    driver_text = (
        f"xoff={case.offset_mm / 1000:.12g}\n"
        f"indent={case.indent_mm / 1000:.12g}\n"
        f"retry_mode={retry_mode}\n"
        f"mesh_size={config.mesh_size_mm / 1000:.12g}\n"
        f"eyelid_thickness={case.eyelid_thickness_mm / 1000:.12g}\n"
        "*use,param_eye_sweep.mac,xoff,indent,retry_mode,mesh_size,eyelid_thickness\n"
        f"resume,{case.name},db\n"
        f"/filname,{case.name}\n"
        "*use,post_sweep.mac\n"
    )
    if case.kind == "thickness":
        driver_text += "*use,post_thickness_geometry.mac\n"
    driver_text += "*use,plot_sweep_views.mac\n"
    driver.write_text(
        driver_text,
        encoding="ascii",
    )
    np_used = config.np if attempt_number == 1 else max(1, config.np // 2)
    command = [
        str(config.ansys_bin), "-b", "-np", str(np_used), "-dir", str(attempt_dir),
        "-i", str(driver), "-o", str(attempt_dir / "solve.out"), "-j", case.name,
    ]
    env = os.environ.copy()
    env.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
    started_at = utc_now()
    returncode, timed_out, elapsed_seconds = execute_command(
        command, attempt_dir, env, config.timeout_seconds
    )
    if case.kind == "thickness" and not timed_out and returncode == 0:
        try:
            geometry = analyze_files(
                attempt_dir / "inner_preload_faces.csv",
                attempt_dir / "inner_final_faces.csv",
            )
            write_geometry_results(attempt_dir, geometry)
        except (OSError, ValueError) as error:
            (attempt_dir / "thickness_geometry_error.txt").write_text(
                f"{type(error).__name__}: {error}\n", encoding="utf-8"
            )
    outcome = validate_attempt(attempt_dir, case, returncode, timed_out, elapsed_seconds)
    try:
        prune_stats = prune_attempt(
            attempt_dir,
            case.name,
            keep_primary_results=outcome.status == "complete",
        )
        outcome.artifact_pruned_files = prune_stats.files_selected
        outcome.artifact_pruned_bytes = prune_stats.bytes_selected
        if outcome.status != "complete":
            outcome.rst_path = None
    except OSError as error:
        outcome.artifact_prune_error = str(error)
    atomic_json(attempt_dir / "attempt.json", {
        "attempt": attempt_number,
        "retry_mode": retry_mode,
        "np": np_used,
        "command": command,
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "status": outcome.status,
        "reason": outcome.reason,
        "returncode": returncode,
        "ansys_error_count": outcome.error_count,
        "artifact_retention": {
            "policy": ARTIFACT_POLICY,
            "pruned_files": outcome.artifact_pruned_files,
            "pruned_bytes": outcome.artifact_pruned_bytes,
            "error": outcome.artifact_prune_error,
        },
    })
    return outcome


def run_case(case: CaseSpec, config: RunConfig) -> dict:
    case_dir = config.run_root / case.name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    started_at = utc_now()
    total_elapsed = 0.0
    outcome: AttemptOutcome | None = None
    selected_attempt = 0
    for attempt_number in range(1, config.retry_count + 2):
        selected_attempt = attempt_number
        try:
            outcome = run_attempt(case, config, attempt_number)
        except Exception as error:  # Keep the remaining parallel cases running and preserve the failure.
            outcome = AttemptOutcome("ansys_error", f"runner exception: {error}", None,
                                     0.0, 0, 0, {}, None)
        total_elapsed += outcome.elapsed_seconds
        if outcome.status == "complete":
            break
        if outcome.status not in RETRYABLE_STATUSES or attempt_number > config.retry_count:
            break
    assert outcome is not None
    attempt_dir = case_dir / f"attempt_{selected_attempt}"
    row = {field: "" for field in MANIFEST_FIELDS}
    row.update({
        "case": case.name,
        "profile": config.profile,
        "offset_mm": case.offset_mm,
        "indent_mm": case.indent_mm,
        "eyelid_thickness_mm": case.eyelid_thickness_mm,
        "cornea_thickness_mm": 0.6,
        "mesh_size_mm": config.mesh_size_mm,
        "status": outcome.status,
        "failure_reason": outcome.reason,
        "attempt_count": selected_attempt,
        "selected_attempt": selected_attempt,
        "np_used": config.np if selected_attempt == 1 else max(1, config.np // 2),
        "returncode": "" if outcome.returncode is None else outcome.returncode,
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(total_elapsed, 3),
        "timeout_seconds": config.timeout_seconds,
        "ansys_error_count": outcome.error_count,
        "views_count": outcome.views_count,
        "artifact_pruned_files": outcome.artifact_pruned_files,
        "artifact_pruned_bytes": outcome.artifact_pruned_bytes,
        "artifact_prune_error": outcome.artifact_prune_error,
        "commanded_push_m": GAP_M + case.indent_mm / 1000.0,
        "attempt_dir": str(attempt_dir.relative_to(config.run_root)),
        "git_commit": config.git_commit,
        "git_dirty": str(config.git_dirty).lower(),
    })
    row.update(outcome.metrics)
    if outcome.rst_path is not None:
        row["result_rst"] = str(outcome.rst_path.relative_to(config.run_root))
    return row


def parse_case(value: str) -> tuple[float, float]:
    try:
        offset, indent = value.split(":", 1)
        return float(offset), float(indent)
    except ValueError as error:
        raise argparse.ArgumentTypeError("case must use OFFSET:INDENT in mm") from error


def choose_cases(parser: argparse.ArgumentParser, cli: argparse.Namespace) -> tuple[str, list[CaseSpec]]:
    custom_grid = cli.offsets is not None or cli.indents is not None
    thickness_grid = cli.eyelid_thicknesses is not None
    selected_modes = sum((cli.profile is not None, bool(cli.case), custom_grid, thickness_grid))
    if selected_modes > 1:
        parser.error(
            "use only one of --profile, --case, --offsets/--indents, or --eyelid-thicknesses"
        )
    if custom_grid and (cli.offsets is None or cli.indents is None):
        parser.error("--offsets and --indents must be provided together")
    if thickness_grid or cli.profile == "thickness":
        profile = "thickness-custom" if thickness_grid else "thickness"
        thicknesses = cli.eyelid_thicknesses if thickness_grid else THICKNESS_MM
        if any(
            value < MIN_EYELID_THICKNESS_MM - 1e-12
            or value > MAX_EYELID_THICKNESS_MM + 1e-12
            for value in thicknesses
        ):
            parser.error(
                f"eyelid thickness must be within {MIN_EYELID_THICKNESS_MM:g}-"
                f"{MAX_EYELID_THICKNESS_MM:g} mm"
            )
        unique = list(dict.fromkeys(thicknesses))
        return profile, [
            CaseSpec(0.0, 0.8, index, thickness, "thickness")
            for index, thickness in enumerate(unique)
        ]
    if cli.case:
        profile = "custom"
        pairs = tuple(cli.case)
    elif custom_grid:
        profile = "custom"
        pairs = tuple((offset, indent) for offset in cli.offsets for indent in cli.indents)
    else:
        profile = cli.profile or "smoke"
        pairs = PROFILE_CASES[profile]
    if not pairs or any(offset < 0 or indent < 0 for offset, indent in pairs):
        parser.error("offset and indentation values must be non-negative")
    if any(indent > MAX_INDENT_MM + 1e-12 for _, indent in pairs):
        parser.error(f"indentation exceeds the validated {MAX_INDENT_MM:g} mm limit")
    unique_pairs = list(dict.fromkeys(pairs))
    return profile, [CaseSpec(offset, indent, index) for index, (offset, indent) in enumerate(unique_pairs)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=(*PROFILE_CASES, "thickness"))
    parser.add_argument("--case", action="append", type=parse_case, metavar="OFFSET:INDENT")
    parser.add_argument("--offsets", type=float, nargs="+")
    parser.add_argument("--indents", type=float, nargs="+")
    parser.add_argument("--eyelid-thicknesses", type=float, nargs="+")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--np", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=7200)
    parser.add_argument("--retry-count", type=int, choices=(0, 1), default=1)
    parser.add_argument("--mesh-size-mm", type=float, default=0.3)
    parser.add_argument("--ansys-bin", type=Path, default=os.environ.get("ANSYS_BIN"))
    parser.add_argument("--allow-dirty", action="store_true",
                        help="allow an uncommitted worktree for debugging; never use for formal results")
    return parser


def main() -> int:
    parser = build_parser()
    cli = parser.parse_args()
    if cli.workers < 1 or cli.np < 1 or cli.timeout_seconds <= 0 or cli.mesh_size_mm <= 0:
        parser.error("workers, np, timeout, and mesh size must be positive")
    profile, cases = choose_cases(parser, cli)
    git_commit, git_dirty = git_provenance()
    if git_dirty and not cli.allow_dirty:
        parser.error("formal runs require a clean Git worktree; commit changes or use --allow-dirty for debugging")
    ansys_bin = find_ansys_binary(cli.ansys_bin)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{git_commit[:8]}_{profile}"
    if cli.run_root is not None:
        run_root = cli.run_root.expanduser().resolve()
    elif os.environ.get("BLUEKNOW_RUN_ROOT"):
        run_root = Path(os.environ["BLUEKNOW_RUN_ROOT"]).expanduser().resolve()
    else:
        data_root = Path(os.environ.get(
            "BLUEKNOW_DATA_ROOT", "/home/xuanyu/PROJECT/ziyu/blueknow-data/indentation_sweep"
        ))
        run_root = data_root / run_id
    if run_root.exists() and any(run_root.iterdir()):
        parser.error(f"run root must be new or empty: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    config = RunConfig(run_root, profile, cli.np, cli.timeout_seconds, cli.retry_count,
                       ansys_bin, cli.mesh_size_mm, git_commit, git_dirty)
    metadata = {
        "run_id": run_id,
        "profile": profile,
        "run_root": str(run_root),
        "host": socket.gethostname(),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "ansys_executable": str(ansys_bin),
        "ansys_version": ansys_version(ansys_bin),
        "invocation": [sys.executable, *sys.argv],
        "workers": cli.workers,
        "np": cli.np,
        "timeout_seconds": cli.timeout_seconds,
        "retry_count": cli.retry_count,
        "mesh_size_mm": cli.mesh_size_mm,
        "started_at_utc": utc_now(),
        "cases": [{
            "offset_mm": case.offset_mm,
            "indent_mm": case.indent_mm,
            "eyelid_thickness_mm": case.eyelid_thickness_mm,
            "cornea_thickness_mm": 0.6,
        } for case in cases],
        "apdl_sha256": {filename: sha256(MODEL_DIR / filename) for filename in APDL_FILES},
        "artifact_retention_policy": ARTIFACT_POLICY,
    }
    atomic_json(run_root / "run_metadata.json", metadata)
    manifest_path = run_root / "run_manifest.csv"
    order = {case.name: case.order for case in cases}
    rows: list[dict] = []
    atomic_manifest(manifest_path, rows, order)
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = {pool.submit(run_case, case, config): case for case in cases}
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            atomic_manifest(manifest_path, rows, order)
            print(f"{row['case']}: {row['status']} attempts={row['attempt_count']}", flush=True)
    completed = sum(row["status"] == "complete" for row in rows)
    metadata.update({
        "ended_at_utc": utc_now(),
        "completed_cases": completed,
        "failed_cases": len(rows) - completed,
    })
    atomic_json(run_root / "run_metadata.json", metadata)
    print(f"completed={completed} failed={len(rows) - completed} root={run_root}")
    return 0 if completed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
