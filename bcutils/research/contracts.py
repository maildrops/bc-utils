from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, Iterable, List
from zoneinfo import ZoneInfo

import pandas as pd


MONTH_CODES = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

MONTH_NUM_TO_CODE = {value: key for key, value in MONTH_CODES.items()}


@dataclass(frozen=True)
class ContractInfo:
    symbol: str
    contract: str
    contract_month: int
    contract_year: int
    source_file: Path

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (self.contract_year, self.contract_month, self.contract)


def infer_contract_info(path: Path, symbol: str) -> ContractInfo:
    stem = path.stem.upper()
    symbol = symbol.upper()
    split_freq = re.match(
        rf"^(?:HOUR|DAY)_{re.escape(symbol)}_(\d{{4}})(\d{{2}})00$", stem
    )
    if split_freq:
        year_text, month_text = split_freq.groups()
        year = int(year_text)
        month = int(month_text)
        if month not in MONTH_NUM_TO_CODE:
            raise ValueError(f"Cannot infer contract month from {path.name}")
        month_code = MONTH_NUM_TO_CODE[month]
        contract = f"{symbol}{month_code}{str(year)[-2:]}"
        return ContractInfo(
            symbol=symbol,
            contract=contract,
            contract_month=month,
            contract_year=year,
            source_file=path,
        )
    pattern = re.compile(
        rf"{re.escape(symbol)}[^A-Z0-9]*([FGHJKMNQUVXZ])[^0-9]*(\d{{1,4}})"
    )
    match = pattern.search(stem)
    if not match:
        generic = re.search(r"([FGHJKMNQUVXZ])[^0-9]*(\d{1,4})", stem)
        if not generic:
            raise ValueError(f"Cannot infer contract month/year from {path.name}")
        month_code, year_text = generic.groups()
    else:
        month_code, year_text = match.groups()
    year = expand_year(int(year_text))
    contract = f"{symbol}{month_code}{str(year)[-2:]}"
    return ContractInfo(
        symbol=symbol,
        contract=contract,
        contract_month=MONTH_CODES[month_code],
        contract_year=year,
        source_file=path,
    )


def expand_year(year: int) -> int:
    if year >= 1000:
        return year
    if year < 70:
        return 2000 + year
    return 1900 + year


def third_friday(year: int, month: int) -> date:
    current = date(year, month, 1)
    while current.weekday() != 4:
        current += timedelta(days=1)
    return current + timedelta(days=14)


def approximate_expiry_date(symbol: str, year: int, month: int) -> date:
    """Return a simple first-version expiry date.

    MES/MNQ use the common third-Friday approximation. MGC/MCL are deliberately
    isolated here because their exact exchange rules should replace this logic
    before production use.
    """
    symbol = symbol.upper()
    if symbol in {"MES", "MNQ"}:
        return third_friday(year, month)
    if symbol in {"MGC", "MCL"}:
        # TODO: Replace with exact COMEX/NYMEX last-trade rules.
        return third_friday(year, month)
    return third_friday(year, month)


def subtract_trading_days(value: date, count: int) -> date:
    current = value
    remaining = count
    while remaining:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def roll_timestamp_utc(
    symbol: str,
    year: int,
    month: int,
    roll_days: int,
    roll_at: str,
    instrument: Dict[str, str],
) -> pd.Timestamp:
    expiry = approximate_expiry_date(symbol, year, month)
    roll_date = subtract_trading_days(expiry, roll_days)
    time_text = instrument["session_end"] if roll_at == "session_end" else roll_at
    local_time = time.fromisoformat(time_text)
    local_dt = datetime.combine(
        roll_date, local_time, tzinfo=ZoneInfo(instrument["timezone"])
    )
    return pd.Timestamp(local_dt).tz_convert("UTC")


def sorted_contracts(contract_infos: Iterable[ContractInfo]) -> List[ContractInfo]:
    return sorted(contract_infos, key=lambda item: item.sort_key)
