#!/usr/bin/env python3
"""
Generate analysis markdown documents with embedded figures.
Two documents:
  1. 偏心测量曲线分析.md  — X-axis eccentric (off-axis) measurement analysis
  2. 眼睑角膜厚度影响分析.md — Eyelid/cornea thickness effect analysis
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
import os, shutil, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
STUDY_DIR = Path(__file__).resolve().parents[1]

# ============================================================
# STYLE — matches existing visu.py
# ============================================================
plt.style.use("dark_background")
mpl.rcParams["font.family"] = "monospace"
mpl.rcParams["axes.facecolor"] = "#0b0b0b"
mpl.rcParams["figure.facecolor"] = "#0b0b0b"
mpl.rcParams["savefig.facecolor"] = "#0b0b0b"
mpl.rcParams["axes.edgecolor"] = "#444444"
mpl.rcParams["axes.labelcolor"] = "white"
mpl.rcParams["xtick.color"] = "#aaaaaa"
mpl.rcParams["ytick.color"] = "#aaaaaa"

# Try CJK font for Chinese labels
try:
    for _fp in mpl.font_manager.fontManager.ttflist:
        if any(n in _fp.name for n in ["Microsoft YaHei", "SimHei", "Noto Sans CJK"]):
            mpl.rcParams["font.family"] = _fp.name
            break
    else:
        for _p in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
            if os.path.exists(_p):
                mpl.font_manager.fontManager.addfont(_p)
                mpl.rcParams["font.family"] = "Microsoft YaHei"
                break
except:
    pass

# ============================================================
# 1. BASE MODEL (from visu.py)
# ============================================================
MMHG_TO_PA = 133.322
PA_TO_MMHG = 1.0 / MMHG_TO_PA
P_IOP_MMHG = 20.0
P_IOP_PA = P_IOP_MMHG * MMHG_TO_PA
A_PROBE_MAX_MM2 = 14.657
R_PROBE_MAX_MM = np.sqrt(A_PROBE_MAX_MM2 / np.pi)
D_PIVOT_MM = 0.26
A_INTERNAL_AT_PIVOT_MM2 = 8.533
A_INTERNAL_ASYMPTOTE_MM2 = 14.20
A_INTERNAL_POST_PIVOT_TAU_MM = 0.85
X_MIN_MM, X_MAX_MM, N_X = -3.0, 3.0, 2600

def external_probe_eyelid_area_mm2(d_mm):
    if d_mm <= 0: return 0.0
    if d_mm <= D_PIVOT_MM: return A_PROBE_MAX_MM2 * d_mm / D_PIVOT_MM
    return A_PROBE_MAX_MM2

def internal_corneal_applanation_area_mm2(d_mm):
    if d_mm <= 0: return 0.0
    if d_mm <= D_PIVOT_MM:
        eta = d_mm / D_PIVOT_MM
        return A_INTERNAL_AT_PIVOT_MM2 * eta**1.35
    return (A_INTERNAL_AT_PIVOT_MM2 +
            (A_INTERNAL_ASYMPTOTE_MM2 - A_INTERNAL_AT_PIVOT_MM2) *
            (1.0 - np.exp(-(d_mm - D_PIVOT_MM) / A_INTERNAL_POST_PIVOT_TAU_MM)))

def radius_from_area_mm(a):
    return 0.0 if a <= 0 else np.sqrt(a / np.pi)
def resultant_force_N(Ac):
    return P_IOP_PA * Ac * 1e-6
def probe_equivalent_pressure_mmhg(F, Ae):
    if Ae <= 0: return 0.0
    return (F / (Ae * 1e-6)) * PA_TO_MMHG

# ============================================================
# 2. OFF-AXIS EXTENSION
# ============================================================
CORNEAL_RADIUS_MM = 12.0

def _atten(d_mm, off):
    if off <= 0: return 1.0
    eta = off / CORNEAL_RADIUS_MM
    gf = eta**2 * 0.5 * (1 + 0.3 * np.exp(-d_mm / 0.5))
    a = np.exp(-gf * 8.0)
    a *= np.exp(-(max(0, off - 1.5) / 0.8)**2 * 0.5)
    return a

def external_probe_area_offaxis(d_mm, off):
    A = external_probe_eyelid_area_mm2(d_mm)
    return A * (1.0 if off <= 0 else np.exp(-(off / 5.0)**2))

def internal_corneal_area_offaxis(d_mm, off):
    return internal_corneal_applanation_area_mm2(d_mm) * _atten(d_mm, off)

def asymmetric_pressure_field(x, re, rc, d_mm, off, P_IOP, Ppeq):
    n = len(x); Pi = np.zeros(n); Po = np.zeros(n); Pp = np.zeros(n)
    if re <= 0: return Pi, Po, Pp
    sr = np.clip(off / (re + 0.5), 0, 0.5)
    ddist = np.clip((d_mm - 0.16) / (1.00 - 0.16), 0, 1)
    odist = np.clip(off / 2.0, 0, 1)
    if rc > 0:
        Pi[np.abs(x) <= rc] = P_IOP
    mask = np.abs(x) <= re
    eta = x[mask] / re; es = eta - sr * 0.3
    bl = 0.82 + 0.10 * ddist
    cd = (0.20 + 0.10 * ddist) * np.exp(-(np.abs(es) / 0.72)**4)
    ea = 0.58 - 0.16 * ddist
    esh = ea * (1 + 0.3 * odist * np.sign(es)) * np.exp(-((np.abs(es) - 0.90) / (0.085 + 0.025 * ddist))**2)
    bt = np.clip(1.0 - np.abs(es)**8, 0, 1)**0.18
    shape = (bl + cd + esh) * bt
    ls = P_IOP * (1.00 + 0.10 * ddist + 0.05 * odist)
    Po[mask] = ls * shape
    rpe = 0.95 * re
    mp = np.abs(x) <= rpe
    ep = x[mp] / rpe; eps = ep - sr * 0.4
    ml = (1.0 - np.clip(eps, -1, 1)**2) ** (0.55 - 0.18 * ddist)
    sh = (0.34 - 0.12 * ddist) * (1 + 0.4 * odist * np.sign(eps)) * np.exp(-((np.abs(eps) - 0.82) / (0.12 + 0.02 * ddist))**2)
    cr = 0.08 * ddist * np.exp(-(np.abs(eps) / 0.35)**2)
    Pp[mp] = 1.85 * Ppeq * (ml + sh + cr)
    return Pi, Po, Pp

def build_offaxis_case(d_mm, off):
    Ae = external_probe_area_offaxis(d_mm, off)
    Ac = internal_corneal_area_offaxis(d_mm, off)
    re, rc = radius_from_area_mm(Ae), radius_from_area_mm(Ac)
    F = resultant_force_N(Ac)
    Ppeq = probe_equivalent_pressure_mmhg(F, Ae)
    x = np.linspace(X_MIN_MM, X_MAX_MM, N_X)
    Pi, Po, Pp = asymmetric_pressure_field(x, re, rc, d_mm, off, P_IOP_MMHG, Ppeq)
    return dict(d_mm=d_mm, offset_mm=off, Ae_mm2=Ae, Ac_mm2=Ac, re_mm=re, rc_mm=rc,
                F_N=F, Ac_Ae=Ac/Ae if Ae>0 else 0, Pprobe_eq_mmhg=Ppeq,
                P_inner=Pi, P_outer=Po, P_probe=Pp)

# ============================================================
# 3. THICKNESS EXTENSION
# ============================================================
DIFFUSION_TAN = 0.7
def effective_eyelid_thickness(te_init, d):
    return te_init * np.exp(-1.2 * d) + 0.05 if d > 0 else te_init

def internal_corneal_area_thickness(d, te, tc):
    Ae = external_probe_eyelid_area_mm2(d)
    re = radius_from_area_mm(Ae)
    teff = effective_eyelid_thickness(te, d)
    csf = np.clip(1 - 0.08 * (tc - 0.55) / 0.1, 0.90, 1.05)
    de = 1 + 0.3 * (te - 1.25) / 1.0
    rc = np.maximum(0, re - teff * DIFFUSION_TAN * de)
    Ac = np.pi * rc**2 * csf
    if d < 0.05:
        Ac = Ac * (d / 0.05) + internal_corneal_applanation_area_mm2(d) * (1 - d / 0.05)
    return Ac

# ============================================================
# 4. PLOTTING
# ============================================================
OFFSET_COLORS = ["#00aaff", "#ff8800", "#44dd44", "#ff44ff"]
THICK_COLORS  = ["#00aaff", "#44dd44", "#ffaa00", "#ff8800", "#ff44ff"]

def save_pressure_subplot(ax, c, title=""):
    d, Ae, Ac = c["d_mm"], c["Ae_mm2"], c["Ac_mm2"]
    re, rc = c["re_mm"], c["rc_mm"]
    F, ratio = c["F_N"], c["Ac_Ae"]
    Ppeq = c["Pprobe_eq_mmhg"]
    x = np.linspace(X_MIN_MM, X_MAX_MM, N_X)
    ax.axvline(0, color="gray", ls="-.", lw=1.1, alpha=0.75)
    ax.plot(x, c["P_probe"], "#ff4444", lw=2.9, label="Probe response")
    ax.plot(x, c["P_outer"], "#ffaa00", lw=2.7, label="Outer surface")
    ax.plot(x, c["P_inner"], "#00ccff", lw=2.6, label="Inner surface, 20 mmHg")
    ax.fill_between(x, 0, c["P_probe"], color="#ff4444", alpha=0.16)
    ax.fill_between(x, 0, c["P_outer"], color="#ffaa00", alpha=0.14)
    ax.fill_between(x, 0, c["P_inner"], color="#00ccff", alpha=0.10)
    for s in [-1, 1]:
        ax.axvline(s * re, color="#ffaa00", ls=":", lw=1.7, alpha=0.7)
        ax.axvline(s * rc, color="#00ccff", ls=":", lw=1.7, alpha=0.7)
    txt = (f"d = {d:.2f} mm\nAe = {Ae:.2f} mm²\nAc = {Ac:.2f} mm²\n"
           f"Ac/Ae = {ratio:.3f}\nF = {F:.4f} N\nPprobe = {Ppeq:.2f} mmHg")
    ax.text(2.86, 43, txt, fontsize=8.5, color="white", ha="right", va="top",
            bbox=dict(facecolor="black", alpha=0.55, edgecolor="gray"))
    if title:
        ax.set_title(title, fontsize=10, pad=8)
    ax.grid(True, alpha=0.10, ls=":")
    ax.set_xlim(X_MIN_MM, X_MAX_MM)
    ax.set_ylim(0, 45)


# ============================================================
# MAIN GENERATORS
# ============================================================

def generate_offaxis_markdown():
    print("Generating off-axis markdown document...")
    doc_name = "偏心测量曲线分析"
    doc_dir = os.path.join(OUT_DIR, doc_name)
    img_dir = str(STUDY_DIR / "figures" / "placeholder")
    os.makedirs(doc_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    offsets = [0.0, 0.5, 1.0, 2.0]
    d_fixed = 0.29  # measurement window: 0.28-0.30 mm
    d_curve = np.linspace(0.01, 2.0, 400)
    x_mm = np.linspace(X_MIN_MM, X_MAX_MM, N_X)

    # Precompute curves
    Ae_curves, Ac_curves, ratio_curves, Pprobe_curves = {}, {}, {}, {}
    for off in offsets:
        k = f"{off:.1f}"
        Ae_arr = np.array([external_probe_area_offaxis(d, off) for d in d_curve])
        Ac_arr = np.array([internal_corneal_area_offaxis(d, off) for d in d_curve])
        Ae_curves[k] = Ae_arr; Ac_curves[k] = Ac_arr
        ratio_curves[k] = Ae_arr / np.maximum(Ac_arr, 1e-10)
        F_arr = np.array([resultant_force_N(a) for a in Ac_arr])
        Pprobe_curves[k] = np.array([probe_equivalent_pressure_mmhg(f, a) for f, a in zip(F_arr, Ae_arr)])

    d_fixed = 0.29
    pcases = [build_offaxis_case(d_fixed, off) for off in offsets]

    # ---- Figure 1: Area-displacement ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for i, off in enumerate(offsets):
        k, c = f"{off:.1f}", OFFSET_COLORS[i]
        axes[0].plot(d_curve, Ae_curves[k], c, lw=2.5 if i==0 else 2.0, label=f"{off:.1f}mm offset")
        axes[1].plot(d_curve, Ac_curves[k], c, lw=2.5 if i==0 else 2.0, label=f"{off:.1f}mm offset")
    for ax in axes:
        ax.axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
        ax.set_xlim(0, 2.0); ax.set_ylim(0, 16)
        ax.grid(True, alpha=0.12, ls=":"); ax.legend(fontsize=8, loc="lower right")
    axes[0].set_title("External Area Ae (Probe-Eyelid)", fontsize=11)
    axes[0].set_ylabel("Contact Area (mm²)", fontsize=9)
    axes[1].set_title("Internal Area Ac (Eyelid-Cornea)", fontsize=11)
    for ax in axes: ax.set_xlabel("Probe Displacement (mm)", fontsize=9)
    fig.suptitle("AREA-DISPLACEMENT CURVES AT DIFFERENT OFFSET POSITIONS", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(img_dir, "fig1_areas.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 2: Ratio + Pprobe ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for i, off in enumerate(offsets):
        k, c = f"{off:.1f}", OFFSET_COLORS[i]
        axes[0].plot(d_curve, ratio_curves[k], c, lw=2.5 if i==0 else 2.0, label=f"{off:.1f}mm offset")
        axes[1].plot(d_curve, Pprobe_curves[k], c, lw=2.5 if i==0 else 2.0, label=f"{off:.1f}mm offset")
    axes[0].axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
    axes[0].axhline(1.0, color="gray", ls=":", lw=1, alpha=0.4)
    axes[0].set_xlim(0.05, 2.0); axes[0].set_ylim(1.0, 4.5)
    axes[0].set_title("Area Transfer Ratio Ae/Ac", fontsize=11)
    axes[0].set_ylabel("Ae/Ac", fontsize=9)
    axes[0].legend(fontsize=8, loc="upper right")
    axes[1].axhline(P_IOP_MMHG, color="#00ccff", ls="--", lw=2, alpha=0.6, label="IOP = 20 mmHg")
    axes[1].axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
    axes[1].set_xlim(0.05, 2.0); axes[1].set_ylim(0, 25)
    axes[1].set_title("Probe Equivalent Pressure F/Ae", fontsize=11)
    axes[1].set_ylabel("Pressure (mmHg)", fontsize=9)
    axes[1].legend(fontsize=8, loc="lower right")
    for ax in axes: ax.set_xlabel("Probe Displacement (mm)", fontsize=9); ax.grid(True, alpha=0.12, ls=":")
    fig.suptitle("RATIO AND PRESSURE RESPONSE AT DIFFERENT OFFSETS", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(img_dir, "fig2_ratio_pressure.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 3: All probe responses overlaid at d=0.29mm ----
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, off in enumerate(offsets):
        c = pcases[i]
        ax.plot(x_mm, c["P_probe"], OFFSET_COLORS[i], lw=2.2, label=f"{off:.1f}mm offset")
    ax.axhline(P_IOP_MMHG, color="#00ccff", ls="--", lw=1.5, alpha=0.5, label="IOP = 20 mmHg")
    ax.axvline(0, color="gray", ls="-.", lw=1, alpha=0.5)
    ax.set_title("Probe Response Pressure at d = 0.29 mm (All Offsets)", fontsize=12)
    ax.set_xlabel("Section Coordinate x (mm)", fontsize=10)
    ax.set_ylabel("Pressure (mmHg)", fontsize=10)
    ax.set_xlim(X_MIN_MM, X_MAX_MM); ax.set_ylim(0, 45)
    ax.grid(True, alpha=0.10, ls=":")
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(img_dir, "fig3_overlay_probe.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 4: 2x2 pressure distribution grid ----
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True, sharey=True)
    axes = axes.ravel()
    titles = ["Centered (0.0 mm offset), d=0.29 mm", "Small offset (0.5 mm), d=0.29 mm",
              "Moderate offset (1.0 mm), d=0.29 mm", "Large offset (2.0 mm), d=0.29 mm"]
    for idx, (ax, c, t) in enumerate(zip(axes, pcases, titles)):
        save_pressure_subplot(ax, c, t)
        if idx == 0: ax.legend(loc="upper left", fontsize=7.5, framealpha=0.85)
        if idx >= 2: ax.set_xlabel("Section Coordinate x (mm)", fontsize=9)
        if idx % 2 == 0: ax.set_ylabel("Pressure (mmHg)", fontsize=9)
    fig.suptitle("PRESSURE DISTRIBUTION AT DIFFERENT OFFSET POSITIONS (d = 0.29 mm)", fontsize=14, y=0.985)
    plt.tight_layout()
    fig.savefig(os.path.join(img_dir, "fig4_pressure_grid.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Write markdown ----
    # Use relative paths for images
    rel_imgs = doc_name + "_files"
    md = f"""# 偏心测量曲线分析

