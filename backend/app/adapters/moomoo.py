import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)

try:
    from futu import OpenSecTradeContext, TrdEnv, RET_OK
except ImportError:
    OpenSecTradeContext = None
    TrdEnv = None
    RET_OK = "0"

ASSET_CLASS_MAP = {
    "STOCK": "stock",
    "ETF": "etf",
    "BOND": "bond",
    "WARRANT": "stock",
}


class MoomooAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials

    def _make_context(self):
        if OpenSecTradeContext is None:
            raise RuntimeError("futu-api not installed")
        return OpenSecTradeContext(
            host=self._creds.get("host", "127.0.0.1"),
            port=int(self._creds.get("port", 11111)),
        )

    async def get_accounts(self) -> list[AdapterAccount]:
        return [AdapterAccount(
            broker_account_id=str(self._creds["acc_id"]),
            account_type=self._creds.get("trade_env", "REAL"),
            currency="USD",
            name="Moomoo Account",
        )]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.position_list_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    return []
                positions = []
                for _, row in data.iterrows():
                    market = str(row.get("sec_market", ""))
                    stock_type = str(row.get("stock_type", "STOCK"))
                    positions.append(AdapterPosition(
                        ticker=row["code"],
                        name=row["stock_name"],
                        quantity=Decimal(str(row["qty"])),
                        avg_cost=Decimal(str(row["cost_price"])) if row["cost_price"] else None,
                        current_price=Decimal(str(row["current_price"])) if row["current_price"] else None,
                        current_value=Decimal(str(row["market_val"])),
                        currency=row.get("currency", "USD"),
                        asset_class=ASSET_CLASS_MAP.get(stock_type, "stock"),
                        country=market if market else None,
                    ))
                return positions
        return await asyncio.to_thread(_fetch)

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.history_order_list_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    return []
                txns = []
                for _, row in data.iterrows():
                    if row.get("order_status") != "FILLED_ALL":
                        continue
                    executed_at = datetime.fromisoformat(str(row["updated_time"])).replace(tzinfo=timezone.utc)
                    if executed_at < since:
                        continue
                    qty = Decimal(str(row["dealt_qty"]))
                    price = Decimal(str(row["dealt_avg_price"]))
                    txns.append(AdapterTransaction(
                        broker_transaction_id=str(row["order_id"]),
                        ticker=row["code"],
                        type=TransactionType.buy if row["trd_side"] == "BUY" else TransactionType.sell,
                        quantity=qty,
                        price=price,
                        total_value=qty * price,
                        currency=row.get("currency", "USD"),
                        executed_at=executed_at,
                    ))
                return txns
        return await asyncio.to_thread(_fetch)

    async def get_balance(self, account_id: str) -> AdapterBalance:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.accinfo_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    raise ValueError("Failed to fetch Moomoo balance")
                row = data.iloc[0]
                return AdapterBalance(
                    account_id=account_id,
                    total_value=Decimal(str(row["total_assets"])),
                    currency=row.get("currency", "USD"),
                )
        return await asyncio.to_thread(_fetch)
