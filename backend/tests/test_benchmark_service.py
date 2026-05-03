import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pandas as pd

from app.services.benchmark import get_benchmark_series, _cache


@pytest.fixture(autouse=True)
def clear_cache():
    _cache.clear()
    yield
    _cache.clear()


def _make_mock_yfinance(close_values: list[float] | None = None, raise_exc: Exception | None = None):
    """Build a mock yfinance module with a Ticker that returns given close values."""
    if close_values is None:
        close_values = [4500.0, 4600.0]

    mock_yf = MagicMock()

    if raise_exc is not None:
        mock_yf.Ticker.return_value.history.side_effect = raise_exc
    else:
        dates = pd.date_range("2025-01-01", periods=len(close_values), tz="UTC")
        hist_df = pd.DataFrame({"Close": close_values}, index=dates)
        mock_yf.Ticker.return_value.history.return_value = hist_df

    return mock_yf


@pytest.mark.asyncio
async def test_returns_snapshot_series_format():
    mock_yf = _make_mock_yfinance([4500.0, 4600.0])
    with patch.dict("sys.modules", {"yfinance": mock_yf}):
        result = await get_benchmark_series("SPX", "1M")

    assert result["name"] == "S&P 500"
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 2
    assert "timestamp" in result["data"][0]
    assert "value" in result["data"][0]
    assert result["data"][0]["value"] == 4500.0
    assert result["data"][1]["value"] == 4600.0


@pytest.mark.asyncio
async def test_invalid_symbol_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported"):
        await get_benchmark_series("INVALID", "1M")


@pytest.mark.asyncio
async def test_correct_period_passed_to_yfinance():
    mock_yf = _make_mock_yfinance([5000.0])
    with patch.dict("sys.modules", {"yfinance": mock_yf}):
        await get_benchmark_series("SPX", "3M")

    mock_yf.Ticker.assert_called_once_with("^GSPC")
    mock_yf.Ticker.return_value.history.assert_called_once_with(period="3mo")


@pytest.mark.asyncio
async def test_yfinance_error_returns_empty_data():
    mock_yf = _make_mock_yfinance(raise_exc=RuntimeError("network error"))
    with patch.dict("sys.modules", {"yfinance": mock_yf}):
        result = await get_benchmark_series("SPX", "1M")

    assert result["name"] == "S&P 500"
    assert result["data"] == []


@pytest.mark.asyncio
async def test_result_is_cached():
    mock_yf = _make_mock_yfinance([4500.0])
    with patch.dict("sys.modules", {"yfinance": mock_yf}):
        result1 = await get_benchmark_series("SPX", "1M")
        result2 = await get_benchmark_series("SPX", "1M")

    # yfinance Ticker should only have been constructed once
    assert mock_yf.Ticker.call_count == 1
    assert result1 is result2


@pytest.mark.asyncio
async def test_hsi_symbol_uses_correct_ticker():
    mock_yf = _make_mock_yfinance([20000.0])
    with patch.dict("sys.modules", {"yfinance": mock_yf}):
        result = await get_benchmark_series("HSI", "1W")

    assert result["name"] == "Hang Seng"
    mock_yf.Ticker.assert_called_once_with("^HSI")
    mock_yf.Ticker.return_value.history.assert_called_once_with(period="5d")


@pytest.mark.asyncio
async def test_cache_is_separate_per_symbol_and_range():
    mock_yf_spx = _make_mock_yfinance([4500.0])
    mock_yf_hsi = _make_mock_yfinance([20000.0])

    with patch.dict("sys.modules", {"yfinance": mock_yf_spx}):
        r1 = await get_benchmark_series("SPX", "1M")

    with patch.dict("sys.modules", {"yfinance": mock_yf_hsi}):
        r2 = await get_benchmark_series("HSI", "1M")

    assert r1["name"] == "S&P 500"
    assert r2["name"] == "Hang Seng"
    assert len(_cache) == 2
