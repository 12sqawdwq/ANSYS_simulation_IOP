import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# ============================================================
# AXISYMMETRIC MULTI-CASE PRESSURE DISTRIBUTION MODEL
# ============================================================
# Variables:
#   Inner surface  : prescribed uniform corneal inner pressure = 20 mmHg
#   Outer surface  : local eyelid outer contact stress field
#   Probe response : local probe-side stress/equivalent response
#
# Scalar probe reading:
#   F = P_IOP * Ac
#   Pprobe = F / Ae = P_IOP * Ac/Ae
#
# Important:
#   Pprobe is a scalar equivalent reading.
#   Outer surface curve is a local stress distribution and is not forced
#   to have the same average as Pprobe.
# ============================================================

plt.style.use("dark_background")

mpl.rcParams["font.family"] = "monospace"
mpl.rcParams["axes.facecolor"] = "#0b0b0b"
mpl.rcParams["figure.facecolor"] = "#0b0b0b"
mpl.rcParams["savefig.facecolor"] = "#0b0b0b"

# ============================================================
# 1. Units
# ============================================================

MMHG_TO_PA = 133.322
PA_TO_MMHG = 1.0 / MMHG_TO_PA

# ============================================================
# 2. Parameters
# ============================================================

P_IOP_MMHG = 20.0
P_IOP_PA = P_IOP_MMHG * MMHG_TO_PA

A_PROBE_MAX_MM2 = 14.657
R_PROBE_MAX_MM = np.sqrt(A_PROBE_MAX_MM2 / np.pi)

D_PIVOT_MM = 0.26

A_INTERNAL_AT_PIVOT_MM2 = 8.533
A_INTERNAL_ASYMPTOTE_MM2 = 14.20
A_INTERNAL_POST_PIVOT_TAU_MM = 0.85

DISPLACEMENT_CASES_MM = [0.16, 0.26, 0.50, 1.00]

X_MIN_MM = -3.0
X_MAX_MM = 3.0
N_X = 2600

x_mm = np.linspace(X_MIN_MM, X_MAX_MM, N_X)
rho_mm = np.abs(x_mm)

# ============================================================
# 3. Area models
# ============================================================

def external_probe_eyelid_area_mm2(d_mm):
    if d_mm <= 0:
        return 0.0

    if d_mm <= D_PIVOT_MM:
        return A_PROBE_MAX_MM2 * d_mm / D_PIVOT_MM

    return A_PROBE_MAX_MM2


def internal_corneal_applanation_area_mm2(d_mm):
    if d_mm <= 0:
        return 0.0

    if d_mm <= D_PIVOT_MM:
        eta = d_mm / D_PIVOT_MM
        return A_INTERNAL_AT_PIVOT_MM2 * eta**1.35

    return (
        A_INTERNAL_AT_PIVOT_MM2
        + (A_INTERNAL_ASYMPTOTE_MM2 - A_INTERNAL_AT_PIVOT_MM2)
        * (1.0 - np.exp(-(d_mm - D_PIVOT_MM) / A_INTERNAL_POST_PIVOT_TAU_MM))
    )


def radius_from_area_mm(area_mm2):
    if area_mm2 <= 0:
        return 0.0
    return np.sqrt(area_mm2 / np.pi)

# ============================================================
# 4. Force balance
# ============================================================

def resultant_force_N(Ac_mm2):
    return P_IOP_PA * Ac_mm2 * 1e-6


def probe_equivalent_pressure_mmhg(F_N, Ae_mm2):
    if Ae_mm2 <= 0:
        return 0.0

    P_pa = F_N / (Ae_mm2 * 1e-6)
    return P_pa * PA_TO_MMHG

# ============================================================
# 5. Pressure fields
# ============================================================

def inner_surface_pressure(rho_mm, rc_mm):
    """
    Corneal inner surface pressure.
    Prescribed uniform 20 mmHg.
    """
    P = np.zeros_like(rho_mm)

    if rc_mm <= 0:
        return P

    mask = rho_mm <= rc_mm
    P[mask] = P_IOP_MMHG

    return P


