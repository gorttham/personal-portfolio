import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.services.ai import build_portfolio_context, build_system_prompt


def make_position(ticker, name, quantity, current_price, currency, avg_cost=None):
    p = MagicMock()
    p.ticker = ticker
    p.name = name
    p.quantity = quantity
    p.current_price = current_price
    p.currency = currency
    p.avg_cost = avg_cost
    return p


def make_transaction(ticker, txn_type, quantity, price, executed_at):
    t = MagicMock()
    t.ticker = ticker
    t.type = txn_type
    t.quantity = quantity
    t.price = price
    t.executed_at = executed_at
    return t


def make_label(name, tickers):
    lbl = MagicMock()
    lbl.name = name
    lbl.tickers = tickers
    return lbl


def test_build_portfolio_context_includes_positions():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=150.0),
        make_position("TSLA", "Tesla Inc.", 5, 200.0, "USD"),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "AAPL" in ctx
    assert "Apple Inc." in ctx
    assert "TSLA" in ctx
    assert "Tesla Inc." in ctx


def test_build_portfolio_context_calculates_pct_of_total():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 100.0, "USD"),
        make_position("GOOG", "Alphabet Inc.", 5, 100.0, "USD"),
    ]
    # AAPL = 1000, GOOG = 500, total = 1500
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "66.7" in ctx
    assert "33.3" in ctx


def test_build_portfolio_context_shows_gain_loss_when_avg_cost_present():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=150.0),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    # gain = (180 - 150) / 150 * 100 = 20.0%
    assert "+20.0%" in ctx


def test_build_portfolio_context_no_gain_loss_without_avg_cost():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=None),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "n/a" in ctx.lower() or "N/A" in ctx


def test_build_portfolio_context_includes_transactions():
    ts = datetime(2026, 4, 15, tzinfo=timezone.utc)
    txns = [
        make_transaction("AAPL", "buy", 5, 170.0, ts),
        make_transaction("TSLA", "sell", 2, 210.0, ts),
    ]
    ctx = build_portfolio_context(positions=[], transactions=txns, labels=[])
    assert "AAPL" in ctx
    assert "buy" in ctx
    assert "TSLA" in ctx
    assert "sell" in ctx


def test_build_portfolio_context_includes_labels():
    labels = [make_label("Tech", ["AAPL", "GOOG"]), make_label("EV", ["TSLA"])]
    ctx = build_portfolio_context(positions=[], transactions=[], labels=labels)
    assert "Tech" in ctx
    assert "AAPL" in ctx
    assert "GOOG" in ctx
    assert "EV" in ctx
    assert "TSLA" in ctx


def test_build_portfolio_context_empty_portfolio():
    ctx = build_portfolio_context(positions=[], transactions=[], labels=[])
    assert "No positions" in ctx or "none" in ctx.lower()


def test_build_system_prompt_contains_static_preamble():
    ctx = "POSITIONS: none"
    prompt = build_system_prompt(ctx)
    assert "portfolio analyst" in prompt.lower()
    assert "financial advice" in prompt.lower()


def test_build_system_prompt_embeds_context():
    ctx = "POSITIONS: AAPL | Apple | $1800 | USD"
    prompt = build_system_prompt(ctx)
    assert ctx in prompt
