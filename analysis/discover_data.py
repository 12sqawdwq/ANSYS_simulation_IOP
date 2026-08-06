from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import ROOT, load_config, output_dir, relative_path, write_csv, write_json


DATA_EXTENSIONS = {".csv", ".tsv", ".txt", ".xlsx", ".xls", ".dat", ".json"}


def classify(path: Path) -> tuple[str, str]:
    normalized = path.as_posix().lower()
    if normalized.startswith("analysis/outputs/"):
        return "generated", "pipeline output"
    if "placeholder" in normalized:
        return "excluded", "placeholder data are not FE evidence"
    if normalized.startswith("data/raw/") or normalized.startswith("data/"):
        return "context", "material/experimental reference data, not the thickness-pressure FE matrix"
    if normalized.startswith("offset/") or normalized.startswith("baseline/"):
        return "context", "different offset/baseline study"
    if "high_iop_mechanical_transfer" in normalized:
        return "primary", "multi-IOP FE transfer data at h=1.25 mm"
    if normalized.startswith("thick/"):
        if "candidate" in normalized or "sensitivity" in normalized:
            return "diagnostic", "candidate/sensitivity post-processing only"
        return "primary", "thickness FE data or associated metadata"
    return "context", "not selected by the primary analysis routes"


def first_line(path: Path) -> str:
    if path.suffix.lower() not in {".csv", ".tsv", ".txt", ".dat"}:
        return ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            return handle.readline().strip()[:4000]
    except OSError:
        return ""


def run(config: dict | None = None) -> pd.DataFrame:
    config = config or load_config()
    out = output_dir(config)
    rows: list[dict] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DATA_EXTENSIONS:
            continue
        rel = relative_path(path)
        if rel.startswith("analysis/outputs/"):
            continue
        relevance, reason = classify(Path(rel))
        rows.append(
            {
                "relative_path": rel,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "modified_time": path.stat().st_mtime,
                "relevance": relevance,
                "classification_reason": reason,
                "header_or_first_line": first_line(path),
            }
        )
    inventory = pd.DataFrame(rows)
    write_csv(inventory, out / "data_inventory.csv")
    summary = {
        "total_files": int(len(inventory)),
        "counts_by_extension": inventory["extension"].value_counts().to_dict(),
        "counts_by_relevance": inventory["relevance"].value_counts().to_dict(),
    }
    write_json(summary, out / "data_inventory_summary.json")
    return inventory


if __name__ == "__main__":
    run()

