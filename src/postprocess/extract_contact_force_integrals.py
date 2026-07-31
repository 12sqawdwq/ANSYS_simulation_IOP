#!/usr/bin/env python3
"""Read one retained DB/RST pair and integrate contact-force vectors without resolving."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[2]
MACRO = REPO_ROOT / "models" / "apdl" / "post_contact_force_integrals.mac"
FIELDS_A = (
    "result_time",
    "result_load_step",
    "probe_node_count",
    "probe_rf_x_n",
    "probe_rf_y_n",
    "probe_rf_z_n",
    "outer_contact_count",
    "outer_closed_count",
    "outer_cnf_x_n",
    "outer_cnf_y_n",
    "outer_cnf_z_n",
    "outer_cnt_x_n",
    "outer_cnt_y_n",
    "outer_cnt_z_n",
    "outer_contact_area_m2",
)
FIELDS_B = (
    "inner_contact_count",
    "inner_closed_count",
    "inner_cnf_x_n",
    "inner_cnf_y_n",
    "inner_cnf_z_n",
    "inner_cnt_x_n",
    "inner_cnt_y_n",
    "inner_cnt_z_n",
    "inner_contact_area_m2",
    "support_node_count",
    "support_rf_x_n",
    "support_rf_y_n",
    "support_rf_z_n",
)
COUNT_FIELDS = {
    "probe_node_count",
    "outer_contact_count",
    "outer_closed_count",
    "inner_contact_count",
    "inner_closed_count",
    "support_node_count",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {name}: {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"non-finite {name}: {value!r}")
    return result


def parse_integral_file(path: Path, fields: tuple[str, ...]) -> dict[str, float | int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [[item.strip() for item in row if item.strip()] for row in csv.reader(handle)]
    rows = [row for row in rows if row]
    if len(rows) != 1 or len(rows[0]) != len(fields):
        raise ValueError(f"expected one {len(fields)}-column row in {path}; found {rows}")
    output: dict[str, float | int] = {}
    for name, raw in zip(fields, rows[0]):
        value = finite(raw, name)
        output[name] = int(round(value)) if name in COUNT_FIELDS else value
    return output


def parse_integrals(output: Path) -> dict[str, float | int]:
    values = parse_integral_file(output / "contact_force_integrals_a.csv", FIELDS_A)
    values.update(parse_integral_file(output / "contact_force_integrals_b.csv", FIELDS_B))
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ansys-bin", type=Path, required=True)
    parser.add_argument("--np", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--maximum-probe-force-relative-error", type=float, default=0.01)
    args = parser.parse_args()
    state_path = args.state_json.expanduser().resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    source_rst = Path(state["source_rst"]).resolve()
    source_attempt = Path(state["source_attempt"]).resolve()
    job = source_rst.stem
    source_db = source_attempt / f"{job}.db"
    for path in (source_db, source_rst, MACRO, args.ansys_bin.expanduser().resolve()):
        if not path.exists():
            raise FileNotFoundError(path)
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    for source, suffix in ((source_db, ".db"), (source_rst, ".rst")):
        link = output / f"job{suffix}"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(source)
    shutil.copy2(MACRO, output / MACRO.name)
    target_time = finite(state["result_time"], "result time")
    driver = output / "driver.dat"
    driver.write_text(
        "finish\n"
        "resume,job,db\n"
        "/post1\n"
        "file,job,rst\n"
        f"*use,{MACRO.name},{target_time:.16g}\n"
        "/exit,nosave\n",
        encoding="ascii",
    )
    solve_output = output / "post.out"
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
        "contact_force_post",
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
    error_count = len(re.findall(r"\*\*\* ERROR \*\*\*", text, flags=re.IGNORECASE))
    if "RUN COMPLETED" not in text.upper() or error_count:
        raise RuntimeError(
            f"MAPDL postprocessing failed rc={completed.returncode}, errors={error_count}; see {solve_output}"
        )
    values = parse_integrals(output)
    probe = abs(float(values["probe_rf_y_n"]))
    outer = abs(float(values["outer_cnf_y_n"]))
    relative_error = abs(outer - probe) / probe
    if relative_error > args.maximum_probe_force_relative_error:
        raise ValueError(
            f"probe contact/reaction mismatch {relative_error:.6%} exceeds "
            f"{args.maximum_probe_force_relative_error:.6%}"
        )
    for prefix in ("outer", "inner"):
        for axis in "xyz":
            values[f"{prefix}_normal_{axis}_n"] = (
                float(values[f"{prefix}_cnf_{axis}_n"])
                - float(values[f"{prefix}_cnt_{axis}_n"])
            )
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "iop_mmhg": finite(state["iop_mmhg"], "IOP"),
        "actual_indent_mm": finite(state["actual_indent_mm"], "actual indent"),
        "state_json": str(state_path),
        "source_db": str(source_db),
        "source_rst": str(source_rst),
        "source_git_commit": state.get("source_git_commit", ""),
        "macro_sha256": sha256(MACRO),
        "mapdl_returncode": completed.returncode,
        "mapdl_error_count": error_count,
        "probe_contact_reaction_relative_error": relative_error,
        **values,
    }
    (output / "contact_force_integrals.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "contact_force_integrals_with_header.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result), lineterminator="\n")
        writer.writeheader()
        writer.writerow(result)
    print(output / "contact_force_integrals.json")
    print(
        f"IOP={result['iop_mmhg']:g} Fprobe={probe:.9f} "
        f"Fouter={outer:.9f} Finner={abs(float(values['inner_cnf_y_n'])):.9f} "
        f"outer_error={relative_error:.6%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