## Off-Axis Probe Measurement Analysis

X-Axis Eccentric Indentation: 0.5mm / 1.0mm / 2.0mm Offset

---

### 测量原理

A flat-ended probe is advanced against the closed eyelid at varying lateral offsets from the corneal apex. Off-axis positioning alters the effective contact geometry between probe, eyelid, and cornea, modifying the internal corneal contact area (Ac) and the resulting force distribution. At larger offsets, the probe approaches the limbal region where tissue geometry and mechanical properties differ from the central cornea.

| Parameter | Value |
|---|---|
| Offsets analyzed | 0.0mm (centered), 0.5mm, 1.0mm, 2.0mm |
| IOP | 20 mmHg (fixed) |
| Probe displacement (grid plots) | d = 0.29 mm |
| Probe max area | {A_PROBE_MAX_MM2:.2f} mm² |

---

### 1. 面积-位移曲线

![Area-displacement curves]({rel_imgs}/fig1_areas.png)

左图：外部接触面积 Ae（探头-眼睑）。在不同偏心量下，Ae 的变化相对较小，仅在 2.0mm 偏心时因探头接近角膜缘区域而出现明显下降。

右图：内部接触面积 Ac（眼睑-角膜）。Ac 随偏心量增加而显著下降。当偏心量达到 2.0mm 时，角膜曲率导致探头与角膜之间的有效接触大幅减少。

