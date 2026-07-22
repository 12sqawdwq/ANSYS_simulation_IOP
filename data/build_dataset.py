"""Build literature-derived corneal biomechanics tables and figures.

The generated files are deterministic and contain only values reported in the
linked primary sources or values evaluated from published constitutive equations.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
FIGURES = ROOT / "figures"
DRYAD_RAW = ROOT / "raw" / "dryad_z8w9ghx9f"
RETRIEVED = "2026-07-22"


def ci95_half_width(sd: float, n: int) -> float:
    """Normal-approximation 95% CI half width from published mean, SD, and n."""
    return 1.96 * sd / math.sqrt(n)


def write_csv(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(ROOT / name, index=False, encoding="utf-8-sig", float_format="%.8g")


def build_sources() -> pd.DataFrame:
    rows = [
        {
            "source_id": "CID_2021",
            "year": 2021,
            "title": "A Novel Indentation Assessment to Measure Corneal Biomechanical Properties in Glaucoma and Ocular Hypertension",
            "species": "human",
            "test_mode": "in_vivo_flat_punch_indentation",
            "sample_size": 186,
            "data_level": "group_summary_and_repeatability",
            "reusable_content": "CCT, IOP, stiffness and tangent modulus by healthy/OHT/POAG group",
            "inverse_use": "Primary human scale check; no raw force-displacement curves",
            "license": "CC BY-NC-ND 4.0 article",
            "doi": "10.1167/tvst.10.9.36",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8411863/",
        },
        {
            "source_id": "CID_METHOD_2019",
            "year": 2019,
            "title": "Characterization of Corneal Biomechanical Properties and Determination of Natural Intraocular Pressure Using CID-GAT",
            "species": "human",
            "test_mode": "in_vivo_flat_punch_indentation",
            "sample_size": np.nan,
            "data_level": "method_and_equations",
            "reusable_content": "E=s/Kg conversion and geometry/IOP dependence",
            "inverse_use": "Prevents treating CID modulus as a geometry-free constitutive parameter",
            "license": "Open-access article",
            "doi": "10.1167/tvst.8.5.10",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6743645/",
        },
        {
            "source_id": "REGIONAL_CID_2017",
            "year": 2017,
            "title": "In vivo measurement of regional corneal tangent modulus",
            "species": "human",
            "test_mode": "in_vivo_flat_punch_indentation",
            "sample_size": np.nan,
            "data_level": "regional_summary",
            "reusable_content": "Regional tangent modulus and the 0.3-0.6 mm fitting interval",
            "inverse_use": "Protocol alignment and spatial heterogeneity check",
            "license": "CC BY 4.0 article",
            "doi": "10.1038/s41598-017-14750-w",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5668273/",
        },
        {
            "source_id": "AGE_INFLATION_2010",
            "year": 2010,
            "title": "Characterization of age-related variation in corneal biomechanical properties",
            "species": "human_donor",
            "test_mode": "ex_vivo_inflation",
            "sample_size": 57,
            "data_level": "continuous_published_equations",
            "reusable_content": "Age-dependent first- and fourth-cycle stress-strain equations",
            "inverse_use": "Human nonlinear constitutive prior and age sensitivity",
            "license": "Open-access article",
            "doi": "10.1098/rsif.2010.0108",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2935603/",
        },
        {
            "source_id": "PORCINE_DRYAD_2020",
            "year": 2020,
            "title": "Inflation test on eye globe for experimental evaluation of corneal cross-linking",
            "species": "porcine_paired",
            "test_mode": "ex_vivo_inflation_and_inverse_FE",
            "sample_size": 14,
            "data_level": "complete_raw_workbooks",
            "reusable_content": "Pressure-apex curves, stress-strain curves, tangent modulus and paired samples",
            "inverse_use": "End-to-end inverse pipeline validation; not a human absolute target",
            "license": "CC0 1.0 dataset",
            "doi": "10.5061/dryad.z8w9ghx9f",
            "url": "https://datadryad.org/dataset/doi%3A10.5061/dryad.z8w9ghx9f",
        },
        {
            "source_id": "PORCINE_INFLATION_2020",
            "year": 2020,
            "title": "Experimental evaluation of stiffening effect induced by UVA/Riboflavin corneal cross-linking using intact porcine eye globes",
            "species": "porcine_paired",
            "test_mode": "ex_vivo_inflation_and_inverse_FE",
            "sample_size": 14,
            "data_level": "sample_level_ogden_table_and_summary",
            "reusable_content": "Seven paired Ogden mu/alpha estimates, RMS error and physiological-stress tangent modulus",
            "inverse_use": "Parameter-range and optimizer recovery benchmark",
            "license": "CC BY 4.0 article",
            "doi": "10.1371/journal.pone.0240724",
            "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0240724",
        },
        {
            "source_id": "SSI_2019",
            "year": 2019,
            "title": "Determination of Corneal Biomechanical Behavior in-vivo for Healthy Eyes Using CorVis ST Tonometry: Stress-Strain Index",
            "species": "human",
            "test_mode": "in_vivo_air_puff_full_field",
            "sample_size": np.nan,
            "data_level": "method_reference_curve",
            "reusable_content": "SSI reference stress-strain curve and deformation-profile strategy",
            "inverse_use": "Adds full-field deformation targets beyond a single force slope",
            "license": "CC BY 4.0 article",
            "doi": "10.3389/fbioe.2019.00105",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6532432/",
        },
        {
            "source_id": "HUMAN_VISCO_2014",
            "year": 2014,
            "title": "Analysis of the Viscoelastic Properties of the Human Cornea Using Scheimpflug Imaging in Inflation Experiment of Eye Globes",
            "species": "human_donor",
            "test_mode": "ex_vivo_inflation_creep_hysteresis",
            "sample_size": np.nan,
            "data_level": "curves_and_model_summary",
            "reusable_content": "Loading-unloading hysteresis, creep and modified Zener formulation",
            "inverse_use": "Defines hold/relaxation targets when viscoelasticity is introduced",
            "license": "CC BY 4.0 article",
            "doi": "10.1371/journal.pone.0112169",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4232387/",
        },
        {
            "source_id": "HUMAN_OCE_2024",
            "year": 2024,
            "title": "Simultaneous tensile and shear measurement of the human cornea in vivo using S0- and A0-wave optical coherence elastography",
            "species": "human",
            "test_mode": "in_vivo_OCE",
            "sample_size": 6,
            "data_level": "sample_level_table",
            "reusable_content": "CCT, out-of-plane shear modulus and in-plane tensile modulus by subject",
            "inverse_use": "Independent anisotropy/model-selection constraint",
            "license": "Open-access article",
            "doi": "10.1016/j.actbio.2023.12.019",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10872441/",
        },
        {
            "source_id": "NITI_OCE_2020",
            "year": 2020,
            "title": "Nearly-incompressible transverse isotropy of cornea elasticity: model and experiments with acoustic micro-tapping OCE",
            "species": "porcine",
            "test_mode": "ex_vivo_OCE",
            "sample_size": np.nan,
            "data_level": "method_and_supplement",
            "reusable_content": "NITI forward model separating tensile and shear responses",
            "inverse_use": "Constitutive upgrade path when isotropic residuals remain systematic",
            "license": "CC BY 4.0 article",
            "doi": "10.1038/s41598-020-69909-9",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7395720/",
        },
        {
            "source_id": "CUSTOM_GEOMETRY_2015",
            "year": 2015,
            "title": "Customized Finite Element Modelling of the Human Cornea",
            "species": "human",
            "test_mode": "clinical_geometry_and_FE",
            "sample_size": np.nan,
            "data_level": "open_supporting_geometry",
            "reusable_content": "Anterior coordinates and thickness data for customized geometry",
            "inverse_use": "Geometry/boundary uncertainty reduction before material fitting",
            "license": "CC BY 4.0 article",
            "doi": "10.1371/journal.pone.0130426",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4476710/",
        },
    ]
    frame = pd.DataFrame(rows)
    frame.insert(1, "retrieved", RETRIEVED)
    return frame


def build_cid_metrics() -> pd.DataFrame:
    rows = [
        ("overall", 186, 538.7, 33.2, 16.0, 4.1, 0.080, 0.017, 0.640, 0.147),
        ("healthy", 46, 536.0, 37.9, 13.8, 3.1, 0.076, 0.013, 0.614, 0.138),
        ("OHT", 33, 547.0, 30.1, 19.2, 3.4, 0.087, 0.016, 0.671, 0.154),
        ("POAG", 107, 537.3, 31.8, 15.8, 4.1, 0.080, 0.018, 0.641, 0.148),
    ]
    columns = [
        "group", "n", "cct_mean_um", "cct_sd_um", "iop_mean_mmhg", "iop_sd_mmhg",
        "stiffness_mean_n_per_mm", "stiffness_sd_n_per_mm", "modulus_mean_mpa", "modulus_sd_mpa",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    for prefix in ("cct", "iop", "stiffness", "modulus"):
        mean_col = f"{prefix}_mean_" + {"cct": "um", "iop": "mmhg", "stiffness": "n_per_mm", "modulus": "mpa"}[prefix]
        sd_col = mean_col.replace("mean", "sd")
        half = frame.apply(lambda row: ci95_half_width(row[sd_col], int(row["n"])), axis=1)
        frame[mean_col.replace("mean", "ci95_low")] = frame[mean_col] - half
        frame[mean_col.replace("mean", "ci95_high")] = frame[mean_col] + half
    frame.insert(0, "source_id", "CID_2021")
    return frame


def build_cid_repeatability() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("stiffness", "N/mm", 0.079, 0.013, 0.080, 0.013, 0.812),
            ("tangent_modulus", "MPa", 0.653, 0.123, 0.659, 0.129, 0.858),
        ],
        columns=["metric", "unit", "test1_mean", "test1_sd", "test2_mean", "test2_sd", "icc"],
    ).assign(source_id="CID_2021")


def build_model_benchmark() -> pd.DataFrame:
    c10_base = 0.11
    c01_base = 0.025
    scale = 0.75
    c10 = c10_base * scale
    c01 = c01_base * scale
    return pd.DataFrame(
        [
            {
                "model": "current_cornea_mooney_rivlin",
                "c10_base_mpa": c10_base,
                "c01_base_mpa": c01_base,
                "material_scale": scale,
                "c10_mpa": c10,
                "c01_mpa": c01,
                "d1_pa_inverse": 0.1e-6,
                "small_strain_e_mpa": 6.0 * (c10 + c01),
                "comparison_note": "Near-incompressible small-strain linearization; not identical to CID tangent-modulus extraction",
            }
        ]
    )


def build_age_curves() -> tuple[pd.DataFrame, pd.DataFrame]:
    cycles = {
        "first_loading": (
            lambda age: -53e-9 * age**2 + 26.8e-6 * age + 6.7e-6,
            lambda age: 0.0028 * age**2 - 0.308 * age + 100.0,
        ),
        "fourth_loading": (
            lambda age: 35e-9 * age**2 + 1.4e-6 * age + 1.03e-3,
            lambda age: 0.0013 * age**2 + 0.013 * age + 99.0,
        ),
    }
    rows = []
    for cycle, (a_fn, b_fn) in cycles.items():
        for age in range(40, 101, 10):
            a = a_fn(age)
            b = b_fn(age)
            for strain in np.linspace(0.0, 0.03, 61):
                stress = a * (math.exp(b * strain) - 1.0)
                tangent = a * b * math.exp(b * strain)
                rows.append(("AGE_INFLATION_2010", cycle, age, strain, stress, tangent, a, b))
    curves = pd.DataFrame(
        rows,
        columns=["source_id", "cycle", "age_year", "strain", "stress_mpa", "tangent_modulus_mpa", "coefficient_a_mpa", "coefficient_b"],
    )

    reference_rows = [
        (40, 0.01, 0.002, 0.231), (40, 0.02, 0.005, 0.580), (40, 0.03, 0.015, 1.457),
        (60, 0.01, 0.002, 0.327), (60, 0.02, 0.007, 0.817), (60, 0.03, 0.021, 2.042),
        (80, 0.01, 0.003, 0.431), (80, 0.02, 0.010, 1.095), (80, 0.03, 0.028, 2.784),
        (100, 0.01, 0.004, 0.556), (100, 0.02, 0.013, 1.471), (100, 0.03, 0.038, 3.891),
    ]
    reference = pd.DataFrame(
        reference_rows,
        columns=["age_year", "strain", "reported_stress_mpa", "reported_tangent_modulus_mpa"],
    )
    calc = curves[curves["cycle"] == "first_loading"].set_index(["age_year", "strain"])
    reference["equation_stress_mpa"] = [calc.loc[(a, e), "stress_mpa"] for a, e in zip(reference.age_year, reference.strain)]
    reference["equation_tangent_modulus_mpa"] = [calc.loc[(a, e), "tangent_modulus_mpa"] for a, e in zip(reference.age_year, reference.strain)]
    reference["stress_rounding_difference_mpa"] = reference.equation_stress_mpa - reference.reported_stress_mpa
    reference["modulus_rounding_difference_mpa"] = reference.equation_tangent_modulus_mpa - reference.reported_tangent_modulus_mpa
    reference["modulus_relative_difference_percent"] = 100.0 * reference.modulus_rounding_difference_mpa / reference.reported_tangent_modulus_mpa
    reference.insert(0, "source_id", "AGE_INFLATION_2010")
    return curves, reference


def build_oce_data() -> pd.DataFrame:
    rows = [
        (1, 31, "M", -3.00, 0.558, 81, 3, 3730, 570, 11.5),
        (2, 34, "F", -1.50, 0.509, 93, 12, 3060, 270, 8.3),
        (3, 33, "M", -2.50, 0.559, 99, 7, 3510, 460, 8.9),
        (4, 34, "M", -7.75, 0.601, 130, 10, 3980, 500, 7.7),
        (5, 62, "M", -3.00, 0.557, 70, 3, 3400, 140, 12.0),
        (6, 53, "M", -5.75, 0.578, 89, 2, 6060, 870, 22.4),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "subject", "age_year", "sex", "spherical_diopter", "cct_mm", "out_of_plane_shear_g_kpa",
            "out_of_plane_shear_sd_kpa", "in_plane_tensile_e_kpa", "in_plane_tensile_sd_kpa", "reported_e_over_4g",
        ],
    )
    frame["calculated_e_over_4g"] = frame.in_plane_tensile_e_kpa / (4.0 * frame.out_of_plane_shear_g_kpa)
    frame["ratio_consistency_flag"] = np.where(
        (frame.calculated_e_over_4g - frame.reported_e_over_4g).abs() <= 0.15,
        "consistent_with_rounded_moduli",
        "reported_ratio_inconsistent_with_displayed_moduli",
    )
    frame.insert(0, "source_id", "HUMAN_OCE_2024")
    return frame


def build_porcine_ogden() -> pd.DataFrame:
    control = [(0.0102, 96.07), (0.0100, 57.30), (0.0091, 64.69), (0.0144, 75.52), (0.0082, 57.65), (0.0096, 53.10), (0.0133, 51.36)]
    cxl = [(0.0403, 112.54), (0.0139, 73.31), (0.0126, 80.93), (0.0112, 151.22), (0.0088, 90.42), (0.0085, 84.40), (0.0288, 67.62)]
    rows = []
    for eye, (ctrl, treated) in enumerate(zip(control, cxl), start=1):
        rows.append(("PORCINE_INFLATION_2020", eye, "control_PBS", "left", ctrl[0], ctrl[1]))
        rows.append(("PORCINE_INFLATION_2020", eye, "CXL", "right", treated[0], treated[1]))
    return pd.DataFrame(rows, columns=["source_id", "pair_id", "treatment", "eye", "ogden_mu_mpa", "ogden_alpha"])


def build_porcine_summary(ogden: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for treatment, group in ogden.groupby("treatment", sort=False):
        for metric in ("ogden_mu_mpa", "ogden_alpha"):
            mean = group[metric].mean()
            sd = group[metric].std(ddof=1)
            half = ci95_half_width(sd, len(group))
            rows.append(("PORCINE_INFLATION_2020", treatment, metric, len(group), mean, sd, mean - half, mean + half))
    rows.extend(
        [
            ("PORCINE_INFLATION_2020", "control_PBS", "tangent_modulus_at_0p03mpa_mpa", 7, 1.73, 0.40, 1.73 - ci95_half_width(0.40, 7), 1.73 + ci95_half_width(0.40, 7)),
            ("PORCINE_INFLATION_2020", "CXL", "tangent_modulus_at_0p03mpa_mpa", 7, 2.48, 0.69, 2.48 - ci95_half_width(0.69, 7), 2.48 + ci95_half_width(0.69, 7)),
            ("PORCINE_INFLATION_2020", "control_PBS", "apex_displacement_at_27p25mmhg_mm", 7, 0.437, 0.063, 0.437 - ci95_half_width(0.063, 7), 0.437 + ci95_half_width(0.063, 7)),
            ("PORCINE_INFLATION_2020", "CXL", "apex_displacement_at_27p25mmhg_mm", 7, 0.307, 0.065, 0.307 - ci95_half_width(0.065, 7), 0.307 + ci95_half_width(0.065, 7)),
            ("PORCINE_INFLATION_2020", "all", "inverse_rms_error_percent", 14, 5.58, 1.79, 5.58 - ci95_half_width(1.79, 14), 5.58 + ci95_half_width(1.79, 14)),
        ]
    )
    return pd.DataFrame(rows, columns=["source_id", "group", "metric", "n", "mean", "sd", "ci95_low", "ci95_high"])


def build_inverse_targets(cid: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group in ("healthy", "OHT", "POAG"):
        item = cid[cid.group == group].iloc[0]
        rows.extend(
            [
                ("CID_2021", "human", group, "tangent_modulus", item.modulus_mean_mpa, item.modulus_sd_mpa, "MPa", "primary_scale_check", "0.3-0.6 mm slope-derived"),
                ("CID_2021", "human", group, "indentation_stiffness", item.stiffness_mean_n_per_mm, item.stiffness_sd_n_per_mm, "N/mm", "primary_indentation_target", "2 mm flat punch; 1 mm at 12 mm/s"),
            ]
        )
    rows.extend(
        [
            ("PORCINE_INFLATION_2020", "porcine", "control_PBS", "apex_displacement_at_27p25mmhg", 0.437, 0.063, "mm", "pipeline_validation", "Species-specific; do not fit as human absolute target"),
            ("PORCINE_INFLATION_2020", "porcine", "control_PBS", "tangent_modulus_at_0p03mpa", 1.73, 0.40, "MPa", "nonlinearity_validation", "Inflation-derived Ogden response"),
            ("PROJECT_EXPERIMENT", "eye_with_eyelid", "eyelid_0p8_to_1p25mm", "ae_over_ac_2deg", 1.75, 0.25, "ratio_range_midpoint_and_half_width", "primary_project_acceptance", "Internal experimental range 1.5-2.0; allow 20% error"),
            ("PROJECT_EXPERIMENT", "eye_with_eyelid", "eyelid_1p5mm", "ae_over_ac_2deg", 2.5, np.nan, "ratio", "secondary_project_acceptance", "Internal approximate reference"),
            ("PROJECT_EXPERIMENT", "eye_with_eyelid", "eyelid_2p0mm", "ae_over_ac_2deg", 5.0, np.nan, "ratio_lower_bound", "secondary_project_acceptance", "Internal observation: above 5 and below 9"),
        ]
    )
    return pd.DataFrame(rows, columns=["source_id", "species_or_system", "cohort_or_condition", "metric", "value", "sd_or_half_width", "unit", "inverse_role", "protocol_or_limit"])


def build_metric_priority() -> pd.DataFrame:
    rows = [
        (1, "full force-displacement curve", "F(delta)", "all converged substeps", "material scale plus nonlinearity", "Fit curve, not only endpoint or peak"),
        (2, "contact area-displacement curve", "Ae(delta)", "same states as force", "contact/boundary response", "Separates similar force curves with different pressure footprints"),
        (3, "multi-IOP response", "F(delta,IOP)", "at least 10/15/20/25 mmHg", "prestress versus material", "Required before interpreting force as IOP"),
        (4, "internal flattened area", "Ac(delta,theta)", "1/2/3 degree plus smooth/raw", "eyelid transmission", "Keep threshold sensitivity and face count"),
        (5, "full-field surface deformation", "u(r,delta)", "apex plus radial profile", "geometry/boundary/anisotropy", "More identifiable than apex displacement alone"),
        (6, "pressure-weighted contact centroid", "xp(delta)", "surface pressure integration", "offset and alignment", "Needed for eccentric cases"),
        (7, "loading-unloading hysteresis", "H", "matched-rate unload cycle", "viscoelastic loss", "Do not fit with hyperelastic parameters"),
        (8, "hold relaxation", "F(t)|delta", "fixed indentation hold", "time constants", "Only needed when adding viscoelasticity"),
        (9, "independent shear/tensile modulus", "G and E_in_plane", "OCE or mechanical test", "anisotropy/model choice", "Do not force both into one isotropic modulus"),
        (10, "geometry and covariates", "CCT/R/age/hydration", "per specimen", "nuisance control", "Fit material only after geometry is fixed"),
    ]
    return pd.DataFrame(rows, columns=["priority", "metric", "symbol", "minimum_protocol", "identifies", "implementation_note"])


def build_dryad_manifest() -> pd.DataFrame:
    files = [
        (455439, "eye1_stressvsstrain.xlsx", 24643, "8bc95605d4039c7105344ed32721c24040eee45980cab9bce2f8e88095d0d2ea"),
        (455440, "EYE1_target_curve_before_after_CXL.xlsx", 17602, "60bf6041058a62f8c667b41d6cf9626662ed8a932ec043662b60e51e40b37d77"),
        (455441, "eye2_stressvsstrain.xlsx", 24430, "d3e8ff691948c157116658c4c29a0c2f91b63bbcaef854991b738b2a7953690a"),
        (455442, "EYE2_target_curve_before_after_CXL.xlsx", 17595, "8a31a3d9c5c0d636116bcf9b2f95353ecb57ff68ab66f77228c2d681e7ba4473"),
        (455443, "eye3_stressvsstrain.xlsx", 24414, "0dd06d560bedd3f4583875b3f229ffb135a1f49e73468a248c47e54590964fca"),
        (455444, "EYE3_target_curve_before_after_CXL.xlsx", 17213, "d4439e62312407c1a1b8d78caf47d3f1a5c09e91b4736dc8bbe27009867c2468"),
        (455445, "eye4_stressvsstrain.xlsx", 24561, "51256ebef88a613b0d31641ba284583e1bb56a4111bb1c0bed74ea6229f927da"),
        (455446, "EYE4_target_curve_before_after_CXL.xlsx", 17600, "e4a28ae0196d3bb3693c6d82290a820f591142b38e92888c9fb57b1fa6182b4c"),
        (455447, "eye5_stressvsstrain.xlsx", 24921, "5c3443d6626ef5f70a9b1bd3de9d9f171a6b999358ccedcfb0153a03b667d4dd"),
        (455448, "EYE5_target_curve_before_after_CXL.xlsx", 17487, "a9e16172e8d76e1d83e21a11eb484ad7e7fc9e04faf5726188482426f38b3317"),
        (455449, "eye6_stressvsstrain.xlsx", 22816, "5a29caa24e8e6f14ec58994465f8f70b3a7a5024e1e1ee44aadfc6a8dcb31f36"),
        (455450, "EYE6_target_curve_before_after_CXL.xlsx", 16570, "10979b5e599ebfd395b728de8691acf3843b2e8f05c6f66ab1d9d738adaa6106"),
        (455451, "eye7_stressvsstrain.xlsx", 24844, "5d9dfa13edf2b36420b3603fe4c2fda65b3f1ce13e2dd142742236bfa679aaab"),
        (455452, "EYE7_target_cuve_before_after_CXL.xlsx", 17487, "c2e813c310038c0c55cc14cf527de0963b9b249bb8b1940d3f19b8bb2dfd01e3"),
        (455453, "Tangent_(Et)_vs_stress_curve.xlsx", 92514, "8c8f7bdc1bba436b127e026ac017289831e3c53044ab00a1da0b9e9d045574ac"),
    ]
    rows = []
    for file_id, filename, expected_bytes, expected_sha in files:
        path = DRYAD_RAW / filename
        if path.exists():
            actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            status = "verified" if actual_sha == expected_sha and path.stat().st_size == expected_bytes else "checksum_mismatch"
            actual_bytes = path.stat().st_size
        else:
            actual_sha = ""
            actual_bytes = np.nan
            status = "not_downloaded_aws_waf"
        role = "stress_strain" if "stressvsstrain" in filename else "pressure_apex_curve" if "target_" in filename else "tangent_modulus"
        rows.append(
            (file_id, filename, expected_bytes, expected_sha, actual_bytes, actual_sha, status, role, f"https://datadryad.org/downloads/file_stream/{file_id}")
        )
    return pd.DataFrame(
        rows,
        columns=["file_id", "filename", "expected_bytes", "expected_sha256", "local_bytes", "local_sha256", "local_status", "data_role", "official_download_url"],
    )


def plot_cid(cid: pd.DataFrame, model: pd.DataFrame) -> None:
    groups = cid[cid.group != "overall"].copy()
    labels = groups.group.tolist()
    x = np.arange(len(groups))
    colors = ["#2a9d8f", "#e76f51", "#457b9d"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), constrained_layout=True)

    axes[0].bar(x, groups.modulus_mean_mpa, color=colors, width=0.68)
    axes[0].errorbar(x, groups.modulus_mean_mpa, yerr=groups.modulus_mean_mpa - groups.modulus_ci95_low_mpa, fmt="none", ecolor="#222222", capsize=4)
    e0 = float(model.small_strain_e_mpa.iloc[0])
    axes[0].axhline(e0, color="#6a4c93", linestyle="--", linewidth=2, label=f"Current MR E0 = {e0:.4f} MPa")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("Tangent modulus (MPa)")
    axes[0].set_title("CID group means with 95% CI")
    axes[0].legend(frameon=False, fontsize=8)

    axes[1].bar(x, groups.stiffness_mean_n_per_mm, color=colors, width=0.68)
    axes[1].errorbar(x, groups.stiffness_mean_n_per_mm, yerr=groups.stiffness_mean_n_per_mm - groups.stiffness_ci95_low_n_per_mm, fmt="none", ecolor="#222222", capsize=4)
    axes[1].set_xticks(x, labels)
    axes[1].set_ylabel("Indentation stiffness (N/mm)")
    axes[1].set_title("2 mm flat-punch indentation")
    fig.suptitle("Human in-vivo CID benchmarks", fontsize=13)
    fig.savefig(FIGURES / "cid_human_benchmark.png", dpi=180)
    plt.close(fig)


def plot_age_curves(curves: pd.DataFrame) -> None:
    data = curves[curves.cycle == "first_loading"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.08, 0.92, data.age_year.nunique()))
    for color, (age, group) in zip(colors, data.groupby("age_year")):
        axes[0].plot(group.strain * 100, group.stress_mpa, color=color, label=f"{age} y")
        axes[1].plot(group.strain * 100, group.tangent_modulus_mpa, color=color, label=f"{age} y")
    axes[0].set_xlabel("Strain (%)")
    axes[0].set_ylabel("Stress (MPa)")
    axes[0].set_title("Published first-cycle equation")
    axes[1].set_xlabel("Strain (%)")
    axes[1].set_ylabel("Tangent modulus (MPa)")
    axes[1].set_title("Strain-dependent tangent modulus")
    axes[1].legend(frameon=False, ncol=2, fontsize=8)
    fig.suptitle("Human donor cornea age-dependent inflation response", fontsize=13)
    fig.savefig(FIGURES / "human_age_stress_strain.png", dpi=180)
    plt.close(fig)


def plot_porcine_ogden(ogden: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 5.0), constrained_layout=True)
    control = ogden[ogden.treatment == "control_PBS"].set_index("pair_id")
    cxl = ogden[ogden.treatment == "CXL"].set_index("pair_id")
    for pair_id in control.index:
        ax.plot(
            [control.loc[pair_id, "ogden_mu_mpa"], cxl.loc[pair_id, "ogden_mu_mpa"]],
            [control.loc[pair_id, "ogden_alpha"], cxl.loc[pair_id, "ogden_alpha"]],
            color="#adb5bd", linewidth=1.2, zorder=1,
        )
    ax.scatter(control.ogden_mu_mpa, control.ogden_alpha, color="#457b9d", s=55, label="PBS control", zorder=2)
    ax.scatter(cxl.ogden_mu_mpa, cxl.ogden_alpha, color="#e76f51", marker="s", s=55, label="CXL", zorder=2)
    for pair_id in control.index:
        ax.annotate(str(pair_id), (control.loc[pair_id, "ogden_mu_mpa"], control.loc[pair_id, "ogden_alpha"]), xytext=(4, 3), textcoords="offset points", fontsize=8)
    ax.set_xlabel("First-order Ogden mu (MPa)")
    ax.set_ylabel("First-order Ogden alpha")
    ax.set_title("Seven paired porcine inverse-FE estimates")
    ax.legend(frameon=False)
    fig.savefig(FIGURES / "porcine_ogden_pairs.png", dpi=180)
    plt.close(fig)


def plot_oce(oce: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    y = np.arange(len(oce))
    ax.barh(y - 0.18, oce.in_plane_tensile_e_kpa, height=0.34, color="#e9c46a", label="In-plane tensile E")
    ax.barh(y + 0.18, 4.0 * oce.out_of_plane_shear_g_kpa, height=0.34, color="#2a9d8f", label="4 x out-of-plane G")
    ax.set_yticks(y, [f"Subject {i}" for i in oce.subject])
    ax.set_xscale("log")
    ax.set_xlabel("Modulus scale (kPa, logarithmic)")
    ax.set_title("Human in-vivo OCE: tensile and shear responses are not equivalent")
    ax.legend(frameon=False)
    ax.invert_yaxis()
    fig.savefig(FIGURES / "human_oce_anisotropy.png", dpi=180)
    plt.close(fig)


def validate(
    cid: pd.DataFrame,
    model: pd.DataFrame,
    age_reference: pd.DataFrame,
    oce: pd.DataFrame,
    ogden: pd.DataFrame,
) -> None:
    healthy = cid[cid.group == "healthy"].iloc[0]
    assert abs(float(model.small_strain_e_mpa.iloc[0]) - 0.6075) < 1e-12
    assert abs(healthy.modulus_mean_mpa - 0.614) < 1e-12
    assert age_reference.stress_rounding_difference_mpa.abs().max() < 0.001
    # The article prints rounded equation coefficients and rounded table values.
    assert age_reference.modulus_relative_difference_percent.abs().max() < 0.6
    assert np.allclose(oce.iloc[:5].calculated_e_over_4g, oce.iloc[:5].reported_e_over_4g, atol=0.15)
    assert oce.iloc[5].ratio_consistency_flag == "reported_ratio_inconsistent_with_displayed_moduli"
    assert len(ogden) == 14
    control = ogden[ogden.treatment == "control_PBS"]
    cxl = ogden[ogden.treatment == "CXL"]
    assert abs(control.ogden_mu_mpa.mean() - 0.0107) < 0.0002
    assert abs(cxl.ogden_alpha.mean() - 94.3) < 0.1


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    DRYAD_RAW.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({"font.size": 9.5, "axes.titleweight": "bold", "axes.edgecolor": "#555555"})

    sources = build_sources()
    cid = build_cid_metrics()
    repeatability = build_cid_repeatability()
    model = build_model_benchmark()
    age_curves, age_reference = build_age_curves()
    oce = build_oce_data()
    ogden = build_porcine_ogden()
    porcine_summary = build_porcine_summary(ogden)
    targets = build_inverse_targets(cid)
    priorities = build_metric_priority()
    dryad_manifest = build_dryad_manifest()

    validate(cid, model, age_reference, oce, ogden)
    for frame, name in [
        (sources, "sources.csv"),
        (cid, "cid_group_metrics.csv"),
        (repeatability, "cid_repeatability.csv"),
        (model, "current_model_benchmark.csv"),
        (age_curves, "human_age_stress_strain.csv"),
        (age_reference, "human_age_reference_points.csv"),
        (oce, "human_oce_anisotropy.csv"),
        (ogden, "porcine_ogden_parameters.csv"),
        (porcine_summary, "porcine_inflation_summary.csv"),
        (targets, "inverse_targets.csv"),
        (priorities, "metric_priority.csv"),
        (dryad_manifest, "dryad_file_manifest.csv"),
    ]:
        write_csv(frame, name)

    plot_cid(cid, model)
    plot_age_curves(age_curves)
    plot_porcine_ogden(ogden)
    plot_oce(oce)
    verified = int((dryad_manifest.local_status == "verified").sum())
    print(f"Built 12 tables and 4 figures; Dryad files verified: {verified}/15")


if __name__ == "__main__":
    main()
