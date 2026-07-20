#!/usr/bin/env python3
"""Re-extract thickness geometry from a retained MAPDL database/result pair."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

try:
    from .thickness_geometry import analyze_files, write_results
except ImportError:  # Direct script execution.
    from thickness_geometry import analyze_files, write_results


REPO_ROOT = Path(__file__).resolve().parents[2]
MACRO = REPO_ROOT / "models" / "apdl" / "post_thickness_geometry.mac"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt_dir", type=Path)
    parser.add_argument("--ansys-bin", type=Path, required=True)
    parser.add_argument("--np", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    cli = parser.parse_args()
    attempt = cli.attempt_dir.expanduser().resolve()
    job = attempt.parent.name
    for suffix in ("db", "rst"):
        if not (attempt / f"{job}.{suffix}").is_file():
            parser.error(f"missing retained {job}.{suffix} in {attempt}")
    shutil.copy2(MACRO, attempt / MACRO.name)
    driver = attempt / "thickness_geometry_driver.dat"
    driver.write_text(
        "finish\n"
        f"resume,{job},db\n"
        "/post1\n"
        f"file,{job},rst\n"
        f"*use,{MACRO.name}\n"
        "/exit,nosave\n",
        encoding="ascii",
    )
    output = attempt / "thickness_geometry_post.out"
    command = [
        str(cli.ansys_bin.expanduser().resolve()),
        "-b", "-np", str(cli.np), "-dir", str(attempt),
        "-i", str(driver), "-o", str(output), "-j", "thickness_geometry_post",
    ]
    env = os.environ.copy()
    env.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
    completed = subprocess.run(
        command,
        cwd=attempt,
        env=env,
        timeout=cli.timeout_seconds,
        check=False,
    )
    text = output.read_text(errors="replace") if output.exists() else ""
    if completed.returncode != 0 or "RUN COMPLETED" not in text.upper():
        raise RuntimeError(
            f"MAPDL postprocessing failed with return code {completed.returncode}; see {output}"
        )
    metrics = analyze_files(
        attempt / "inner_preload_faces.csv",
        attempt / "inner_final_faces.csv",
    )
    write_results(attempt, metrics)
    print(attempt / "thickness_geometry.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