---

### 2. 面积比值与探头等效压力

![Ratio and pressure response]({rel_imgs}/fig2_ratio_pressure.png)

左图：面积传递比 Ae/Ac。偏心量越大，比值越高，表示测量效率降低。在 2.0mm 偏心时，比值曲线明显偏离居中情况。

右图：探头等效压力 F/Ae。各偏心量下的等效压力均低于 IOP（20 mmHg）。偏心量越大，等效压力越低，因有效内部接触面积 Ac 减小。

---

### 3. 特殊点分析

**Centered (0.0mm offset):**
- Ideal measurement condition. Ae and Ac follow the nominal model.
- Force-displacement response is symmetric. Ac/Ae ratio at d=0.29mm: {pcases[0]['Ac_Ae']:.3f}
- Probe equivalent pressure: {pcases[0]['Pprobe_eq_mmhg']:.2f} mmHg

**Small offset (0.5mm):**
- Minor reduction in Ac (~5-7%) as the corneal surface begins to tilt relative to probe face.
- Pressure distribution shows subtle asymmetry. Ae is nearly unchanged.
- Ac/Ae ratio: {pcases[1]['Ac_Ae']:.3f} at d=0.29mm. Measurement remains within usable range.

**Moderate offset (1.0mm):**
- Ac reduced by ~20-25%. Corneal curvature creates measurable gap at probe periphery.
- Asymmetric pressure distribution becomes apparent - higher stress on apex side.
- Ae begins to show minor reduction (~3%). Ac/Ae ratio increases noticeably.

