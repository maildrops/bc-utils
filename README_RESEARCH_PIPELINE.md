# Futures Research Pipeline

This fork adds a simple research layer around bc-utils contract downloads. It keeps raw hourly contract CSVs unchanged, builds continuous unadjusted and difference back-adjusted futures series, aggregates those hourly bars into larger research timeframes, and writes audit files for rolls and adjustments.

The project is intentionally small and file-based. It is for kicking the tyres on breakout-system ideas, not for production data operations.

## Layout

```text
config/
  instruments.yaml
  roll_rules.yaml
  aggregation.yaml
data/
  raw_contracts/{SYMBOL}/
  continuous/hourly/
  aggregated/{TIMEFRAME}/
  validation/
scripts/
  download_barchart_hourly.py
  build_continuous.py
  aggregate_bars.py
  validate_data.py
```

Raw files live under `data/raw_contracts/MES/`, `data/raw_contracts/MNQ/`, `data/raw_contracts/MGC/`, and `data/raw_contracts/MCL/`. Derived files are written separately under `data/continuous`, `data/aggregated`, and `data/validation`.

## Raw Data Schema

Raw input files are normalized internally to:

```text
timestamp, symbol, contract, open, high, low, close, volume, source
```

Existing Barchart files are loaded with `source = "barchart"`. The schema is designed so a later `scripts/update_from_ibkr.py` can append recent rows with `source = "ibkr"`, then deduplicate and sort before rebuilding continuous data. Version 1 does not implement the IBKR downloader.

The loader accepts common Barchart column names such as `Time`, `Open`, `High`, `Low`, `Close`, and `Volume`.

## Configuration

Edit `config/instruments.yaml` to add or change markets. The initial symbols are:

- `MES`: Micro E-mini S&P 500
- `MNQ`: Micro E-mini Nasdaq 100
- `MGC`: Micro Gold
- `MCL`: Micro WTI Crude Oil

Roll behavior is in `config/roll_rules.yaml`. Version 1 supports calendar rolls only. Aggregation timeframes are in `config/aggregation.yaml`.

## Download Raw Hourly Data

Create a private config file with your Barchart credentials:

```bash
cp sample/private_config_sample.yaml private_config.yaml
```

Edit `private_config.yaml`, then run a dry-run first:

```bash
uv run python scripts/download_barchart_hourly.py --symbol MES --dry-run
```

Download hourly raw contract files:

```bash
uv run python scripts/download_barchart_hourly.py --symbol MES --credentials private_config.yaml
```

The script saves raw Barchart hourly files under:

```text
data/raw_contracts/{SYMBOL}/
```

For example:

```text
data/raw_contracts/MES/Hour_MES_20240300.csv
data/raw_contracts/MES/Hour_MES_20240600.csv
data/raw_contracts/MES/Hour_MES_20240900.csv
```

Existing files are skipped so Barchart allowance is not wasted. The loader also accepts contract-style names such as `MESH24.csv`.

Barchart Premier web downloads have a 10,000-record limit per request. Version 1 deliberately avoids changing Barchart 5-minute or 1-minute download behavior.

## Build Continuous Series

Build one symbol:

```bash
uv run python scripts/build_continuous.py --symbol MES
```

Build all configured symbols:

```bash
uv run python scripts/build_continuous.py --symbol ALL
```

Try a roll-day sensitivity run:

```bash
uv run python scripts/build_continuous.py --symbol MES --roll-days 7
```

Outputs:

```text
data/continuous/hourly/MES_60min_unadjusted.csv
data/continuous/hourly/MES_60min_backadjusted.csv
data/continuous/hourly/MES_roll_schedule.csv
data/continuous/hourly/MES_adjustments.csv
```

Back-adjustment uses constant difference adjustment. At each roll, the new contract close minus old contract close is added to earlier OHLC history. Volume is not adjusted.

## Aggregate Bars

Aggregate all configured timeframes:

```bash
uv run python scripts/aggregate_bars.py --symbol MES --source backadjusted
```

Aggregate one timeframe:

```bash
uv run python scripts/aggregate_bars.py --symbol MES --source backadjusted --timeframe 240min
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

Intraday aggregations are anchored to the configured session start. Session and daily bars use the futures session, not naive midnight-to-midnight calendar days.

## Validate Outputs

Run:

```bash
uv run python scripts/validate_data.py --symbol MES --write-csv
```

Validation checks duplicate timestamps, timestamp sorting, OHLC sanity, non-negative volume, large close jumps, roll bars, and adjustment values. CSV reports are written to:

```text
data/validation/{SYMBOL}_validation_report.csv
```

## Tests

Run:

```bash
uv run pytest
```

The tests cover calendar roll dates, contract ordering, back-adjustment, aggregation, session grouping, and validation checks.

## Known Limitations

- Expiry logic is approximate. MES/MNQ use third Friday; MGC/MCL currently use placeholder third-Friday logic with TODOs for exact exchange rules.
- Calendar roll is the only version 1 roll method.
- Volume/open-interest roll is not implemented.
- IBKR top-up support is planned by schema, but no IBKR downloader is implemented in version 1.
- 5-minute and 1-minute Barchart download changes are deliberately out of scope.
- This is not production-grade market data infrastructure.

## Suggested Research Workflow

1. Prime contract history from Barchart hourly files.
2. Build continuous unadjusted and back-adjusted series.
3. Aggregate to 120, 240, 360, 720 minute, session, and daily bars.
4. Validate outputs and inspect roll audit files.
5. Test broad breakout ideas across multiple timeframes.
6. Test roll-day sensitivity using 3, 5, 7, and 10 days.
7. If results look promising, validate later with professional intraday data.

## Avoid In Version 1

- Live trading
- Web dashboards
- Databases
- 5-minute/1-minute Barchart download changes
- Implementing IBKR downloader code immediately
