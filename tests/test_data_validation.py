import pandas as pd

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


def row(timestamp, open_, high, low, close, volume):
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
