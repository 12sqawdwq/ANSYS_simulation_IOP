from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy
import pandas
import scipy
import sklearn
import statsmodels
import yaml

import build_report
import discover_data
import extract_stiffness
import fit_pressure_model
import make_figures
import preprocess
import sensitivity_analysis
import validate_theory
from common import ANALYSIS_DIR, load_config, output_dir, relative_path, write_csv, write_json


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run() -> None:
    config = load_config()
    out = output_dir(config)
    discover_data.run(config)
    preprocess.run(config)
    fit_pressure_model.run(config)
    extract_stiffness.run(config)
    sensitivity_analysis.run(config)
    validate_theory.run(config)
    make_figures.run(config)
    build_report.build(config)

    required = [
        "tidy_data.csv",
        "data_dictionary.csv",
        "fitted_parameters.csv",
        "stiffness_parameters.csv",
        "sensitivity_results.csv",
        "model_validation.csv",
        "report.md",
    ]
    missing = [name for name in required if not (out / name).exists()]
    figures = sorted((out / "figures").glob("fig*.svg"))
    validation = {
        "status": "pass" if not missing and len(figures) >= 10 else "fail",
        "missing_required_outputs": missing,
        "svg_figure_count": len(figures),
        "required_minimum_svg_figures": 10,
    }
    write_json(validation, out / "pipeline_validation.json")

    manifest_rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "output_manifest.csv":
            manifest_rows.append(
                {
                    "relative_path": path.relative_to(out).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    write_csv(pandas.DataFrame(manifest_rows), out / "output_manifest.csv")

    run_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": {
            "pandas": pandas.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
            "scikit_learn": sklearn.__version__,
            "matplotlib": matplotlib.__version__,
            "pyyaml": yaml.__version__,
        },
        "random_seed": config["project"]["random_seed"],
        "bootstrap_replicates": config["fit"]["bootstrap_replicates"],
        "config_sha256": sha256(ANALYSIS_DIR / "config.yaml"),
        "validation": validation,
    }
    write_json(run_manifest, out / "run_manifest.json")


if __name__ == "__main__":
    run()
