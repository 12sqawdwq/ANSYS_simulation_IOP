#!/usr/bin/env python3
"""Extract eyelid equivalent-strain section views from a completed load path."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.extract_thickness_state import (
    read_csv,
    result_time_for_indent,
    target_case_name,
)
from src.runners.run_indentation_sweep import (
    ansys_version,
    atomic_json,
    execute_command,
    find_ansys_binary,
    git_provenance,
    sha256,
    utc_now,
)

MACRO = REPO_ROOT / "models" / "apdl" / "plot_thickness_eyelid_strain.mac"
MANIFEST_FIELDS = (
    "case",
    "eyelid_thickness_mm",
    "indent_mm",
    "status",
    "failure_reason",
    "elapsed_seconds",
    "returncode",
    "ansys_error_count",
    "image",
    "source_case",
    "source_attempt_dir",
    "source_result_rst",
    "source_result_time",
    "target_result_time",
    "git_commit",
)


def write_manifest(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: float(item["eyelid_thickness_mm"])):
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})
    temporary.replace(path)


def extract_view(
    source_root: Path,
    output_root: Path,
    source: dict[str, str],
    target_indent_mm: float,
    target_time: float,
    ansys_bin: Path,
    np: int,
    timeout_seconds: float,
    git_commit: str,
    include_probe: bool,
) -> dict:
    thickness_mm = float(source["eyelid_thickness_mm"])
    source_case = source["case"]
    target_case = target_case_name(thickness_mm, target_indent_mm)
    source_attempt = source_root / source["attempt_dir"]
    source_db = source_attempt / f"{source_case}.db"
    source_rst = source_root / source["result_rst"]
    work = output_root / ".work" / target_case
    destination_dir = output_root / target_case
    destination_dir.mkdir(parents=True)
    started = time.monotonic()
    row = {
        "case": target_case,
        "eyelid_thickness_mm": thickness_mm,
        "indent_mm": target_indent_mm,
        "status": "ansys_error",
        "failure_reason": "",
        "elapsed_seconds": "",
        "returncode": "",
        "ansys_error_count": "",
        "image": "",
        "source_case": source_case,
        "source_attempt_dir": source["attempt_dir"],
        "source_result_rst": source["result_rst"],
        "source_result_time": source["result_time"],
        "target_result_time": target_time,
        "git_commit": git_commit,
    }
    try:
        if source.get("status") != "complete":
            raise ValueError("source case is not complete")
        if not source_db.is_file() or source_db.stat().st_size == 0 or not source_rst.is_file():
            raise FileNotFoundError("source DB or RST is missing")
        work.mkdir(parents=True)
        shutil.copy2(source_db, work / source_db.name)
        (work / source_rst.name).symlink_to(source_rst)
        shutil.copy2(MACRO, work / MACRO.name)
        driver = work / "driver.dat"
        driver.write_text(
            f"resume,{source_case},db\n"
            f"/filname,{source_case}\n"
            f"*use,{MACRO.name},{target_time:.14g},{int(include_probe)}\n",
            encoding="ascii",
        )
        command = [
            str(ansys_bin), "-b", "-np", str(np), "-dir", str(work),
            "-i", str(driver), "-o", str(work / "post.out"), "-j", f"strain_{target_case}",
        ]
        env = os.environ.copy()
        env.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
        returncode, timed_out, _ = execute_command(command, work, env, timeout_seconds)
        output = (work / "post.out").read_text(errors="replace")
        error_count = output.upper().count("*** ERROR ***")
        row["returncode"] = returncode
        row["ansys_error_count"] = error_count
        if timed_out:
            raise RuntimeError("postprocessing exceeded timeout")
        if returncode != 0 or "RUN COMPLETED" not in output.upper() or error_count:
            raise RuntimeError(
                f"MAPDL postprocessing failed: returncode={returncode}, errors={error_count}"
            )
        images = [path for path in work.glob("*.png") if path.stat().st_size > 0]
        if len(images) != 1:
            raise ValueError(f"expected one non-empty PNG, found {len(images)}")
        destination = destination_dir / f"{target_case}007.png"
        shutil.copy2(images[0], destination)
        row.update({
            "status": "complete",
            "image": str(destination.relative_to(output_root)),
        })
    except (OSError, RuntimeError, ValueError) as error:
        row["failure_reason"] = f"{type(error).__name__}: {error}"
    finally:
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if work.exists():
            shutil.rmtree(work)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run", type=Path)
    parser.add_argument("output_run", type=Path)
    parser.add_argument("--target-indent-mm", type=float, default=0.28)
    parser.add_argument("--source-indent-mm", type=float, default=0.8)
    parser.add_argument("--workers", type=int, default=7)
    parser.add_argument("--np", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--ansys-bin", type=Path, default=os.environ.get("ANSYS_BIN"))
    parser.add_argument("--include-probe", action="store_true")
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
        and abs(float(row["indent_mm"]) - cli.source_indent_mm) < 1e-9
    ]
    source_rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    if not source_rows:
        parser.error("source manifest has no matching complete thickness cases")
    ansys_bin = find_ansys_binary(cli.ansys_bin)
    git_commit, git_dirty = git_provenance()
    metadata = {
        "profile": (
            "thickness_eyelid_probe_strain_007"
            if cli.include_probe else "thickness_eyelid_strain_007"
        ),
        "source_run": str(source_root),
        "source_indent_mm": cli.source_indent_mm,
        "target_indent_mm": cli.target_indent_mm,
        "target_result_time": target_time,
        "result": "EPEL,EQV equivalent Hencky strain; dimensionless",
        "scope": (
            "MAT=2 eyelid and MAT=3 probe solid elements"
            if cli.include_probe else "MAT=2 eyelid solid elements"
        ),
        "view": "actual-scale deformed central section matching standard view 007",
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "ansys_executable": str(ansys_bin),
        "ansys_version": ansys_version(ansys_bin),
        "workers": cli.workers,
        "np": cli.np,
        "started_at_utc": utc_now(),
        "macro_sha256": sha256(MACRO),
    }
    atomic_json(output_root / "metadata.json", metadata)
    rows: list[dict] = []
    manifest_path = output_root / "manifest.csv"
    write_manifest(manifest_path, rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                extract_view, source_root, output_root, source, cli.target_indent_mm,
                target_time, ansys_bin, cli.np, cli.timeout_seconds, git_commit,
                cli.include_probe,
            )
            for source in source_rows
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            write_manifest(manifest_path, rows)
            print(f"{row['case']}: {row['status']}", flush=True)
    work_root = output_root / ".work"
    if work_root.exists():
        work_root.rmdir()
    completed = sum(row["status"] == "complete" for row in rows)
    metadata.update({
        "ended_at_utc": utc_now(),
        "completed_cases": completed,
        "failed_cases": len(rows) - completed,
    })
    atomic_json(output_root / "metadata.json", metadata)
    print(f"completed={completed} failed={len(rows) - completed} root={output_root}")
    return 0 if completed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
