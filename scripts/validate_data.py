#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bcutils.research.config import PROJECT_ROOT, load_instruments, selected_symbols
from bcutils.research.validation import (
    save_validation_report,
    validate_file,
    validate_roll_continuity,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate continuous and aggregated futures outputs."
    )
    parser.add_argument("--symbol", required=True, help="Instrument symbol, or ALL")
    parser.add_argument(
        "--write-csv", action="store_true", help="Write validation report CSV"
    )
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--config-dir", type=Path, default=PROJECT_ROOT / "config")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruments = load_instruments(args.config_dir)
    for symbol in selected_symbols(args.symbol, instruments):
        reports = []
        hourly_dir = args.data_root / "continuous" / "hourly"
        for source in ["unadjusted", "backadjusted"]:
            path = hourly_dir / f"{symbol}_60min_{source}.csv"
            if path.exists():
                reports.append(validate_file(path, f"{symbol}_60min_{source}"))
        adjusted_path = hourly_dir / f"{symbol}_60min_backadjusted.csv"
        schedule_path = hourly_dir / f"{symbol}_roll_schedule.csv"
        if adjusted_path.exists() and schedule_path.exists():
            try:
                schedule = pd.read_csv(schedule_path)
            except pd.errors.EmptyDataError:
                schedule = pd.DataFrame()
            if not schedule.empty:
                adjusted = pd.read_csv(adjusted_path)
                adjusted["timestamp"] = pd.to_datetime(adjusted["timestamp"], utc=True)
                schedule["roll_timestamp"] = pd.to_datetime(
                    schedule["roll_timestamp"], utc=True
                )
                reports.append(
                    validate_roll_continuity(
                        adjusted, schedule, f"{symbol}_roll_continuity"
                    )
                )
        for path in sorted((args.data_root / "aggregated").glob(f"*/*{symbol}_*.csv")):
            reports.append(validate_file(path, path.stem))
        report = pd.concat(reports, ignore_index=True) if reports else pd.DataFrame()
        if report.empty:
            print(f"{symbol}: no output files found to validate")
            continue
        print(report.to_string(index=False))
        if args.write_csv:
            out = save_validation_report(report, args.data_root, symbol)
            print(f"{symbol}: wrote validation report to {out}")


if __name__ == "__main__":
    main()
