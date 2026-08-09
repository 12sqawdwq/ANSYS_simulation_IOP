#!/usr/bin/env python3
"""Build manuscript figures directly from frozen repository results."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "high_iop_mechanical_transfer_t1p25_c0p60" / "results"
INTERFACE_CSV = RESULTS_DIR / "20260731_3ce7c957_interface_force_integrals_summary.csv"
GLOBAL_JSON = RESULTS_DIR / "20260731_global_load_share_derivation.json"
PRESSURE_CSV = RESULTS_DIR / "20260731_5017b619_iop_0_to_60_step2p5_summary.csv"
REGRESSION_JSON = RESULTS_DIR / "20260730_rational_regression_0_to_50_step2p5.json"
ANALYSIS_OUTPUTS_DIR = ROOT / "analysis" / "outputs"
THICKNESS_PREDICTIONS_CSV = ANALYSIS_OUTPUTS_DIR / "thickness_iop_predictions.csv"
FITTED_PARAMETERS_CSV = ANALYSIS_OUTPUTS_DIR / "fitted_parameters.csv"
OUTPUT_DIR = PAPER_DIR / "figures"
OUTPUT_PNG = OUTPUT_DIR / "forward_mechanical_response.png"
OUTPUT_SVG = OUTPUT_DIR / "forward_mechanical_response.svg"
CONTOUR_INPUT_DIR = OUTPUT_DIR / "mechanical_contours_raw"
CONTOUR_MANIFEST = CONTOUR_INPUT_DIR / "manifest.json"
CONTOUR_OUTPUT = OUTPUT_DIR / "central_section_stress_contours.png"
THICKNESS_OUTPUT_PNG = OUTPUT_DIR / "thickness_response_identifiability.png"
THICKNESS_OUTPUT_SVG = OUTPUT_DIR / "thickness_response_identifiability.svg"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_svg(path: Path) -> None:
    """Remove generator-only trailing whitespace and force portable LF endings."""
    text = path.read_text(encoding="utf-8")
    normalized = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> None:
    bounds = draw.textbbox((0, 0), text, font=font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.text((xy[0] - width / 2, xy[1] - height / 2), text, font=font, fill=fill)


def build_contour_figure() -> None:
    """Verify and assemble representative MAPDL central-section contours."""
    manifest = json.loads(CONTOUR_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "existing_rst_postprocessing_only":
        raise ValueError("unexpected contour provenance status")
    rows_by_pressure = {float(row["iop_mmhg"]): row for row in manifest["rows"]}
    pressures = [0.0, 20.0, 40.0, 50.0]
    name = "eyelid_1p25mm_indent_0p28mm007.png"

    font_path = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
    header_font = ImageFont.truetype(str(font_path), 43)
    panel_font = ImageFont.truetype(str(font_path), 35)
    header_height = 92
    gap = 8
    panels: list[Image.Image] = []

    for pressure in pressures:
        row = rows_by_pressure[pressure]
        if (
            not row.get("run_completed")
            or int(row.get("mapdl_error_count", -1)) != 0
            or not np.isclose(float(row["actual_indent_mm"]), 0.259875)
        ):
            raise ValueError(f"contour state failed provenance checks at {pressure:g} mmHg")
        path = CONTOUR_INPUT_DIR / f"iop{pressure:g}" / name
        if sha256(path) != row["images"][name]:
            raise ValueError(f"contour hash mismatch: {path.relative_to(ROOT)}")
        with Image.open(path) as source:
            # Retain the probe, both tissues, actual-scale deformed section,
            # native legend, units, extrema, and MAPDL plot label.
            panel = source.convert("RGB").crop((0, 170, source.width, source.height))
        panels.append(panel)

    panel_width, panel_height = panels[0].size
    canvas = Image.new(
        "RGB",
        (2 * panel_width + gap, header_height + 2 * panel_height + gap),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    centered_text(
        draw,
        (canvas.width / 2, header_height / 2),
        "Central-section von Mises stress (deformed geometry, actual scale)",
        header_font,
        "black",
    )

    for index, (pressure, panel) in enumerate(zip(pressures, panels)):
        row, column = divmod(index, 2)
        x = column * (panel_width + gap)
        y = header_height + row * (panel_height + gap)
        canvas.paste(panel, (x, y))
        label = f"{'ABCD'[index]}  IOP = {pressure:g} mmHg"
        draw.rounded_rectangle(
            (x + 18, y + 16, x + 390, y + 68),
            radius=8,
            fill="black",
            outline="white",
            width=2,
        )
        draw.text((x + 31, y + 20), label, font=panel_font, fill="white")

    canvas.save(CONTOUR_OUTPUT, format="PNG", compress_level=9)


def build_thickness_figure() -> None:
    """Plot direct thickness responses and the pressure-coverage limitation."""
    rows = read_csv(THICKNESS_PREDICTIONS_CSV)
    fitted_rows = [
        row
        for row in read_csv(FITTED_PARAMETERS_CSV)
        if row["state"] == "sensitivity_0p28"
    ]
    rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    fitted_rows.sort(key=lambda row: float(row["eyelid_thickness_mm"]))
    thickness = np.array([float(row["eyelid_thickness_mm"]) for row in rows])
    fitted_thickness = np.array([
        float(row["eyelid_thickness_mm"]) for row in fitted_rows
    ])
    expected_thickness = np.array([0.8, 1.0, 1.2, 1.25, 1.4, 1.5, 1.6, 1.8, 2.0])
    if not (
        len(rows) == 9
        and np.allclose(thickness, expected_thickness)
        and np.allclose(fitted_thickness, expected_thickness)
    ):
        raise ValueError("unexpected thickness-analysis grid")

    force_zero = np.array([float(row["force_zero_baseline_n"]) for row in rows])
    force_20 = np.array([float(row["force_iop_n"]) for row in rows])
    delta_q_20 = np.array([float(row["delta_probe_pressure_mmhg"]) for row in rows])
    pressure_counts = np.array([
        int(float(row["n_distinct_pressures"])) for row in fitted_rows
    ])
    reference_index = int(np.flatnonzero(np.isclose(thickness, 1.25))[0])
    reference_q = delta_q_20[reference_index]
    cv_percent = 100.0 * np.std(delta_q_20, ddof=1) / np.mean(delta_q_20)
    max_reference_deviation = 100.0 * np.max(
        np.abs(delta_q_20 / reference_q - 1.0)
    )

    colors = {
        "blue": "#0072B2",
        "orange": "#D55E00",
        "green": "#009E73",
        "gray": "#8A929D",
        "dark": "#3F4854",
    }
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.8))

    ax = axes[0]
    ax.plot(thickness, force_zero, marker="o", color=colors["blue"],
            label="Total probe force at 0 mmHg")
    ax.plot(thickness, force_20, marker="s", color=colors["orange"],
            label="Total probe force at 20 mmHg")
    ax.fill_between(thickness, force_zero, force_20, color=colors["green"],
                    alpha=0.12, label="Zero-referenced increment")
    ax.set_title("A  Absolute force is thickness-sensitive")
    ax.set_xlabel("Eyelid thickness (mm)")
    ax.set_ylabel("Total probe force (N)")
    ax.legend(loc="upper left")

    ax = axes[1]
    ax.plot(thickness, delta_q_20, marker="o", color=colors["green"], lw=1.8)
    ax.axhline(reference_q, color=colors["dark"], linestyle="--", lw=1.0,
               label="1.25-mm reference")
    ax.scatter([1.25], [reference_q], marker="*", s=95, color=colors["orange"],
               edgecolor="white", linewidth=0.7, zorder=4)
    ax.text(
        0.03,
        0.96,
        f"CV = {cv_percent:.2f}%\nmax deviation = {max_reference_deviation:.2f}%",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.85,
              "edgecolor": "#C8CDD3"},
    )
    ax.set_title("B  Zero-referenced 20-mmHg output")
    ax.set_xlabel("Eyelid thickness (mm)")
    ax.set_ylabel(r"Probe pressure increment, $q(20)$ (mmHg)")
    ax.legend(loc="lower left")

    ax = axes[2]
    categorical_x = np.arange(len(thickness))
    bar_colors = [colors["orange"] if np.isclose(value, 1.25) else colors["gray"]
                  for value in thickness]
    ax.bar(categorical_x, pressure_counts, width=0.68, color=bar_colors,
           edgecolor="white", linewidth=0.8)
    ax.text(
        reference_index,
        pressure_counts[reference_index] + 0.7,
        "25 states\n(24 nonzero)",
        ha="center",
        va="bottom",
        fontsize=8.2,
    )
    ax.text(
        0.98,
        0.62,
        "Eight other thicknesses:\n2 states each (0 and 20 mmHg)\n"
        "$\\Rightarrow$ one nonzero constraint\n$G_0$ and $\\lambda_r$ not separable",
        transform=ax.transAxes,
        ha="right",
        va="center",
        fontsize=8.4,
        color=colors["dark"],
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.9,
              "edgecolor": "#C8CDD3"},
    )
    ax.set_ylim(0, 29.5)
    ax.set_title("C  Pressure coverage limits identifiability")
    ax.set_xlabel("Eyelid thickness (mm)")
    ax.set_ylabel("Distinct pressure states")
    ax.set_xticks(categorical_x)
    ax.set_xticklabels([f"{value:g}" for value in thickness], rotation=45, ha="right")

    for index, ax in enumerate(axes):
        reference_x = reference_index if index == 2 else 1.25
        ax.axvline(reference_x, color="#A6ADB6", lw=0.9, linestyle=":", zorder=0)
        ax.grid(True, color="#D9DEE5", linewidth=0.65, alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Eyelid thickness: direct response and parameter-identifiability boundary",
        fontsize=12.5,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    fig.savefig(
        THICKNESS_OUTPUT_PNG,
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": "paper/build_figures.py"},
    )
    fig.savefig(
        THICKNESS_OUTPUT_SVG,
        bbox_inches="tight",
        metadata={"Date": None, "Creator": "paper/build_figures.py"},
    )
    normalize_svg(THICKNESS_OUTPUT_SVG)
    plt.close(fig)


def main() -> int:
    interface_rows = read_csv(INTERFACE_CSV)
    all_pressure_rows = read_csv(PRESSURE_CSV)
    primary_rows = [row for row in all_pressure_rows if row["state"] == "primary_0p26"]
    sensitivity_rows = [
        row for row in all_pressure_rows if row["state"] == "sensitivity_0p28"
    ]
    global_payload = json.loads(GLOBAL_JSON.read_text(encoding="utf-8"))
    regression = json.loads(REGRESSION_JSON.read_text(encoding="utf-8"))

    if len(interface_rows) != 21 or not global_payload.get("derivation_pass"):
        raise ValueError("frozen 0-50 mmHg mechanical-response inputs did not pass")
    interface_p = np.array([float(row["input_iop_mmhg"]) for row in interface_rows])
    if not np.allclose(interface_p, np.arange(0.0, 50.0 + 2.5, 2.5)):
        raise ValueError("unexpected interface-force pressure grid")

    global_by_p = {
        float(row["input_iop_mmhg"]): row for row in global_payload["rows"]
    }
    global_rows = [global_by_p[pressure] for pressure in interface_p]

    pressure_p = np.array([float(row["input_iop_mmhg"]) for row in primary_rows])
    sensitivity_p = np.array([
        float(row["input_iop_mmhg"]) for row in sensitivity_rows
    ])
    expected_pressure_grid = np.arange(0.0, 60.0 + 2.5, 2.5)
    if not (
        np.allclose(pressure_p, expected_pressure_grid)
        and np.allclose(sensitivity_p, expected_pressure_grid)
    ):
        raise ValueError("unexpected 0-60 mmHg pressure grid")

    primary_indent = np.array([float(row["actual_indent_mm"]) for row in primary_rows])
    sensitivity_indent = np.array([
        float(row["actual_indent_mm"]) for row in sensitivity_rows
    ])
    if not (
        np.allclose(primary_indent, 0.259875)
        and np.allclose(sensitivity_indent, 0.28)
    ):
        raise ValueError("unexpected indentation states for coupled secant stiffness")

    total_probe_force = np.array([float(row["probe_force_n"]) for row in primary_rows])
    sensitivity_force = np.array([
        float(row["probe_force_n"]) for row in sensitivity_rows
    ])
    coupled_secant_stiffness = (
        (sensitivity_force - total_probe_force)
        / (sensitivity_indent - primary_indent)
    )
    pressure_q = np.array([
        float(row["delta_probe_pressure_mmhg"]) for row in primary_rows
    ])

    # Stored JSON uses historical names: b_dimensionless is display a, and
    # a_per_mmhg is display b in p=a*q/(1-b*q).
    a_display = float(regression["parameters"]["b_dimensionless"])
    b_display = float(regression["parameters"]["a_per_mmhg"])
    fit_p = np.linspace(0.0, 60.0, 601)
    fit_q = fit_p / (a_display + b_display * fit_p)

    f_iop = np.array([
        float(row["global_iop_projected_force_n"]) for row in global_rows
    ])
    area_correction = np.array([
        float(row["ka_ap_over_ac5"]) for row in interface_rows
    ])
    delta_interface = np.array([
        float(row["delta_interface_force_n"]) for row in interface_rows
    ])
    delta_probe = np.array([
        float(row["delta_probe_force_n"]) for row in interface_rows
    ])

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "legend.fontsize": 8.2,
        "svg.hashsalt": "blueknow-paper-forward-response",
    })
    colors = {
        "blue": "#0072B2",
        "orange": "#D55E00",
        "green": "#009E73",
        "purple": "#7A3E9D",
        "gray": "#5B6573",
        "red": "#CC3311",
    }
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.8))
    twin_axes = []

    ax = axes[0, 0]
    ax.plot(
        pressure_p,
        total_probe_force,
        color=colors["blue"],
        marker="o",
        ms=3.2,
        label=r"Total probe force at $s=0.259875$ mm",
    )
    ax.set_title("A  IOP-dependent coupled stiffness at fixed indentation")
    ax.set_xlabel("Input IOP, $p$ (mmHg)")
    ax.set_ylabel(r"Total probe force, $F_{probe}$ (N)", color=colors["blue"])
    ax.tick_params(axis="y", labelcolor=colors["blue"])
    ax2 = ax.twinx()
    twin_axes.append(ax2)
    ax2.plot(
        pressure_p,
        coupled_secant_stiffness,
        color=colors["orange"],
        marker="s",
        ms=3.0,
        label=r"Coupled secant stiffness, $k_{probe,sec}$",
    )
    ax2.set_ylabel(r"$k_{probe,sec}$ (N/mm)", color=colors["orange"])
    ax2.tick_params(axis="y", labelcolor=colors["orange"])
    handles = ax.get_lines() + ax2.get_lines()
    ax.legend(handles, [line.get_label() for line in handles], loc="lower right")

    ax = axes[0, 1]
    ax.plot(
        interface_p,
        f_iop,
        color=colors["blue"],
        marker="o",
        ms=3.5,
        label=r"Projected corneal pressure load $F_{IOP}$",
    )
    ax.set_title("B  Corneal pressure loading and area correction")
    ax.set_xlabel("Input IOP, $p$ (mmHg)")
    ax.set_ylabel(r"$F_{IOP}$ (N)", color=colors["blue"])
    ax.tick_params(axis="y", labelcolor=colors["blue"])
    ax2 = ax.twinx()
    twin_axes.append(ax2)
    ax2.plot(
        interface_p,
        area_correction,
        color=colors["orange"],
        marker="s",
        ms=3.2,
        label=r"Area correction $K_A=A_p/A_{c,5^\circ}$",
    )
    ax2.set_ylabel(r"Area correction $K_A$", color=colors["orange"])
    ax2.tick_params(axis="y", labelcolor=colors["orange"])
    handles = ax.get_lines() + ax2.get_lines()
    ax.legend(handles, [line.get_label() for line in handles], loc="center right")

    ax = axes[1, 0]
    ax.plot(
        interface_p,
        delta_interface,
        color=colors["green"],
        marker="s",
        ms=3.4,
        label=r"Cornea-eyelid interface, $\Delta F_{ec}$",
    )
    ax.plot(
        interface_p,
        delta_probe,
        color=colors["purple"],
        marker="o",
        ms=3.4,
        label=r"Eyelid-probe output, $\Delta F_{probe}$",
    )
    ax.set_title("C  Forward force response through cornea and eyelid")
    ax.set_xlabel("Input IOP, $p$ (mmHg)")
    ax.set_ylabel("Zero-referenced normal force increment (N)")
    ax.legend(loc="lower right")

    ax = axes[1, 1]
    train = pressure_p <= 50.0
    held_out = pressure_p > 50.0
    ax.plot(
        fit_p[fit_p <= 50.0],
        fit_q[fit_p <= 50.0],
        color=colors["blue"],
        lw=2.0,
        label=r"Version-2 forward form $q=p/(a+bp)$",
    )
    ax.plot(
        fit_p[fit_p >= 50.0],
        fit_q[fit_p >= 50.0],
        color=colors["blue"],
        lw=2.0,
        linestyle="--",
    )
    ax.scatter(
        pressure_p[train],
        pressure_q[train],
        color=colors["gray"],
        s=19,
        zorder=3,
        label="FE identification states (0-50)",
    )
    ax.scatter(
        pressure_p[held_out],
        pressure_q[held_out],
        facecolors="white",
        edgecolors=colors["red"],
        linewidths=1.5,
        s=35,
        zorder=4,
        label="Unseen FE states (52.5-60)",
    )
    ax.axvline(50.0, color="#999999", lw=1.0, linestyle=":")
    ax.set_title("D  Nonlinear probe output and the version-2 fit")
    ax.set_xlabel("Input IOP, $p$ (mmHg)")
    ax.set_ylabel(r"Probe pressure increment, $q$ (mmHg)")
    ax.legend(loc="lower right")

    for ax in axes.flat:
        ax.grid(True, color="#D9DEE5", linewidth=0.65, alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    for ax in twin_axes:
        ax.spines["top"].set_visible(False)

    fig.suptitle(
        "IOP-dependent stiffness, load redistribution, and nonlinear probe output",
        fontsize=13,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.965))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=300, metadata={"Software": "paper/build_figures.py"})
    fig.savefig(
        OUTPUT_SVG,
        metadata={"Date": None, "Creator": "paper/build_figures.py"},
    )
    normalize_svg(OUTPUT_SVG)
    plt.close(fig)

    build_contour_figure()
    build_thickness_figure()
    for path in (
        OUTPUT_PNG,
        OUTPUT_SVG,
        CONTOUR_OUTPUT,
        THICKNESS_OUTPUT_PNG,
        THICKNESS_OUTPUT_SVG,
    ):
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