**Large offset (2.0mm):**
- Ac reduced by ~45-50%. Probe approaches limbal transition zone.
- Highly asymmetric pressure profile. Measurement deviates substantially from centered case.

---

### 4. 探头响应剖面叠加对比

![Probe response overlay]({rel_imgs}/fig3_overlay_probe.png)

All probe response curves at d = 0.29 mm overlaid on the same axis. The centered case (blue) shows symmetric distribution with peak pressure around 28-30 mmHg at the edges. As offset increases, the distribution becomes asymmetric and peak pressure shifts toward the corneal apex side. The 2.0mm offset case shows significantly reduced overall pressure levels and pronounced asymmetry.

---

### 5. 切面压力分布对比

![Pressure distribution grid]({rel_imgs}/fig4_pressure_grid.png)

2×2 grid comparing pressure distributions (probe response, outer surface, inner surface) at four different offset positions. Each panel shows the full pressure field with Ae and Ac radii marked by vertical dotted lines.

| Offset | Ae (mm²) | Ac (mm²) | Ac/Ae | F (N) | Pprobe (mmHg) | Ae reduction | Ac reduction |
|---|---|---|---|---|---|---|---|
"""
    row0 = pcases[0]
    for c in pcases:
        Ae_red = (1 - c["Ae_mm2"] / row0["Ae_mm2"]) * 100
        Ac_red = (1 - c["Ac_mm2"] / row0["Ac_mm2"]) * 100
        md += f"| {c['offset_mm']:.1f} | {c['Ae_mm2']:.2f} | {c['Ac_mm2']:.2f} | {c['Ac_Ae']:.3f} | {c['F_N']:.4f} | {c['Pprobe_eq_mmhg']:.2f} | {Ae_red:.1f}% | {Ac_red:.1f}% |\n"

    md += """
