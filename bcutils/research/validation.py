from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

from bcutils.research.io import write_csv


def validate_frame(
    frame: pd.DataFrame, name: str, jump_tolerance: float = 0.05
) -> pd.DataFrame:
    checks: List[Dict[str, object]] = []
    duplicate_count = int(frame["timestamp"].duplicated().sum())
    checks.append(
        row(name, "duplicate_timestamps", duplicate_count == 0, duplicate_count)
    )
    sorted_ok = bool(frame["timestamp"].is_monotonic_increasing)
    checks.append(row(name, "timestamps_sorted", sorted_ok, 0 if sorted_ok else 1))
    ohlc_bad = frame[
        (frame["high"] < frame[["open", "close"]].max(axis=1))
        | (frame["low"] > frame[["open", "close"]].min(axis=1))
        | (frame["high"] < frame["low"])
    ]
    checks.append(row(name, "ohlc_sanity", ohlc_bad.empty, len(ohlc_bad)))
    volume_bad = frame[frame["volume"] < 0]
    checks.append(row(name, "non_negative_volume", volume_bad.empty, len(volume_bad)))
    jumps = frame["close"].pct_change().abs().fillna(0)
    jump_count = int((jumps > jump_tolerance).sum())
    checks.append(row(name, "large_close_jumps", jump_count == 0, jump_count))
    if "is_roll_bar" in frame.columns:
        checks.append(
            row(name, "roll_bars", True, int(frame["is_roll_bar"].astype(bool).sum()))
        )
    if "adjustment" in frame.columns:
        checks.append(
            row(
                name, "nonzero_adjustments", True, int((frame["adjustment"] != 0).sum())
            )
        )
    if is_hourly_dataset(frame, name):
        missing = missing_hourly_by_session(frame)
        checks.append(
            row(name, "sessions_with_lt_20_hourly_bars", missing.empty, len(missing))
        )
    return pd.DataFrame(checks)


def row(dataset: str, check: str, passed: bool, count: int) -> Dict[str, object]:
    return {"dataset": dataset, "check": check, "passed": passed, "count": int(count)}


def missing_hourly_by_session(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["date", "actual_bars"])
    local_dates = frame["timestamp"].dt.date
    counts = frame.groupby(local_dates).size().reset_index(name="actual_bars")
    counts = counts.rename(columns={"timestamp": "date"})
    return counts[counts["actual_bars"] < 20]


def is_hourly_dataset(frame: pd.DataFrame, name: str) -> bool:
    if "target_timeframe" in frame.columns:
        target = frame["target_timeframe"].dropna().astype(str)
        if not target.empty:
            return target.iloc[0] in {"60min", "hourly"}
    return "_60min_" in name or name.endswith("_60min")


def validate_file(path: Path, name: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return validate_frame(frame, name)


def save_validation_report(report: pd.DataFrame, data_root: Path, symbol: str) -> Path:
    path = data_root / "validation" / f"{symbol}_validation_report.csv"
    write_csv(report, path)
    return path


def validate_roll_continuity(
    adjusted: pd.DataFrame,
    roll_schedule: pd.DataFrame,
    name: str,
    tolerance: float = 1e-9,
) -> pd.DataFrame:
    checks = []
    adjusted = adjusted.sort_values("timestamp")
    for _, roll in roll_schedule.iterrows():
        roll_ts = roll["roll_timestamp"]
        before = adjusted[adjusted["timestamp"] < roll_ts]
        after = adjusted[adjusted["timestamp"] >= roll_ts]
        if before.empty or after.empty:
            checks.append(
                row(
                    name,
                    f"roll_continuity_{roll['old_contract']}_to_{roll['new_contract']}",
                    False,
                    1,
                )
            )
            continue
        gap = abs(float(after.iloc[0]["close"]) - float(before.iloc[-1]["close"]))
        checks.append(
            row(
                name,
                f"roll_continuity_{roll['old_contract']}_to_{roll['new_contract']}",
                gap <= tolerance,
                0 if gap <= tolerance else 1,
            )
        )
    return pd.DataFrame(checks)
