from __future__ import annotations

import io
import json

import pandas as pd
import pytest

from residual_grid_research.data.trial_adapters import (
    EODHDEventsAdapter,
    EarningsAPIAdapter,
    HFDataLibraryAdapter,
    HistoricalDataNetSampleAdapter,
    MarketParquetLocalAdapter,
    _exchange_rth,
)


class Response:
    def __init__(self, payload=None, *, content=b""):
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

    def iter_content(self, chunk_size=1024 * 1024):
        yield self.content


class CatalogSession:
    def get(self, url, **kwargs):
        return Response({"count": 2, "symbols": [
            {"ticker": "AAPL", "size_bytes": 10, "last_modified": "2026-01-01"},
            {"ticker": "SPY", "size_bytes": 20, "last_modified": "2026-01-01"},
        ]})


def test_hf_public_symbol_coverage_and_auth_boundary(tmp_path):
    adapter = HFDataLibraryAdapter(tmp_path, session=CatalogSession())
    coverage = adapter.coverage(["AAPL", "SPY", "MISSING"])
    assert coverage.set_index("symbol").at["AAPL", "available"]
    assert not coverage.set_index("symbol").at["MISSING", "available"]
    with pytest.raises(RuntimeError, match="HFDL_API_KEY"):
        adapter.download("AAPL", timeframe="5min")


def test_hf_cached_download_does_not_require_key(tmp_path):
    cached = tmp_path / "5min" / "AAPL_clean.parquet"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"cached")
    adapter = HFDataLibraryAdapter(tmp_path)
    assert adapter.download("AAPL", timeframe="5min") == cached


def test_exchange_rth_removes_holiday_and_early_close_prints():
    index = pd.DatetimeIndex([
        "2025-07-03 12:55", "2025-07-03 13:00",
        "2025-07-03 13:05", "2025-07-03 15:00",
        "2025-07-04 10:00", "2025-07-07 10:00",
    ]).tz_localize("America/New_York")
    frame = pd.DataFrame({
        "open": [1.0] * len(index), "high": [1.0] * len(index),
        "low": [1.0] * len(index), "close": [1.0] * len(index),
        "volume": [1] * len(index),
    }, index=index)
    result = _exchange_rth(frame)
    assert list(result.index.strftime("%Y-%m-%d %H:%M")) == [
        "2025-07-03 12:55", "2025-07-03 13:00", "2025-07-07 10:00",
    ]
    assert result.attrs["calendar_rth_removed_bars"] == 3


def test_marketparquet_stub_refuses_missing_archive(tmp_path):
    adapter = MarketParquetLocalAdapter(tmp_path / "absent")
    assert adapter.files("5min") == []
    with pytest.raises(FileNotFoundError):
        adapter.load("AAPL", timeframe="5min")


def test_historicaldata_sample_resamples_raw_and_adjusted(tmp_path, monkeypatch):
    root = tmp_path / "stocks_sample_2022H2"
    minute = root / "minute_by_symbol"
    minute.mkdir(parents=True)
    frame = pd.DataFrame({
        "timestamp": pd.date_range("2022-07-01 09:30", periods=15, freq="1min"),
        "open": range(100, 115), "high": range(101, 116), "low": range(99, 114),
        "close": range(100, 115), "volume": [10] * 15,
        "adj_open": range(50, 65), "adj_high": range(51, 66), "adj_low": range(49, 64),
        "adj_close": range(50, 65), "adj_volume": [20] * 15, "session": ["regular"] * 15,
    })
    frame.to_csv(minute / "KO_minute.csv", index=False)
    adapter = HistoricalDataNetSampleAdapter(tmp_path)
    monkeypatch.setattr(adapter, "ensure_sample", lambda: root)
    result = adapter.load("KO", timeframe="5min")
    assert len(result) == 3
    assert result.iloc[0]["open"] == 100
    assert result.iloc[0]["adjusted_open"] == 50
    assert result.iloc[0]["volume"] == 50


class EventSession:
    def get(self, url, **kwargs):
        if "earningsapi" in url:
            return Response({"earnings": [{"event_date": "2025-01-30", "release_time": "after"}]})
        if "/div/" in url:
            return Response([{"date": "2025-02-07", "value": 0.25}])
        return Response([{"date": "2025-03-01", "split": "2.00/1.00"}])


def test_earningsapi_normalizes_event_rows(tmp_path):
    result = EarningsAPIAdapter(tmp_path, api_key="x", session=EventSession()).fetch("AAPL")
    assert result.iloc[0]["event_type"] == "EARNINGS"
    assert result.iloc[0]["symbol"] == "AAPL"


def test_eodhd_normalizes_dividends_and_splits(tmp_path):
    result = EODHDEventsAdapter(tmp_path, api_key="x", session=EventSession()).fetch(
        "AAPL", start="2025-01-01", end="2025-12-31"
    )
    assert set(result["event_type"]) == {"EX_DIVIDEND", "SPLIT"}
