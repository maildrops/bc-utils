# User Guide

`bc-utils` has two related workflows:

- Download daily and hourly futures contract CSVs from Barchart.
- Build research-ready continuous futures series from raw hourly contract CSVs.

The research workflow is file-based. Raw contract files stay unchanged under
`data/raw_contracts/`, and derived files are written under `data/continuous/`,
`data/aggregated/`, and `data/validation/`.

## Project Layout

```text
bcutils/                  Python package
config/                   Research pipeline configuration
data/raw_contracts/       Raw hourly contract CSVs, grouped by symbol
data/continuous/hourly/   Continuous hourly outputs and roll audit files
data/aggregated/          Aggregated research bars
data/validation/          Validation reports
sample/                   Example Barchart/PST snippets
scripts/                  Command-line workflow scripts
tests/                    Research pipeline tests
```

## Barchart Download Usage

The original downloader API lives in `bcutils.bc_utils`. It logs in to Barchart
and downloads individual contract files.

Minimal example:

```python
import os
from bcutils.bc_utils import create_bc_session, get_barchart_downloads

contracts = {
    "AUD": {"code": "A6", "cycle": "HMUZ", "exchange": "CME"},
    "GOLD": {"code": "GC", "cycle": "GJMQVZ", "exchange": "COMEX"},
}

session = create_bc_session(
    config_obj={
        "barchart_username": "user@example.com",
        "barchart_password": "your-password",
    }
)

get_barchart_downloads(
    session,
    contract_map=contracts,
    instr_list=["AUD", "GOLD"],
    save_dir=os.getcwd(),
    start_year=2020,
    end_year=2021,
)
```

For pysystemtrade-style configuration, start from:

```text
sample/private_config_sample.yaml
sample/pst.py
```

Copy `sample/private_config_sample.yaml`, fill in your credentials and target
data path, then run your download script through uv:

```bash
uv run python sample/pst.py
```

Do not commit private config files containing credentials.

## Research Pipeline Inputs

The research pipeline expects raw hourly contract CSVs under:

```text
data/raw_contracts/{SYMBOL}/
```

Examples:

```text
data/raw_contracts/MES/MESH24.csv
data/raw_contracts/MES/MESM24.csv
data/raw_contracts/MES/MESU24.csv
```

Input files are normalized internally to:

```text
timestamp, symbol, contract, open, high, low, close, volume, source
```

The loader accepts common Barchart column names including `Time`, `Open`,
`High`, `Low`, `Close`, and `Volume`.

## Configure Markets

Edit `config/instruments.yaml` to add or change markets.

Each instrument defines:

- `description`: display description
- `exchange`: exchange code
- `barchart_root`: Barchart root symbol
- `month_cycle`: futures month codes to include
- `timezone`: exchange/session timezone
- `roll_days_before_expiry`: default roll offset
- `session_start` and `session_end`: session boundaries

The initial configured symbols are:

- `MES`: Micro E-mini S&P 500
- `MNQ`: Micro E-mini Nasdaq 100
- `MGC`: Micro Gold
- `MCL`: Micro WTI Crude Oil

Roll behavior is configured in `config/roll_rules.yaml`. Version 1 supports
calendar rolls with difference back-adjustment.

Aggregation timeframes are configured in `config/aggregation.yaml`.

## Build Continuous Series

Build one symbol:

```bash
uv run python scripts/build_continuous.py --symbol MES
```

Build every configured symbol:

```bash
uv run python scripts/build_continuous.py --symbol ALL
```

Preview without writing files:

```bash
uv run python scripts/build_continuous.py --symbol MES --dry-run
```

Override the configured roll offset:

```bash
uv run python scripts/build_continuous.py --symbol MES --roll-days 7
```

Use alternate data or config directories:

```bash
uv run python scripts/build_continuous.py \
  --symbol MES \
  --data-root /path/to/data \
  --config-dir /path/to/config
```

Outputs:

```text
data/continuous/hourly/MES_60min_unadjusted.csv
data/continuous/hourly/MES_60min_backadjusted.csv
data/continuous/hourly/MES_roll_schedule.csv
data/continuous/hourly/MES_adjustments.csv
```

Back-adjustment uses constant difference adjustment. At each roll, the new
contract close minus the old contract close is added to earlier OHLC history.
Volume is not adjusted.

## Aggregate Bars

Aggregate all configured timeframes from the back-adjusted series:

```bash
uv run python scripts/aggregate_bars.py --symbol MES --source backadjusted
```

Aggregate from the unadjusted series:

```bash
uv run python scripts/aggregate_bars.py --symbol MES --source unadjusted
```

Build one configured timeframe:

```bash
uv run python scripts/aggregate_bars.py \
  --symbol MES \
  --source backadjusted \
  --timeframe 240min
```

Outputs are written under:

```text
data/aggregated/120min/
data/aggregated/240min/
data/aggregated/360min/
data/aggregated/720min/
data/aggregated/session/
data/aggregated/daily/
```

Intraday aggregations are anchored to the configured session start. Session and
daily bars use the futures session rather than calendar midnight.

## Validate Outputs

Print validation results:

```bash
uv run python scripts/validate_data.py --symbol MES
```

Write validation results to CSV:

```bash
uv run python scripts/validate_data.py --symbol MES --write-csv
```

Validate all configured symbols:

```bash
uv run python scripts/validate_data.py --symbol ALL --write-csv
```

Validation checks include:

- duplicate timestamps
- timestamp sorting
- OHLC sanity
- non-negative volume
- large close jumps
- roll continuity
- adjustment values

CSV reports are written to:

```text
data/validation/{SYMBOL}_validation_report.csv
```

## Suggested End-To-End Workflow

1. Install and verify the environment with `uv sync --dev` and `uv run pytest`.
2. Add or review instruments in `config/instruments.yaml`.
3. Place raw hourly contract CSVs under `data/raw_contracts/{SYMBOL}/`.
4. Build continuous hourly files with `scripts/build_continuous.py`.
5. Aggregate research timeframes with `scripts/aggregate_bars.py`.
6. Validate outputs with `scripts/validate_data.py`.
7. Inspect roll schedules and adjustment audit files before using the data.

## Operational Notes

- Keep raw Barchart files unchanged.
- Treat generated files under `data/continuous`, `data/aggregated`, and
  `data/validation` as reproducible outputs.
- Rebuild continuous data after adding or changing raw contract files.
- Re-run aggregation after rebuilding continuous data.
- This workflow is intended for research, not live trading or production data
  operations.