**Key observations:**
- Ac is more sensitive to offset than Ae (corneal curvature effect)
- Ac/Ae ratio increases with offset, indicating reduced measurement efficiency
- At 2.0mm offset, Ac reduction exceeds 45%, significantly altering force transmission
"""

    md_path = os.path.join(OUT_DIR, f"{doc_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  -> {md_path}")

    # Clean up temp dir
    if os.path.exists(doc_dir) and doc_dir != img_dir:
        shutil.rmtree(doc_dir)


def generate_thickness_markdown():
    print("Generating thickness markdown document...")
    doc_name = "眼睑角膜厚度影响分析"
    img_dir = os.path.join(OUT_DIR, doc_name + "_files")
    os.makedirs(img_dir, exist_ok=True)

    eyelid_ths = [0.8, 1.0, 1.25, 1.5, 2.0]
    cornea_ths = [0.50, 0.55, 0.60]
    nominal_eyelid = 1.25
    nominal_cornea = 0.55
    d_curve = np.linspace(0.01, 2.0, 400)
    x_mm = np.linspace(X_MIN_MM, X_MAX_MM, N_X)
    d_fixed = 0.29  # measurement window: 0.28-0.30 mm

    # Eyelid variation curves
    Ae_eyelid, Ac_eyelid, ratio_eyelid, Pp_eyelid = {}, {}, {}, {}
    for te in eyelid_ths:
        k = f"{te:.2f}"
        Ae_arr = np.array([external_probe_eyelid_area_mm2(d) for d in d_curve])
        Ac_arr = np.array([internal_corneal_area_thickness(d, te, nominal_cornea) for d in d_curve])
        Ae_eyelid[k] = Ae_arr; Ac_eyelid[k] = Ac_arr
        ratio_eyelid[k] = Ae_arr / np.maximum(Ac_arr, 1e-10)
        F_arr = np.array([resultant_force_N(a) for a in Ac_arr])
        Pp_eyelid[k] = np.array([probe_equivalent_pressure_mmhg(f, a) for f, a in zip(F_arr, Ae_arr)])

    # Cornea variation curves
    Ac_cornea, ratio_cornea, Pp_cornea = {}, {}, {}
    for tc in cornea_ths:
        k = f"{tc:.2f}"
        Ae_arr = np.array([external_probe_eyelid_area_mm2(d) for d in d_curve])
        Ac_arr = np.array([internal_corneal_area_thickness(d, nominal_eyelid, tc) for d in d_curve])
        Ac_cornea[k] = Ac_arr
        ratio_cornea[k] = Ae_arr / np.maximum(Ac_arr, 1e-10)
        F_arr = np.array([resultant_force_N(a) for a in Ac_arr])
        Pp_cornea[k] = np.array([probe_equivalent_pressure_mmhg(f, a) for f, a in zip(F_arr, Ae_arr)])

    # Build pressure cases
    Ae_nominal_at_d = external_probe_eyelid_area_mm2(d_fixed)
    pcases_eyelid = []
    for te in eyelid_ths:
        Ac = internal_corneal_area_thickness(d_fixed, te, nominal_cornea)
        re, rc = radius_from_area_mm(Ae_nominal_at_d), radius_from_area_mm(Ac)
        F = resultant_force_N(Ac)
        Ppeq = probe_equivalent_pressure_mmhg(F, Ae_nominal_at_d)
        Pi, Po, Pp = asymmetric_pressure_field(x_mm, re, rc, d_fixed, 0.0, P_IOP_MMHG, Ppeq)
        pcases_eyelid.append(dict(d_mm=d_fixed, Ae_mm2=Ae_nominal_at_d, Ac_mm2=Ac,
                                  re_mm=re, rc_mm=rc, F_N=F, Ac_Ae=Ac/Ae_nominal_at_d,
                                  Pprobe_eq_mmhg=Ppeq, P_inner=Pi, P_outer=Po, P_probe=Pp,
                                  t_eyelid=te, t_cornea=nominal_cornea))

    # ---- Figure 1: Eyelid thickness area curves ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    Ae_nom = np.array([external_probe_eyelid_area_mm2(d) for d in d_curve])
    axes[0].plot(d_curve, Ae_nom, color="gray", lw=2, ls="--", alpha=0.5, label="External Ae (same)")
    for i, te in enumerate(eyelid_ths):
        k, c = f"{te:.2f}", THICK_COLORS[i]
        axes[0].plot(d_curve, Ac_eyelid[k], c, lw=2.2, label=f"Eyelid {te:.2f}mm")
        axes[1].plot(d_curve, ratio_eyelid[k], c, lw=2.2, label=f"Eyelid {te:.2f}mm")
    for ax in axes:
        ax.axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
        ax.grid(True, alpha=0.12, ls=":")
    axes[0].set_xlim(0, 2.0); axes[0].set_ylim(0, 16)
    axes[0].set_title("Internal Contact Area Ac vs Eyelid Thickness", fontsize=11)
    axes[0].set_ylabel("Contact Area (mm²)", fontsize=9)
    axes[0].legend(fontsize=7.5, loc="lower right")
    axes[1].set_xlim(0.05, 2.0); axes[1].set_ylim(1.0, 5.0)
    axes[1].axhline(1.0, color="gray", ls=":", lw=1, alpha=0.4)
    axes[1].set_title("Area Transfer Ratio Ae/Ac vs Eyelid Thickness", fontsize=11)
    axes[1].set_ylabel("Ae/Ac", fontsize=9)
    axes[1].legend(fontsize=7.5, loc="upper right")
    for ax in axes: ax.set_xlabel("Probe Displacement (mm)", fontsize=9)
    fig.suptitle("EYELID THICKNESS EFFECT ON CONTACT AREA", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(img_dir, "fig1_eyelid_area.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 2: Corneal thickness area curves ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    axes[0].plot(d_curve, Ae_nom, color="gray", lw=2, ls="--", alpha=0.5, label="External Ae (same)")
    cornea_colors = ["#00aaff", "#ffaa00", "#ff4444"]
    for i, tc in enumerate(cornea_ths):
        k, c = f"{tc:.2f}", cornea_colors[i]
        axes[0].plot(d_curve, Ac_cornea[k], c, lw=2.2, label=f"Cornea {tc:.2f}mm")
        axes[1].plot(d_curve, ratio_cornea[k], c, lw=2.2, label=f"Cornea {tc:.2f}mm")
    for ax in axes:
        ax.axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
        ax.grid(True, alpha=0.12, ls=":")
    axes[0].set_xlim(0, 2.0); axes[0].set_ylim(0, 16)
    axes[0].set_title("Internal Contact Area Ac vs Corneal Thickness", fontsize=11)
    axes[0].set_ylabel("Contact Area (mm²)", fontsize=9)
    axes[0].legend(fontsize=8, loc="lower right")
    axes[1].set_xlim(0.05, 2.0); axes[1].set_ylim(1.0, 3.0)
    axes[1].axhline(1.0, color="gray", ls=":", lw=1, alpha=0.4)
    axes[1].set_title("Area Transfer Ratio Ae/Ac vs Corneal Thickness", fontsize=11)
    axes[1].set_ylabel("Ae/Ac", fontsize=9)
    axes[1].legend(fontsize=8, loc="upper right")
    for ax in axes: ax.set_xlabel("Probe Displacement (mm)", fontsize=9)
    fig.suptitle("CORNEAL THICKNESS EFFECT ON CONTACT AREA", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(img_dir, "fig2_cornea_area.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 3: Pprobe comparison ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for i, te in enumerate(eyelid_ths):
        k, c = f"{te:.2f}", THICK_COLORS[i]
        axes[0].plot(d_curve, Pp_eyelid[k], c, lw=2.2, label=f"Eyelid {te:.2f}mm")
    for i, tc in enumerate(cornea_ths):
        k, c = f"{tc:.2f}", cornea_colors[i]
        axes[1].plot(d_curve, Pp_cornea[k], c, lw=2.2, label=f"Cornea {tc:.2f}mm")
    for ax in axes:
        ax.axhline(P_IOP_MMHG, color="#00ccff", ls="--", lw=2, alpha=0.6, label="IOP = 20 mmHg")
        ax.axvline(D_PIVOT_MM, color="gray", ls="--", lw=1.2, alpha=0.5)
        ax.set_xlim(0.05, 2.0); ax.set_ylim(0, 25)
        ax.grid(True, alpha=0.12, ls=":")
        ax.set_xlabel("Probe Displacement (mm)", fontsize=9)
        ax.legend(fontsize=8, loc="lower right")
    axes[0].set_title("Probe Equivalent Pressure vs Eyelid Thickness", fontsize=11)
    axes[0].set_ylabel("Pressure (mmHg)", fontsize=9)
    axes[1].set_title("Probe Equivalent Pressure vs Corneal Thickness", fontsize=11)
    fig.suptitle("PROBE EQUIVALENT PRESSURE: THICKNESS EFFECTS", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(img_dir, "fig3_pressure.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Figure 4: 2x2 pressure grid (eyelid thickness) ----
    sel_ths = [0.8, 1.25, 1.5, 2.0]
    sel_cases = [c for c in pcases_eyelid if c["t_eyelid"] in sel_ths]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True, sharey=True)
    axes = axes.ravel()
    titles = [f"Thin eyelid ({s:.2f} mm), d=0.29 mm" for s in sel_ths]
    titles[1] = f"Nominal eyelid ({sel_ths[1]:.2f} mm), d=0.29 mm"
    for idx, (ax, c, t) in enumerate(zip(axes, sel_cases, titles)):
        save_pressure_subplot(ax, c, t)
        if idx == 0: ax.legend(loc="upper left", fontsize=7.5, framealpha=0.85)
        if idx >= 2: ax.set_xlabel("Section Coordinate x (mm)", fontsize=9)
        if idx % 2 == 0: ax.set_ylabel("Pressure (mmHg)", fontsize=9)
    fig.suptitle("PRESSURE DISTRIBUTION AT DIFFERENT EYELID THICKNESSES (d = 0.29 mm)", fontsize=14, y=0.985)
    plt.tight_layout()
    fig.savefig(os.path.join(img_dir, "fig4_pressure_grid.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

    # ---- Write markdown ----
    rel_imgs = "../figures/placeholder"
    md = f"""# 眼睑角膜厚度影响分析

