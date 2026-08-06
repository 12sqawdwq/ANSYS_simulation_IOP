from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


ANALYSIS_DIR = Path(__file__).resolve().parent
ROOT = ANALYSIS_DIR.parent


def load_config() -> dict[str, Any]:
    with (ANALYSIS_DIR / "config.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def output_dir(config: dict[str, Any]) -> Path:
    path = ROOT / config["project"]["output_dir"]
    path.mkdir(parents=True, exist_ok=True)
    (path / "figures").mkdir(exist_ok=True)
    return path


def source_path(config: dict[str, Any], key: str) -> Path:
    return ROOT / config["inputs"][key]


def read_csv(config: dict[str, Any], key: str) -> pd.DataFrame:
    path = source_path(config, key)
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return pd.read_csv(path)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)


def finite(values: pd.Series | np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def cv(values: pd.Series | np.ndarray) -> float:
    array = finite(values)
    if len(array) < 2 or np.isclose(np.mean(array), 0.0):
        return np.nan
    return float(np.std(array, ddof=1) / np.mean(array))


def fmt(value: Any, digits: int = 4, missing: str = "不可估计") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return missing
    if not np.isfinite(number):
        return missing
    return f"{number:.{digits}g}"


def md_table(frame: pd.DataFrame, digits: int = 4) -> str:
    shown = frame.copy()
    for column in shown.select_dtypes(include=[np.number]).columns:
        shown[column] = shown[column].map(
            lambda value: "NA" if pd.isna(value) else f"{value:.{digits}g}"
        )
    header = "| " + " | ".join(map(str, shown.columns)) + " |"
    divider = "|" + "|".join(["---"] * len(shown.columns)) + "|"
    rows = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in shown.itertuples(index=False, name=None)
    ]
    return "\n".join([header, divider, *rows])


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()

