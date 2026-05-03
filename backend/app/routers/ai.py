from __future__ import annotations

import json
from typing import AsyncGenerator, Literal

import anthropic
import openai
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.tables import User, UserAISettings, Position, Transaction, AssetLabel, AssetLabelAssignment
from app.services.auth import get_current_user_email
from app.services.encryption import encrypt, decrypt
from app.services.ai import build_portfolio_context, build_system_prompt

router = APIRouter()

VALID_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
    "openai": ["gpt-4o", "gpt-4o-mini"],
}


class AISettingsRequest(BaseModel):
    provider: Literal["anthropic", "openai"]
    api_key: str
    model: str

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        provider = info.data.get("provider")
        if provider and v not in VALID_MODELS.get(provider, []):
            raise ValueError(f"Model '{v}' is not valid for provider '{provider}'")
        return v


class ChatRequest(BaseModel):
    message: str


async def _get_user(email: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _get_ai_settings(user_id, session: AsyncSession) -> UserAISettings | None:
    result = await session.execute(
        select(UserAISettings).where(UserAISettings.user_id == user_id)
    )
    return result.scalars().first()


@router.get("/settings")
async def get_ai_settings(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)
    if not settings:
        return {"configured": False}
    return {"configured": True, "provider": settings.provider, "model": settings.model}


@router.post("/settings")
async def save_ai_settings(
    body: AISettingsRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)

    encrypted_key = encrypt(body.api_key)

    if settings:
        settings.provider = body.provider
        settings.api_key = encrypted_key
        settings.model = body.model
    else:
        settings = UserAISettings(
            user_id=user.id,
            provider=body.provider,
            api_key=encrypted_key,
            model=body.model,
        )
        session.add(settings)

    await session.commit()
    return {"configured": True, "provider": body.provider, "model": body.model}


@router.post("/test")
async def test_ai_connection(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)

    if not settings:
        return {"success": False, "error": "AI not configured. Please add your API key in Settings."}

    raw_key = decrypt(settings.api_key)

    try:
        if settings.provider == "anthropic":
            client = anthropic.Anthropic(api_key=raw_key)
            client.messages.create(
                model=str(settings.model),
                max_tokens=5,
                messages=[{"role": "user", "content": "Say OK"}],
            )
        else:
            client = openai.OpenAI(api_key=raw_key)
            client.chat.completions.create(
                model=str(settings.model),
                max_tokens=5,
                messages=[{"role": "user", "content": "Say OK"}],
            )
        return {"success": True}
    except (anthropic.AuthenticationError, openai.AuthenticationError) as exc:
        return {"success": False, "error": f"Invalid API key: {exc}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def _stream_anthropic(
    client: anthropic.Anthropic, model: str, system: str, message: str
) -> AsyncGenerator[str, None]:
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'token': text})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def _stream_openai(
    client: openai.OpenAI, model: str, system: str, message: str
) -> AsyncGenerator[str, None]:
    stream = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        stream=True,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield f"data: {json.dumps({'token': delta.content})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)
    if not settings:
        raise HTTPException(status_code=400, detail="AI not configured")

    pos_result = await session.execute(
        select(Position).where(Position.user_id == user.id)
    )
    positions = list(pos_result.scalars().all())

    from datetime import datetime, timedelta, timezone
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    txn_result = await session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.executed_at >= thirty_days_ago,
        )
    )
    transactions = list(txn_result.scalars().all())

    label_result = await session.execute(
        select(AssetLabel).where(AssetLabel.user_id == user.id)
    )
    raw_labels = list(label_result.scalars().all())

    class _LabelGroup:
        def __init__(self, name: str, tickers: list[str]):
            self.name = name
            self.tickers = tickers

    label_groups: list[_LabelGroup] = []
    for lbl in raw_labels:
        assign_result = await session.execute(
            select(AssetLabelAssignment).where(AssetLabelAssignment.label_id == lbl.id)
        )
        assignments = list(assign_result.scalars().all())
        label_groups.append(_LabelGroup(lbl.name, [a.ticker for a in assignments]))

    context = build_portfolio_context(
        positions=positions,
        transactions=transactions,
        labels=label_groups,
    )
    system_prompt = build_system_prompt(context)
    raw_key = decrypt(settings.api_key)

    if str(settings.provider) == "anthropic":
        client = anthropic.Anthropic(api_key=raw_key)
        generator = _stream_anthropic(client, str(settings.model), system_prompt, body.message)
    else:
        client = openai.OpenAI(api_key=raw_key)
        generator = _stream_openai(client, str(settings.model), system_prompt, body.message)

    return StreamingResponse(generator, media_type="text/event-stream")
