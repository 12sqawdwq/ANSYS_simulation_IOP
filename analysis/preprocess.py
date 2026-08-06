from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import load_config, output_dir, read_csv, relative_path, source_path, write_csv, write_json


STANDARD_COLUMNS = [
    "record_type",
    "source_file",
    "case_id",
    "state",
    "eyelid_thickness_mm",
    "cornea_thickness_mm",
    "p_iop_mmhg",
    "p_iop_pa",
    "p_probe_delta_mmhg",
    "p_probe_delta_pa",
    "p_probe_absolute_mmhg",
    "probe_force_n",
    "probe_force_delta_n",
    "probe_displacement_mm",
    "eyelid_modulus_scale",
    "cornea_modulus_scale",
    "corneal_radius_mm",
    "probe_area_mm2",
    "corneal_applanation_area_mm2",
    "contact_force_n",
    "eyelid_displacement_mm",
    "corneal_displacement_mm",
    "tangent_stiffness_n_per_mm",
    "source_status",
    "assumption_note",
]


def blank_frame(size: int) -> pd.DataFrame:
    return pd.DataFrame({column: [np.nan] * size for column in STANDARD_COLUMNS})


def build_pressure_scan(config: dict) -> pd.DataFrame:
    raw = read_csv(config, "pressure_scan")
    frame = blank_frame(len(raw))
    frame["record_type"] = "pressure_scan"
    frame["source_file"] = relative_path(source_path(config, "pressure_scan"))
    frame["case_id"] = raw["state"].astype(str) + "_iop_" + raw["input_iop_mmhg"].astype(str)
    frame["state"] = raw["state"]
    frame["eyelid_thickness_mm"] = config["geometry"]["reference_thickness_mm"]
    frame["cornea_thickness_mm"] = 0.60
    frame["p_iop_mmhg"] = raw["input_iop_mmhg"]
    frame["p_probe_delta_mmhg"] = raw["delta_probe_pressure_mmhg"]
    frame["probe_force_n"] = raw["probe_force_n"]
    frame["probe_force_delta_n"] = raw["delta_force_n"]
    frame["probe_displacement_mm"] = raw["actual_indent_mm"]
    frame["probe_area_mm2"] = config["geometry"]["probe_area_mm2"]
    frame["corneal_radius_mm"] = config["geometry"]["corneal_radius_mm"]
    frame["corneal_applanation_area_mm2"] = raw["inner_ac_5deg_mm2"]
    frame["source_status"] = "accepted_FE_summary"
    frame["assumption_note"] = "P_probe is zero-referenced delta pressure; absolute tissue preload is excluded"
    return frame


def build_thickness_endpoints(config: dict) -> pd.DataFrame:
    raw = read_csv(config, "thickness_pressure_endpoints")
    records: list[dict] = []
    source = relative_path(source_path(config, "thickness_pressure_endpoints"))
    for row in raw.to_dict("records"):
        common = {
            "record_type": "thickness_pressure_endpoint",
            "source_file": source,
            "state": "sensitivity_0p28",
            "eyelid_thickness_mm": row["eyelid_thickness_mm"],
            "cornea_thickness_mm": 0.60,
            "probe_displacement_mm": row["indent_mm"],
            "probe_area_mm2": row["probe_area_mm2"],
            "corneal_radius_mm": config["geometry"]["corneal_radius_mm"],
            "source_status": row["status"],
            "eyelid_modulus_scale": 1.0,
            "cornea_modulus_scale": 0.75,
        }
        records.append(
            {
                **common,
                "case_id": f"h{row['eyelid_thickness_mm']}_iop0",
                "p_iop_mmhg": 0.0,
                "p_probe_delta_mmhg": 0.0,
                "p_probe_absolute_mmhg": row["probe_pressure_zero_baseline_mmhg"],
                "probe_force_n": row["force_zero_baseline_n"],
                "probe_force_delta_n": 0.0,
                "corneal_applanation_area_mm2": np.nan,
                "assumption_note": "independent zero-IOP FE baseline",
            }
        )
        records.append(
            {
                **common,
                "case_id": f"h{row['eyelid_thickness_mm']}_iop{row['actual_iop_mmhg']}",
                "p_iop_mmhg": row["actual_iop_mmhg"],
                "p_probe_delta_mmhg": row["delta_probe_pressure_mmhg"],
                "p_probe_absolute_mmhg": row["probe_pressure_iop_mmhg"],
                "probe_force_n": row["force_iop_n"],
                "probe_force_delta_n": row["delta_force_n"],
                "corneal_applanation_area_mm2": row["inner_ac_5deg_mm2"],
                "assumption_note": "20-mmHg FE endpoint paired with independent zero baseline",
            }
        )
    return pd.DataFrame.from_records(records).reindex(columns=STANDARD_COLUMNS)


