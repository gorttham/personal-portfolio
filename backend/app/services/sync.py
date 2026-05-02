import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tables import (
    BrokerageConnection, Account, Position, PortfolioSnapshot,
    Transaction, SyncLog, ConnectionStatus, SyncStatus, TransactionType
)
from app.adapters.base import BrokerageAdapter
from app.adapters.longbridge import LongbridgeAdapter
from app.adapters.moomoo import MoomooAdapter
from app.adapters.ibkr import IBKRAdapter
from app.services.encryption import decrypt


def build_adapter(broker: str, credentials: dict) -> BrokerageAdapter:
    if broker == "longbridge":
        return LongbridgeAdapter(credentials)
    if broker == "moomoo":
        return MoomooAdapter(credentials)
    if broker == "ibkr":
        return IBKRAdapter(credentials)
    raise ValueError(f"Unknown broker: {broker}")


async def run_sync_for_connection(connection: BrokerageConnection, session: AsyncSession) -> dict:
    try:
        raw_creds = decrypt(connection.credentials)
        credentials = json.loads(raw_creds)
        adapter = build_adapter(connection.broker, credentials)

        accounts = await adapter.get_accounts()
        since = datetime.now(timezone.utc) - timedelta(days=90)

        for acct_data in accounts:
            result = await session.execute(
                select(Account).where(
                    Account.connection_id == connection.id,
                    Account.broker_account_id == acct_data.broker_account_id,
                )
            )
            account = result.scalar_one_or_none()
            if not account:
                account = Account(
                    id=uuid.uuid4(),
                    connection_id=connection.id,
                    user_id=connection.user_id,
                    broker_account_id=acct_data.broker_account_id,
                    account_type=acct_data.account_type,
                    currency=acct_data.currency,
                    name=acct_data.name,
                )
                session.add(account)
                await session.commit()

            positions = await adapter.get_positions(acct_data.broker_account_id)
            for pos in positions:
                result = await session.execute(
                    select(Position).where(
                        Position.account_id == account.id,
                        Position.ticker == pos.ticker,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.quantity = pos.quantity
                    existing.avg_cost = pos.avg_cost
                    existing.current_price = pos.current_price
                    existing.current_value = pos.current_value
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(Position(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        user_id=connection.user_id,
                        ticker=pos.ticker,
                        name=pos.name,
                        quantity=pos.quantity,
                        avg_cost=pos.avg_cost,
                        current_price=pos.current_price,
                        current_value=pos.current_value,
                        currency=pos.currency,
                        asset_class=pos.asset_class,
                        sector=pos.sector,
                        country=pos.country,
                    ))

            balance = await adapter.get_balance(acct_data.broker_account_id)
            session.add(PortfolioSnapshot(
                id=uuid.uuid4(),
                user_id=connection.user_id,
                account_id=account.id,
                total_value=balance.total_value,
                currency=balance.currency,
            ))

            transactions = await adapter.get_transactions(acct_data.broker_account_id, since)
            for txn in transactions:
                result = await session.execute(
                    select(Transaction).where(
                        Transaction.user_id == connection.user_id,
                        Transaction.broker_transaction_id == txn.broker_transaction_id,
                    )
                )
                if result.scalar_one_or_none() is None:
                    session.add(Transaction(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        user_id=connection.user_id,
                        ticker=txn.ticker,
                        type=TransactionType(txn.type.value),
                        quantity=txn.quantity,
                        price=txn.price,
                        total_value=txn.total_value,
                        currency=txn.currency,
                        executed_at=txn.executed_at,
                        broker_transaction_id=txn.broker_transaction_id,
                    ))

        connection.last_synced_at = datetime.now(timezone.utc)
        connection.status = ConnectionStatus.active
        session.add(SyncLog(
            id=uuid.uuid4(),
            user_id=connection.user_id,
            connection_id=connection.id,
            status=SyncStatus.success,
        ))
        await session.commit()
        return {"status": "success"}

    except Exception as e:
        connection.status = ConnectionStatus.error
        session.add(SyncLog(
            id=uuid.uuid4(),
            user_id=connection.user_id,
            connection_id=connection.id,
            status=SyncStatus.error,
            error_message=str(e),
        ))
        await session.commit()
        return {"status": "error", "error": str(e)}


async def run_all_syncs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(BrokerageConnection).where(
            BrokerageConnection.status.in_([ConnectionStatus.active, ConnectionStatus.error])
        )
    )
    connections = result.scalars().all()
    return [await run_sync_for_connection(conn, session) for conn in connections]
