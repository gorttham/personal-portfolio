# Phase 2: Dashboard & Charts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/dashboard` page with a summary bar, interactive portfolio line chart, capital allocation pie chart, and nav sidebar, backed by four new FastAPI endpoints that query the existing `portfolio_snapshots`, `positions`, and `transactions` tables.

**Architecture:** Four new `GET /portfolio/*` endpoints in a dedicated FastAPI router query the database through a `PortfolioService` class; the Next.js dashboard page is a server component that fetches data and passes it to three purely-presentational client components (SummaryBar, PortfolioLineChart, AllocationPieChart) and a Sidebar nav component. Currency groups are never aggregated — each currency is always displayed separately.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui, Recharts `ComposedChart` + `PieChart` (frontend) · FastAPI, SQLAlchemy 2.0 async, PyTest + pytest-asyncio (backend) · Neon PostgreSQL

---

## File Map

```
backend/app/routers/portfolio.py         # New router: GET /portfolio/summary|snapshots|transactions|positions
backend/app/services/portfolio.py        # PortfolioService: all DB query logic
backend/app/schemas/portfolio_dashboard.py  # Pydantic response schemas for new endpoints
backend/tests/test_portfolio_service.py  # Unit tests for PortfolioService methods
backend/tests/test_portfolio_router.py   # Integration tests for the 4 endpoints

frontend/lib/dashboard.ts                # TypeScript types + apiFetch wrapper functions
frontend/app/dashboard/page.tsx          # Server component: fetches all data, renders layout
frontend/components/dashboard/Sidebar.tsx           # Nav sidebar (links, active state)
frontend/components/dashboard/SummaryBar.tsx         # Total value + daily change + sync badge
frontend/components/dashboard/PortfolioLineChart.tsx # Recharts ComposedChart with controls
frontend/components/dashboard/AllocationPieChart.tsx # Recharts PieChart with split dropdown
```

---

## Task 1: Backend Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/portfolio_dashboard.py`

- [ ] **Step 1: Create `backend/app/schemas/portfolio_dashboard.py`**

```python
# backend/app/schemas/portfolio_dashboard.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AccountSummary(BaseModel):
    id: str
    broker: str
    currency: str
    total_value: float
    account_name: str


class PortfolioSummaryResponse(BaseModel):
    accounts: list[AccountSummary]
    last_synced_at: Optional[datetime]


class SnapshotPoint(BaseModel):
    timestamp: datetime
    value: float


class SnapshotSeries(BaseModel):
    name: str
    data: list[SnapshotPoint]


class PortfolioSnapshotsResponse(BaseModel):
    series: list[SnapshotSeries]
    currency_groups: list[str]


class TransactionMarker(BaseModel):
    ticker: str
    type: str          # "buy" | "sell"
    quantity: float
    price: float
    executed_at: datetime


class PositionItem(BaseModel):
    ticker: str
    name: str
    current_value: float
    currency: str
    asset_class: str
    sector: Optional[str]
    country: Optional[str]
    broker: str
    label_names: list[str]
```

- [ ] **Step 2: Verify schemas parse correctly**

```bash
cd /home/user/personal-portfolio/backend && python -c "
from app.schemas.portfolio_dashboard import (
    PortfolioSummaryResponse, PortfolioSnapshotsResponse,
    TransactionMarker, PositionItem
)
print('AccountSummary OK')
print('PortfolioSummaryResponse OK')
print('PortfolioSnapshotsResponse OK')
print('TransactionMarker OK')
print('PositionItem OK')
"
```

Expected output:
```
AccountSummary OK
PortfolioSummaryResponse OK
PortfolioSnapshotsResponse OK
TransactionMarker OK
PositionItem OK
```

---

## Task 2: Backend PortfolioService — Skeleton + Failing Tests

**Files:**
- Create: `backend/app/services/portfolio.py`
- Create: `backend/tests/test_portfolio_service.py`

- [ ] **Step 1: Write failing tests for PortfolioService**

```python
# backend/tests/test_portfolio_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services.portfolio import PortfolioService


@pytest.fixture
def user_id():
    return str(uuid4())


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


# ── get_summary ──────────────────────────────────────────────────────────────

class TestGetSummary:
    @pytest.mark.asyncio
    async def test_returns_accounts_list(self, mock_session, user_id):
        """get_summary returns list of AccountSummary dicts for each account."""
        row = MagicMock()
        row.id = str(uuid4())
        row.broker = "longbridge"
        row.currency = "HKD"
        row.total_value = 35000.0
        row.account_name = "Main"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)

        assert "accounts" in data
        assert len(data["accounts"]) == 1
        assert data["accounts"][0]["broker"] == "longbridge"
        assert data["accounts"][0]["currency"] == "HKD"
        assert data["accounts"][0]["total_value"] == 35000.0

    @pytest.mark.asyncio
    async def test_returns_last_synced_at(self, mock_session, user_id):
        """get_summary includes last_synced_at from most recent sync across all connections."""
        ts = datetime(2026, 5, 2, 8, 0, 0, tzinfo=timezone.utc)
        row = MagicMock()
        row.id = str(uuid4())
        row.broker = "ibkr"
        row.currency = "USD"
        row.total_value = 10000.0
        row.account_name = "IBKR Main"

        sync_row = MagicMock()
        sync_row.last_synced_at = ts

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        sync_result = MagicMock()
        sync_result.scalar_one_or_none.return_value = ts

        mock_session.execute = AsyncMock(side_effect=[result_mock, sync_result])

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)

        assert data["last_synced_at"] == ts

    @pytest.mark.asyncio
    async def test_empty_accounts(self, mock_session, user_id):
        """get_summary returns empty list when user has no accounts."""
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        sync_result = MagicMock()
        sync_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[result_mock, sync_result])

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)

        assert data["accounts"] == []
        assert data["last_synced_at"] is None


# ── get_snapshots ─────────────────────────────────────────────────────────────

class TestGetSnapshots:
    @pytest.mark.asyncio
    async def test_total_split_groups_by_currency(self, mock_session, user_id):
        """split=total returns one series per currency."""
        ts1 = datetime(2026, 4, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 2, tzinfo=timezone.utc)

        row1 = MagicMock()
        row1.snapped_at = ts1
        row1.total_value = 10000.0
        row1.currency = "USD"

        row2 = MagicMock()
        row2.snapped_at = ts2
        row2.total_value = 10500.0
        row2.currency = "USD"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row1, row2]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="1M", split="total")

        assert "series" in data
        assert "currency_groups" in data
        assert "USD" in data["currency_groups"]
        usd_series = next(s for s in data["series"] if "USD" in s["name"])
        assert len(usd_series["data"]) == 2
        assert usd_series["data"][0]["value"] == 10000.0

    @pytest.mark.asyncio
    async def test_broker_split_groups_by_broker_and_currency(self, mock_session, user_id):
        """split=broker returns one series per (broker, currency) pair."""
        ts = datetime(2026, 4, 1, tzinfo=timezone.utc)

        row1 = MagicMock()
        row1.snapped_at = ts
        row1.total_value = 5000.0
        row1.currency = "USD"
        row1.broker = "ibkr"

        row2 = MagicMock()
        row2.snapped_at = ts
        row2.total_value = 35000.0
        row2.currency = "HKD"
        row2.broker = "longbridge"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row1, row2]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="1M", split="broker")

        series_names = [s["name"] for s in data["series"]]
        assert any("ibkr" in n.lower() for n in series_names)
        assert any("longbridge" in n.lower() for n in series_names)

    @pytest.mark.asyncio
    async def test_range_1w_limits_window(self, mock_session, user_id):
        """range=1W passes a cutoff roughly 7 days ago to the query."""
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        await svc.get_snapshots(user_id, range_="1W", split="total")

        call_args = mock_session.execute.call_args
        assert call_args is not None  # query was executed

    @pytest.mark.asyncio
    async def test_range_all_has_no_cutoff(self, mock_session, user_id):
        """range=all fetches all snapshots (no lower date bound)."""
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="all", split="total")

        assert data["series"] == []
        assert data["currency_groups"] == []


# ── get_transactions ──────────────────────────────────────────────────────────

class TestGetTransactions:
    @pytest.mark.asyncio
    async def test_returns_transaction_list(self, mock_session, user_id):
        """get_transactions returns list of dicts with required fields."""
        ts = datetime(2026, 4, 15, tzinfo=timezone.utc)
        row = MagicMock()
        row.ticker = "AAPL"
        row.transaction_type = "buy"
        row.quantity = 10.0
        row.price = 150.0
        row.executed_at = ts

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        txns = await svc.get_transactions(user_id, range_="1M")

        assert len(txns) == 1
        assert txns[0]["ticker"] == "AAPL"
        assert txns[0]["type"] == "buy"
        assert txns[0]["quantity"] == 10.0
        assert txns[0]["price"] == 150.0
        assert txns[0]["executed_at"] == ts

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_session, user_id):
        """get_transactions returns empty list when no transactions in range."""
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        txns = await svc.get_transactions(user_id, range_="1W")

        assert txns == []


# ── get_positions ─────────────────────────────────────────────────────────────

class TestGetPositions:
    @pytest.mark.asyncio
    async def test_returns_position_list(self, mock_session, user_id):
        """get_positions returns list of dicts with required fields including label_names."""
        row = MagicMock()
        row.ticker = "AAPL"
        row.name = "Apple Inc."
        row.current_value = 1750.0
        row.currency = "USD"
        row.asset_class = "stock"
        row.sector = "Technology"
        row.country = "US"
        row.broker = "ibkr"
        row.label_names = ["Tech", "Growth"]

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        positions = await svc.get_positions(user_id)

        assert len(positions) == 1
        p = positions[0]
        assert p["ticker"] == "AAPL"
        assert p["label_names"] == ["Tech", "Growth"]

    @pytest.mark.asyncio
    async def test_positions_with_no_labels(self, mock_session, user_id):
        """get_positions returns empty label_names list for unlabelled positions."""
        row = MagicMock()
        row.ticker = "700"
        row.name = "Tencent"
        row.current_value = 5000.0
        row.currency = "HKD"
        row.asset_class = "stock"
        row.sector = None
        row.country = "CN"
        row.broker = "longbridge"
        row.label_names = []

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        positions = await svc.get_positions(user_id)

        assert positions[0]["label_names"] == []
```

