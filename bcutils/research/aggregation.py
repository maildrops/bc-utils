from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo

import pandas as pd

from bcutils.research.io import write_csv


def read_continuous(data_root: Path, symbol: str, source: str) -> pd.DataFrame:
    path = data_root / "continuous" / "hourly" / f"{symbol}_60min_{source}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.sort_values("timestamp")


def aggregate_timeframe(
    frame: pd.DataFrame,
    symbol: str,
    timeframe: Dict[str, object],
    instrument: Dict[str, str],
    source: str,
) -> pd.DataFrame:
    tf_type = timeframe.get("type")
    if tf_type in {"custom_session", "session_daily"} or timeframe["name"] in {"session", "daily"}:
        return aggregate_session(frame, symbol, timeframe["name"], instrument, source)
    return aggregate_intraday(frame, symbol, timeframe, instrument, source)


def aggregate_intraday(
    frame: pd.DataFrame,
    symbol: str,
    timeframe: Dict[str, object],
    instrument: Dict[str, str],
    source: str,
) -> pd.DataFrame:
    local = with_session_columns(frame, instrument)
    rule = str(timeframe["pandas_rule"])
    grouped = local.groupby("session_date", group_keys=False)
    pieces = []
    for _, session_rows in grouped:
        session_rows = session_rows.sort_values("timestamp").set_index("timestamp")
        origin = session_rows.index.min()
        bars = session_rows.resample(rule, origin=origin, label="left", closed="left").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            symbol=("symbol", "first"),
            source=("source", first_joined),
            first_contract=("contract", "first"),
            last_contract=("contract", "last"),
            contains_roll_bar=("is_roll_bar", "max"),
            source_count=("close", "count"),
        )
        pieces.append(bars.dropna(subset=["open", "high", "low", "close"]).reset_index())
    if not pieces:
        return pd.DataFrame()
    result = pd.concat(pieces, ignore_index=True)
    expected = pd.Timedelta(rule) / pd.Timedelta("60min")
    result["source_timeframe"] = "60min"
    result["target_timeframe"] = timeframe["name"]
    result["is_complete"] = result["source_count"] >= expected
    return result


def aggregate_session(
    frame: pd.DataFrame,
    symbol: str,
    target: str,
    instrument: Dict[str, str],
    source: str,
) -> pd.DataFrame:
    local = with_session_columns(frame, instrument)
    rows = []
    for _, group in local.groupby("session_date"):
        group = group.sort_values("timestamp")
        rows.append(
            {
                "timestamp": group.iloc[0]["timestamp"],
                "symbol": symbol,
                "open": group.iloc[0]["open"],
                "high": group["high"].max(),
                "low": group["low"].min(),
                "close": group.iloc[-1]["close"],
                "volume": group["volume"].sum(),
                "source": first_joined(group["source"]) if "source" in group.columns else "",
                "source_timeframe": "60min",
                "target_timeframe": target,
                "first_contract": group.iloc[0]["contract"],
                "last_contract": group.iloc[-1]["contract"],
                "contains_roll_bar": bool(group.get("is_roll_bar", False).max()),
                "source_count": len(group),
                "is_complete": True,
            }
        )
    return pd.DataFrame(rows)


def first_joined(values: pd.Series) -> str:
    unique = [str(value) for value in values.dropna().unique()]
    return "+".join(unique)


def with_session_columns(frame: pd.DataFrame, instrument: Dict[str, str]) -> pd.DataFrame:
    result = frame.copy()
    tz = ZoneInfo(instrument["timezone"])
    session_start = time.fromisoformat(instrument["session_start"])
    local_ts = result["timestamp"].dt.tz_convert(tz)
    result["local_timestamp"] = local_ts
    result["session_date"] = [
        ts.date() if ts.time() >= session_start else (ts - pd.Timedelta(days=1)).date()
        for ts in local_ts
    ]
    if "is_roll_bar" not in result.columns:
        result["is_roll_bar"] = False
    return result


def save_aggregated(frame: pd.DataFrame, data_root: Path, symbol: str, timeframe: str, source: str) -> Path:
    path = data_root / "aggregated" / timeframe / f"{symbol}_{timeframe}_{source}.csv"
    write_csv(frame, path)
    return path
