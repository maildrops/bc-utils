from pathlib import Path

import pandas as pd

from bcutils.research.export import (
    export_ohlc_file,
    iter_pipeline_ohlc_files,
    output_path_for,
    to_backtest_ohlc,
)


def test_to_backtest_ohlc_uses_requested_timezone_and_columns():
    frame = pd.DataFrame(
        [
            {
                "timestamp": "2024-01-15T15:30:00Z",
                "open": 4500.25,
                "high": 4502.50,
                "low": 4498.75,
                "close": 4501.00,
                "volume": 1250,
            }
        ]
    )

    result = to_backtest_ohlc(frame, timezone="America/Chicago")

    assert list(result.columns) == [
        "Date",
        "Time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]
    assert result.iloc[0].to_dict() == {
        "Date": "2024-01-15",
        "Time": "09:30",
        "Open": 4500.25,
        "High": 4502.50,
        "Low": 4498.75,
        "Close": 4501.00,
        "Volume": 1250,
    }


def test_export_ohlc_file_writes_tab_separated_output(tmp_path):
    input_path = tmp_path / "MNQ_60min_backadjusted.csv"
    output_path = tmp_path / "exports" / "MNQ_60min_backadjusted_ohlc.csv"
    pd.DataFrame(
        [
            {
                "timestamp": "2024-01-15T15:30:00Z",
                "open": 1,
                "high": 2,
                "low": 0,
                "close": 1.5,
                "volume": 10,
            }
        ]
    ).to_csv(input_path, index=False)

    result = export_ohlc_file(input_path, output_path, timezone="UTC", separator="tab")

    assert result.exported
    assert output_path.read_text().splitlines()[0] == (
        "Date\tTime\tOpen\tHigh\tLow\tClose\tVolume"
    )


def test_export_ohlc_file_skips_non_ohlc_csv(tmp_path):
    input_path = tmp_path / "MNQ_roll_schedule.csv"
    output_path = tmp_path / "exports" / "MNQ_roll_schedule_ohlc.csv"
    pd.DataFrame([{"symbol": "MNQ", "old_contract": "NMH24"}]).to_csv(
        input_path, index=False
    )

    result = export_ohlc_file(input_path, output_path)

    assert not result.exported
    assert result.reason == "missing OHLC columns"
    assert not output_path.exists()


def test_iter_pipeline_ohlc_files_finds_continuous_and_aggregated_sources(tmp_path):
    continuous = tmp_path / "continuous" / "hourly"
    aggregated = tmp_path / "aggregated" / "240min"
    continuous.mkdir(parents=True)
    aggregated.mkdir(parents=True)
    continuous_file = continuous / "MNQ_60min_backadjusted.csv"
    aggregated_file = aggregated / "MNQ_240min_backadjusted.csv"
    ignored_file = aggregated / "MNQ_240min_unadjusted.csv"
    for path in [continuous_file, aggregated_file, ignored_file]:
        path.write_text("timestamp,open,high,low,close\n")

    result = list(iter_pipeline_ohlc_files(tmp_path, source="backadjusted"))

    assert result == [continuous_file, aggregated_file]


def test_output_path_for_appends_ohlc_suffix(tmp_path):
    result = output_path_for(
        Path("data/aggregated/240min/MNQ_240min_backadjusted.csv"),
        tmp_path,
    )

    assert result == tmp_path / "MNQ_240min_backadjusted_ohlc.csv"
