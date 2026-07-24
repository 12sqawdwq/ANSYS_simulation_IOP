#!/usr/bin/env python3
"""Re-zero indentation at stable first contact and export existing result states."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.runners.run_indentation_sweep import RAW_METRIC_FIELDS, parse_numeric_csv


MODEL_DIR = REPO_ROOT / "models" / "apdl"
HISTORY_MACRO = MODEL_DIR / "post_contact_history.mac"
STATE_MACROS = (
    MODEL_DIR / "post_sweep.mac",
    MODEL_DIR / "post_thickness_geometry.mac",
)
HISTORY_FIELDS = (
    "total_push_m",
    "result_time",
    "result_load_step",
    "probe_fy_n",
    "probe_uy_min_m",
    "probe_uy_max_m",
    "loaded_contact_count",
    "loaded_contact_area_m2",
    "pmax_pa",
)
CONTACT_FIELDS = (
    "source_case",
    "eyelid_thickness_mm",
    "source_total_push_mm",
    "force_baseline_n",
    "force_threshold_n",
    "stable_points",
    "contact_zero_total_push_mm",
    "contact_zero_result_time",
    "contact_zero_bracket_low_mm",
    "contact_zero_bracket_high_mm",
    "history_step_mm",
    "fixed_gap_zero_mm",
    "zero_shift_from_fixed_gap_mm",
)
STATE_FIELDS = (
    "case",
    "profile",
    "status",
    "failure_reason",
    "attempt_dir",
    "source_case",
    "eyelid_thickness_mm",
    "cornea_thickness_mm",
    "mesh_size_mm",
    "iop_mmhg",
    "eyelid_material_scale",
    "cornea_material_scale",
    "indent_mm",
    "effective_indent_mm",
    "contact_zero_total_push_mm",
    "zero_shift_from_fixed_gap_mm",
    "target_total_push_mm",
    "old_fixed_gap_indent_mm",
    "target_result_time",
    *RAW_METRIC_FIELDS,
)


@dataclass(frozen=True)
class ContactZero:
    push_m: float
    result_time: float
    bracket_low_m: float
    bracket_high_m: float
    baseline_force_n: float
    threshold_force_n: float
    history_step_m: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def label(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def read_manifest(root: Path) -> list[dict[str, str]]:
    with (root / "run_manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("status") == "complete"]
    if not rows:
        raise ValueError("source manifest has no complete cases")
    return rows


def read_history(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="ascii") as handle:
        for number, raw in enumerate(csv.reader(handle), 1):
            values = [value.strip() for value in raw if value.strip()]
            if not values:
                continue
            if len(values) != len(HISTORY_FIELDS):
                raise ValueError(
                    f"{path}:{number}: expected {len(HISTORY_FIELDS)} values, got {len(values)}"
                )
            row = dict(zip(HISTORY_FIELDS, map(float, values)))
            if not all(math.isfinite(value) for value in row.values()):
                raise ValueError(f"{path}:{number}: non-finite history value")
            rows.append(row)
    if len(rows) < 10:
        raise ValueError(f"too few contact-history points: {len(rows)}")
    return rows


def detect_contact_zero(
    rows: list[dict[str, float]],
    force_threshold_n: float = 1e-3,
    stable_points: int = 3,
) -> ContactZero:
    if force_threshold_n <= 0 or stable_points < 1:
        raise ValueError("contact threshold and stable-point count must be positive")
    baseline = median(abs(row["probe_fy_n"]) for row in rows[:3])
    force_signal = [max(0.0, abs(row["probe_fy_n"]) - baseline) for row in rows]
    active = [
        force >= force_threshold_n
        and row["loaded_contact_count"] >= 1
        and row["loaded_contact_area_m2"] > 0
        and row["pmax_pa"] > 1.0
        for row, force in zip(rows, force_signal)
    ]
    first = None
    for index in range(0, len(rows) - stable_points + 1):
        if all(active[index:index + stable_points]):
            first = index
            break
    if first is None:
        raise ValueError("no stable first-contact point found")
    previous = max(0, first - 1)
    low = rows[previous]
    high = rows[first]
    low_force = force_signal[previous]
    high_force = force_signal[first]
    if first > 0 and high_force > low_force:
        fraction = min(
            1.0,
            max(0.0, (force_threshold_n - low_force) / (high_force - low_force)),
        )
        push = low["total_push_m"] + fraction * (
            high["total_push_m"] - low["total_push_m"]
        )
    else:
        push = high["total_push_m"]
    source_push = rows[-1]["total_push_m"]
    result_time = 1.0 + push / source_push
    steps = [
        rows[index + 1]["total_push_m"] - rows[index]["total_push_m"]
        for index in range(len(rows) - 1)
    ]
    return ContactZero(
        push_m=push,
        result_time=result_time,
        bracket_low_m=low["total_push_m"],
        bracket_high_m=high["total_push_m"],
        baseline_force_n=baseline,
        threshold_force_n=force_threshold_n,
        history_step_m=median(steps),
    )


def result_time_for_effective_indent(
    contact_push_m: float,
    effective_indent_mm: float,
    source_push_m: float,
) -> tuple[float, float]:
    target_push = contact_push_m + effective_indent_mm / 1000.0
    if target_push < 0 or target_push > source_push_m + 1e-12:
        raise ValueError(
            f"target push {target_push * 1e3:.4f} mm exceeds source path "
            f"0-{source_push_m * 1e3:.4f} mm"
        )
    return target_push, 1.0 + target_push / source_push_m


def _source_files(source_root: Path, row: dict[str, str]) -> tuple[Path, Path]:
    attempt = source_root / row["attempt_dir"]
    case = row["case"]
    return attempt / f"{case}.db", source_root / row["result_rst"]


def _prepare_attempt(
    attempt: Path,
    source_db: Path,
    source_rst: Path,
    macros: tuple[Path, ...],
) -> None:
    if attempt.exists():
        shutil.rmtree(attempt)
    attempt.mkdir(parents=True)
    if not source_db.is_file() or not source_rst.is_file():
        raise FileNotFoundError("source DB or RST is missing")
    shutil.copy2(source_db, attempt / source_db.name)
    (attempt / source_rst.name).symlink_to(source_rst)
    for macro in macros:
        shutil.copy2(macro, attempt / macro.name)


def _run_mapdl(
    attempt: Path,
    driver: Path,
    ansys_bin: Path,
    np_count: int,
    timeout_seconds: float,
    job_name: str,
) -> None:
    command = [
        str(ansys_bin), "-b", "-np", str(np_count), "-dir", str(attempt),
        "-i", str(driver), "-o", str(attempt / "post.out"), "-j", job_name,
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


def _remove_solver_sources(attempt: Path) -> None:
    for pattern in ("*.db", "*.rst"):
        for path in attempt.glob(pattern):
            path.unlink(missing_ok=True)


def extract_history(
    source_root: Path,
    output_root: Path,
    row: dict[str, str],
    ansys_bin: Path,
    intervals: int,
    np_count: int,
    timeout_seconds: float,
    force_threshold_n: float,
    stable_points: int,
) -> tuple[dict[str, str], ContactZero]:
    case = row["case"]
    source_db, source_rst = _source_files(source_root, row)
    attempt = output_root / "contact_history" / case
    _prepare_attempt(attempt, source_db, source_rst, (HISTORY_MACRO,))
    source_push = float(row["commanded_push_m"])
    driver = attempt / "driver.dat"
    driver.write_text(
        f"resume,{case},db\n/filname,{case}\n"
        f"*use,{HISTORY_MACRO.name},{intervals},{source_push:.14g}\n",
        encoding="ascii",
    )
    _run_mapdl(
        attempt, driver, ansys_bin, np_count, timeout_seconds,
        f"zero_{label(float(row['eyelid_thickness_mm']))}",
    )
    curve = attempt / "contact_history.csv"
    rows = read_history(curve)
    if len(rows) != intervals + 1:
        raise ValueError(f"expected {intervals + 1} history points, got {len(rows)}")
    contact = detect_contact_zero(rows, force_threshold_n, stable_points)
    _remove_solver_sources(attempt)
    return row, contact


def extract_state(
    source_root: Path,
    target_root: Path,
    source: dict[str, str],
    contact: ContactZero,
    effective_indent_mm: float,
    ansys_bin: Path,
    np_count: int,
    timeout_seconds: float,
) -> dict[str, str | float]:
    thickness = float(source["eyelid_thickness_mm"])
    source_push = float(source["commanded_push_m"])
    target_push, target_time = result_time_for_effective_indent(
        contact.push_m, effective_indent_mm, source_push
    )
    case = (
        f"eyelid_{label(thickness)}mm_effective_indent_"
        f"{label(effective_indent_mm)}mm"
    )
    attempt = target_root / case / "attempt_1"
    source_db, source_rst = _source_files(source_root, source)
    started = time.monotonic()
    row: dict[str, str | float] = {
        "case": case,
        "profile": "contact_rezeroed_state",
        "status": "failed",
        "failure_reason": "",
        "attempt_dir": str(attempt.relative_to(target_root)),
        "source_case": source["case"],
        "eyelid_thickness_mm": thickness,
        "cornea_thickness_mm": float(source["cornea_thickness_mm"]),
        "mesh_size_mm": float(source["mesh_size_mm"]),
        "iop_mmhg": float(source.get("iop_mmhg") or 20.0),
        "eyelid_material_scale": float(source.get("eyelid_material_scale") or 1.0),
        "cornea_material_scale": float(source.get("cornea_material_scale") or 1.0),
        "indent_mm": effective_indent_mm,
        "effective_indent_mm": effective_indent_mm,
        "contact_zero_total_push_mm": contact.push_m * 1e3,
        "zero_shift_from_fixed_gap_mm": (0.05e-3 - contact.push_m) * 1e3,
        "target_total_push_mm": target_push * 1e3,
        "old_fixed_gap_indent_mm": (target_push - 0.05e-3) * 1e3,
        "target_result_time": target_time,
    }
    try:
        _prepare_attempt(attempt, source_db, source_rst, STATE_MACROS)
        driver = attempt / "driver.dat"
        driver.write_text(
            f"resume,{source['case']},db\n/filname,{source['case']}\n"
            f"*use,post_sweep.mac,{target_time:.14g}\n"
            f"*use,post_thickness_geometry.mac,{target_time:.14g}\n",
            encoding="ascii",
        )
        _run_mapdl(
            attempt, driver, ansys_bin, np_count, timeout_seconds,
            f"state_{label(thickness)}_{label(effective_indent_mm)}",
        )
        metrics = dict(zip(
            RAW_METRIC_FIELDS,
            parse_numeric_csv(attempt / "metrics.csv", len(RAW_METRIC_FIELDS)),
        ))
        if not math.isclose(metrics["result_time"], target_time, abs_tol=1e-6):
            raise ValueError("MAPDL did not select the requested result time")
        if not math.isclose(metrics["probe_uy_m"], -target_push, abs_tol=2e-7):
            raise ValueError("probe displacement does not match the re-zeroed target")
        row.update(metrics)
        row["status"] = "complete"
        _remove_solver_sources(attempt)
    except Exception as error:
        row["failure_reason"] = str(error)
    row["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return row


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def parse_indents(value: str) -> tuple[float, ...]:
    parsed = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not parsed or any(item <= 0 for item in parsed):
        raise argparse.ArgumentTypeError("effective indents must be positive")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--effective-indents", type=parse_indents, default=(0.26, 0.28))
    parser.add_argument("--history-intervals", type=int, default=132)
    parser.add_argument("--force-threshold-n", type=float, default=1e-3)
    parser.add_argument("--stable-points", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--np", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=1800)
    parser.add_argument(
        "--ansys-bin", type=Path,
        default=Path("/ansys_inc/v252/ansys/bin/ansys252"),
    )
    return parser.parse_args()


def main() -> int:
    cli = parse_args()
    if cli.history_intervals < 20 or cli.workers < 1 or cli.np < 1:
        raise SystemExit("invalid history interval, worker or core count")
    source_rows = read_manifest(cli.source_root)
    cli.output_root.mkdir(parents=True, exist_ok=True)

    contacts: list[tuple[dict[str, str], ContactZero]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        futures = [
            pool.submit(
                extract_history, cli.source_root, cli.output_root, row, cli.ansys_bin,
                cli.history_intervals, cli.np, cli.timeout_seconds,
                cli.force_threshold_n, cli.stable_points,
            )
            for row in source_rows
        ]
        for future in concurrent.futures.as_completed(futures):
            contacts.append(future.result())
    contacts.sort(key=lambda item: float(item[0]["eyelid_thickness_mm"]))

    contact_rows = []
    for source, contact in contacts:
        contact_rows.append({
            "source_case": source["case"],
            "eyelid_thickness_mm": float(source["eyelid_thickness_mm"]),
            "source_total_push_mm": float(source["commanded_push_m"]) * 1e3,
            "force_baseline_n": contact.baseline_force_n,
            "force_threshold_n": contact.threshold_force_n,
            "stable_points": cli.stable_points,
            "contact_zero_total_push_mm": contact.push_m * 1e3,
            "contact_zero_result_time": contact.result_time,
            "contact_zero_bracket_low_mm": contact.bracket_low_m * 1e3,
            "contact_zero_bracket_high_mm": contact.bracket_high_m * 1e3,
            "history_step_mm": contact.history_step_m * 1e3,
            "fixed_gap_zero_mm": 0.05,
            "zero_shift_from_fixed_gap_mm": (0.05e-3 - contact.push_m) * 1e3,
        })
    write_csv(cli.output_root / "contact_zero.csv", CONTACT_FIELDS, contact_rows)

    all_states: dict[float, list[dict[str, str | float]]] = {
        indent: [] for indent in cli.effective_indents
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        future_map = {}
        for source, contact in contacts:
            for indent in cli.effective_indents:
                target_root = cli.output_root / f"effective_{label(indent)}"
                future = pool.submit(
                    extract_state, cli.source_root, target_root, source, contact,
                    indent, cli.ansys_bin, cli.np, cli.timeout_seconds,
                )
                future_map[future] = indent
        for future in concurrent.futures.as_completed(future_map):
            all_states[future_map[future]].append(future.result())

    failures = []
    for indent, rows in all_states.items():
        rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
        target_root = cli.output_root / f"effective_{label(indent)}"
        write_csv(target_root / "run_manifest.csv", STATE_FIELDS, rows)
        failures.extend(row for row in rows if row["status"] != "complete")
    metadata = {
        "created_at_utc": utc_now(),
        "source_root": str(cli.source_root),
        "effective_indents_mm": cli.effective_indents,
        "history_intervals": cli.history_intervals,
        "force_threshold_n": cli.force_threshold_n,
        "stable_points": cli.stable_points,
        "workers": cli.workers,
        "np": cli.np,
        "complete_states": sum(
            row["status"] == "complete" for rows in all_states.values() for row in rows
        ),
        "failed_states": len(failures),
    }
    (cli.output_root / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
