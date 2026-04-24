#!/usr/bin/env python
"""Download hourly Barchart contract files into the research raw-data layout."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from bcutils.bc_utils import (
    HistoricalDataResult,
    Resolution,
    _before_available_res,
    _build_contract_list,
    _get_contract_month_year,
    _get_start_end_dates,
    create_bc_session,
    save_prices_for_contract,
)
from bcutils.research.config import PROJECT_ROOT, load_instruments, selected_symbols
from bcutils.research.contracts import infer_contract_info


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Barchart hourly contracts into " "data/raw_contracts/{SYMBOL}/."
        )
    )
    parser.add_argument("--symbol", required=True, help="Instrument symbol, or ALL")
    parser.add_argument(
        "--contract",
        default=None,
        help="Optional single Barchart contract ID to download, e.g. ETH24",
    )
    parser.add_argument(
        "--credentials",
        "--config",
        dest="credentials",
        type=Path,
        default=PROJECT_ROOT / "private_config.yaml",
        help="Private YAML containing barchart_username and barchart_password",
    )
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned downloads only"
    )
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--config-dir", type=Path, default=PROJECT_ROOT / "config")
    parser.add_argument("--default-day-count", type=int, default=400)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def load_private_config(path: Path) -> Dict[str, Any]:
    config: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            config.update(yaml.safe_load(handle) or {})
    if os.environ.get("BARCHART_USERNAME"):
        config["barchart_username"] = os.environ["BARCHART_USERNAME"]
    if os.environ.get("BARCHART_PASSWORD"):
        config["barchart_password"] = os.environ["BARCHART_PASSWORD"]
    return config


def contract_map_for_symbols(
    instruments: Dict[str, Dict[str, Any]],
    symbols: Iterable[str],
) -> Dict[str, Dict[str, str]]:
    result = {}
    for symbol in symbols:
        instrument = instruments[symbol]
        result[symbol] = {
            "code": str(instrument["barchart_root"]),
            "cycle": str(instrument["month_cycle"]),
            "exchange": str(instrument["exchange"]),
        }
    return result


def expected_hour_path(raw_dir: Path, symbol: str, contract: str) -> Path:
    month, year = _get_contract_month_year(contract)
    return raw_dir / f"Hour_{symbol}_{year}{month:02d}00.csv"


def existing_contracts(raw_dir: Path, symbol: str) -> set[str]:
    found = set()
    if not raw_dir.exists():
        return found
    for path in raw_dir.glob("*.csv"):
        try:
            found.add(infer_contract_info(path, symbol).contract)
        except ValueError:
            logger.warning("Skipping unrecognized raw file name: %s", path)
    return found


def contracts_to_download(
    symbol: str,
    contract_map: Dict[str, Dict[str, str]],
    raw_dir: Path,
    start_year: int,
    end_year: int,
    contract: str | None = None,
) -> List[str]:
    if contract is None:
        requested = _build_contract_list(
            start_year,
            end_year,
            instr_list=[symbol],
            contract_map=contract_map,
        )
    else:
        requested = [normalize_requested_contract(symbol, contract, contract_map)]
    existing = existing_contracts(raw_dir, symbol)
    existing_keys = {contract_month_year_key(contract) for contract in existing}
    return [
        contract
        for contract in requested
        if contract_month_year_key(contract) not in existing_keys
    ]


def contract_month_year_key(contract: str) -> tuple[int, int]:
    month, year = _get_contract_month_year(contract)
    return year, month


def normalize_requested_contract(
    symbol: str,
    contract: str,
    contract_map: Dict[str, Dict[str, str]],
) -> str:
    contract = contract.upper()
    expected_root = contract_map[symbol]["code"].upper()
    if not contract.startswith(expected_root):
        raise ValueError(
            f"Contract {contract!r} does not match {symbol} "
            f"Barchart root {expected_root!r}"
        )
    _get_contract_month_year(contract)
    return contract


def download_symbol(
    session,
    symbol: str,
    contract_map: Dict[str, Dict[str, str]],
    raw_dir: Path,
    contracts: List[str],
    dry_run: bool,
    default_day_count: int,
) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    instrument = contract_map[symbol]
    for contract in contracts:
        month, year = _get_contract_month_year(contract)
        save_path = expected_hour_path(raw_dir, symbol, contract)
        start_date, end_date = _get_start_end_dates(
            month,
            year,
            instrument,
            default_day_count=default_day_count,
        )
        if _before_available_res(Resolution.Hour, start_date, instrument):
            logger.info(
                "%s: skipping %s before configured hourly availability",
                symbol,
                contract,
            )
            continue
        if dry_run:
            print(f"{symbol}: would download {contract} -> {save_path}")
            continue
        result = save_prices_for_contract(
            session,
            contract,
            str(save_path),
            start_date,
            end_date,
            dry_run=False,
        )
        status = result.name if isinstance(result, HistoricalDataResult) else result
        print(f"{symbol}: {contract} {status}")


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper()))
    private_config = load_private_config(args.credentials)
    instruments = load_instruments(args.config_dir)
    symbols = selected_symbols(args.symbol, instruments)
    if args.contract and len(symbols) != 1:
        raise SystemExit("--contract can only be used with one concrete --symbol")
    contract_map = contract_map_for_symbols(instruments, symbols)
    start_year = int(
        args.start_year or private_config.get("barchart_start_year") or 2020
    )
    end_year = int(args.end_year or private_config.get("barchart_end_year") or 2026)

    planned: Dict[str, List[str]] = {}
    for symbol in symbols:
        raw_dir = args.data_root / "raw_contracts" / symbol
        planned[symbol] = contracts_to_download(
            symbol,
            contract_map,
            raw_dir,
            start_year,
            end_year,
            args.contract,
        )
        print(f"{symbol}: {len(planned[symbol])} hourly contracts pending")

    if args.dry_run:
        session = None
    else:
        missing = [
            key
            for key in ["barchart_username", "barchart_password"]
            if not private_config.get(key)
        ]
        if missing:
            names = ", ".join(missing)
            raise SystemExit(f"Missing Barchart credentials: {names}")
        session = create_bc_session(private_config)

    for symbol in symbols:
        download_symbol(
            session,
            symbol,
            contract_map,
            args.data_root / "raw_contracts" / symbol,
            planned[symbol],
            args.dry_run,
            args.default_day_count,
        )

    if session is not None:
        session.get("https://www.barchart.com/logout", timeout=10)


if __name__ == "__main__":
    main()