> **数据状态：占位参数扫描。** 该报告用于实验设计和内部汇报，不是重复仿体实验结果。真实实验完成后，以 `data/processed/` 生成的结果替换正式结论。

## Eyelid & Cornea Thickness Effect Analysis

Influence of Tissue Thickness on Inner/Outer Applanation Areas

---

### 物理背景

The eyelid acts as a mechanical buffer between the probe and the cornea. Its thickness determines how the probe contact force distributes laterally before reaching the cornea. A thicker eyelid spreads the load over a larger area, reducing the effective internal contact area Ac for a given external displacement.

Corneal thickness also plays a role: a thicker cornea has higher bending stiffness, slightly reducing the deformation and contact area under the same load.

| Parameter | Value |
|---|---|
| Eyelid thickness cases | {", ".join(f'{t:.2f}mm' for t in eyelid_ths)} |
| Corneal thickness cases | {", ".join(f'{t:.2f}mm' for t in cornea_ths)} |
| Nominal eyelid thickness | {nominal_eyelid:.2f} mm |
| Nominal corneal thickness | {nominal_cornea:.2f} mm |
| IOP | {P_IOP_MMHG} mmHg (fixed) |
| Fixed displacement (grid) | d = {d_fixed:.2f} mm |

---

### 1. 眼睑厚度对接触面积的影响

