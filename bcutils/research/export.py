from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import pandas as pd


SEPARATORS = {
    "comma": ",",
    "tab": "\t",
    "space": " ",
}


@dataclass(frozen=True)
class ExportResult:
    source: Path
    output: Path | None
    exported: bool
    reason: str = ""


def export_ohlc_file(
    input_path: Path,
    output_path: Path,
    timezone: str = "UTC",
    separator: str = "comma",
) -> ExportResult:
    frame = pd.read_csv(input_path)
    if not is_ohlc_frame(frame):
        return ExportResult(input_path, None, False, "missing OHLC columns")
    output = to_backtest_ohlc(frame, timezone=timezone)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, sep=separator_value(separator))
    return ExportResult(input_path, output_path, True)


def to_backtest_ohlc(frame: pd.DataFrame, timezone: str = "UTC") -> pd.DataFrame:
    timestamp = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(timezone)
    output = pd.DataFrame(
        {
            "Date": timestamp.dt.strftime("%Y-%m-%d"),
            "Time": timestamp.dt.strftime("%H:%M"),
            "Open": frame["open"],
            "High": frame["high"],
            "Low": frame["low"],
            "Close": frame["close"],
        }
    )
    if "volume" in frame.columns:
        output["Volume"] = frame["volume"]
    return output


def is_ohlc_frame(frame: pd.DataFrame) -> bool:
    required = {"timestamp", "open", "high", "low", "close"}
    return required.issubset(set(frame.columns))


def separator_value(separator: str) -> str:
    if separator not in SEPARATORS:
        known = ", ".join(sorted(SEPARATORS))
        raise ValueError(f"Unknown separator {separator!r}. Use one of: {known}")
    return SEPARATORS[separator]


def output_path_for(input_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{input_path.stem}_ohlc.csv"


def iter_pipeline_ohlc_files(
    data_root: Path,
    source: str | None = None,
) -> Iterable[Path]:
    continuous = data_root / "continuous" / "hourly"
    if continuous.exists():
        yield from matching_csvs(continuous, source)

    aggregated = data_root / "aggregated"
    if aggregated.exists():
        for directory in sorted(path for path in aggregated.iterdir() if path.is_dir()):
            yield from matching_csvs(directory, source)


def matching_csvs(directory: Path, source: str | None = None) -> List[Path]:
    paths = sorted(path for path in directory.glob("*.csv") if path.is_file())
    if source is None:
        return paths
    return [path for path in paths if f"_{source}" in path.stem]