def build_force_curves(config: dict) -> pd.DataFrame:
    raw = read_csv(config, "force_displacement")
    frame = blank_frame(len(raw))
    frame["record_type"] = "force_displacement"
    frame["source_file"] = relative_path(source_path(config, "force_displacement"))
    frame["case_id"] = raw["source_case"].astype(str) + "_s" + raw["indentation_mm"].astype(str)
    frame["state"] = "loading_path_0p8"
    frame["eyelid_thickness_mm"] = raw["eyelid_thickness_mm"]
    frame["cornea_thickness_mm"] = raw["cornea_thickness_mm"]
    frame["p_iop_mmhg"] = config["stiffness"]["force_curve_assumed_iop_mmhg"]
    frame["p_probe_absolute_mmhg"] = raw["probe_equivalent_pressure_mmhg"]
    frame["probe_force_n"] = raw["probe_force_n"]
    frame["probe_displacement_mm"] = raw["actual_indentation_mm"]
    frame["tangent_stiffness_n_per_mm"] = raw["tangent_stiffness_n_per_mm"]
    frame["probe_area_mm2"] = config["geometry"]["probe_area_mm2"]
    frame["corneal_radius_mm"] = config["geometry"]["corneal_radius_mm"]
    frame["source_status"] = "accepted_loading_path"
    frame["assumption_note"] = "metadata omits IOP; linked study report identifies the source sweep as IOP=20 mmHg"
    return frame


def data_dictionary(config: dict) -> pd.DataFrame:
    rows = [
        ("record_type", "category", "standardized record family", "pipeline"),
        ("source_file", "path", "source relative path", "pipeline"),
        ("case_id", "string", "unique row/case identifier", "case/source_case/state"),
        ("state", "category", "FE work point", "state or inferred dataset state"),
        ("eyelid_thickness_mm", "mm", "eyelid thickness h_l", "eyelid_thickness_mm"),
        ("cornea_thickness_mm", "mm", "corneal thickness", "cornea_thickness_mm/run metadata"),
        ("p_iop_mmhg", "mmHg", "applied intraocular pressure", "input_iop_mmhg/actual_iop_mmhg/iop_mmhg"),
        ("p_iop_pa", "Pa", "applied intraocular pressure in SI", "p_iop_mmhg × pa_per_mmhg"),
        ("p_probe_delta_mmhg", "mmHg", "zero-referenced probe pressure used in rational fit", "delta_probe_pressure_mmhg"),
        ("p_probe_delta_pa", "Pa", "zero-referenced probe pressure in SI", "p_probe_delta_mmhg × pa_per_mmhg"),
        ("p_probe_absolute_mmhg", "mmHg", "absolute force/nominal probe-area pressure including tissue baseline", "probe_pressure_* or probe_equivalent_pressure_mmhg"),
        ("probe_force_n", "N", "total probe reaction force", "probe_force_n/force_iop_n"),
        ("probe_force_delta_n", "N", "probe force increment from the independent 0-IOP baseline", "delta_force_n"),
        ("probe_displacement_mm", "mm", "nominal/actual probe advance s", "actual_indent_mm/indent_mm/indentation_mm"),
        ("eyelid_modulus_scale", "1", "eyelid material multiplier", "eyelid_material_scale"),
        ("cornea_modulus_scale", "1", "corneal material multiplier", "cornea_material_scale"),
        ("corneal_radius_mm", "mm", "nominal corneal curvature radius R_c", "run_spec/config"),
        ("probe_area_mm2", "mm^2", "nominal full probe area A_p", "probe_area_mm2 or diameter 4.32 mm"),
        ("corneal_applanation_area_mm2", "mm^2", "5-degree corneal-side area proxy, not validated optical applanation", "inner_ac_5deg_mm2"),
        ("contact_force_n", "N", "probe contact force when explicitly integrated", "probe_contact_force_n"),
        ("eyelid_displacement_mm", "mm", "eyelid-only displacement; absent in current selected data", "candidate mapping only"),
        ("corneal_displacement_mm", "mm", "corneal-side displacement proxy", "inner_max_downward_mm when present"),
        ("tangent_stiffness_n_per_mm", "N/mm", "coupled probe-system tangent stiffness", "tangent_stiffness_n_per_mm"),
    ]
    return pd.DataFrame(rows, columns=["column", "unit", "meaning", "source_or_derivation"])


