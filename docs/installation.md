# Installation Guide

This project uses `uv` for dependency management and local execution. The
recommended setup creates a project-local virtual environment in `.venv` and
uses the locked dependency set in `uv.lock`.

## Prerequisites

- macOS, Linux, or Windows with a shell
- `git`
- `uv`
- Python 3.12, or permission for `uv` to install/manage one
- A Barchart account if you plan to download data from Barchart

The repository includes `.python-version` with `3.12`, so `uv` will prefer
Python 3.12 for this checkout.

## Clone The Repository

```bash
git clone https://github.com/maildrops/bc-utils.git
cd bc-utils
```

If you already have the checkout, move into it:

```bash
cd /path/to/bc-utils
```

## Create The Environment

Install runtime and development dependencies:

```bash
uv sync --dev
```

This creates `.venv` and installs the package in editable mode.

For runtime-only usage, omit the development tools:

```bash
uv sync
```

## Verify The Install

Run the test suite:

```bash
uv run pytest
```

Expected result:

```text
7 passed
```

Check that the package imports:

```bash
uv run python -c "import bcutils; print(bcutils.__name__)"
```

## Running Commands

Run project scripts through `uv run` so they use the project environment:

```bash
uv run python scripts/build_continuous.py --symbol MES
uv run python scripts/aggregate_bars.py --symbol MES --source backadjusted
uv run python scripts/validate_data.py --symbol MES --write-csv
```

You can also activate the environment manually:

```bash
source .venv/bin/activate
python scripts/build_continuous.py --symbol MES
```

Using `uv run` is preferred because it works without remembering whether the
shell is currently activated.

## Updating Dependencies

After changing dependencies in `pyproject.toml`, refresh the lockfile:

```bash
uv lock
uv sync --dev
uv run pytest
```

Commit both `pyproject.toml` and `uv.lock` when dependency changes are
intentional.

## Troubleshooting

If `uv` uses an unexpected Python version, check:

```bash
uv python list --only-installed
uv run python --version
```

If needed, install Python 3.12 through `uv`:

```bash
uv python install 3.12
uv sync --dev
```

If imports fail, resync the environment:

```bash
uv sync --dev --reinstall
```

If Barchart downloads fail, verify credentials and quota first. Free accounts
have a lower daily download allowance than paid subscriptions.
