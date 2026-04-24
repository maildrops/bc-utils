# Repository Guidelines

## Project Structure & Module Organization

`bcutils/` contains the importable Python package. Core Barchart download helpers live in `bcutils/bc_utils.py`; research pipeline modules live in `bcutils/research/`. Command-line workflow scripts are in `scripts/`. YAML configuration for instruments, rolls, and aggregation lives in `config/`. Research inputs and generated outputs use `data/raw_contracts/`, `data/continuous/`, `data/aggregated/`, and `data/validation/`. Tests are in top-level `tests/`, with legacy package tests in `bcutils/tests/`. User-facing docs are in `README.md`, `README_RESEARCH_PIPELINE.md`, and `docs/`.

## Build, Test, and Development Commands

Use `uv` for environment management.

```bash
uv sync --dev
```

Creates `.venv` and installs runtime plus development dependencies.

```bash
uv run pytest
```

Runs the configured test suite.

```bash
uv run python scripts/build_continuous.py --symbol MES
uv run python scripts/aggregate_bars.py --symbol MES --source backadjusted
uv run python scripts/validate_data.py --symbol MES --write-csv
```

Runs the research pipeline for continuous series, aggregation, and validation.

## Coding Style & Naming Conventions

Use Python 3.12 locally via `.python-version`. Format with Black using the repo settings: 88-character line length and Python 3.10 target syntax. Use 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and uppercase names for constants. Keep scripts thin; put reusable logic in `bcutils/` modules. Prefer structured YAML config changes over hard-coded instrument or timeframe values.

## Testing Guidelines

Tests use `pytest`. Add focused tests under `tests/` for research pipeline behavior and name files `test_*.py`. Keep fixtures small and deterministic; avoid depending on private Barchart credentials or live network access. Run `uv run pytest` before handing off changes. For changes that affect formatting or style, also run:

```bash
uv run black --check .
uv run flake8 .
```

## Commit & Pull Request Guidelines

Existing history uses short, imperative or descriptive commit messages such as `Add futures research pipeline`, `fix cycles for HIGHYIELD and IG`, and `black`. Keep commits scoped and terse. Pull requests should describe what changed, why it changed, validation performed, and any data or config migration impact. Link related issues when available. Do not include credentials, private config files, or large generated market-data outputs unless explicitly required.

## Security & Configuration Tips

Do not commit Barchart usernames, passwords, or personal data paths. Use a private copy of `sample/private_config_sample.yaml`. Keep raw data under `data/raw_contracts/{SYMBOL}/` unchanged, and treat derived files under `data/continuous/`, `data/aggregated/`, and `data/validation/` as reproducible outputs.
