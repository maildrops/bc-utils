import pandas as pd

from bcutils.research.aggregation import aggregate_timeframe, with_session_columns


INSTRUMENT = {
    "timezone": "America/Chicago",
    "session_start": "17:00",
    "session_end": "16:00",
}


def test_two_hour_aggregation_uses_ohlcv_rules():
    frame = pd.DataFrame(
        [
            row("2024-01-02 23:00", 10, 12, 9, 11, 100),
            row("2024-01-03 00:00", 11, 14, 10, 13, 200),
            row("2024-01-03 01:00", 13, 15, 12, 14, 300),
            row("2024-01-03 02:00", 14, 16, 13, 15, 400),
        ]
    )
    timeframe = {"name": "120min", "pandas_rule": "120min", "anchored_to_session": True}

    result = aggregate_timeframe(frame, "MES", timeframe, INSTRUMENT, "backadjusted")

    first = result.iloc[0]
    assert first["open"] == 10
    assert first["high"] == 14
    assert first["low"] == 9
    assert first["close"] == 13
    assert first["volume"] == 300
    assert first["first_contract"] == "MESH24"
    assert first["target_timeframe"] == "120min"


def test_session_grouping_is_not_naive_midnight():
    frame = pd.DataFrame(
        [
            row("2024-01-02 23:00", 10, 11, 9, 10, 100),
            row("2024-01-03 01:00", 10, 12, 9, 11, 100),
            row("2024-01-03 21:00", 11, 13, 10, 12, 100),
        ]
    )

    local = with_session_columns(frame, INSTRUMENT)

    assert local.iloc[0]["session_date"].isoformat() == "2024-01-02"
    assert local.iloc[1]["session_date"].isoformat() == "2024-01-02"
    assert local.iloc[2]["session_date"].isoformat() == "2024-01-02"


def test_intraday_aggregation_returns_globally_sorted_rows():
    frame = pd.DataFrame(
        [
            row("2024-01-03 01:00", 13, 15, 12, 14, 300),
            row("2024-01-03 00:00", 11, 14, 10, 13, 200),
            row("2024-01-02 23:00", 10, 12, 9, 11, 100),
            row("2024-01-04 00:00", 15, 17, 14, 16, 500),
            row("2024-01-03 23:00", 14, 16, 13, 15, 400),
        ]
    )
    timeframe = {"name": "120min", "pandas_rule": "120min", "anchored_to_session": True}

    result = aggregate_timeframe(frame, "MES", timeframe, INSTRUMENT, "backadjusted")

    assert result["timestamp"].is_monotonic_increasing


def row(timestamp, open_, high, low, close, volume):
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "symbol": "MES",
        "contract": "MESH24",
        "source": "barchart",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "is_roll_bar": False,
    }
