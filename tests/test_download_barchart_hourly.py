import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "download_barchart_hourly.py"
)
SPEC = importlib.util.spec_from_file_location("download_barchart_hourly", SCRIPT_PATH)
download_barchart_hourly = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(download_barchart_hourly)


def test_contract_map_for_symbols_uses_research_instrument_config():
    instruments = {
        "MES": {
            "barchart_root": "MES",
            "month_cycle": "HMUZ",
            "exchange": "CME",
        }
    }

    result = download_barchart_hourly.contract_map_for_symbols(instruments, ["MES"])

    assert result == {"MES": {"code": "MES", "cycle": "HMUZ", "exchange": "CME"}}


def test_contracts_to_download_skips_existing_raw_contract(tmp_path):
    raw_dir = tmp_path / "MES"
    raw_dir.mkdir()
    (raw_dir / "Hour_MES_20240300.csv").write_text("Time,Open,High,Low,Close,Volume\n")
    contract_map = {"MES": {"code": "MES", "cycle": "HM", "exchange": "CME"}}

    result = download_barchart_hourly.contracts_to_download(
        "MES",
        contract_map,
        raw_dir,
        2024,
        2025,
    )

    assert "MESH24" not in result
    assert "MESM24" in result
