#!/usr/bin/env python3
"""Summarize contact-rezeroed area states and render their thickness trends."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


PROBE_AREA_MM2 = math.pi * 2.16**2
FIELDS = (
    "effective_indent_mm",
    "eyelid_thickness_mm",
    "contact_zero_total_push_mm",
    "preload_force_n",
    "preload_contact_area_mm2",
    "target_total_push_mm",
    "old_fixed_gap_indent_mm",
    "probe_force_n",
    "outer_contact_area_mm2",
    "outer_contact_coverage_fraction",
    "outer_conservative_area_mm2",
    "outer_conservative_coverage_fraction",
    "inner_pressure_participation_area_mm2",
    "hybrid_ae_over_ac",
    "outer_pressure_effective_area_mm2",
    "inner_pressure_effective_area_mm2",
    "pressure_effective_ratio",
    "status",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def keyed(rows: list[dict[str, str]], field: str) -> dict[float, dict[str, str]]:
    return {float(row[field]): row for row in rows}


def collect(root: Path) -> list[dict[str, float | str]]:
    zeros = keyed(read_csv(root / "contact_zero.csv"), "eyelid_thickness_mm")
    output: list[dict[str, float | str]] = []
    for state_root in sorted(root.glob("effective_*")):
        if not (state_root / "run_manifest.csv").is_file():
            continue
        states = keyed(read_csv(state_root / "run_manifest.csv"), "eyelid_thickness_mm")
        displacement = keyed(read_csv(
            state_root / "analysis" / "displacement_support" /
            "displacement_support_manifest.csv"
        ), "eyelid_thickness_mm")
        mechanical = keyed(read_csv(
            state_root / "analysis" / "mechanical_area" /
            "mechanical_area_comparison.csv"
        ), "eyelid_thickness_mm")
        for thickness in sorted(states):
            state = states[thickness]
            area = displacement[thickness]
            pressure = mechanical[thickness]
            zero = zeros[thickness]
            outer_contact = float(state["contact_area_m2"]) * 1e6
            outer_conservative = float(area["outer_conservative_area_mm2"])
            inner_pressure = float(area["inner_pressure_participation_area_mm2"])
            output.append({
                "effective_indent_mm": float(state["effective_indent_mm"]),
                "eyelid_thickness_mm": thickness,
                "contact_zero_total_push_mm": float(zero["contact_zero_total_push_mm"]),
                "preload_force_n": float(zero["preload_force_n"]),
                "preload_contact_area_mm2": float(zero["preload_contact_area_mm2"]),
                "target_total_push_mm": float(state["target_total_push_mm"]),
                "old_fixed_gap_indent_mm": float(state["old_fixed_gap_indent_mm"]),
                "probe_force_n": abs(float(state["probe_fy_n"])),
                "outer_contact_area_mm2": outer_contact,
                "outer_contact_coverage_fraction": outer_contact / PROBE_AREA_MM2,
                "outer_conservative_area_mm2": outer_conservative,
                "outer_conservative_coverage_fraction": outer_conservative / PROBE_AREA_MM2,
                "inner_pressure_participation_area_mm2": inner_pressure,
                "hybrid_ae_over_ac": outer_conservative / inner_pressure,
                "outer_pressure_effective_area_mm2": float(
                    pressure["outer_pressure_effective_area_mm2"]
                ),
                "inner_pressure_effective_area_mm2": float(
                    pressure["inner_pressure_effective_area_mm2"]
                ),
                "pressure_effective_ratio": float(pressure["pressure_effective_ratio"]),
                "status": "contact_rezeroed_candidate_not_approved",
            })
    if not output:
        raise ValueError("no re-zeroed analysis outputs found")
    output.sort(key=lambda row: (
        float(row["effective_indent_mm"]),
        float(row["eyelid_thickness_mm"]),
    ))
    return output


def write_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({field: row[field] for field in FIELDS} for row in rows)


def plot(path: Path, rows: list[dict[str, float | str]]) -> None:
    indents = sorted({float(row["effective_indent_mm"]) for row in rows})
    colors = {indents[0]: "#2667A8", indents[-1]: "#D34A3A"}
    figure, axes = plt.subplots(1, 3, figsize=(15.0, 5.1))
    for indent in indents:
        selected = [row for row in rows if float(row["effective_indent_mm"]) == indent]
        x = [float(row["eyelid_thickness_mm"]) for row in selected]
        color = colors[indent]
        label = f"effective {indent:.2f} mm"
        axes[0].plot(
            x,
            [100 * float(row["outer_conservative_coverage_fraction"]) for row in selected],
            marker="o", color=color, linewidth=2, label=f"Ae coverage, {indent:.2f}",
        )
        axes[0].plot(
            x,
            [100 * float(row["outer_contact_coverage_fraction"]) for row in selected],
            marker="s", color=color, linewidth=1.6, linestyle="--",
            label=f"contact coverage, {indent:.2f}",
        )
        axes[1].plot(
            x,
            [float(row["hybrid_ae_over_ac"]) for row in selected],
            marker="o", color=color, linewidth=2, label=label,
        )
        axes[2].plot(
            x,
            [float(row["pressure_effective_ratio"]) for row in selected],
            marker="o", color=color, linewidth=2, label=label,
        )

    axes[0].set_title("Outer area coverage")
    axes[0].set_ylabel("Coverage of probe area (%)")
    axes[0].set_ylim(20, 100)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].set_title("Candidate area ratio")
    axes[1].set_ylabel("K(L/P) = outer displacement / inner pressure")
    axes[1].legend(frameon=False, fontsize=8)
    axes[2].set_title("Pressure-area diagnostic")
    axes[2].set_ylabel("K(P/P) = outer pressure / inner pressure")
    axes[2].legend(frameon=False, fontsize=8)
    for axis in axes:
        axis.set_xlabel("Eyelid thickness (mm)")
        axis.grid(True, color="#D8DDE3", linewidth=0.7)
    figure.suptitle(
        "Contact-rezeroed 0.26 / 0.28 mm area comparison\n"
        "Mechanical zero: |Fy| >= 1 mN with stable pressure-bearing contact",
        fontsize=14,
    )
    figure.tight_layout(rect=(0.02, 0.02, 0.98, 0.90))
    figure.savefig(path, dpi=180)
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    cli = parse_args()
    rows = collect(cli.run_root)
    cli.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(cli.output_dir / "contact_rezeroed_area_summary.csv", rows)
    plot(cli.output_dir / "contact_rezeroed_area_trends.png", rows)
    print(f"states={len(rows)} output={cli.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
