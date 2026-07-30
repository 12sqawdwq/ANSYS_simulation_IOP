#!/usr/bin/env python3
"""Extract one retained geometry-zero indentation state without resolving.

A lightweight MAPDL postprocessing run reads an existing DB/RST pair, exports
preload and selected-state face geometry, and extracts the complete probe force
history.  Python then computes the frozen Ae/Ac5 geometry at the result set
nearest the requested indentation.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.postprocess.thickness_geometry import (  # noqa: E402
    PROBE_AREA_M2,
    conservative_projected_support,
    read_faces,
    select_displacement_support,
    select_flat_surface,
)

PA_PER_MMHG = 133.32236842105263
FACE_MACRO = REPO_ROOT / "models" / "apdl" / "post_thickness_geometry.mac"
CURVE_MACRO = REPO_ROOT / "models" / "apdl" / "post_geometry_zero_probe_pressure_curve.mac"


def finite(value: str | float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(number):
        raise ValueError(f"non-finite {name}: {value!r}")
    return number


def close(left: float, right: float, tolerance: float = 1e-7) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def select_manifest_row(
    manifest: Path,
    thickness_mm: float,
    iop_mmhg: float,
    source_indent_mm: float,
) -> dict[str, str]:
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    matching = [
        row
        for row in rows
        if close(finite(row.get("eyelid_thickness_mm", "nan"), "thickness"), thickness_mm)
        and close(finite(row.get("iop_mmhg", "nan"), "IOP"), iop_mmhg)
        and close(finite(row.get("indent_mm", "nan"), "source indent"), source_indent_mm)
    ]
    if len(matching) != 1:
        raise ValueError(
            f"expected one t={thickness_mm:g}, IOP={iop_mmhg:g}, "
            f"d={source_indent_mm:g} row in "
            f"{manifest}; found {len(matching)}"
        )
    row = matching[0]
    if row.get("status") != "complete":
        raise ValueError(f"source row is not complete: {manifest}")
    for field in ("preload_converged", "approach_converged", "indentation_converged"):
        if finite(row.get(field, "nan"), field) < 0.5:
            raise ValueError(f"source row failed {field}: {manifest}")
    return row


def read_curve(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for line_number, values in enumerate(csv.reader(handle), 1):
            cleaned = [item.strip() for item in values if item.strip()]
            if not cleaned:
                continue
            if len(cleaned) != 7:
                raise ValueError(f"{path}:{line_number}: expected 7 values")
            parsed = [finite(item, f"curve column {index}") for index, item in enumerate(cleaned)]
            rows.append(
                dict(
                    target_indent_m=parsed[0],
                    actual_indent_m=parsed[1],
                    result_time=parsed[2],
                    result_load_step=parsed[3],
                    probe_fy_n=parsed[4],
                    probe_uy_min_m=parsed[5],
                    probe_uy_max_m=parsed[6],
                )
            )
    if not rows:
        raise ValueError(f"empty probe curve: {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--eyelid-thickness-mm", type=float, required=True)
    parser.add_argument("--iop-mmhg", type=float, required=True)
    parser.add_argument("--target-indent-mm", type=float, default=0.26)
    parser.add_argument("--source-indent-mm", type=float, default=0.28)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ansys-bin", type=Path, required=True)
    parser.add_argument("--np", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--max-indent-error-mm", type=float, default=0.001)
    args = parser.parse_args()
    if args.target_indent_mm <= 0 or args.np < 1 or args.timeout_seconds <= 0:
        parser.error("indent, np, and timeout must be positive")

    manifest = args.manifest.expanduser().resolve()
    row = select_manifest_row(
        manifest,
        args.eyelid_thickness_mm,
        args.iop_mmhg,
        args.source_indent_mm,
    )
    attempt = manifest.parent / row["attempt_dir"]
    job = Path(row["result_rst"]).stem
    source_db = attempt / f"{job}.db"
    source_rst = attempt / f"{job}.rst"
    for source in (source_db, source_rst, FACE_MACRO, CURVE_MACRO):
        if not source.is_file():
            raise FileNotFoundError(source)

    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    for source in (source_db, source_rst):
        link = output / source.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(source)
    shutil.copy2(FACE_MACRO, output / FACE_MACRO.name)
    shutil.copy2(CURVE_MACRO, output / CURVE_MACRO.name)

    source_indent_m = finite(row["indent_mm"], "source indent") * 1e-3
    approach_push_m = finite(row["approach_push_m"], "approach push")
    requested_indent_m = args.target_indent_mm * 1e-3
    target_time = 2.0 + requested_indent_m / source_indent_m
    driver = output / "geometry_state_driver.dat"
    driver.write_text(
        "finish\n"
        f"resume,{job},db\n"
        "/post1\n"
        f"file,{job},rst\n"
        f"*use,{CURVE_MACRO.name},{source_indent_m:.16g},{approach_push_m:.16g}\n"
        "/post1\n"
        f"file,{job},rst\n"
        f"*use,{FACE_MACRO.name},{target_time:.16g}\n"
        "/exit,nosave\n",
        encoding="ascii",
    )
    solve_output = output / "geometry_state_post.out"
    command = [
        str(args.ansys_bin.expanduser().resolve()),
        "-b",
        "-np",
        str(args.np),
        "-dir",
        str(output),
        "-i",
        str(driver),
        "-o",
        str(solve_output),
        "-j",
        "geometry_state_post",
    ]
    environment = os.environ.copy()
    environment.update({"ANSYSLMD_LICENSE_FILE": "1055@localhost", "ANSYS_LOCK": "OFF"})
    completed = subprocess.run(
        command,
        cwd=output,
        env=environment,
        timeout=args.timeout_seconds,
        check=False,
    )
    text = solve_output.read_text(errors="replace") if solve_output.exists() else ""
    if completed.returncode != 0 or "RUN COMPLETED" not in text.upper():
        raise RuntimeError(
            f"MAPDL postprocessing failed rc={completed.returncode}; see {solve_output}"
        )

    curve = read_curve(output / "probe_pressure_curve.csv")
    selected_curve = min(curve, key=lambda item: abs(item["actual_indent_m"] - requested_indent_m))
    actual_indent_mm = selected_curve["actual_indent_m"] * 1e3
    indent_error_mm = actual_indent_mm - args.target_indent_mm
    if abs(indent_error_mm) > args.max_indent_error_mm:
        raise ValueError(
            f"nearest result indent {actual_indent_mm:g} mm is too far from "
            f"target {args.target_indent_mm:g} mm"
        )

    outer_preload = read_faces(output / "outer_preload_faces.csv")
    outer_final = read_faces(output / "outer_final_faces.csv")
    inner_preload = read_faces(output / "inner_preload_faces.csv")
    inner_final = read_faces(output / "inner_final_faces.csv")
    _, outer_selected = select_displacement_support(outer_preload, outer_final)
    ae_lower, ae_clipped, strict, boundary = conservative_projected_support(
        outer_final, outer_selected
    )
    inner5, _ = select_flat_surface(inner_preload, inner_final, angle_limit_deg=5.0)
    force = abs(selected_curve["probe_fy_n"])
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "case": row["case"],
        "eyelid_thickness_mm": args.eyelid_thickness_mm,
        "iop_mmhg": args.iop_mmhg,
        "requested_indent_mm": args.target_indent_mm,
        "actual_indent_mm": actual_indent_mm,
        "indent_error_mm": indent_error_mm,
        "result_time": selected_curve["result_time"],
        "result_load_step": selected_curve["result_load_step"],
        "probe_force_n": force,
        "probe_pressure_mmhg": force / (PROBE_AREA_M2 * PA_PER_MMHG),
        "outer_ae_lower_mm2": ae_lower * 1e6,
        "outer_ae_clipped_mm2": ae_clipped * 1e6,
        "outer_strict_faces": len(strict),
        "outer_boundary_faces": len(boundary),
        "inner_ac_5deg_mm2": inner5.projected_area * 1e6,
        "inner_5deg_faces": inner5.face_count,
        "kgeo_5deg": ae_lower / inner5.projected_area,
        "source_manifest": str(manifest),
        "source_attempt": str(attempt),
        "source_rst": str(source_rst),
        "source_git_commit": row.get("git_commit", ""),
        "mapdl_returncode": completed.returncode,
    }
    (output / "geometry_state.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "geometry_state.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=result.keys())
        writer.writeheader()
        writer.writerow(result)
    print(output / "geometry_state.json")
    print(
        f"t={args.eyelid_thickness_mm:.2f} IOP={args.iop_mmhg:g} "
        f"requested={args.target_indent_mm:.6f} actual={actual_indent_mm:.6f} "
        f"F={force:.9f} Ae={ae_lower*1e6:.6f} "
        f"Ac5={inner5.projected_area*1e6:.6f} K={ae_lower/inner5.projected_area:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
