from copy import deepcopy

from residual_grid_research.data import make_synthetic_universe
from residual_grid_research.research import all_configured_symbols, run_full_research


def test_offline_research_pipeline_writes_report(config, tmp_path):
    config = deepcopy(config)
    config["universe"]["stock_etf_map"] = {"CSCO": ["XLK"]}
    config["universe"]["stock_pairs"] = [["VZ", "T"]]
    config["universe"]["blind_expansion_pairs"] = [["WMT", "TGT"]]
    config["universe"]["natural_long_symbols"] = ["JPM"]
    data = make_synthetic_universe(all_configured_symbols(config), periods=420, seed=7)
    target = tmp_path / "report.md"
    result = run_full_research(
        data, config, output_path=target, data_source="synthetic test fixture"
    )
    text = result.read_text(encoding="utf-8")
    assert "Executive verdict" in text
    assert "Mandatory baseline comparison" in text
    assert "Selection-bias check" in text
    assert "no market-edge claim" in text
    assert target.with_name("report_trades.csv").exists()
    assert target.with_name("report_decisions.csv").exists()
