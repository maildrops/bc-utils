from pathlib import Path

import pandas as pd

from bcutils.research.contracts import (
    ContractInfo,
    approximate_expiry_date,
    infer_contract_info,
    subtract_trading_days,
)
from bcutils.research.continuous import build_roll_schedule


def test_five_trading_days_before_expiry_for_mes_march_2024():
    expiry = approximate_expiry_date("MES", 2024, 3)

    assert expiry.isoformat() == "2024-03-15"
    assert subtract_trading_days(expiry, 5).isoformat() == "2024-03-08"


def test_roll_schedule_contract_order_and_gap():
    contracts = [
        ContractInfo("MES", "MESH24", 3, 2024, Path("MESH24.csv")),
        ContractInfo("MES", "MESM24", 6, 2024, Path("MESM24.csv")),
    ]
    rows = pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-03-08 21:00", tz="UTC"),
                "contract": "MESH24",
                "close": 100.0,
            },
            {
                "timestamp": pd.Timestamp("2024-03-08 21:00", tz="UTC"),
                "contract": "MESM24",
                "close": 103.0,
            },
        ]
    )
    instrument = {"timezone": "America/Chicago", "session_end": "16:00"}
    rule = {"method": "calendar", "roll_at": "session_end"}

    schedule = build_roll_schedule("MES", contracts, rows, instrument, rule, 5)

    assert schedule.iloc[0]["old_contract"] == "MESH24"
    assert schedule.iloc[0]["new_contract"] == "MESM24"
    assert schedule.iloc[0]["roll_gap"] == 3.0


def test_infer_contract_info_from_bcutils_hourly_filename():
    info = infer_contract_info(Path("Hour_MES_20240300.csv"), "MES")

    assert info.contract == "MESH24"
    assert info.contract_month == 3
    assert info.contract_year == 2024
