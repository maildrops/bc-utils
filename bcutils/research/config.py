from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def load_instruments(config_dir: Path | None = None) -> Dict[str, Dict[str, Any]]:
    config_dir = config_dir or PROJECT_ROOT / "config"
    return load_yaml(config_dir / "instruments.yaml").get("instruments", {})


def load_roll_rule(config_dir: Path | None = None) -> Dict[str, Any]:
    config_dir = config_dir or PROJECT_ROOT / "config"
    return load_yaml(config_dir / "roll_rules.yaml").get("default_roll_rule", {})


def load_aggregation_config(config_dir: Path | None = None) -> Dict[str, Any]:
    config_dir = config_dir or PROJECT_ROOT / "config"
    return load_yaml(config_dir / "aggregation.yaml")


def selected_symbols(requested: str, instruments: Dict[str, Dict[str, Any]]) -> List[str]:
    if requested.upper() == "ALL":
        return sorted(instruments.keys())
    symbol = requested.upper()
    if symbol not in instruments:
        known = ", ".join(sorted(instruments))
        raise ValueError(f"Unknown symbol {symbol!r}. Known symbols: {known}")
    return [symbol]


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
