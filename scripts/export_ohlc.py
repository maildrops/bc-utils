#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from bcutils.research.config import PROJECT_ROOT
from bcutils.research.export import (
    export_ohlc_file,
    iter_pipeline_ohlc_files,
    output_path_for,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export pipeline CSVs to simple Date/Time/OHLC format."
    )
    parser.add_argument("--symbol", help="Instrument symbol, e.g. MNQ")
    parser.add_argument(
        "--timeframe",
        help="60min, 120min, 240min, 360min, 720min, session, or daily",
    )
    parser.add_argument(
        "--source",
        choices=["backadjusted", "unadjusted"],
        default="backadjusted",
        help="Pipeline data source to export",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export all generated pipeline OHLC CSVs for the selected source",
    )
    parser.add_argument("--input", type=Path, help="Specific input CSV to export")
    parser.add_argument("--output", type=Path, help="Specific output file path")
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "backtest_exports",
    )
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument(
        "--separator",
        choices=["comma", "tab", "space"],
        default="comma",
    )
    return parser.parse_args()


def input_path_for(data_root: Path, symbol: str, timeframe: str, source: str) -> Path:
    symbol = symbol.upper()
    if timeframe == "60min":
        return data_root / "continuous" / "hourly" / f"{symbol}_60min_{source}.csv"
    return data_root / "aggregated" / timeframe / f"{symbol}_{timeframe}_{source}.csv"


def selected_inputs(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return list(iter_pipeline_ohlc_files(args.data_root, source=args.source))
    if args.input:
        return [args.input]
    if not args.symbol or not args.timeframe:
        raise SystemExit("Provide --all, --input, or both --symbol and --timeframe")
    return [input_path_for(args.data_root, args.symbol, args.timeframe, args.source)]


def main() -> None:
    args = parse_args()
    inputs = selected_inputs(args)
    exported = 0
    skipped = 0
    for input_path in inputs:
        if not input_path.exists():
            print(f"skipped missing: {input_path}")
            skipped += 1
            continue
        if args.output:
            output_path = args.output
        else:
            output_path = output_path_for(input_path, args.output_dir)
        result = export_ohlc_file(
            input_path,
            output_path,
            timezone=args.timezone,
            separator=args.separator,
        )
        if result.exported:
            print(f"exported: {result.source} -> {result.output}")
            exported += 1
        else:
            print(f"skipped: {result.source} ({result.reason})")
            skipped += 1
    print(f"summary: exported {exported}, skipped {skipped}")


if __name__ == "__main__":
    main()
