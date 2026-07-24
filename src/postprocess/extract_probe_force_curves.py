#!/usr/bin/env python3
"""Extract probe force curves in parallel from completed MAPDL thickness cases."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MACRO = REPO_ROOT / "models" / "apdl" / "post_probe_force_curve.mac"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(source_root: Path) -> list[dict[str, str]]:
    path = source_root / "run_manifest.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("status") == "complete"]


def label(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def validate_curve(path: Path, expected_rows: int, expected_endpoint_force: float) -> None:
    rows: list[list[float]] = []
    with path.open(newline="", encoding="ascii") as handle:
        for raw in csv.reader(handle):
            values = [value.strip() for value in raw if value.strip()]
            if values:
                rows.append([float(value) for value in values])
    if len(rows) != expected_rows or any(len(row) != 6 for row in rows):
        raise ValueError(f"invalid curve dimensions: {len(rows)} rows")
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("curve contains a non-finite value")
    endpoint_force = abs(rows[-1][3])
    if not math.isclose(endpoint_force, expected_endpoint_force, rel_tol=2e-4, abs_tol=1e-6):
        raise ValueError(
            f"endpoint force mismatch: curve={endpoint_force}, manifest={expected_endpoint_force}"
        )


def extract_case(
    source_root: Path,
    output_root: Path,
    row: dict[str, str],
    ansys_bin: Path,
    intervals: int,
    np_count: int,
    timeout_seconds: float,
) -> dict[str, object]:
    case = row["case"]
    thickness = float(row["eyelid_thickness_mm"])
    source_attempt = source_root / row["attempt_dir"]
    source_db = source_attempt / f"{case}.db"
    source_rst = source_root / row["result_rst"]
    attempt = output_root / "attempts" / case
    if attempt.exists():
        shutil.rmtree(attempt)
    attempt.mkdir(parents=True)
    started = time.monotonic()
    result: dict[str, object] = {
        "case": case,
        "eyelid_thickness_mm": thickness,
        "status": "failed",
        "started_at_utc": utc_now(),
    }
    try:
        if not source_db.is_file() or not source_rst.is_file():
            raise FileNotFoundError("source DB or RST is missing")
        shutil.copy2(source_db, attempt / source_db.name)
        (attempt / source_rst.name).symlink_to(source_rst)
        shutil.copy2(MACRO, attempt / MACRO.name)
        driver = attempt / "driver.dat"
        driver.write_text(
            f"resume,{case},db\n"
            f"/filname,{case}\n"
            f"*use,{MACRO.name},{intervals},0.8e-3,0.05e-3\n",
            encoding="ascii",
        )
        command = [
            str(ansys_bin), "-b", "-np", str(np_count), "-dir", str(attempt),
            "-i", str(driver), "-o", str(attempt / "post.out"),
            "-j", f"force_{label(thickness)}",
        ]
        environment = os.environ.copy()
        environment.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
        completed = subprocess.run(
            command, cwd=attempt, env=environment, timeout=timeout_seconds, check=False,
        )
        output = (attempt / "post.out").read_text(errors="replace")
        if completed.returncode != 0 or "RUN COMPLETED" not in output.upper():
            raise RuntimeError(f"MAPDL failed with return code {completed.returncode}")
        if "*** ERROR ***" in output.upper():
            raise RuntimeError("MAPDL reported an error")
        curve = attempt / "probe_force_curve.csv"
        validate_curve(curve, intervals + 1, abs(float(row["probe_fy_n"])))
        destination = output_root / "raw" / f"eyelid_{label(thickness)}mm.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(curve, destination)
        result.update({
            "status": "complete",
            "curve_file": str(destination.relative_to(output_root)),
            "endpoint_force_n": abs(float(row["probe_fy_n"])),
            "returncode": completed.returncode,
        })
    except Exception as error:  # Preserve every case outcome in the run manifest.
        result["failure_reason"] = str(error)
    result.update({
        "ended_at_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    })
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--ansys-bin", type=Path, default=Path("/ansys_inc/v252/ansys/bin/ansys252"))
    parser.add_argument("--intervals", type=int, default=32)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--np", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.intervals < 2 or args.workers < 1 or args.np < 1:
        raise SystemExit("intervals, workers and np must be positive")
    cases = read_manifest(args.source_root)
    if not cases:
        raise SystemExit("source manifest has no complete cases")
    args.output_root.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                extract_case, args.source_root, args.output_root, row, args.ansys_bin,
                args.intervals, args.np, args.timeout_seconds,
            )
            for row in cases
        ]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    results.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    metadata = {
        "created_at_utc": utc_now(),
        "source_root": str(args.source_root),
        "source_manifest": "run_manifest.csv",
        "macro": str(MACRO.relative_to(REPO_ROOT)),
        "macro_sha256": sha256(MACRO),
        "intervals": args.intervals,
        "workers": args.workers,
        "np": args.np,
        "cases": results,
    }
    (args.output_root / "extraction_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    failed = [row for row in results if row["status"] != "complete"]
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
