#!/usr/bin/env python3
"""Validate and summarize controlled-phantom thickness experiment data."""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = (
    "run_id", "assembly_id", "repeat_id", "eyelid_thickness_mm",
    "cornea_thickness_mm", "reference_iop_mmhg", "probe_advance_mm",
    "probe_force_n", "outer_area_mm2", "inner_area_mm2", "image_id_outer",
    "image_id_inner", "qc_status", "operator", "timestamp",
)
NUMERIC_COLUMNS = (
    "repeat_id", "eyelid_thickness_mm", "cornea_thickness_mm",
    "reference_iop_mmhg", "probe_advance_mm", "probe_force_n",
    "outer_area_mm2", "inner_area_mm2",
)
T_CRITICAL_95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571,
                 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262, 15: 2.145,
                 20: 2.086, 30: 2.042}
MEASURES = (
    "outer_area_mm2", "inner_area_mm2", "ae_over_ac", "ac_over_ae",
    "probe_force_n", "probe_pressure_mmhg", "pressure_error_mmhg",
)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def t_critical(n: int) -> float:
    if n < 2:
        return float("nan")
    for limit in sorted(T_CRITICAL_95):
        if n <= limit:
            return T_CRITICAL_95[limit]
    return 1.96


def read_valid_rows(raw_csv: Path) -> list[dict[str, object]]:
    with raw_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        fields = set(reader.fieldnames)
        missing = set(REQUIRED_COLUMNS) - fields
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        rows = [
            {key.strip(): value.strip() if isinstance(value, str) else value for key, value in row.items()}
            for row in reader
        ]
    run_ids = [row["run_id"] for row in rows]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("run_id must be unique.")

    valid: list[dict[str, object]] = []
    for row in rows:
        if row["qc_status"] not in {"pass", "fail"}:
            raise ValueError("qc_status must contain only pass or fail.")
        for column in NUMERIC_COLUMNS:
            row[column] = float(row[column])
        if row["qc_status"] != "pass":
            continue
        if any(float(row[column]) <= 0 for column in ("outer_area_mm2", "inner_area_mm2", "probe_force_n")):
            raise ValueError("Passing records require positive force and contact areas.")
        row["ae_over_ac"] = float(row["outer_area_mm2"]) / float(row["inner_area_mm2"])
        row["ac_over_ae"] = float(row["inner_area_mm2"]) / float(row["outer_area_mm2"])
        row["probe_pressure_mmhg"] = float(row["probe_force_n"]) / (float(row["outer_area_mm2"]) * 1e-6) / 133.322
        row["pressure_error_mmhg"] = float(row["probe_pressure_mmhg"]) - float(row["reference_iop_mmhg"])
        valid.append(row)
    if not valid:
        raise ValueError("No qc_status=pass records available.")
    return valid


def summarize(valid: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = ("eyelid_thickness_mm", "cornea_thickness_mm", "reference_iop_mmhg")
    per_assembly: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in valid:
        per_assembly[tuple(row[key] for key in keys) + (row["assembly_id"],)].append(row)

    assembly_rows: list[dict[str, object]] = []
    for identity, rows in per_assembly.items():
        item = dict(zip(keys + ("assembly_id",), identity))
        for measure in MEASURES:
            item[measure] = mean([float(row[measure]) for row in rows])
        assembly_rows.append(item)

    by_condition: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in assembly_rows:
        by_condition[tuple(row[key] for key in keys)].append(row)

    summary: list[dict[str, object]] = []
    for condition in sorted(by_condition):
        assemblies = by_condition[condition]
        item = dict(zip(keys, condition))
        item["n_assemblies"] = len(assemblies)
        item["n_measurements"] = sum(
            len(per_assembly[condition + (row["assembly_id"],)]) for row in assemblies
        )
        for measure in MEASURES:
            values = [float(row[measure]) for row in assemblies]
            center = mean(values)
            sem = math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1) / len(values)) if len(values) > 1 else float("nan")
            margin = t_critical(len(values)) * sem if len(values) > 1 else float("nan")
            item[f"{measure}_mean"] = center
            item[f"{measure}_ci95_low"] = center - margin
            item[f"{measure}_ci95_high"] = center + margin
        summary.append(item)
    return summary


