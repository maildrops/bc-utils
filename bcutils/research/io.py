from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from bcutils.research.contracts import (
    ContractInfo,
    infer_contract_info,
    sorted_contracts,
)


COLUMN_ALIASES = {
    "timestamp": "timestamp",
    "time": "timestamp",
    "date": "timestamp",
    "datetime": "timestamp",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "last": "close",
    "volume": "volume",
    "vol": "volume",
}


def normalize_columns(frame: pd.DataFrame, timezone: str = "UTC") -> pd.DataFrame:
    rename = {}
    for column in frame.columns:
        normalized = str(column).strip().lower().replace(" ", "_")
        rename[column] = COLUMN_ALIASES.get(normalized, normalized)
    frame = frame.rename(columns=rename)
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    frame = frame.copy()
    parsed = pd.to_datetime(frame["timestamp"], errors="coerce")
    if getattr(parsed.dt, "tz", None) is None:
        frame["timestamp"] = parsed.dt.tz_localize(timezone).dt.tz_convert("UTC")
    else:
        frame["timestamp"] = parsed.dt.tz_convert("UTC")
    if frame["timestamp"].isna().any():
        bad = int(frame["timestamp"].isna().sum())
        raise ValueError(f"{bad} timestamps could not be parsed")
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[required]
        .dropna(subset=["open", "high", "low", "close"])
        .sort_values("timestamp")
    )


def raw_contract_files(data_root: Path, symbol: str) -> List[Path]:
    symbol_dir = data_root / "raw_contracts" / symbol.upper()
    if not symbol_dir.exists():
        return []
    return sorted(path for path in symbol_dir.glob("*.csv") if path.is_file())


def load_contract_file(
    path: Path, symbol: str, source: str = "barchart", timezone: str = "UTC"
) -> pd.DataFrame:
    info = infer_contract_info(path, symbol)
    frame = normalize_columns(pd.read_csv(path), timezone=timezone)
    frame["symbol"] = info.symbol
    frame["contract"] = info.contract
    frame["contract_month"] = info.contract_month
    frame["contract_year"] = info.contract_year
    frame["source_file"] = str(info.source_file)
    frame["source"] = source
    return frame


def load_all_contracts(
    data_root: Path,
    symbol: str,
    source: str = "barchart",
    timezone: str = "UTC",
) -> pd.DataFrame:
    files = raw_contract_files(data_root, symbol)
    if not files:
        raise FileNotFoundError(
            f"No raw CSV files found in {data_root / 'raw_contracts' / symbol}"
        )
    frames = [
        load_contract_file(path, symbol, source=source, timezone=timezone)
        for path in files
    ]
    frame = pd.concat(frames, ignore_index=True)
    canonical = [
        "timestamp",
        "symbol",
        "contract",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "contract_month",
        "contract_year",
        "source_file",
    ]
    frame = frame[canonical]
    return (
        frame.sort_values(["contract_year", "contract_month", "timestamp", "source"])
        .drop_duplicates(subset=["timestamp", "contract"], keep="last")
        .reset_index(drop=True)
    )


def contract_infos(data_root: Path, symbol: str) -> List[ContractInfo]:
    return sorted_contracts(
        infer_contract_info(path, symbol)
        for path in raw_contract_files(data_root, symbol)
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    output.to_csv(path, index=False)
