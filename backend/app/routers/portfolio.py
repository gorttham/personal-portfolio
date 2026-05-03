from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_session
from app.services.auth import get_current_user_email
from app.services.portfolio import PortfolioService
from app.services.benchmark import get_benchmark_series
from app.schemas.portfolio_dashboard import (
    PortfolioSummaryResponse,
    PortfolioSnapshotsResponse,
    TransactionMarker,
    PositionItem,
    SnapshotSeries,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

RangeParam = Literal["1W", "1M", "3M", "6M", "1Y", "all"]
SplitParam = Literal["total", "broker", "label", "stock"]


async def _get_user_id(email: str, session: AsyncSession) -> str:
    result = await session.execute(
        text("SELECT id::text FROM users WHERE email = :email"),
        {"email": email},
    )
    return result.scalar_one()


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_summary(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = await _get_user_id(email, session)
    return await PortfolioService(session).get_summary(user_id)


@router.get("/snapshots", response_model=PortfolioSnapshotsResponse)
async def get_snapshots(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
    range: RangeParam = Query(default="1M"),
    split: SplitParam = Query(default="total"),
):
    user_id = await _get_user_id(email, session)
    return await PortfolioService(session).get_snapshots(user_id, range_=range, split=split)


@router.get("/transactions", response_model=list[TransactionMarker])
async def get_transactions(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
    range: RangeParam = Query(default="1M"),
):
    user_id = await _get_user_id(email, session)
    return await PortfolioService(session).get_transactions(user_id, range_=range)


@router.get("/positions", response_model=list[PositionItem])
async def get_positions(
    email: Annotated[str, Depends(get_current_user_email)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = await _get_user_id(email, session)
    return await PortfolioService(session).get_positions(user_id)


@router.get("/benchmark", response_model=SnapshotSeries)
async def get_benchmark(
    email: Annotated[str, Depends(get_current_user_email)],
    symbol: Literal["SPX", "HSI"] = Query(...),
    range: RangeParam = Query(default="1M"),
):
    try:
        return await get_benchmark_series(symbol=symbol, range_=range)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
