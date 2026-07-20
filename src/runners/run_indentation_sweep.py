#!/usr/bin/env python3
"""Run a 4-offset by 9-indentation MAPDL sweep with per-case diagnostics."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "models" / "apdl"
OFFSETS_MM = (0.0, 0.5, 1.0, 2.0)
INDENTS_MM = tuple(i / 4 for i in range(9))


def label(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


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


def run_case(args: tuple[Path, float, float, int, Path]) -> dict[str, str]:
    run_root, offset, indent, np, ansys_bin = args
    name = f"offset_{label(offset)}mm_indent_{label(indent)}mm"
    case_dir = run_root / name
    case_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("param_eye_sweep.mac", "post_sweep.mac", "plot_sweep_views.mac"):
        shutil.copy2(MODEL_DIR / filename, case_dir / filename)
    driver = case_dir / "driver.dat"
    driver.write_text(
        f"xoff={offset / 1000:.9g}\nindent={indent / 1000:.9g}\n"
        "*use,param_eye_sweep.mac,xoff,indent\n"
        f"resume,{name},db\n"
        f"/filname,{name}\n"
        "*use,post_sweep.mac\n"
        "*use,plot_sweep_views.mac\n",
        encoding="ascii",
    )
    command = [
        str(ansys_bin), "-b", "-np", str(np),
        "-dir", str(case_dir), "-i", str(driver), "-o", str(case_dir / "solve.out"),
        "-j", name,
    ]
    env = os.environ.copy()
    env.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
    completed = subprocess.run(command, cwd=case_dir, env=env, capture_output=True, text=True)
    output = (case_dir / "solve.out").read_text(errors="replace") if (case_dir / "solve.out").exists() else completed.stderr
    status = "complete" if completed.returncode == 0 and "RUN COMPLETED" in output else "failed"
    metrics = (case_dir / "metrics.csv").read_text().strip() if (case_dir / "metrics.csv").exists() else ""
    return {"case": name, "offset_mm": str(offset), "indent_mm": str(indent), "status": status,
            "returncode": str(completed.returncode), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=Path(os.environ.get("BLUEKNOW_RUN_ROOT", "/home/xuanyu/PROJECT/ziyu/blueknow-data/indentation_sweep")))
    parser.add_argument("--workers", type=int, default=4,
                        help="parallel MAPDL cases; 4 workers x 4 MPI ranks uses 16 physical cores on 5090d")
    parser.add_argument("--np", type=int, default=4)
    parser.add_argument("--offsets", type=float, nargs="+", default=OFFSETS_MM)
    parser.add_argument("--indents", type=float, nargs="+", default=INDENTS_MM)
    parser.add_argument("--ansys-bin", type=Path, default=os.environ.get("ANSYS_BIN"))
    parser.add_argument("--allow-dirty", action="store_true",
                        help="allow an uncommitted worktree for debugging; never use for formal results")
    cli = parser.parse_args()
    git_commit, git_dirty = git_provenance()
    if git_dirty and not cli.allow_dirty:
        parser.error("formal runs require a clean Git worktree; commit changes or use --allow-dirty for debugging")
    ansys_bin = find_ansys_binary(cli.ansys_bin)
    cli.run_root.mkdir(parents=True, exist_ok=True)
    jobs = [(cli.run_root, o, d, cli.np, ansys_bin) for o in cli.offsets for d in cli.indents]
    with concurrent.futures.ThreadPoolExecutor(max_workers=cli.workers) as pool:
        rows = list(pool.map(run_case, jobs))
    for row in rows:
        row["git_commit"] = git_commit
        row["git_dirty"] = str(git_dirty).lower()
    with (cli.run_root / "run_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    failed = [row["case"] for row in rows if row["status"] != "complete"]
    print(f"completed={len(rows) - len(failed)} failed={len(failed)} root={cli.run_root}")
    if failed:
        print("failed_cases=" + ",".join(failed))


if __name__ == "__main__":
    main()
