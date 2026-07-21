#!/usr/bin/env python3
"""Extract a fixed indentation state from a completed thickness load path."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.summarize_thickness_sweep import (
    build_qc,
    plot_curves,
    summary_rows,
    write_csv as write_summary,
)
from src.postprocess.thickness_geometry import (
    GEOMETRY_FIELDS,
    analyze_files,
    write_results as write_geometry_results,
)
from src.runners.run_indentation_sweep import (
    APDL_FILES,
    GAP_M,
    MANIFEST_FIELDS,
    MODEL_DIR,
    RAW_METRIC_FIELDS,
    ansys_version,
    atomic_json,
    execute_command,
    find_ansys_binary,
    git_provenance,
    label,
    parse_numeric_csv,
    sha256,
    utc_now,
)

SOURCE_FIELDS = (
    "source_case",
    "source_attempt_dir",
    "source_result_rst",
    "source_result_time",
    "target_result_time",
    "extraction_method",
)
OUTPUT_FIELDS = MANIFEST_FIELDS + SOURCE_FIELDS


def result_time_for_indent(
    target_indent_mm: float,
    source_indent_mm: float,
    gap_m: float = GAP_M,
) -> float:
    if source_indent_mm <= 0:
        raise ValueError("source indentation must be positive")
    if target_indent_mm < 0 or target_indent_mm > source_indent_mm:
        raise ValueError("target indentation must be between zero and the source indentation")
    source_push_m = gap_m + source_indent_mm / 1000.0
    target_push_m = gap_m + target_indent_mm / 1000.0
    return 1.0 + target_push_m / source_push_m


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_manifest(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: float(item["eyelid_thickness_mm"])):
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})
    temporary.replace(path)


def target_case_name(thickness_mm: float, target_indent_mm: float) -> str:
    return f"eyelid_{label(thickness_mm)}mm_indent_{label(target_indent_mm)}mm"


def _rename_views(attempt: Path, source_case: str, target_case: str) -> int:
    views = sorted(attempt.glob(f"{source_case}[0-9][0-9][0-9].png"))
    for index, source in enumerate(views):
        source.replace(attempt / f"{target_case}{index:03d}.png")
    return len([path for path in attempt.glob(f"{target_case}*.png") if path.stat().st_size > 0])


def _failed_row(
    source: dict[str, str],
    target_case: str,
    target_indent_mm: float,
    target_time: float,
    started_at: str,
    elapsed: float,
    reason: str,
) -> dict:
    row = {field: "" for field in OUTPUT_FIELDS}
    row.update({
        "case": target_case,
        "profile": "thickness_state",
        "offset_mm": 0.0,
        "indent_mm": target_indent_mm,
        "eyelid_thickness_mm": source["eyelid_thickness_mm"],
        "cornea_thickness_mm": source["cornea_thickness_mm"],
        "mesh_size_mm": source["mesh_size_mm"],
        "iop_mmhg": source.get("iop_mmhg", 20.0),
        "eyelid_material_scale": source.get("eyelid_material_scale", 1.0),
        "cornea_material_scale": source.get("cornea_material_scale", 1.0),
        "status": "invalid_metrics",
        "failure_reason": reason,
        "attempt_count": 1,
        "selected_attempt": 1,
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(elapsed, 3),
        "source_case": source["case"],
        "source_attempt_dir": source["attempt_dir"],
        "source_result_rst": source["result_rst"],
        "source_result_time": source["result_time"],
        "target_result_time": target_time,
        "extraction_method": "same_load_path_time_interpolation",
    })
    return row


def extract_case(
    source_root: Path,
    output_root: Path,
    source: dict[str, str],
    target_indent_mm: float,
    target_time: float,
    ansys_bin: Path,
    np: int,
    timeout_seconds: float,
    git_commit: str,
    git_dirty: bool,
    view_policy: str = "all",
) -> dict:
    thickness_mm = float(source["eyelid_thickness_mm"])
    source_case = source["case"]
    target_case = target_case_name(thickness_mm, target_indent_mm)
    source_attempt = source_root / source["attempt_dir"]
    attempt = output_root / target_case / "attempt_1"
    attempt.mkdir(parents=True)
    for filename in APDL_FILES[1:]:
        shutil.copy2(MODEL_DIR / filename, attempt / filename)

    source_db = source_attempt / f"{source_case}.db"
    source_rst = source_root / source["result_rst"]
    linked_db = attempt / source_db.name
    linked_rst = attempt / source_rst.name
    started_at = utc_now()
    started = time.monotonic()
    returncode: int | None = None
    views_count = 0
    error_count = 0
    try:
        if source.get("status") != "complete":
            raise ValueError("source case is not complete")
        if not source_db.is_file() or not source_rst.is_file():
            raise FileNotFoundError("source DB or RST is missing")
        # MAPDL can truncate the active database name when it exits. Use a real
        # disposable DB copy and expose the large, read-only result through a symlink.
        shutil.copy2(source_db, linked_db)
        linked_rst.symlink_to(source_rst)
        driver = attempt / "driver.dat"
        plot_command = (
            f"*use,plot_sweep_views.mac,{target_time:.14g}\n"
            if view_policy == "all" else ""
        )
        driver.write_text(
            f"resume,{source_case},db\n"
            f"/filname,{source_case}\n"
            f"*use,post_sweep.mac,{target_time:.14g}\n"
            f"*use,post_thickness_geometry.mac,{target_time:.14g}\n"
            + plot_command,
            encoding="ascii",
        )
        command = [
            str(ansys_bin), "-b", "-np", str(np), "-dir", str(attempt),
            "-i", str(driver), "-o", str(attempt / "solve.out"), "-j", f"post_{target_case}",
        ]
        env = os.environ.copy()
        env.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
        returncode, timed_out, _ = execute_command(command, attempt, env, timeout_seconds)
        output = (attempt / "solve.out").read_text(errors="replace")
        upper_output = output.upper()
        error_count = upper_output.count("*** ERROR ***")
        if timed_out:
            raise RuntimeError("postprocessing exceeded timeout")
        if returncode != 0 or "RUN COMPLETED" not in upper_output or error_count:
            raise RuntimeError(
                f"MAPDL postprocessing failed: returncode={returncode}, errors={error_count}"
            )
        views_count = _rename_views(attempt, source_case, target_case)
        expected_views = 9 if view_policy == "all" else 0
        if views_count != expected_views:
            raise ValueError(f"expected {expected_views} views, found {views_count}")

        geometry = analyze_files(
            attempt / "inner_preload_faces.csv",
            attempt / "inner_final_faces.csv",
        )
        write_geometry_results(attempt, geometry)
        metrics = dict(zip(
            RAW_METRIC_FIELDS,
            parse_numeric_csv(attempt / "metrics.csv", len(RAW_METRIC_FIELDS)),
        ))
        metrics.update(zip(
            GEOMETRY_FIELDS,
            parse_numeric_csv(attempt / "thickness_geometry.csv", len(GEOMETRY_FIELDS)),
        ))
        push_m = GAP_M + target_indent_mm / 1000.0
        # MAPDL labels a time-interpolated result as load step zero; the selected
        # result time and imposed probe displacement are the authoritative checks.
        if round(metrics["result_load_step"]) not in (0, 2) or not math.isclose(
            metrics["result_time"], target_time, rel_tol=0.0, abs_tol=1e-6
        ):
            raise ValueError("MAPDL did not select the requested load-step time")
        for field in ("probe_uy_m", "probe_uy_max_m"):
            if abs(metrics[field] + push_m) > max(1e-8, 0.005 * push_m):
                raise ValueError(f"{field} does not match the target displacement")
        areas = [metrics[f"inner_area_{angle}deg_m2"] for angle in (1, 2, 3)]
        if not (0 < areas[0] <= areas[1] <= areas[2] <= metrics["inner_effect_area_m2"]):
            raise ValueError("inner geometric areas violate angle ordering")

        row = {field: "" for field in OUTPUT_FIELDS}
        row.update({
            "case": target_case,
            "profile": "thickness_state",
            "offset_mm": 0.0,
            "indent_mm": target_indent_mm,
            "eyelid_thickness_mm": thickness_mm,
            "cornea_thickness_mm": source["cornea_thickness_mm"],
            "mesh_size_mm": source["mesh_size_mm"],
            "iop_mmhg": source.get("iop_mmhg", 20.0),
            "eyelid_material_scale": source.get("eyelid_material_scale", 1.0),
            "cornea_material_scale": source.get("cornea_material_scale", 1.0),
            "status": "complete",
            "attempt_count": 1,
            "selected_attempt": 1,
            "np_used": np,
            "returncode": returncode,
            "started_at_utc": started_at,
            "ended_at_utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "timeout_seconds": timeout_seconds,
            "ansys_error_count": error_count,
            "views_count": views_count,
            "commanded_push_m": push_m,
            "preload_converged": source["preload_converged"],
            "indentation_converged": source["indentation_converged"],
            "attempt_dir": str(attempt.relative_to(output_root)),
            "git_commit": git_commit,
            "git_dirty": str(git_dirty).lower(),
            "source_case": source_case,
            "source_attempt_dir": source["attempt_dir"],
            "source_result_rst": source["result_rst"],
            "source_result_time": source["result_time"],
            "target_result_time": target_time,
            "extraction_method": "same_load_path_time_interpolation",
        })
        row.update(metrics)
        row["n_outer"] = int(round(row["n_outer"]))
        row["inner_face_count"] = int(round(row["inner_face_count"]))
        return row
    except (OSError, RuntimeError, ValueError) as error:
        return _failed_row(
            source, target_case, target_indent_mm, target_time, started_at,
            time.monotonic() - started, f"{type(error).__name__}: {error}",
        )
    finally:
        for path in (linked_db, linked_rst):
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run", type=Path)
    parser.add_argument("output_run", type=Path)
    parser.add_argument("--target-indent-mm", type=float, required=True)
    parser.add_argument("--source-indent-mm", type=float, default=0.8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--np", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--ansys-bin", type=Path, default=os.environ.get("ANSYS_BIN"))
    parser.add_argument("--view-policy", choices=("all", "none"), default="all")
    cli = parser.parse_args()
    if cli.workers < 1 or cli.np < 1 or cli.timeout_seconds <= 0:
        parser.error("workers, np, and timeout must be positive")
    try:
        target_time = result_time_for_indent(cli.target_indent_mm, cli.source_indent_mm)
    except ValueError as error:
        parser.error(str(error))

    source_root = cli.source_run.expanduser().resolve()
    output_root = cli.output_run.expanduser().resolve()
    if output_root.exists() and any(output_root.iterdir()):
        parser.error(f"output run must be new or empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    source_rows = [
        row for row in read_csv(source_root / "run_manifest.csv")
        if row.get("status") == "complete"
        and math.isclose(float(row["indent_mm"]), cli.source_indent_mm, abs_tol=1e-9)
    ]
    if not source_rows:
        parser.error("source manifest has no matching complete thickness cases")
    source_rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    ansys_bin = find_ansys_binary(cli.ansys_bin)
    git_commit, git_dirty = git_provenance()
    run_id = output_root.name
    metadata = {
        "run_id": run_id,
        "profile": "thickness_state",
        "run_root": str(output_root),
        "source_run": str(source_root),
        "source_indent_mm": cli.source_indent_mm,
        "target_indent_mm": cli.target_indent_mm,
        "target_result_time": target_time,
        "extraction_method": "same_load_path_time_interpolation",
        "host": socket.gethostname(),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "ansys_executable": str(ansys_bin),
        "ansys_version": ansys_version(ansys_bin),
        "invocation": [sys.executable, *sys.argv],
        "workers": cli.workers,
        "np": cli.np,
        "timeout_seconds": cli.timeout_seconds,
        "view_policy": cli.view_policy,
        "started_at_utc": utc_now(),
        "cases": [{
            "eyelid_thickness_mm": float(row["eyelid_thickness_mm"]),
            "cornea_thickness_mm": float(row["cornea_thickness_mm"]),
            "indent_mm": cli.target_indent_mm,
            "iop_mmhg": float(row.get("iop_mmhg") or 20.0),
            "eyelid_material_scale": float(row.get("eyelid_material_scale") or 1.0),
            "cornea_material_scale": float(row.get("cornea_material_scale") or 1.0),
        } for row in source_rows],
        "apdl_sha256": {
            filename: sha256(MODEL_DIR / filename) for filename in APDL_FILES[1:]
        },
    }
    atomic_json(output_root / "run_metadata.json", metadata)
    manifest_path = output_root / "run_manifest.csv"
    rows: list[dict] = []
    write_manifest(manifest_path, rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                extract_case, source_root, output_root, source, cli.target_indent_mm,
                target_time, ansys_bin, cli.np, cli.timeout_seconds, git_commit, git_dirty,
                cli.view_policy,
            )
            for source in source_rows
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            write_manifest(manifest_path, rows)
            print(f"{row['case']}: {row['status']}", flush=True)

    summaries = summary_rows(rows)
    write_summary(output_root / "summary.csv", summaries)
    expected_views = 9 if cli.view_policy == "all" else 0
    qc = build_qc(rows, summaries, metadata["cases"], expected_views)
    (output_root / "qc_report.json").write_text(
        json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if summaries:
        plot_curves(output_root, summaries)
    complete = sum(row["status"] == "complete" for row in rows)
    metadata.update({
        "ended_at_utc": utc_now(),
        "completed_cases": complete,
        "failed_cases": len(rows) - complete,
        "qc_passed": qc["passed"],
    })
    atomic_json(output_root / "run_metadata.json", metadata)
    print(f"completed={complete} failed={len(rows) - complete} root={output_root}")
    return 0 if complete == len(rows) and qc["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
