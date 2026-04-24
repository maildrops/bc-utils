import pandas as pd

from bcutils.research.io import normalize_columns
from bcutils.research.validation import validate_frame


def test_validation_detects_duplicate_timestamps():
    frame = pd.DataFrame(
        [
            row("2024-01-01 00:00", 10, 11, 9, 10, 1),
            row("2024-01-01 00:00", 10, 11, 9, 10, 1),
        ]
    )

    report = validate_frame(frame, "sample")
    duplicate = report[report["check"] == "duplicate_timestamps"].iloc[0]

    assert not duplicate["passed"]
    assert duplicate["count"] == 1


def test_validation_detects_ohlc_sanity_failures():
    frame = pd.DataFrame([row("2024-01-01 00:00", 10, 9, 11, 10, 1)])

    report = validate_frame(frame, "sample")
    sanity = report[report["check"] == "ohlc_sanity"].iloc[0]

    assert not sanity["passed"]
    assert sanity["count"] == 1


def test_normalize_columns_accepts_barchart_latest_close_header():
    frame = pd.DataFrame(
        [
            {
                "Time": "2023-03-06T15:00:00+0000",
                "Open": 13050.0,
                "High": 13060.0,
                "Low": 13050.0,
                "Latest": 13060.0,
                "Volume": 2,
            }
        ]
    )

    normalized = normalize_columns(frame)

    assert list(normalized.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert normalized.iloc[0]["close"] == 13060.0


def row(timestamp, open_, high, low, close, volume):
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
