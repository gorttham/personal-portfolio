from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)

try:
    from longbridge.openapi import TradeContext, Config
except ImportError:
    TradeContext = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]


class LongbridgeAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials

    @asynccontextmanager
    async def _get_trade_context(self):
        if Config is None:
            raise RuntimeError("longbridge package not installed")
        config = Config(
            app_key=self._creds["app_key"],
            app_secret=self._creds["app_secret"],
            access_token=self._creds["access_token"],
        )
        ctx = TradeContext(config)
        try:
            yield ctx
        finally:
            pass

    async def get_accounts(self) -> list[AdapterAccount]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.account_balance()
            return [
                AdapterAccount(
                    broker_account_id=acct.account_id,
                    account_type=acct.account_type.name,
                    currency=acct.currency,
                    name=f"Longbridge {acct.account_type.name}",
                )
                for acct in resp.list
            ]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.stock_positions()
            positions = []
            for channel in resp.channels:
                for pos in channel.positions:
                    market = getattr(pos, "market", None)
                    country = market.name if market else None
                    positions.append(AdapterPosition(
                        ticker=pos.symbol,
                        name=pos.symbol_name,
                        quantity=Decimal(str(pos.quantity)),
                        avg_cost=Decimal(str(pos.cost_price)) if pos.cost_price else None,
                        current_price=Decimal(str(pos.current_price)) if pos.current_price else None,
                        current_value=Decimal(str(pos.market_value)),
                        currency=pos.currency,
                        asset_class="stock",
                        sector=getattr(pos, "sector", None),
                        country=country,
                    ))
            return positions

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.history_executions()
            txns = []
            for order in resp.orders:
                executed_at = order.trade_done_at.replace(tzinfo=timezone.utc) if order.trade_done_at else None
                if not executed_at or executed_at < since:
                    continue
                txns.append(AdapterTransaction(
                    broker_transaction_id=order.order_id,
                    ticker=order.symbol,
                    type=TransactionType.buy if order.side.name == "Buy" else TransactionType.sell,
                    quantity=Decimal(str(order.executed_quantity)),
                    price=Decimal(str(order.executed_price)),
                    total_value=Decimal(str(order.executed_quantity)) * Decimal(str(order.executed_price)),
                    currency=order.currency,
                    executed_at=executed_at,
                ))
            return txns

    async def get_balance(self, account_id: str) -> AdapterBalance:
        async with self._get_trade_context() as ctx:
            resp = await ctx.account_balance()
            for acct in resp.list:
                if acct.account_id == account_id:
                    return AdapterBalance(
                        account_id=account_id,
                        total_value=Decimal(str(acct.total_cash)),
                        currency=acct.currency,
                    )
        raise ValueError(f"Account {account_id} not found")
