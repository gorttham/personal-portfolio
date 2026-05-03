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

    async def get_summary(self, user_id: str) -> dict[str, Any]:
        accounts_sql = text("""
            SELECT
                a.id::text,
                bc.broker,
                a.currency,
                COALESCE(SUM(p.current_value), 0.0) AS total_value,
                COALESCE(a.name, bc.broker::text) AS account_name
            FROM accounts a
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            LEFT JOIN positions p ON p.account_id = a.id
            WHERE bc.user_id = :user_id
            GROUP BY a.id, bc.broker, a.currency, a.name
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

        sync_sql = text("""
            SELECT MAX(last_synced_at) AS last_synced_at
            FROM brokerage_connections
            WHERE user_id = :user_id
        """)
        sync_result = await self.session.execute(sync_sql, {"user_id": user_id})
        last_synced_at = sync_result.scalar_one_or_none()

        return {"accounts": accounts, "last_synced_at": last_synced_at}

    async def get_snapshots(self, user_id: str, range_: str, split: str) -> dict[str, Any]:
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

    async def _snapshots_total(self, user_id: str, cutoff: str | None) -> dict[str, Any]:
        where_cutoff = "AND ps.snapshot_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapshot_at,
                a.currency,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapshot_at, a.currency
            ORDER BY a.currency, ps.snapshot_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()
        return self._rows_to_series(rows, key_fn=lambda r: f"Total {r.currency}")

    async def _snapshots_broker(self, user_id: str, cutoff: str | None) -> dict[str, Any]:
        where_cutoff = "AND ps.snapshot_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapshot_at,
                a.currency,
                bc.broker,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapshot_at, a.currency, bc.broker
            ORDER BY bc.broker, a.currency, ps.snapshot_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()
        return self._rows_to_series(rows, key_fn=lambda r: f"{r.broker} ({r.currency})")

    async def _snapshots_label(self, user_id: str, cutoff: str | None) -> dict[str, Any]:
        where_cutoff = "AND ps.snapshot_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapshot_at,
                a.currency,
                COALESCE(al.name, 'Unassigned') AS label_name,
                SUM(ps.total_value) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            LEFT JOIN positions pos ON pos.account_id = a.id
            LEFT JOIN asset_label_assignments ala ON ala.ticker = pos.ticker AND ala.user_id = bc.user_id
            LEFT JOIN asset_labels al ON al.id = ala.label_id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapshot_at, a.currency, label_name
            ORDER BY label_name, a.currency, ps.snapshot_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()
        return self._rows_to_series(rows, key_fn=lambda r: f"{r.label_name} ({r.currency})")

    async def _snapshots_stock(self, user_id: str, cutoff: str | None) -> dict[str, Any]:
        where_cutoff = "AND ps.snapshot_at >= :cutoff" if cutoff else ""
        sql = text(f"""
            SELECT
                ps.snapshot_at,
                a.currency,
                pos.ticker,
                SUM(ps.total_value) * (pos.current_value / NULLIF(acct_total.total, 0)) AS total_value
            FROM portfolio_snapshots ps
            JOIN accounts a ON a.id = ps.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            JOIN positions pos ON pos.account_id = a.id
            JOIN (
                SELECT account_id, SUM(current_value) AS total
                FROM positions
                GROUP BY account_id
            ) acct_total ON acct_total.account_id = a.id
            WHERE bc.user_id = :user_id
            {where_cutoff}
            GROUP BY ps.snapshot_at, a.currency, pos.ticker, pos.current_value, acct_total.total
            ORDER BY pos.ticker, a.currency, ps.snapshot_at
        """)
        params: dict[str, Any] = {"user_id": user_id}
        if cutoff:
            params["cutoff"] = cutoff

        result = await self.session.execute(sql, params)
        rows = result.mappings().all()
        return self._rows_to_series(rows, key_fn=lambda r: f"{r.ticker} ({r.currency})")

    @staticmethod
    def _rows_to_series(rows: list, key_fn) -> dict[str, Any]:
        series_map: dict[str, list[dict]] = {}
        currencies: set[str] = set()

        for row in rows:
            key = key_fn(row)
            currencies.add(row.currency)
            if key not in series_map:
                series_map[key] = []
            series_map[key].append(
                {"timestamp": row.snapshot_at, "value": float(row.total_value)}
            )

        return {
            "series": [{"name": k, "data": v} for k, v in series_map.items()],
            "currency_groups": sorted(currencies),
        }

    async def get_transactions(self, user_id: str, range_: str) -> list[dict[str, Any]]:
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
                t.type,
                t.quantity,
                t.price,
                t.executed_at
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
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
                "type": str(row.type),
                "quantity": float(row.quantity),
                "price": float(row.price),
                "executed_at": row.executed_at,
            }
            for row in rows
        ]

    async def get_positions(self, user_id: str) -> list[dict[str, Any]]:
        sql = text("""
            SELECT
                pos.ticker,
                pos.name,
                pos.current_value,
                pos.quantity,
                pos.avg_cost,
                pos.current_price,
                a.currency,
                pos.asset_class,
                pos.sector,
                pos.country,
                bc.broker,
                COALESCE(
                    ARRAY_AGG(al.name ORDER BY al.name) FILTER (WHERE al.name IS NOT NULL),
                    ARRAY[]::text[]
                ) AS label_names
            FROM positions pos
            JOIN accounts a ON a.id = pos.account_id
            JOIN brokerage_connections bc ON bc.id = a.connection_id
            LEFT JOIN asset_label_assignments ala ON ala.ticker = pos.ticker AND ala.user_id = bc.user_id
            LEFT JOIN asset_labels al ON al.id = ala.label_id
            WHERE bc.user_id = :user_id
            GROUP BY pos.id, pos.ticker, pos.name, pos.current_value,
                     pos.quantity, pos.avg_cost, pos.current_price,
                     a.currency, pos.asset_class, pos.sector, pos.country, bc.broker
            ORDER BY pos.ticker
        """)
        result = await self.session.execute(sql, {"user_id": user_id})
        rows = result.mappings().all()

        results = []
        for row in rows:
            avg_cost = float(row.avg_cost) if row.avg_cost is not None else None
            current_price = float(row.current_price) if row.current_price is not None else None
            quantity = float(row.quantity) if row.quantity is not None else None
            if avg_cost is not None and avg_cost != 0 and current_price is not None and quantity is not None:
                unrealized_gain = (current_price - avg_cost) * quantity
                unrealized_gain_pct = round((current_price - avg_cost) / avg_cost * 100, 2)
            else:
                unrealized_gain = None
                unrealized_gain_pct = None
            results.append({
                "ticker": row.ticker,
                "name": row.name,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "current_value": float(row.current_value),
                "unrealized_gain": unrealized_gain,
                "unrealized_gain_pct": unrealized_gain_pct,
                "currency": row.currency,
                "asset_class": row.asset_class,
                "sector": row.sector,
                "country": row.country,
                "broker": str(row.broker),
                "label_names": list(row.label_names) if row.label_names else [],
            })
        return results
