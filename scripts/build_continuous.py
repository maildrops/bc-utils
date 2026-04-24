#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from bcutils.research.config import (
    PROJECT_ROOT,
    load_instruments,
    load_roll_rule,
    selected_symbols,
)
from bcutils.research.continuous import build_continuous_series, save_continuous_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build continuous hourly futures series."
    )
    parser.add_argument("--symbol", required=True, help="Instrument symbol, or ALL")
    parser.add_argument(
        "--roll-days", type=int, default=None, help="Override roll days before expiry"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned outputs without writing files",
    )
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--config-dir", type=Path, default=PROJECT_ROOT / "config")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruments = load_instruments(args.config_dir)
    roll_rule = load_roll_rule(args.config_dir)
    for symbol in selected_symbols(args.symbol, instruments):
        result = build_continuous_series(
            symbol,
            instruments[symbol],
            roll_rule,
            args.data_root,
            roll_days_override=args.roll_days,
        )
        if args.dry_run:
            row_count = len(result.unadjusted)
            roll_count = len(result.roll_schedule)
            print(f"{symbol}: {row_count} hourly rows, " f"{roll_count} rolls")
            continue
        save_continuous_result(result, symbol, args.data_root)
        print(f"{symbol}: wrote continuous hourly outputs")


if __name__ == "__main__":
    main()