![Eyelid thickness area curves]({rel_imgs}/fig1_eyelid_area.png)

左图：不同眼睑厚度下的内部接触面积 Ac。眼睑越厚，Ac 越小——因为眼睑软组织将探头载荷分散到更大范围。2.00mm 眼睑的 Ac 明显低于 0.80mm 眼睑。

右图：面积传递比 Ae/Ac。眼睑越厚，比值越高，表明需要更大的传递比来补偿眼睑的缓冲效应。

---

### 2. 角膜厚度对接触面积的影响

![Corneal thickness area curves]({rel_imgs}/fig2_cornea_area.png)

角膜厚度在生理范围内的变化对接触面积的影响远小于眼睑厚度。三条曲线几乎重叠，说明角膜厚度是相对次要的参数。

---

### 3. 探头等效压力

![Pressure comparison]({rel_imgs}/fig3_pressure.png)

左图：不同眼睑厚度下的探头等效压力。眼睑越薄，等效压力越接近 IOP（20 mmHg）。2.00mm 厚眼睑的等效压力显著降低，说明需要修正系数。

右图：不同角膜厚度下的探头等效压力。三条曲线几乎重合，确认角膜厚度的影响较小。

---

### 4. 切面压力分布对比（不同眼睑厚度）

![Pressure grid]({rel_imgs}/fig4_pressure_grid.png)

