import asyncio
from datetime import datetime, timezone
from typing import Any

BENCHMARK_SYMBOLS = {
    "SPX": ("^GSPC", "S&P 500"),
    "HSI": ("^HSI", "Hang Seng"),
}

YFINANCE_PERIODS = {
    "1W": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "all": "5y",
}

# Simple in-memory cache: key -> (fetched_at, data)
_cache: dict[str, tuple[datetime, dict]] = {}
CACHE_TTL_SECONDS = 3600


def _is_cached(key: str) -> bool:
    if key not in _cache:
        return False
    fetched_at, _ = _cache[key]
    age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    return age < CACHE_TTL_SECONDS


async def get_benchmark_series(symbol: str, range_: str) -> dict[str, Any]:
    if symbol not in BENCHMARK_SYMBOLS:
        raise ValueError(f"Unsupported benchmark symbol: {symbol}")

    cache_key = f"{symbol}:{range_}"
    if _is_cached(cache_key):
        return _cache[cache_key][1]

    yf_symbol, display_name = BENCHMARK_SYMBOLS[symbol]
    period = YFINANCE_PERIODS.get(range_, "1mo")

    def _fetch() -> list[dict]:
        import yfinance as yf  # lazy import
        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period)
            return [
                {
                    "timestamp": idx.to_pydatetime().isoformat(),
                    "value": float(row["Close"]),
                }
                for idx, row in hist.iterrows()
            ]
        except Exception:
            return []

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch)

    result = {"name": display_name, "data": data}
    _cache[cache_key] = (datetime.now(timezone.utc), result)
    return result
