from __future__ import annotations

import numpy as np
import pandas as pd

from common import load_config, output_dir, write_csv


def run(config: dict | None = None) -> dict[str, pd.DataFrame]:
    config = config or load_config()
    out = output_dir(config)
    fitted = pd.read_csv(out / "fitted_parameters.csv")
    successful = fitted[fitted["fit_status"] == "success"].copy()

    theory_inputs = pd.DataFrame(
        [
            {
                "input": "A_p",
                "value": config["geometry"]["probe_area_mm2"],
                "unit": "mm^2",
                "status": "available",
                "source": "run metadata/config",
            },
            {
                "input": "s",
                "value": 0.259875,
                "unit": "mm",
                "status": "available_by_state",
                "source": "pressure scan actual_indent_mm (0.259875 or 0.28)",
            },
            {
                "input": "R_c",
                "value": config["geometry"]["corneal_radius_mm"],
                "unit": "mm",
                "status": "available",
                "source": "run metadata",
            },
            {
                "input": "k_l",
                "value": np.nan,
                "unit": "N/mm",
                "status": "not_identifiable",
                "source": "eyelid-only force/displacement is absent",
            },
            {
                "input": "k_c0",
                "value": np.nan,
                "unit": "N/mm",
                "status": "not_identifiable",
                "source": "no corneal force-displacement curves across pressure",
            },
            {
                "input": "alpha",
                "value": np.nan,
                "unit": "model-dependent",
                "status": "not_identifiable",
                "source": "cannot estimate beta/R_c without k_c(P)",
            },
        ]
    )

    mapping = {
        "a": "a_per_mmhg",
        "b": "b_dimensionless",
        "G0=1/b": "g0_1_over_b",
        "lambda=a/b": "lambda_a_over_b_per_mmhg",
    }
    rows = []
    for _, fit in successful.iterrows():
        for label, column in mapping.items():
            rows.append(
                {
                    "state": fit["state"],
                    "eyelid_thickness_mm": fit["eyelid_thickness_mm"],
                    "parameter": label,
                    "fit_value": fit[column],
                    "theory_value": np.nan,
                    "relative_error": np.nan,
                    "pair_status": "theory_not_computable",
                    "reason": "independent k_l, k_c0 and alpha are not identified by the current outputs",
                }
            )
    validation = pd.DataFrame(rows)
    agreement = pd.DataFrame(
        [
            {
                "comparison": "theory_vs_direct_fit",
                "n_pairs": 0,
                "pearson_r": np.nan,
                "pearson_p": np.nan,
                "spearman_rho": np.nan,
                "spearman_p": np.nan,
                "mean_relative_error": np.nan,
                "bland_altman_mean_difference": np.nan,
                "bland_altman_lower_loa": np.nan,
                "bland_altman_upper_loa": np.nan,
                "consistency_intercept": np.nan,
                "consistency_slope": np.nan,
                "status": "not_estimable_no_theory_pairs",
            }
        ]
    )
    write_csv(theory_inputs, out / "theory_input_availability.csv")
    write_csv(validation, out / "model_validation.csv")
    write_csv(agreement, out / "agreement_statistics.csv")
    return {"inputs": theory_inputs, "validation": validation, "agreement": agreement}


if __name__ == "__main__":
    run()