def outer_surface_pressure(rho_mm, re_mm, d_mm):
    """
    Eyelid outer-surface local contact stress field.

    This is not normalized to Pprobe = F/Ae.
    It is a local FEA-like field, so local values may be higher than
    the scalar probe-equivalent pressure.

    Shape target:
      - broad contact field
      - visible edge shoulders
      - high outer-surface stress band
      - mild deformation with increasing indentation
    """
    P = np.zeros_like(rho_mm)

    if re_mm <= 0:
        return P

    mask = rho_mm <= re_mm
    eta = rho_mm[mask] / re_mm

    distortion = np.clip((d_mm - 0.16) / (1.00 - 0.16), 0.0, 1.0)

    # Central/broad level: around internal pressure scale.
    base_level = 0.82 + 0.10 * distortion

    # Edge shoulder: mimics FEA red/yellow stress band near contact boundary.
    edge_amp = 0.58 - 0.16 * distortion
    edge_pos = 0.90
    edge_width = 0.085 + 0.025 * distortion

    edge_shoulder = edge_amp * np.exp(-((eta - edge_pos) / edge_width) ** 2)

    # Central shallow dome.
    central_dome = (0.20 + 0.10 * distortion) * np.exp(-(eta / 0.72) ** 4)

    # Soft taper near boundary, not too aggressive.
    boundary_taper = np.clip(1.0 - eta**8, 0.0, 1.0) ** 0.18

    shape = (base_level + central_dome + edge_shoulder) * boundary_taper

    # Local outer field referenced to internal IOP scale.
    # This is what fixes the previous "too flat / too low" issue.
    local_scale = P_IOP_MMHG * (1.00 + 0.10 * distortion)

    P[mask] = local_scale * shape

    return P


def probe_response_pressure(rho_mm, re_mm, Pprobe_equiv_mmhg, d_mm):
    """
    Probe-side local stress response.

    This is a local stress curve, not the scalar reading.
    The scalar reading remains Pprobe = F/Ae.
    """
    P = np.zeros_like(rho_mm)

    if re_mm <= 0:
        return P

    r_probe_effective = 0.95 * re_mm
    mask = rho_mm <= r_probe_effective
    eta = rho_mm[mask] / r_probe_effective

    distortion = np.clip((d_mm - 0.16) / (1.00 - 0.16), 0.0, 1.0)

    main_lobe = (1.0 - eta**2) ** (0.55 - 0.18 * distortion)

    shoulder = (0.34 - 0.12 * distortion) * np.exp(
        -((eta - 0.82) / (0.12 + 0.02 * distortion)) ** 2
    )

    central_reinforcement = 0.08 * distortion * np.exp(-(eta / 0.35) ** 2)

    shape = main_lobe + shoulder + central_reinforcement

    local_amplification = 1.85
    P[mask] = local_amplification * Pprobe_equiv_mmhg * shape

    return P


def add_noise(P, mask, amplitude, seed):
    rng = np.random.default_rng(seed)
    noisy = P + rng.normal(0, amplitude, len(P)) * mask
    return np.clip(noisy, 0.0, None)

# ============================================================
# 6. Build one case
# ============================================================

def build_case(d_mm):
    Ae = external_probe_eyelid_area_mm2(d_mm)
    Ac = internal_corneal_applanation_area_mm2(d_mm)

    re = radius_from_area_mm(Ae)
    rc = radius_from_area_mm(Ac)

    F = resultant_force_N(Ac)
    Pprobe_eq = probe_equivalent_pressure_mmhg(F, Ae)

    P_inner = inner_surface_pressure(rho_mm, rc)
    P_outer = outer_surface_pressure(rho_mm, re, d_mm)
    P_probe = probe_response_pressure(rho_mm, re, Pprobe_eq, d_mm)

    outer_mask = rho_mm <= re
    probe_mask = rho_mm <= 0.95 * re

    P_outer = add_noise(
        P_outer,
        outer_mask,
        amplitude=0.12,
        seed=1100 + int(d_mm * 1000)
    )

    P_probe = add_noise(
        P_probe,
        probe_mask,
        amplitude=0.15,
        seed=2100 + int(d_mm * 1000)
    )

    return {
        "d_mm": d_mm,
        "Ae_mm2": Ae,
        "Ac_mm2": Ac,
        "re_mm": re,
        "rc_mm": rc,
        "F_N": F,
        "Ac_Ae": Ac / Ae if Ae > 0 else 0.0,
        "Pprobe_eq_mmhg": Pprobe_eq,
        "P_inner": P_inner,
        "P_outer": P_outer,
        "P_probe": P_probe,
    }


