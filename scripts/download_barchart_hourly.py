#!/usr/bin/env python
"""Placeholder wrapper for existing bc-utils hourly contract downloads.

This checkout did not contain the original downloader code. Keep raw Barchart
files under data/raw_contracts/{SYMBOL}/ and leave them unchanged. When the
upstream bc-utils package is present, this script is the intended place to call
its hourly contract download command without mixing raw and derived outputs.
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run existing bc-utils hourly downloads.")
    parser.add_argument("--symbol", required=True)
    parser.parse_args()
    raise SystemExit(
        "Existing bc-utils downloader code is not present in this workspace. "
        "Use the upstream download workflow and save CSVs in data/raw_contracts/{SYMBOL}/."
    )


if __name__ == "__main__":
    main()