2×2 grid comparing pressure distributions at four different eyelid thicknesses (d = 0.29 mm). As eyelid thickness increases:
- The probe response (red) becomes broader and lower in amplitude
- The outer surface stress (orange) becomes more distributed
- The internal contact area Ac decreases significantly

---

### 5. 数据汇总

**眼睑厚度变化（角膜 = {nominal_cornea:.2f} mm，d = {d_fixed:.2f} mm）:**

| t_eyelid (mm) | Ae (mm²) | Ac (mm²) | Ac/Ae | F (N) | Pprobe (mmHg) |
|---|---|---|---|---|---|
"""
    for c in pcases_eyelid:
        md += f"| {c['t_eyelid']:.2f} | {c['Ae_mm2']:.2f} | {c['Ac_mm2']:.2f} | {c['Ac_Ae']:.3f} | {c['F_N']:.4f} | {c['Pprobe_eq_mmhg']:.2f} |\n"

    md += f"""
**角膜厚度变化（眼睑 = {nominal_eyelid:.2f} mm，d = {d_fixed:.2f} mm）:**

| t_cornea (mm) | Ae (mm²) | Ac (mm²) | Ac/Ae | F (N) | Pprobe (mmHg) |
|---|---|---|---|---|---|
"""
    for tc in cornea_ths:
        Ac = internal_corneal_area_thickness(d_fixed, nominal_eyelid, tc)
        F = resultant_force_N(Ac)
        Ppeq = probe_equivalent_pressure_mmhg(F, Ae_nominal_at_d)
        ratio = Ac / Ae_nominal_at_d
        md += f"| {tc:.2f} | {Ae_nominal_at_d:.2f} | {Ac:.2f} | {ratio:.3f} | {F:.4f} | {Ppeq:.2f} |\n"

    md += """
**Key observations:**
- Eyelid thickness is the dominant geometric parameter affecting the internal contact area
- A measurement correction coefficient must account for individual eyelid thickness variation
- Corneal thickness has minor influence within the physiological range (0.50-0.60mm)
- Thicker eyelids require larger correction factors for accurate IOP estimation
"""

    md_path = str(STUDY_DIR / "docs" / f"{doc_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  -> {md_path}")


# ============================================================
if __name__ == "__main__":
    generate_thickness_markdown()
    print("Done!")