cases = [build_case(d) for d in DISPLACEMENT_CASES_MM]

# ============================================================
# 7. Multi-case sectional plots
# ============================================================

fig, axes = plt.subplots(
    2,
    2,
    figsize=(17, 10),
    sharex=True,
    sharey=True
)

axes = axes.ravel()

for ax, c in zip(axes, cases):
    d = c["d_mm"]
    Ae = c["Ae_mm2"]
    Ac = c["Ac_mm2"]
    re = c["re_mm"]
    rc = c["rc_mm"]
    F = c["F_N"]
    ratio = c["Ac_Ae"]
    Pprobe_eq = c["Pprobe_eq_mmhg"]

    ax.axvline(
        0,
        color="gray",
        linestyle="-.",
        lw=1.1,
        alpha=0.75
    )

    ax.plot(
        x_mm,
        c["P_probe"],
        color="#ff4444",
        lw=2.9,
        label="Probe response"
    )

    ax.plot(
        x_mm,
        c["P_outer"],
        color="#ffaa00",
        lw=2.7,
        label="Outer surface"
    )

    ax.plot(
        x_mm,
        c["P_inner"],
        color="#00ccff",
        lw=2.6,
        label="Inner surface, 20 mmHg"
    )

    ax.fill_between(
        x_mm,
        0,
        c["P_probe"],
        color="#ff4444",
        alpha=0.16
    )

    ax.fill_between(
        x_mm,
        0,
        c["P_outer"],
        color="#ffaa00",
        alpha=0.14
    )

    ax.fill_between(
        x_mm,
        0,
        c["P_inner"],
        color="#00ccff",
        alpha=0.10
    )

    for s in [-1, 1]:
        ax.axvline(
            s * re,
            color="#ffaa00",
            linestyle=":",
            lw=1.7,
            alpha=0.70
        )

        ax.axvline(
            s * rc,
            color="#00ccff",
            linestyle=":",
            lw=1.7,
            alpha=0.70
        )

    panel_text = (
        f"d = {d:.2f} mm\n"
        f"Ae = {Ae:.2f} mm²\n"
        f"Ac = {Ac:.2f} mm²\n"
        f"Ac/Ae = {ratio:.3f}\n"
        f"F = {F:.4f} N\n"
        f"Pprobe = {Pprobe_eq:.2f} mmHg"
    )

    ax.text(
        2.86,
        43,
        panel_text,
        fontsize=9,
        color="white",
        ha="right",
        va="top",
        bbox=dict(
            facecolor="black",
            alpha=0.55,
            edgecolor="gray"
        )
    )

    ax.set_title(
        f"Probe displacement d = {d:.2f} mm",
        fontsize=12,
        pad=10
    )

    ax.grid(
        True,
        alpha=0.10,
        linestyle=":"
    )

    ax.set_xlim(X_MIN_MM, X_MAX_MM)
    ax.set_ylim(0, 45)

axes[0].legend(
    loc="upper left",
    fontsize=9,
    framealpha=0.85
)

for ax in axes[2:]:
    ax.set_xlabel(
        "Section Coordinate x (mm), center axis at x = 0",
        fontsize=10
    )

for ax in axes[::2]:
    ax.set_ylabel(
        "Pressure / Equivalent Stress (mmHg)",
        fontsize=10
    )

fig.suptitle(
    "AXISYMMETRIC SECTIONAL PRESSURE DISTRIBUTION\n"
    "Probe Response / Eyelid Outer Surface / Corneal Inner Surface",
    fontsize=15,
    y=0.985
)

plt.tight_layout()
plt.show()

# ============================================================
# 8. Summary curves
# ============================================================

d_curve = np.linspace(0.001, 1.20, 600)

Ae_curve = np.array([
    external_probe_eyelid_area_mm2(d)
    for d in d_curve
])

Ac_curve = np.array([
    internal_corneal_applanation_area_mm2(d)
    for d in d_curve
])

