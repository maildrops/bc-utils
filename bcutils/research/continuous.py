from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from bcutils.research.contracts import ContractInfo, roll_timestamp_utc
from bcutils.research.io import contract_infos, load_all_contracts, write_csv


@dataclass
class ContinuousResult:
    unadjusted: pd.DataFrame
    backadjusted: pd.DataFrame
    roll_schedule: pd.DataFrame
    adjustments: pd.DataFrame


def build_continuous_series(
    symbol: str,
    instrument: Dict[str, str],
    roll_rule: Dict[str, object],
    data_root: Path,
    roll_days_override: int | None = None,
) -> ContinuousResult:
    symbol = symbol.upper()
    contracts = contract_infos(data_root, symbol)
    if not contracts:
        raise FileNotFoundError(f"No contracts found for {symbol}")
    all_rows = load_all_contracts(
        data_root, symbol, timezone=str(instrument.get("timezone", "UTC"))
    )
    roll_days = int(
        roll_days_override
        or instrument.get("roll_days_before_expiry")
        or roll_rule["roll_days_before_expiry"]
    )
    schedule = build_roll_schedule(
        symbol, contracts, all_rows, instrument, roll_rule, roll_days
    )
    unadjusted = select_active_contract_rows(all_rows, contracts, schedule)
    backadjusted, adjustments = apply_difference_backadjustment(unadjusted, schedule)
    return ContinuousResult(unadjusted, backadjusted, schedule, adjustments)


def build_roll_schedule(
    symbol: str,
    contracts: List[ContractInfo],
    all_rows: pd.DataFrame,
    instrument: Dict[str, str],
    roll_rule: Dict[str, object],
    roll_days: int,
) -> pd.DataFrame:
    rows = []
    cumulative = 0.0
    for old, new in zip(contracts[:-1], contracts[1:]):
        ts = roll_timestamp_utc(
            symbol,
            old.contract_year,
            old.contract_month,
            roll_days,
            str(roll_rule.get("roll_at", "session_end")),
            instrument,
        )
        old_close = close_at_or_before(all_rows, old.contract, ts)
        new_close = close_at_or_before(all_rows, new.contract, ts)
        roll_gap = new_close - old_close
        cumulative += roll_gap
        rows.append(
            {
                "symbol": symbol,
                "old_contract": old.contract,
                "new_contract": new.contract,
                "roll_timestamp": ts,
                "roll_date": ts.date().isoformat(),
                "old_close": old_close,
                "new_close": new_close,
                "roll_gap": roll_gap,
                "cumulative_adjustment_after_roll": cumulative,
                "roll_rule": str(roll_rule.get("method", "calendar")),
                "roll_days_before_expiry": roll_days,
            }
        )
    columns = [
        "symbol",
        "old_contract",
        "new_contract",
        "roll_timestamp",
        "roll_date",
        "old_close",
        "new_close",
        "roll_gap",
        "cumulative_adjustment_after_roll",
        "roll_rule",
        "roll_days_before_expiry",
    ]
    return pd.DataFrame(rows, columns=columns)


def close_at_or_before(
    frame: pd.DataFrame, contract: str, timestamp: pd.Timestamp
) -> float:
    rows = frame[(frame["contract"] == contract) & (frame["timestamp"] <= timestamp)]
    if rows.empty:
        rows = frame[frame["contract"] == contract]
    if rows.empty:
        raise ValueError(f"No data found for contract {contract}")
    return float(rows.sort_values("timestamp").iloc[-1]["close"])


def select_active_contract_rows(
    all_rows: pd.DataFrame,
    contracts: List[ContractInfo],
    schedule: pd.DataFrame,
) -> pd.DataFrame:
    pieces = []
    start = None
    for index, contract in enumerate(contracts):
        end = None
        if index < len(schedule):
            end = schedule.iloc[index]["roll_timestamp"]
        mask = all_rows["contract"] == contract.contract
        if start is not None:
            mask = mask & (all_rows["timestamp"] >= start)
        if end is not None:
            mask = mask & (all_rows["timestamp"] < end)
        pieces.append(all_rows.loc[mask].copy())
        if index < len(schedule):
            start = schedule.iloc[index]["roll_timestamp"]
    if not pieces:
        return pd.DataFrame()
    result = pd.concat(pieces, ignore_index=True).sort_values("timestamp")
    return result.drop_duplicates(subset=["timestamp"], keep="last").reset_index(
        drop=True
    )


def apply_difference_backadjustment(
    unadjusted: pd.DataFrame,
    schedule: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    adjusted = unadjusted.copy().sort_values("timestamp").reset_index(drop=True)
    for column in ["open", "high", "low", "close", "volume"]:
        adjusted[f"raw_{column}"] = adjusted[column]
    adjusted["adjustment"] = 0.0
    adjusted["is_roll_bar"] = False
    adjusted["roll_id"] = ""
    adjustment_rows = []
    for roll_index, roll in schedule.iterrows():
        gap = float(roll["roll_gap"])
        ts = roll["roll_timestamp"]
        mask = adjusted["timestamp"] < ts
        adjusted.loc[mask, "adjustment"] += gap
        adjusted.loc[mask, ["open", "high", "low", "close"]] = (
            adjusted.loc[mask, ["open", "high", "low", "close"]] + gap
        )
        roll_mask = adjusted["timestamp"] >= ts
        if roll_mask.any():
            first_idx = adjusted.loc[roll_mask].index[0]
            adjusted.loc[first_idx, "is_roll_bar"] = True
            adjusted.loc[
                first_idx, "roll_id"
            ] = f"{roll['old_contract']}_to_{roll['new_contract']}"
        adjustment_rows.append(
            {
                "timestamp": ts,
                "contract": roll["old_contract"],
                "adjustment": gap,
                "reason": f"roll_to_{roll['new_contract']}",
            }
        )
    ordered = [
        "timestamp",
        "symbol",
        "contract",
        "source",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "adjustment",
        "is_roll_bar",
        "roll_id",
    ]
    adjustment_columns = ["timestamp", "contract", "adjustment", "reason"]
    return adjusted[ordered], pd.DataFrame(adjustment_rows, columns=adjustment_columns)


def save_continuous_result(
    result: ContinuousResult, symbol: str, data_root: Path
) -> None:
    out_dir = data_root / "continuous" / "hourly"
    write_csv(result.unadjusted, out_dir / f"{symbol}_60min_unadjusted.csv")
    write_csv(result.backadjusted, out_dir / f"{symbol}_60min_backadjusted.csv")
    write_csv(result.roll_schedule, out_dir / f"{symbol}_roll_schedule.csv")
    write_csv(result.adjustments, out_dir / f"{symbol}_adjustments.csv")
