#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from bcutils.research.aggregation import (
    aggregate_timeframe,
    read_continuous,
    save_aggregated,
)
from bcutils.research.config import (
    PROJECT_ROOT,
    load_aggregation_config,
    load_instruments,
    selected_symbols,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate continuous hourly futures bars."
    )
    parser.add_argument("--symbol", required=True, help="Instrument symbol, or ALL")
    parser.add_argument(
        "--source", choices=["backadjusted", "unadjusted"], default="backadjusted"
    )
    parser.add_argument(
        "--timeframe", default=None, help="Single configured timeframe to build"
    )
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--config-dir", type=Path, default=PROJECT_ROOT / "config")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruments = load_instruments(args.config_dir)
    agg_config = load_aggregation_config(args.config_dir)
    configured = {item["name"]: item for item in agg_config["timeframes"]}
    timeframes = (
        [configured[args.timeframe]] if args.timeframe else list(configured.values())
    )
    for symbol in selected_symbols(args.symbol, instruments):
        source = read_continuous(args.data_root, symbol, args.source)
        for timeframe in timeframes:
            output = aggregate_timeframe(
                source, symbol, timeframe, instruments[symbol], args.source
            )
            if (
                bool(agg_config.get("drop_incomplete_bars", False))
                and "is_complete" in output.columns
            ):
                output = output[output["is_complete"]].copy()
            path = save_aggregated(
                output, args.data_root, symbol, timeframe["name"], args.source
            )
            print(f"{symbol}: wrote {len(output)} {timeframe['name']} rows to {path}")


if __name__ == "__main__":
    main()