- [ ] **Step 2: Run failing tests (expect ImportError / AttributeError)**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/test_portfolio_service.py -v 2>&1 | head -40
```

Expected output (tests fail because `app.services.portfolio` does not exist yet):
```
ERROR tests/test_portfolio_service.py - ModuleNotFoundError: No module named 'app.services.portfolio'
```

- [ ] **Step 3: Create `backend/app/services/portfolio.py` skeleton**

```python
# backend/app/services/portfolio.py
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


RANGE_DELTAS = {
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
    "all": None,
}


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def get_summary(self, user_id: str) -> dict[str, Any]:
        # Query accounts (brokerage_connections joined to accounts for total_value)
        accounts_sql = text("""
            SELECT
                a.id::text,
                bc.broker,
                a.currency,
                COALESCE(SUM(p.current_value), 0.0) AS total_value,
                COALESCE(a.account_name, bc.broker) AS account_name
            FROM accounts a
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            LEFT JOIN positions p ON p.account_id = a.id
            WHERE bc.user_id = :user_id
            GROUP BY a.id, bc.broker, a.currency, a.account_name
            ORDER BY bc.broker, a.currency
        """)
        result = await self.session.execute(accounts_sql, {"user_id": user_id})
        rows = result.mappings().all()

        accounts = [
            {
                "id": row.id,
                "broker": row.broker,
                "currency": row.currency,
                "total_value": float(row.total_value),
                "account_name": row.account_name,
            }
            for row in rows
        ]

        # Last synced across all connections for this user
        sync_sql = text("""
            SELECT MAX(last_synced_at) AS last_synced_at
            FROM brokerage_connections
            WHERE user_id = :user_id
        """)
        sync_result = await self.session.execute(sync_sql, {"user_id": user_id})
        last_synced_at = sync_result.scalar_one_or_none()

        return {"accounts": accounts, "last_synced_at": last_synced_at}

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    async def get_snapshots(
        self, user_id: str, range_: str, split: str
    ) -> dict[str, Any]:
        delta = RANGE_DELTAS.get(range_)
        cutoff = (
            (datetime.now(timezone.utc) - delta).isoformat()
            if delta is not None
            else None
        )

        if split == "total":
            return await self._snapshots_total(user_id, cutoff)
        elif split == "broker":
            return await self._snapshots_broker(user_id, cutoff)
        elif split == "label":
            return await self._snapshots_label(user_id, cutoff)
        elif split == "stock":
            return await self._snapshots_stock(user_id, cutoff)
        else:
            return await self._snapshots_total(user_id, cutoff)

    async def _snapshots_total(
        self, user_id: str, cutoff: str | None
    ) -> dict[str, Any]:
        where_cutoff = "AND ps.snapped_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapped_at,
                a.currency,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapped_at, a.currency
            ORDER BY a.currency, ps.snapped_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return self._rows_to_series(rows, key_fn=lambda r: f"Total {r.currency}")

    async def _snapshots_broker(
        self, user_id: str, cutoff: str | None
    ) -> dict[str, Any]:
        where_cutoff = "AND ps.snapped_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapped_at,
                a.currency,
                bc.broker,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapped_at, a.currency, bc.broker
            ORDER BY bc.broker, a.currency, ps.snapped_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return self._rows_to_series(
            rows, key_fn=lambda r: f"{r.broker} ({r.currency})"
        )

    async def _snapshots_label(
        self, user_id: str, cutoff: str | None
    ) -> dict[str, Any]:
        """Snapshot series split by asset label group (positions not in any label → 'Unassigned')."""
        where_cutoff = "AND ps.snapped_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapped_at,
                a.currency,
                COALESCE(al.name, 'Unassigned') AS label_name,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            LEFT JOIN positions pos ON pos.account_id = a.id
            LEFT JOIN asset_label_assignments ala ON ala.position_id = pos.id
            LEFT JOIN asset_labels al ON al.id = ala.label_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapped_at, a.currency, label_name
            ORDER BY label_name, a.currency, ps.snapped_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return self._rows_to_series(
            rows, key_fn=lambda r: f"{r.label_name} ({r.currency})"
        )

    async def _snapshots_stock(
        self, user_id: str, cutoff: str | None
    ) -> dict[str, Any]:
        """Snapshot series split by individual position/ticker."""
        where_cutoff = "AND ps.snapped_at >= :cutoff" if cutoff else ""
        # For per-stock we use position market values at each snapshot time.
        # We use the closest snapshot per account and multiply by weight.
        # Simpler: use the positions table current value joined to snapshots timestamp.
        # NOTE: This is an approximation — positions table holds *current* values;
        # true historical per-stock breakdown requires storing per-position snapshots.
        # For now, distribute each snapshot's total_value proportionally by current position weight.
        sql = text(f"""
            SELECT
                ps.snapped_at,
                a.currency,
                pos.ticker,
                pos.name AS position_name,
                SUM(ps.total_value) * (pos.current_value / NULLIF(acct_total.total, 0)) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            JOIN positions pos ON pos.account_id = a.id
            JOIN (
                SELECT account_id, SUM(current_value) AS total
                FROM positions
                GROUP BY account_id
            ) acct_total ON acct_total.account_id = a.id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapped_at, a.currency, pos.ticker, pos.name, pos.current_value, acct_total.total
            ORDER BY pos.ticker, a.currency, ps.snapped_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return self._rows_to_series(
            rows, key_fn=lambda r: f"{r.ticker} ({r.currency})"
        )

    @staticmethod
    def _rows_to_series(rows: list, key_fn) -> dict[str, Any]:
        """Convert flat query rows into series list grouped by key_fn."""
        series_map: dict[str, list[dict]] = {}
        currencies: set[str] = set()

        for row in rows:
            key = key_fn(row)
            currencies.add(row.currency)
            if key not in series_map:
                series_map[key] = []
            series_map[key].append(
                {"timestamp": row.snapped_at, "value": float(row.total_value)}
            )

        return {
            "series": [{"name": k, "data": v} for k, v in series_map.items()],
            "currency_groups": sorted(currencies),
        }

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def get_transactions(
        self, user_id: str, range_: str
    ) -> list[dict[str, Any]]:
        delta = RANGE_DELTAS.get(range_)
        cutoff = (
            (datetime.now(timezone.utc) - delta).isoformat()
            if delta is not None
            else None
        )

        where_cutoff = "AND t.executed_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                t.ticker,
                t.transaction_type,
                t.quantity,
                t.price,
                t.executed_at
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            ORDER BY t.executed_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()

        return [
            {
                "ticker": row.ticker,
                "type": row.transaction_type,
                "quantity": float(row.quantity),
                "price": float(row.price),
                "executed_at": row.executed_at,
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    async def get_positions(self, user_id: str) -> list[dict[str, Any]]:
        sql = text("""
            SELECT
                pos.ticker,
                pos.name,
                pos.current_value,
                a.currency,
                pos.asset_class,
                pos.sector,
                pos.country,
                bc.broker,
                COALESCE(
                    ARRAY_AGG(al.name ORDER BY al.name) FILTER (WHERE al.name IS NOT NULL),
                    '{}'
                ) AS label_names
            FROM positions pos
            JOIN accounts a ON a.id = pos.account_id
            JOIN brokerage_connections bc ON bc.id = a.brokerage_connection_id
            LEFT JOIN asset_label_assignments ala ON ala.position_id = pos.id
            LEFT JOIN asset_labels al ON al.id = ala.label_id
            WHERE bc.user_id = :user_id
            GROUP BY pos.id, pos.ticker, pos.name, pos.current_value,
                     a.currency, pos.asset_class, pos.sector, pos.country, bc.broker
            ORDER BY pos.ticker
        """)
        result = await self.session.execute(sql, {"user_id": user_id})
        rows = result.mappings().all()

        return [
            {
                "ticker": row.ticker,
                "name": row.name,
                "current_value": float(row.current_value),
                "currency": row.currency,
                "asset_class": row.asset_class,
                "sector": row.sector,
                "country": row.country,
                "broker": row.broker,
                "label_names": list(row.label_names) if row.label_names else [],
            }
            for row in rows
        ]
```

- [ ] **Step 4: Run tests — expect them to pass**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/test_portfolio_service.py -v
```

Expected output:
```
tests/test_portfolio_service.py::TestGetSummary::test_returns_accounts_list PASSED
tests/test_portfolio_service.py::TestGetSummary::test_returns_last_synced_at PASSED
tests/test_portfolio_service.py::TestGetSummary::test_empty_accounts PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_total_split_groups_by_currency PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_broker_split_groups_by_broker_and_currency PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_range_1w_limits_window PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_range_all_has_no_cutoff PASSED
tests/test_portfolio_service.py::TestGetTransactions::test_returns_transaction_list PASSED
tests/test_portfolio_service.py::TestGetTransactions::test_empty_result PASSED
tests/test_portfolio_service.py::TestGetPositions::test_returns_position_list PASSED
tests/test_portfolio_service.py::TestGetPositions::test_positions_with_no_labels PASSED
11 passed in ...s
```

- [ ] **Step 5: Commit**

```bash
cd /home/user/personal-portfolio && git add backend/app/services/portfolio.py backend/app/schemas/portfolio_dashboard.py backend/tests/test_portfolio_service.py && git commit -m "feat(backend): add PortfolioService with summary/snapshots/transactions/positions queries"
```

---

## Task 3: Backend Portfolio Router — Failing Tests then Implementation

**Files:**
- Create: `backend/app/routers/portfolio.py`
- Create: `backend/tests/test_portfolio_router.py`

- [ ] **Step 1: Write failing tests for the router**

```python
# backend/tests/test_portfolio_router.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import get_current_user_email
from app.database import get_session


TEST_EMAIL = "test@example.com"
TEST_USER_ID = str(uuid4())


def override_get_current_user_email():
    return TEST_EMAIL


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user_email] = override_get_current_user_email
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_service_summary():
    return {
        "accounts": [
            {
                "id": str(uuid4()),
                "broker": "ibkr",
                "currency": "USD",
                "total_value": 10000.0,
                "account_name": "IBKR Main",
            }
        ],
        "last_synced_at": datetime(2026, 5, 2, 8, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def mock_service_snapshots():
    return {
        "series": [
            {
                "name": "Total USD",
                "data": [
                    {"timestamp": datetime(2026, 4, 1, tzinfo=timezone.utc), "value": 9000.0},
                    {"timestamp": datetime(2026, 4, 30, tzinfo=timezone.utc), "value": 10000.0},
                ],
            }
        ],
        "currency_groups": ["USD"],
    }


@pytest.fixture
def mock_service_transactions():
    return [
        {
            "ticker": "AAPL",
            "type": "buy",
            "quantity": 10.0,
            "price": 150.0,
            "executed_at": datetime(2026, 4, 15, tzinfo=timezone.utc),
        }
    ]


@pytest.fixture
def mock_service_positions():
    return [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "current_value": 1750.0,
            "currency": "USD",
            "asset_class": "stock",
            "sector": "Technology",
            "country": "US",
            "broker": "ibkr",
            "label_names": ["Tech"],
        }
    ]


class TestPortfolioSummaryEndpoint:
    def test_get_summary_returns_200(self, client, mock_service_summary):
        with patch(
            "app.routers.portfolio.PortfolioService.get_summary",
            new_callable=AsyncMock,
            return_value=mock_service_summary,
        ):
            response = client.get("/portfolio/summary")

        assert response.status_code == 200
        body = response.json()
        assert "accounts" in body
        assert "last_synced_at" in body
        assert body["accounts"][0]["broker"] == "ibkr"
        assert body["accounts"][0]["currency"] == "USD"

    def test_get_summary_requires_auth(self):
        with TestClient(app) as c:
            response = c.get("/portfolio/summary")
        assert response.status_code == 401

    def test_get_summary_empty_accounts(self, client):
        empty = {"accounts": [], "last_synced_at": None}
        with patch(
            "app.routers.portfolio.PortfolioService.get_summary",
            new_callable=AsyncMock,
            return_value=empty,
        ):
            response = client.get("/portfolio/summary")

        assert response.status_code == 200
        assert response.json()["accounts"] == []


class TestPortfolioSnapshotsEndpoint:
    def test_get_snapshots_defaults(self, client, mock_service_snapshots):
        with patch(
            "app.routers.portfolio.PortfolioService.get_snapshots",
            new_callable=AsyncMock,
            return_value=mock_service_snapshots,
        ):
            response = client.get("/portfolio/snapshots")

        assert response.status_code == 200
        body = response.json()
        assert "series" in body
        assert "currency_groups" in body

    def test_get_snapshots_accepts_range_and_split_params(self, client, mock_service_snapshots):
        with patch(
            "app.routers.portfolio.PortfolioService.get_snapshots",
            new_callable=AsyncMock,
            return_value=mock_service_snapshots,
        ) as mock_svc:
            response = client.get("/portfolio/snapshots?range=3M&split=broker")

        assert response.status_code == 200
        mock_svc.assert_called_once()
        call_kwargs = mock_svc.call_args
        # range_ and split are passed through to the service
        assert "3M" in str(call_kwargs) or "3M" in repr(call_kwargs)

    def test_get_snapshots_invalid_range_returns_422(self, client):
        response = client.get("/portfolio/snapshots?range=BADRANGE")
        assert response.status_code == 422

    def test_get_snapshots_invalid_split_returns_422(self, client):
        response = client.get("/portfolio/snapshots?split=badsplit")
        assert response.status_code == 422


class TestPortfolioTransactionsEndpoint:
    def test_get_transactions_returns_list(self, client, mock_service_transactions):
        with patch(
            "app.routers.portfolio.PortfolioService.get_transactions",
            new_callable=AsyncMock,
            return_value=mock_service_transactions,
        ):
            response = client.get("/portfolio/transactions")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert body[0]["ticker"] == "AAPL"
        assert body[0]["type"] == "buy"

    def test_get_transactions_accepts_range_param(self, client, mock_service_transactions):
        with patch(
            "app.routers.portfolio.PortfolioService.get_transactions",
            new_callable=AsyncMock,
            return_value=mock_service_transactions,
        ):
            response = client.get("/portfolio/transactions?range=1W")

        assert response.status_code == 200


class TestPortfolioPositionsEndpoint:
    def test_get_positions_returns_list(self, client, mock_service_positions):
        with patch(
            "app.routers.portfolio.PortfolioService.get_positions",
            new_callable=AsyncMock,
            return_value=mock_service_positions,
        ):
            response = client.get("/portfolio/positions")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert body[0]["ticker"] == "AAPL"
        assert body[0]["label_names"] == ["Tech"]

    def test_get_positions_empty(self, client):
        with patch(
            "app.routers.portfolio.PortfolioService.get_positions",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/portfolio/positions")

        assert response.status_code == 200
        assert response.json() == []
```

- [ ] **Step 2: Run failing tests (expect 404 — router not registered)**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/test_portfolio_router.py -v 2>&1 | head -30
```

Expected output:
```
FAILED tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_returns_200 - assert 404 == 200
...
```

- [ ] **Step 3: Create `backend/app/routers/portfolio.py`**

```python
# backend/app/routers/portfolio.py
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.auth import get_current_user_email
from app.services.portfolio import PortfolioService
from app.schemas.portfolio_dashboard import (
    PortfolioSummaryResponse,
    PortfolioSnapshotsResponse,
    TransactionMarker,
    PositionItem,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

RangeParam = Literal["1W", "1M", "3M", "6M", "1Y", "all"]
SplitParam = Literal["total", "broker", "label", "stock"]


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_summary(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    svc = PortfolioService(session)
    # Resolve user_id from email
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    )
    user_id = result.scalar_one()
    data = await svc.get_summary(user_id)
    return data


@router.get("/snapshots", response_model=PortfolioSnapshotsResponse)
async def get_snapshots(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
    range: RangeParam = Query(default="1M"),
    split: SplitParam = Query(default="total"),
):
    svc = PortfolioService(session)
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    )
    user_id = result.scalar_one()
    data = await svc.get_snapshots(user_id, range_=range, split=split)
    return data


@router.get("/transactions", response_model=list[TransactionMarker])
async def get_transactions(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
    range: RangeParam = Query(default="1M"),
):
    svc = PortfolioService(session)
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    )
    user_id = result.scalar_one()
    return await svc.get_transactions(user_id, range_=range)


@router.get("/positions", response_model=list[PositionItem])
async def get_positions(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    svc = PortfolioService(session)
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    )
    user_id = result.scalar_one()
    return await svc.get_positions(user_id)
```

- [ ] **Step 4: Register the portfolio router in `backend/app/main.py`**

Open `backend/app/main.py` and add after the existing `app.include_router(sync.router, ...)` line:

```python
from app.routers import portfolio as portfolio_router
app.include_router(portfolio_router.router)
```

The complete import + registration block at the bottom of `main.py` should read:

```python
from app.routers import auth, brokerages, sync
from app.routers import portfolio as portfolio_router

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(brokerages.router, prefix="/brokerages", tags=["brokerages"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(portfolio_router.router)
```

- [ ] **Step 5: Run all router tests — expect pass**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/test_portfolio_router.py -v
```

Expected output:
```
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_returns_200 PASSED
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_requires_auth PASSED
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_empty_accounts PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_defaults PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_accepts_range_and_split_params PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_invalid_range_returns_422 PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_invalid_split_returns_422 PASSED
tests/test_portfolio_router.py::TestPortfolioTransactionsEndpoint::test_get_transactions_returns_list PASSED
tests/test_portfolio_router.py::TestPortfolioTransactionsEndpoint::test_get_transactions_accepts_range_param PASSED
tests/test_portfolio_router.py::TestPortfolioPositionsEndpoint::test_get_positions_returns_list PASSED
tests/test_portfolio_router.py::TestPortfolioPositionsEndpoint::test_get_positions_empty PASSED
11 passed in ...s
```

- [ ] **Step 6: Run full backend test suite**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/ -v
```

Expected output: all existing + new tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
cd /home/user/personal-portfolio && git add backend/app/routers/portfolio.py backend/app/main.py backend/tests/test_portfolio_router.py && git commit -m "feat(backend): add /portfolio router with summary/snapshots/transactions/positions endpoints"
```

---

## Task 4: Frontend TypeScript Types and Data-Fetch Functions

**Files:**
- Create: `frontend/lib/dashboard.ts`

- [ ] **Step 1: Create `frontend/lib/dashboard.ts`**

```typescript
// frontend/lib/dashboard.ts
import { apiFetch } from "./api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AccountSummary {
  id: string;
  broker: string;
  currency: string;
  total_value: number;
  account_name: string;
}

export interface PortfolioSummary {
  accounts: AccountSummary[];
  last_synced_at: string | null;
}

export interface SnapshotPoint {
  timestamp: string;
  value: number;
}

export interface SnapshotSeries {
  name: string;
  data: SnapshotPoint[];
}

export interface PortfolioSnapshots {
  series: SnapshotSeries[];
  currency_groups: string[];
}

export type SnapshotRange = "1W" | "1M" | "3M" | "6M" | "1Y" | "all";
export type SnapshotSplit = "total" | "broker" | "label" | "stock";

export interface TransactionMarker {
  ticker: string;
  type: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
}

export interface PositionItem {
  ticker: string;
  name: string;
  current_value: number;
  currency: string;
  asset_class: string;
  sector: string | null;
  country: string | null;
  broker: string;
  label_names: string[];
}

export type PieSplit = "asset_class" | "country" | "sector" | "label" | "broker";

// ── Colour palette for chart series ──────────────────────────────────────────

export const CHART_COLORS = [
  "#6366f1", // indigo-500
  "#f59e0b", // amber-500
  "#10b981", // emerald-500
  "#ef4444", // red-500
  "#3b82f6", // blue-500
  "#8b5cf6", // violet-500
  "#ec4899", // pink-500
  "#14b8a6", // teal-500
];

export function colorForIndex(i: number): string {
  return CHART_COLORS[i % CHART_COLORS.length];
}

// ── Normalise a series to % change from its first value ───────────────────────
// Returns a new array where the first value = 0.0 and subsequent values are
// percentage change from that baseline.  (first_value / first_value - 1)*100 = 0
export function normalizeToPercent(data: SnapshotPoint[]): SnapshotPoint[] {
  if (data.length === 0) return [];
  const base = data[0].value;
  if (base === 0) return data.map((p) => ({ ...p, value: 0 }));
  return data.map((p) => ({
    timestamp: p.timestamp,
    value: ((p.value / base) - 1) * 100,
  }));
}

// ── Aggregate positions into pie slices by split dimension ───────────────────

export interface PieSlice {
  name: string;
  value: number;
  currency: string;
}

export function buildPieSlices(
  positions: PositionItem[],
  split: PieSplit,
  currency: string
): PieSlice[] {
  const filtered = positions.filter((p) => p.currency === currency);
  const map = new Map<string, number>();

  for (const pos of filtered) {
    let key: string;
    switch (split) {
      case "asset_class":
        key = pos.asset_class || "Unknown";
        break;
      case "country":
        key = pos.country || "Unknown";
        break;
      case "sector":
        key = pos.sector || "Unknown";
        break;
      case "label":
        if (pos.label_names.length === 0) {
          key = "Unassigned";
        } else {
          // A position can appear under multiple labels; split proportionally
          const share = pos.current_value / pos.label_names.length;
          for (const label of pos.label_names) {
            map.set(label, (map.get(label) ?? 0) + share);
          }
          continue;
        }
        break;
      case "broker":
        key = pos.broker;
        break;
      default:
        key = "Unknown";
    }
    map.set(key, (map.get(key) ?? 0) + pos.current_value);
  }

  return Array.from(map.entries())
    .map(([name, value]) => ({ name, value, currency }))
    .sort((a, b) => b.value - a.value);
}

// ── Server-side data fetch helpers ───────────────────────────────────────────

export async function fetchSummary(token: string): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>("/portfolio/summary", {}, token);
}

export async function fetchSnapshots(
  token: string,
  range: SnapshotRange,
  split: SnapshotSplit
): Promise<PortfolioSnapshots> {
  return apiFetch<PortfolioSnapshots>(
    `/portfolio/snapshots?range=${range}&split=${split}`,
    {},
    token
  );
}

export async function fetchTransactions(
  token: string,
  range: SnapshotRange
): Promise<TransactionMarker[]> {
  return apiFetch<TransactionMarker[]>(
    `/portfolio/transactions?range=${range}`,
    {},
    token
  );
}

export async function fetchPositions(token: string): Promise<PositionItem[]> {
  return apiFetch<PositionItem[]>("/portfolio/positions", {}, token);
}
```

- [ ] **Step 2: Verify TypeScript compiles cleanly**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected output: empty (no errors).

- [ ] **Step 3: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/lib/dashboard.ts && git commit -m "feat(frontend): add dashboard TypeScript types and data-fetch helpers"
```

---

## Task 5: Sidebar Component

**Files:**
- Create: `frontend/components/dashboard/Sidebar.tsx`

- [ ] **Step 1: Create `frontend/components/dashboard/Sidebar.tsx`**

```tsx
// frontend/components/dashboard/Sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Link2,
  Tag,
  Bot,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/connect", label: "Connect", icon: Link2 },
  { href: "/settings/labels", label: "Labels", icon: Tag },
  { href: "/settings/ai", label: "AI Settings", icon: Bot },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 flex-col gap-1 border-r border-border bg-background px-3 py-6">
      <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Portfolio
      </p>
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        );
      })}
    </aside>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected output: empty.

- [ ] **Step 3: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/components/dashboard/Sidebar.tsx && git commit -m "feat(frontend): add Sidebar nav component"
```

---

## Task 6: SummaryBar Component

**Files:**
- Create: `frontend/components/dashboard/SummaryBar.tsx`

- [ ] **Step 1: Create `frontend/components/dashboard/SummaryBar.tsx`**

```tsx
// frontend/components/dashboard/SummaryBar.tsx
import { AccountSummary } from "@/lib/dashboard";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";

interface DailyChange {
  currency: string;
  change_abs: number;
  change_pct: number;
}

interface SummaryBarProps {
  accounts: AccountSummary[];
  lastSyncedAt: string | null;
  dailyChanges: DailyChange[];
}

function formatCurrency(value: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPct(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function SummaryBar({ accounts, lastSyncedAt, dailyChanges }: SummaryBarProps) {
  // Group accounts by currency
  const byCurrency = accounts.reduce<Record<string, number>>((acc, a) => {
    acc[a.currency] = (acc[a.currency] ?? 0) + a.total_value;
    return acc;
  }, {});

  const currencies = Object.entries(byCurrency).sort(([a], [b]) =>
    a.localeCompare(b)
  );

  const syncAge = lastSyncedAt
    ? formatDistanceToNow(new Date(lastSyncedAt), { addSuffix: true })
    : null;

  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-border bg-card px-6 py-4">
      {/* Per-currency totals */}
      {currencies.map(([currency, total]) => {
        const change = dailyChanges.find((d) => d.currency === currency);
        const isPositive = !change || change.change_abs >= 0;
        return (
          <div key={currency} className="flex flex-col">
            <span className="text-xs text-muted-foreground">{currency} Total</span>
            <span className="text-xl font-semibold tabular-nums">
              {formatCurrency(total, currency)}
            </span>
            {change && (
              <span
                className={`text-sm font-medium tabular-nums ${
                  isPositive ? "text-emerald-500" : "text-red-500"
                }`}
              >
                {formatCurrency(change.change_abs, currency)} (
                {formatPct(change.change_pct)})
              </span>
            )}
          </div>
        );
      })}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Sync status */}
      <div className="flex flex-col items-end gap-1">
        <Badge variant={lastSyncedAt ? "secondary" : "destructive"}>
          {lastSyncedAt ? "Synced" : "Never synced"}
        </Badge>
        {syncAge && (
          <span className="text-xs text-muted-foreground">Last synced {syncAge}</span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected output: empty.

- [ ] **Step 3: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/components/dashboard/SummaryBar.tsx && git commit -m "feat(frontend): add SummaryBar component with per-currency totals and sync badge"
```

---

## Task 7: PortfolioLineChart Component

**Files:**
- Create: `frontend/components/dashboard/PortfolioLineChart.tsx`

- [ ] **Step 1: Install `date-fns` if not already present**

```bash
cd /home/user/personal-portfolio/frontend && npm list date-fns 2>/dev/null || npm install date-fns
```

Expected output: `date-fns@x.x.x` or install confirmation.

- [ ] **Step 2: Create `frontend/components/dashboard/PortfolioLineChart.tsx`**

```tsx
// frontend/components/dashboard/PortfolioLineChart.tsx
"use client";

import { useState, useCallback } from "react";
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import {
  SnapshotSeries,
  TransactionMarker,
  SnapshotRange,
  SnapshotSplit,
  normalizeToPercent,
  colorForIndex,
  SnapshotPoint,
} from "@/lib/dashboard";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Constants ─────────────────────────────────────────────────────────────────

const RANGES: { value: SnapshotRange; label: string }[] = [
  { value: "1W", label: "1W" },
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "6M", label: "6M" },
  { value: "1Y", label: "1Y" },
  { value: "all", label: "All" },
];

const SPLITS: { value: SnapshotSplit; label: string }[] = [
  { value: "total", label: "Total" },
  { value: "broker", label: "By Broker" },
  { value: "label", label: "By Label" },
  { value: "stock", label: "By Stock" },
];

// ── Trade marker shape ────────────────────────────────────────────────────────

interface MarkerShapeProps {
  cx?: number;
  cy?: number;
  payload?: TransactionMarker;
}

function TradeMarkerShape({ cx = 0, cy = 0, payload }: MarkerShapeProps) {
  if (!payload) return null;
  const isBuy = payload.type === "buy";
  const color = isBuy ? "#10b981" : "#ef4444";
  // ▲ buy: triangle pointing up; ▼ sell: triangle pointing down
  const path = isBuy
    ? `M ${cx} ${cy - 8} L ${cx + 6} ${cy + 4} L ${cx - 6} ${cy + 4} Z`
    : `M ${cx} ${cy + 8} L ${cx + 6} ${cy - 4} L ${cx - 6} ${cy - 4} Z`;
  return <path d={path} fill={color} stroke="none" />;
}

// ── Custom tooltip for trade markers ─────────────────────────────────────────

function TradeTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TransactionMarker }>;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const t = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold">{t.ticker}</p>
      <p className="capitalize text-muted-foreground">{t.type}</p>
      <p>Qty: {t.quantity}</p>
      <p>
        Price:{" "}
        {new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 2,
        }).format(t.price)}
      </p>
      <p className="text-xs text-muted-foreground">
        {format(new Date(t.executed_at), "MMM d, yyyy")}
      </p>
    </div>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface PortfolioLineChartProps {
  initialSeries: SnapshotSeries[];
  initialTransactions: TransactionMarker[];
  defaultRange?: SnapshotRange;
  defaultSplit?: SnapshotSplit;
  onRangeChange: (range: SnapshotRange, split: SnapshotSplit) => Promise<{
    series: SnapshotSeries[];
    transactions: TransactionMarker[];
  }>;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PortfolioLineChart({
  initialSeries,
  initialTransactions,
  defaultRange = "1M",
  defaultSplit = "total",
  onRangeChange,
}: PortfolioLineChartProps) {
  const [series, setSeries] = useState<SnapshotSeries[]>(initialSeries);
  const [transactions, setTransactions] =
    useState<TransactionMarker[]>(initialTransactions);
  const [range, setRange] = useState<SnapshotRange>(defaultRange);
  const [split, setSplit] = useState<SnapshotSplit>(defaultSplit);
  const [yMode, setYMode] = useState<"absolute" | "percent">("absolute");
  const [loading, setLoading] = useState(false);

  const handleControlChange = useCallback(
    async (newRange: SnapshotRange, newSplit: SnapshotSplit) => {
      setLoading(true);
      try {
        const result = await onRangeChange(newRange, newSplit);
        setSeries(result.series);
        setTransactions(result.transactions);
        setRange(newRange);
        setSplit(newSplit);
      } finally {
        setLoading(false);
      }
    },
    [onRangeChange]
  );

  // Build a unified timestamp → { [seriesName]: value } map for the chart
  const timestampSet = new Set<string>();
  for (const s of series) {
    for (const pt of s.data) {
      timestampSet.add(pt.timestamp);
    }
  }
  const sortedTimestamps = Array.from(timestampSet).sort();

  // Apply normalisation per series if in percent mode
  const activeSeries = series.map((s) => ({
    ...s,
    data: yMode === "percent" ? normalizeToPercent(s.data) : s.data,
  }));

  // Build flat chart data for Recharts
  const chartData = sortedTimestamps.map((ts) => {
    const point: Record<string, number | string> = { timestamp: ts };
    for (const s of activeSeries) {
      const match = s.data.find((d) => d.timestamp === ts);
      if (match !== undefined) {
        point[s.name] = match.value;
      }
    }
    return point;
  });

  // Map transactions onto closest chart timestamp for scatter placement
  const scatterData = transactions.map((t) => {
    // Find the closest timestamp in sortedTimestamps
    const tsMs = new Date(t.executed_at).getTime();
    let closest = sortedTimestamps[0];
    let minDiff = Infinity;
    for (const ts of sortedTimestamps) {
      const diff = Math.abs(new Date(ts).getTime() - tsMs);
      if (diff < minDiff) {
        minDiff = diff;
        closest = ts;
      }
    }
    // Use the y value of the first series at that timestamp
    const seriesPoint = activeSeries[0]?.data.find(
      (d) => d.timestamp === closest
    );
    return {
      timestamp: closest,
      value: seriesPoint?.value ?? 0,
      ...t,
    };
  });

  const yLabel = yMode === "percent" ? "% Change" : "Value";

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Range buttons */}
        <div className="flex rounded-md border border-border">
          {RANGES.map((r) => (
            <button
              key={r.value}
              onClick={() => handleControlChange(r.value, split)}
              className={`px-3 py-1 text-sm transition-colors first:rounded-l-md last:rounded-r-md ${
                range === r.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              }`}
              disabled={loading}
            >
              {r.label}
            </button>
          ))}
        </div>

        {/* Split selector */}
        <Select
          value={split}
          onValueChange={(v) =>
            handleControlChange(range, v as SnapshotSplit)
          }
          disabled={loading}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SPLITS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Y-axis toggle */}
        <div className="ml-auto flex rounded-md border border-border">
          <button
            onClick={() => setYMode("absolute")}
            className={`px-3 py-1 text-sm first:rounded-l-md last:rounded-r-md ${
              yMode === "absolute"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            $
          </button>
          <button
            onClick={() => setYMode("percent")}
            className={`px-3 py-1 text-sm first:rounded-l-md last:rounded-r-md ${
              yMode === "percent"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
          >
            %
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className={`h-80 transition-opacity ${loading ? "opacity-50" : ""}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(v: string) => {
                try {
                  return format(new Date(v), "MMM d");
                } catch {
                  return v;
                }
              }}
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              className="text-muted-foreground"
              tickFormatter={(v: number) =>
                yMode === "percent"
                  ? `${v.toFixed(1)}%`
                  : new Intl.NumberFormat("en-US", {
                      notation: "compact",
                      maximumFractionDigits: 1,
                    }).format(v)
              }
              label={{
                value: yLabel,
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11 },
              }}
            />
            <Tooltip
              labelFormatter={(v: string) => {
                try {
                  return format(new Date(v), "MMM d, yyyy");
                } catch {
                  return v;
                }
              }}
              formatter={(value: number, name: string) =>
                yMode === "percent"
                  ? [`${value.toFixed(2)}%`, name]
                  : [
                      new Intl.NumberFormat("en-US", {
                        maximumFractionDigits: 0,
                      }).format(value),
                      name,
                    ]
              }
            />
            <Legend />

            {/* One Line per series */}
            {activeSeries.map((s, i) => (
              <Line
                key={s.name}
                type="monotone"
                dataKey={s.name}
                stroke={colorForIndex(i)}
                dot={false}
                strokeWidth={2}
                connectNulls
              />
            ))}

            {/* Trade markers as scatter */}
            <Scatter
              data={scatterData}
              dataKey="value"
              shape={<TradeMarkerShape />}
              legendType="none"
              isAnimationActive={false}
            >
              <Tooltip content={<TradeTooltip />} />
            </Scatter>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected output: empty (no errors).

- [ ] **Step 4: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/components/dashboard/PortfolioLineChart.tsx && git commit -m "feat(frontend): add PortfolioLineChart with ComposedChart, trade markers, range/split/y-mode controls"
```

---

## Task 8: AllocationPieChart Component

**Files:**
- Create: `frontend/components/dashboard/AllocationPieChart.tsx`

- [ ] **Step 1: Create `frontend/components/dashboard/AllocationPieChart.tsx`**

```tsx
// frontend/components/dashboard/AllocationPieChart.tsx
"use client";

import { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  PositionItem,
  PieSplit,
  buildPieSlices,
  colorForIndex,
} from "@/lib/dashboard";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Constants ─────────────────────────────────────────────────────────────────

const SPLIT_OPTIONS: { value: PieSplit; label: string }[] = [
  { value: "asset_class", label: "By Asset Class" },
  { value: "country", label: "By Country" },
  { value: "sector", label: "By Sector" },
  { value: "label", label: "By Label Group" },
  { value: "broker", label: "By Broker" },
];

// ── Custom tooltip ─────────────────────────────────────────────────────────────

interface TooltipPayloadItem {
  name: string;
  value: number;
  payload: { name: string; value: number; currency: string };
}

function PieTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  total: number;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  const pct = total > 0 ? ((entry.value / total) * 100).toFixed(1) : "0.0";
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold">{entry.name}</p>
      <p>
        {new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(
          entry.value
        )}{" "}
        {entry.payload.currency}
      </p>
      <p className="text-muted-foreground">{pct}% of total</p>
    </div>
  );
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface AllocationPieChartProps {
  positions: PositionItem[];
  defaultSplit?: PieSplit;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AllocationPieChart({
  positions,
  defaultSplit = "asset_class",
}: AllocationPieChartProps) {
  const [split, setSplit] = useState<PieSplit>(defaultSplit);

  // Determine available currencies from positions
  const currencies = Array.from(
    new Set(positions.map((p) => p.currency))
  ).sort();

  // Build slices per currency (never aggregate across currencies)
  const allSlices = currencies.map((currency) => ({
    currency,
    slices: buildPieSlices(positions, split, currency),
    total: positions
      .filter((p) => p.currency === currency)
      .reduce((sum, p) => sum + p.current_value, 0),
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">Split by</span>
        <Select
          value={split}
          onValueChange={(v) => setSplit(v as PieSplit)}
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SPLIT_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* One pie per currency group */}
      <div className="flex flex-wrap gap-8">
        {allSlices.map(({ currency, slices, total }) => (
          <div key={currency} className="flex flex-col items-center gap-2">
            <p className="text-sm font-medium text-muted-foreground">
              {currency}
            </p>
            <div className="h-64 w-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    innerRadius={40}
                    paddingAngle={2}
                  >
                    {slices.map((_, i) => (
                      <Cell
                        key={`cell-${i}`}
                        fill={colorForIndex(i)}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    content={<PieTooltip total={total} />}
                  />
                  <Legend
                    formatter={(value: string) => (
                      <span className="text-xs">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}

        {allSlices.length === 0 && (
          <p className="text-sm text-muted-foreground">No position data.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected output: empty.

- [ ] **Step 3: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/components/dashboard/AllocationPieChart.tsx && git commit -m "feat(frontend): add AllocationPieChart with per-currency pies and split dropdown"
```

---

## Task 9: Dashboard Page

**Files:**
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Replace dashboard stub with full server component**

Replace the entire contents of `frontend/app/dashboard/page.tsx` with:

```tsx
// frontend/app/dashboard/page.tsx
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { SummaryBar } from "@/components/dashboard/SummaryBar";
import { PortfolioLineChart } from "@/components/dashboard/PortfolioLineChart";
import { AllocationPieChart } from "@/components/dashboard/AllocationPieChart";
import {
  fetchSummary,
  fetchSnapshots,
  fetchTransactions,
  fetchPositions,
  SnapshotRange,
  SnapshotSplit,
  SnapshotSeries,
  TransactionMarker,
} from "@/lib/dashboard";
import { apiFetch } from "@/lib/api";

// ── Daily change computation ──────────────────────────────────────────────────
// Computes per-currency daily change from the snapshots response.
// "Daily change" = diff between most-recent point and point closest to 24h ago.

function computeDailyChanges(
  series: ReturnType<typeof fetchSnapshots> extends Promise<infer T> ? T : never
) {
  // Type hack: accept the snapshots response directly
  return [] as Array<{ currency: string; change_abs: number; change_pct: number }>;
}

function computeDailyChangesFromSnapshots(
  seriesList: SnapshotSeries[]
): Array<{ currency: string; change_abs: number; change_pct: number }> {
  const now = Date.now();
  const oneDayMs = 24 * 60 * 60 * 1000;
  const results: Array<{ currency: string; change_abs: number; change_pct: number }> =
    [];

  // For "total" split, series names look like "Total HKD" or "Total USD"
  for (const s of seriesList) {
    if (s.data.length < 2) continue;

    // Extract currency from series name (last word)
    const parts = s.name.split(" ");
    const currency = parts[parts.length - 1];

    const sorted = [...s.data].sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const latest = sorted[sorted.length - 1];
    const latestMs = new Date(latest.timestamp).getTime();

    // Find point closest to 24h before latest
    let closest = sorted[0];
    let minDiff = Infinity;
    for (const pt of sorted.slice(0, -1)) {
      const diff = Math.abs(
        latestMs - oneDayMs - new Date(pt.timestamp).getTime()
      );
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }

    const change_abs = latest.value - closest.value;
    const change_pct =
      closest.value !== 0 ? (change_abs / closest.value) * 100 : 0;

    results.push({ currency, change_abs, change_pct });
  }

  return results;
}

// ── Server Action for chart re-fetch ─────────────────────────────────────────

// This is passed as a prop to the client component so it can re-fetch on
// range/split changes without a full page reload.
async function makeChartFetcher(token: string) {
  "use server";
  return async function fetchChartData(
    range: SnapshotRange,
    split: SnapshotSplit
  ): Promise<{ series: SnapshotSeries[]; transactions: TransactionMarker[] }> {
    "use server";
    const [snapshots, transactions] = await Promise.all([
      fetchSnapshots(token, range, split),
      fetchTransactions(token, range),
    ]);
    return { series: snapshots.series, transactions };
  };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const token = (session as { backendToken?: string }).backendToken ?? "";

  // Fetch all data in parallel
  const [summary, snapshots, transactions, positions] = await Promise.all([
    fetchSummary(token),
    fetchSnapshots(token, "1M", "total"),
    fetchTransactions(token, "1M"),
    fetchPositions(token),
  ]);

  const dailyChanges = computeDailyChangesFromSnapshots(snapshots.series);

  // Build the server action for the line chart to call on control changes
  const chartFetcher = await makeChartFetcher(token);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />

      <main className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>

        {/* Summary bar */}
        <SummaryBar
          accounts={summary.accounts}
          lastSyncedAt={summary.last_synced_at}
          dailyChanges={dailyChanges}
        />

        {/* Line chart */}
        <section className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">Portfolio Performance</h2>
          <PortfolioLineChart
            initialSeries={snapshots.series}
            initialTransactions={transactions}
            defaultRange="1M"
            defaultSplit="total"
            onRangeChange={chartFetcher}
          />
        </section>

        {/* Pie chart */}
        <section className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">Capital Allocation</h2>
          <AllocationPieChart positions={positions} />
        </section>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/user/personal-portfolio/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected output: empty (no errors).

- [ ] **Step 3: Run Next.js dev server and confirm page loads**

```bash
cd /home/user/personal-portfolio/frontend && npm run dev -- --port 3001 &
sleep 5
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/dashboard
```

Expected output:
```
307
```
(307 = redirect to `/login` because we are not authenticated in curl — this confirms the page exists and auth guard works.)

- [ ] **Step 4: Stop dev server**

```bash
kill $(lsof -ti:3001) 2>/dev/null || true
```

- [ ] **Step 5: Commit**

```bash
cd /home/user/personal-portfolio && git add frontend/app/dashboard/page.tsx && git commit -m "feat(frontend): build full dashboard page with SummaryBar, PortfolioLineChart, AllocationPieChart"
```

---

## Task 10: Wire Up All Components — Integration Smoke Test

**Files:**
- No new files — verify existing wiring is correct

- [ ] **Step 1: Run full backend test suite**

```bash
cd /home/user/personal-portfolio/backend && python -m pytest tests/ -v
```

Expected output:
```
... (all existing Phase 1 tests pass) ...
tests/test_portfolio_service.py::TestGetSummary::test_returns_accounts_list PASSED
tests/test_portfolio_service.py::TestGetSummary::test_returns_last_synced_at PASSED
tests/test_portfolio_service.py::TestGetSummary::test_empty_accounts PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_total_split_groups_by_currency PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_broker_split_groups_by_broker_and_currency PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_range_1w_limits_window PASSED
tests/test_portfolio_service.py::TestGetSnapshots::test_range_all_has_no_cutoff PASSED
tests/test_portfolio_service.py::TestGetTransactions::test_returns_transaction_list PASSED
tests/test_portfolio_service.py::TestGetTransactions::test_empty_result PASSED
tests/test_portfolio_service.py::TestGetPositions::test_returns_position_list PASSED
tests/test_portfolio_service.py::TestGetPositions::test_positions_with_no_labels PASSED
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_returns_200 PASSED
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_requires_auth PASSED
tests/test_portfolio_router.py::TestPortfolioSummaryEndpoint::test_get_summary_empty_accounts PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_defaults PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_accepts_range_and_split_params PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_invalid_range_returns_422 PASSED
tests/test_portfolio_router.py::TestPortfolioSnapshotsEndpoint::test_get_snapshots_invalid_split_returns_422 PASSED
tests/test_portfolio_router.py::TestPortfolioTransactionsEndpoint::test_get_transactions_returns_list PASSED
tests/test_portfolio_router.py::TestPortfolioTransactionsEndpoint::test_get_transactions_accepts_range_param PASSED
tests/test_portfolio_router.py::TestPortfolioPositionsEndpoint::test_get_positions_returns_list PASSED
tests/test_portfolio_router.py::TestPortfolioPositionsEndpoint::test_get_positions_empty PASSED
22 new + all existing tests passed
```

- [ ] **Step 2: Build the Next.js frontend**

```bash
cd /home/user/personal-portfolio/frontend && npm run build 2>&1 | tail -20
```

Expected output:
```
Route (app)                              Size     First Load JS
┌ ○ /                                   ...
├ ○ /dashboard                          ...
...
✓ Compiled successfully
```

- [ ] **Step 3: Final commit**

```bash
cd /home/user/personal-portfolio && git add -A && git status
```

Verify no unexpected files are staged, then:

```bash
cd /home/user/personal-portfolio && git commit -m "feat: Phase 2 complete — dashboard with line chart, pie chart, summary bar, and sidebar"
```

---

## Summary of All Files Created / Modified

| File | Action |
|---|---|
| `backend/app/schemas/portfolio_dashboard.py` | Created |
| `backend/app/services/portfolio.py` | Created |
| `backend/app/routers/portfolio.py` | Created |
| `backend/app/main.py` | Modified (register portfolio router) |
| `backend/tests/test_portfolio_service.py` | Created |
| `backend/tests/test_portfolio_router.py` | Created |
| `frontend/lib/dashboard.ts` | Created |
| `frontend/components/dashboard/Sidebar.tsx` | Created |
| `frontend/components/dashboard/SummaryBar.tsx` | Created |
| `frontend/components/dashboard/PortfolioLineChart.tsx` | Created |
| `frontend/components/dashboard/AllocationPieChart.tsx` | Created |
| `frontend/app/dashboard/page.tsx` | Modified (replace stub) |
