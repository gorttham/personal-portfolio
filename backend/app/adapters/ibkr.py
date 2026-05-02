import httpx
from decimal import Decimal
from datetime import datetime, timezone
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)

ASSET_CLASS_MAP = {
    "STK": "stock",
    "ETF": "etf",
    "BOND": "bond",
    "OPT": "stock",
    "FUND": "etf",
    "CMDTY": "metal",
    "CRYPTO": "crypto",
}


class IBKRAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials
        self._base_url = credentials.get("base_url", "https://localhost:5000/v1/api")
        self._account_id = credentials["account_id"]

    async def get_accounts(self) -> list[AdapterAccount]:
        return [AdapterAccount(
            broker_account_id=self._account_id,
            account_type="IBKR",
            currency="USD",
            name=f"IBKR {self._account_id}",
        )]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(f"/portfolio/{account_id}/positions/0")
            resp.raise_for_status()
            data = resp.json()

        positions = []
        for item in data:
            asset_class_raw = item.get("assetClass", "STK")
            positions.append(AdapterPosition(
                ticker=item["ticker"],
                name=item.get("companyName", item["ticker"]),
                quantity=Decimal(str(item["position"])),
                avg_cost=Decimal(str(item["avgCost"])) if item.get("avgCost") else None,
                current_price=Decimal(str(item["mktPrice"])) if item.get("mktPrice") else None,
                current_value=Decimal(str(item["mktValue"])),
                currency=item.get("currency", "USD"),
                asset_class=ASSET_CLASS_MAP.get(asset_class_raw, "stock"),
                sector=item.get("sector"),
                country=item.get("listingExchange"),
            ))
        return positions

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get("/iserver/account/trades")
            resp.raise_for_status()
            data = resp.json()

        txns = []
        for item in data:
            executed_at = datetime.fromtimestamp(item["trade_time"] / 1000, tz=timezone.utc)
            if executed_at < since:
                continue
            qty = Decimal(str(abs(item["size"])))
            price = Decimal(str(item["price"]))
            txns.append(AdapterTransaction(
                broker_transaction_id=str(item["execution_id"]),
                ticker=item["symbol"],
                type=TransactionType.buy if item["side"] == "B" else TransactionType.sell,
                quantity=qty,
                price=price,
                total_value=qty * price,
                currency=item.get("currency", "USD"),
                executed_at=executed_at,
            ))
        return txns

    async def get_balance(self, account_id: str) -> AdapterBalance:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(f"/portfolio/{account_id}/summary")
            resp.raise_for_status()
            data = resp.json()

        net_liquidation = data.get("netliquidation", {}).get("amount", 0)
        currency = data.get("netliquidation", {}).get("currency", "USD")
        return AdapterBalance(
            account_id=account_id,
            total_value=Decimal(str(net_liquidation)),
            currency=currency,
        )
