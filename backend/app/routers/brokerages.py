import json
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.tables import User, BrokerageConnection, ConnectionStatus, BrokerType
from app.schemas.portfolio import BrokerageConnectionResponse, ConnectTokenRequest
from app.services.auth import get_current_user_email
from app.services.encryption import encrypt

router = APIRouter()


async def _get_user(email: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found — call /auth/session first")
    return user


@router.get("", response_model=list[BrokerageConnectionResponse])
async def list_connections(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    result = await session.execute(
        select(BrokerageConnection).where(BrokerageConnection.user_id == user.id)
    )
    return result.scalars().all()


@router.post("/connect", response_model=BrokerageConnectionResponse)
async def connect_token_broker(
    body: ConnectTokenRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    if body.broker not in ("moomoo", "ibkr"):
        raise HTTPException(status_code=400, detail="Use /brokerages/longbridge/oauth/start for Longbridge")
    user = await _get_user(email, session)
    encrypted = encrypt(json.dumps(body.credentials))
    conn = BrokerageConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        broker=BrokerType(body.broker),
        credentials=encrypted,
        status=ConnectionStatus.active,
    )
    session.add(conn)
    await session.commit()
    return conn


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    result = await session.execute(
        select(BrokerageConnection).where(
            BrokerageConnection.id == connection_id,
            BrokerageConnection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    await session.delete(conn)
    await session.commit()


@router.get("/longbridge/oauth/start")
async def longbridge_oauth_start(email: str = Depends(get_current_user_email)):
    app_key = os.environ["LONGBRIDGE_APP_KEY"]
    redirect_uri = os.environ["LONGBRIDGE_REDIRECT_URI"]
    import urllib.parse
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": app_key,
        "redirect_uri": redirect_uri,
        "state": email,
    })
    return RedirectResponse(f"https://open.longportapp.com/oauth?{params}")


@router.get("/longbridge/oauth/callback")
async def longbridge_oauth_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
):
    import httpx
    token_resp = httpx.post(
        "https://open.longportapp.com/v1/token",
        json={
            "code": code,
            "client_id": os.environ["LONGBRIDGE_APP_KEY"],
            "client_secret": os.environ["LONGBRIDGE_APP_SECRET"],
            "redirect_uri": os.environ["LONGBRIDGE_REDIRECT_URI"],
            "grant_type": "authorization_code",
        },
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()

    result = await session.execute(select(User).where(User.email == state))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Unknown user in OAuth state")

    credentials = {
        "app_key": os.environ["LONGBRIDGE_APP_KEY"],
        "app_secret": os.environ["LONGBRIDGE_APP_SECRET"],
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
    }
    conn = BrokerageConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        broker=BrokerType.longbridge,
        credentials=encrypt(json.dumps(credentials)),
        status=ConnectionStatus.active,
    )
    session.add(conn)
    await session.commit()
    return RedirectResponse(f"{os.environ['FRONTEND_URL']}/connect?connected=longbridge")