def run(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    out = output_dir(config)
    pieces = [build_pressure_scan(config), build_thickness_endpoints(config), build_force_curves(config)]
    tidy = pd.concat(pieces, ignore_index=True).reindex(columns=STANDARD_COLUMNS)
    factor = config["units"]["pa_per_mmhg"]
    tidy["p_iop_pa"] = pd.to_numeric(tidy["p_iop_mmhg"], errors="coerce") * factor
    tidy["p_probe_delta_pa"] = pd.to_numeric(tidy["p_probe_delta_mmhg"], errors="coerce") * factor
    duplicate_keys = ["record_type", "case_id", "state"]
    duplicate_mask = tidy.duplicated(duplicate_keys, keep=False)

    pressure = tidy[tidy["record_type"] == "pressure_scan"].copy()
    expected = (
        pressure["probe_force_delta_n"] * 1e6
        / pressure["probe_area_mm2"]
        / factor
    )
    unit_error = pressure["p_probe_delta_mmhg"] - expected
    quality = {
        "row_count": int(len(tidy)),
        "row_count_by_record_type": tidy["record_type"].value_counts().to_dict(),
        "duplicate_key_rows": int(duplicate_mask.sum()),
        "maximum_pressure_conversion_error_mmhg": float(np.nanmax(np.abs(unit_error))),
        "missing_counts": {key: int(value) for key, value in tidy.isna().sum().items()},
        "pressure_fit_uses_delta_not_absolute": True,
    }

    exclusions = pd.DataFrame(
        [
            {
                "scope": "thick/data/placeholder",
                "reason": "placeholder data explicitly documented as non-FE evidence",
                "action": "excluded from all inference",
            },
            {
                "scope": "contact_rezeroed candidate areas",
                "reason": "source status says candidate_not_approved",
                "action": "retained in inventory; excluded from primary calibration",
            },
            {
                "scope": "older/superseded high-IOP summaries",
                "reason": "complete 0-60 step-2.5 summary is the most inclusive frozen dataset",
                "action": "retained in inventory; excluded to prevent duplicate FE states",
            },
            {
                "scope": "absolute probe pressure",
                "reason": "nonzero tissue preload at P_IOP=0 conflicts with the model's zero intercept",
                "action": "retained in tidy table; zero-referenced delta pressure used for fit",
            },
            {
                "scope": "raw material/offset studies",
                "reason": "different experiment or response definition",
                "action": "retained in inventory; not pooled",
            },
        ]
    )
    dictionary = data_dictionary(config)
    write_csv(tidy, out / "tidy_data.csv")
    write_csv(dictionary, out / "data_dictionary.csv")
    write_csv(exclusions, out / "exclusion_log.csv")
    write_json(quality, out / "data_quality_summary.json")
    return {"tidy": tidy, "dictionary": dictionary, "exclusions": exclusions}


if __name__ == "__main__":
    run()