def isotonic_increasing(values: list[float]) -> list[float]:
    blocks: list[list[float]] = []
    for value in values:
        blocks.append([value, 1.0])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            left, right = blocks[-2], blocks[-1]
            count = left[1] + right[1]
            blocks[-2:] = [[(left[0] * left[1] + right[0] * right[1]) / count, count]]
    return [value for value, count in blocks for _ in range(int(count))]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_svg(path: Path, points: list[dict[str, object]]) -> None:
    width, height, pad = 840, 500, 70
    xs = [float(point["eyelid_thickness_mm"]) for point in points]
    ys = [float(point["ae_over_ac_mean"]) for point in points]
    lo = [float(point["ae_over_ac_ci95_low"]) for point in points]
    hi = [float(point["ae_over_ac_ci95_high"]) for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(lo), max(hi)
    margin = max((ymax - ymin) * 0.1, 0.1)
    ymin, ymax = max(0.0, ymin - margin), ymax + margin
    sx = lambda value: pad + (value - xmin) / max(xmax - xmin, 1e-9) * (width - 2 * pad)
    sy = lambda value: height - pad - (value - ymin) / max(ymax - ymin, 1e-9) * (height - 2 * pad)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="black"/>',
        '<text x="420" y="28" text-anchor="middle" font-size="18">Ae/Ac thickness correction (0.55 mm cornea, 20 mmHg)</text>',
        '<text x="420" y="488" text-anchor="middle" font-size="14">Eyelid thickness (mm)</text>',
        '<text x="18" y="250" transform="rotate(-90 18 250)" text-anchor="middle" font-size="14">Ae/Ac</text>',
    ]
    for point in points:
        x, low, high = sx(float(point["eyelid_thickness_mm"])), sy(float(point["ae_over_ac_ci95_low"])), sy(float(point["ae_over_ac_ci95_high"]))
        lines.append(f'<line x1="{x:.1f}" y1="{low:.1f}" x2="{x:.1f}" y2="{high:.1f}" stroke="#2563eb"/>')
    lines.append('<polyline fill="none" stroke="#dc2626" stroke-width="2" points="' + " ".join(f'{sx(x):.1f},{sy(y):.1f}' for x, y in zip(xs, ys)) + '"/>')
    for x, y in zip(xs, ys):
        lines.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="#2563eb"/>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_outputs(valid: list[dict[str, object]], summary: list[dict[str, object]], output: Path, dataset_id: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    study = output.parents[2]
    write_csv(output / "valid_measurements.csv", valid)
    write_csv(output / "condition_summary.csv", summary)
    nominal = [row for row in summary if abs(float(row["cornea_thickness_mm"]) - 0.55) < 1e-9 and abs(float(row["reference_iop_mmhg"]) - 20.0) < 1e-9]
    nominal.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    figure_note = "未生成：缺少 0.55 mm 角膜、20 mmHg 的有效条件。"
    if nominal:
        correction = isotonic_increasing([float(row["ae_over_ac_mean"]) for row in nominal])
        for row, fitted in zip(nominal, correction):
            row["ae_over_ac_monotonic"] = fitted
        write_csv(output / "nominal_thickness_correction.csv", nominal)
        figures = study / "figures" / "experiment" / dataset_id
        figures.mkdir(parents=True, exist_ok=True)
        write_svg(figures / "ae_over_ac_correction.svg", nominal)
        figure_note = f"修正曲线：`../figures/experiment/{dataset_id}/ae_over_ac_correction.svg`。"
    report = study / "docs" / "真实仿体实验结果.md"
    report.write_text(
        "# 真实仿体厚度实验结果\n\n"
        f"数据集：`{dataset_id}`。本报告由 `thick/code/process_experiment.py` 自动生成。\n\n"
        f"有效记录：{len(valid)}；独立装配体：{len(set(str(row['assembly_id']) for row in valid))}。\n\n"
        f"正式条件汇总：`../data/processed/{dataset_id}/condition_summary.csv`。"
        "95% CI 基于独立装配体均值计算，技术重复先在装配体内汇总。占位参数扫描不参与本报告统计。\n\n"
        + figure_note + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_csv", type=Path)
    parser.add_argument("--dataset-id", required=True)
    args = parser.parse_args()
    study = Path(__file__).resolve().parents[1]
    valid = read_valid_rows(args.raw_csv)
    write_outputs(valid, summarize(valid), study / "data" / "processed" / args.dataset_id, args.dataset_id)


if __name__ == "__main__":
    main()
