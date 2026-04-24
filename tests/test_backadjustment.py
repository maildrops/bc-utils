import pandas as pd

from bcutils.research.continuous import apply_difference_backadjustment


def test_difference_backadjustment_applies_gap_to_earlier_history_only():
    unadjusted = pd.DataFrame(
        [
            row("2024-03-08 19:00", "MESH24", 97, 99, 96, 100, 10),
            row("2024-03-08 20:00", "MESH24", 98, 101, 97, 100, 11),
            row("2024-03-08 21:00", "MESM24", 103, 104, 102, 103, 12),
            row("2024-03-08 22:00", "MESM24", 104, 105, 103, 104, 13),
        ]
    )
    schedule = pd.DataFrame(
        [
            {
                "old_contract": "MESH24",
                "new_contract": "MESM24",
                "roll_timestamp": pd.Timestamp("2024-03-08 21:00", tz="UTC"),
                "roll_gap": 3.0,
            }
        ]
    )

    adjusted, adjustments = apply_difference_backadjustment(unadjusted, schedule)

    assert adjusted.iloc[0]["close"] == 103.0
    assert adjusted.iloc[1]["open"] == 101.0
    assert adjusted.iloc[1]["volume"] == 11
    assert adjusted.iloc[1]["raw_volume"] == 11
    assert adjusted.iloc[2]["close"] == 103.0
    assert adjusted.iloc[2]["is_roll_bar"]
    assert adjustments.iloc[0]["adjustment"] == 3.0


def row(timestamp, contract, open_, high, low, close, volume):
    return {
        "timestamp": pd.Timestamp(timestamp, tz="UTC"),
        "symbol": "MES",
        "contract": contract,
        "source": "barchart",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