F_curve = np.array([
    resultant_force_N(Ac)
    for Ac in Ac_curve
])

Pprobe_curve = np.array([
    probe_equivalent_pressure_mmhg(F, Ae)
    for F, Ae in zip(F_curve, Ae_curve)
])

ratio_curve = Ac_curve / Ae_curve

fig2, axes2 = plt.subplots(1, 3, figsize=(18, 5))

ax = axes2[0]
ax.plot(d_curve, Ae_curve, color="#ffaa00", lw=2.8, label="External area Ae")
ax.plot(d_curve, Ac_curve, color="#00ccff", lw=2.8, label="Internal area Ac")
ax.axvline(D_PIVOT_MM, color="gray", linestyle="--", lw=1.5, label="pivot = 0.26 mm")

for d in DISPLACEMENT_CASES_MM:
    ax.axvline(d, color="white", linestyle=":", lw=0.8, alpha=0.35)

ax.set_title("Contact Area Evolution")
ax.set_xlabel("Probe displacement d (mm)")
ax.set_ylabel("Area (mm²)")
ax.grid(True, alpha=0.12, linestyle=":")
ax.legend(fontsize=9)

ax = axes2[1]
ax.plot(d_curve, Pprobe_curve, color="#ff4444", lw=2.8, label="Probe equivalent pressure F/Ae")
ax.axhline(P_IOP_MMHG, color="#00ccff", linestyle="--", lw=2.0, label="Internal IOP = 20 mmHg")
ax.axvline(D_PIVOT_MM, color="gray", linestyle="--", lw=1.5, label="pivot = 0.26 mm")

for d in DISPLACEMENT_CASES_MM:
    ax.axvline(d, color="white", linestyle=":", lw=0.8, alpha=0.35)

ax.set_title("Probe Equivalent Reading")
ax.set_xlabel("Probe displacement d (mm)")
ax.set_ylabel("Pressure (mmHg)")
ax.grid(True, alpha=0.12, linestyle=":")
ax.legend(fontsize=9)

ax = axes2[2]
ax.plot(d_curve, ratio_curve, color="white", lw=2.8, label="Ac/Ae = Pprobe/PIOP")
ax.axhline(1.0, color="gray", linestyle=":", lw=1.5, label="no area mismatch")
ax.axvline(D_PIVOT_MM, color="gray", linestyle="--", lw=1.5, label="pivot = 0.26 mm")

for d in DISPLACEMENT_CASES_MM:
    ax.axvline(d, color="white", linestyle=":", lw=0.8, alpha=0.35)

ax.set_title("Area Transfer Ratio")
ax.set_xlabel("Probe displacement d (mm)")
ax.set_ylabel("Ac/Ae")
ax.set_ylim(0.0, 1.05)
ax.grid(True, alpha=0.12, linestyle=":")
ax.legend(fontsize=9)

plt.tight_layout()
plt.show()

# ============================================================
# 9. Output
# ============================================================

print("\n========== AXISYMMETRIC MULTI-CASE MODEL SUMMARY ==========")
print(f"Prescribed internal IOP : {P_IOP_MMHG:.2f} mmHg")
print(f"Pivot displacement      : {D_PIVOT_MM:.3f} mm")
print(f"Probe maximum area Ae   : {A_PROBE_MAX_MM2:.3f} mm²")
print("")

for c in cases:
    print(
        f"d = {c['d_mm']:.2f} mm | "
        f"Ae = {c['Ae_mm2']:.3f} mm² | "
        f"Ac = {c['Ac_mm2']:.3f} mm² | "
        f"Ac/Ae = {c['Ac_Ae']:.3f} | "
        f"F = {c['F_N']:.6f} N | "
        f"Pprobe = {c['Pprobe_eq_mmhg']:.2f} mmHg"
    )

print("")
print("Interpretation:")
print("  Inner surface pressure is prescribed as uniform 20 mmHg.")
print("  Probe equivalent pressure is F/Ae and remains lower than 20 mmHg when Ac < Ae.")
print("  Outer surface is plotted as a local FEA-like contact stress field,")
print("  not forced to equal the scalar probe-equivalent pressure.")
print("  The scalar Pprobe and the red/orange local stress curves are different quantities.")