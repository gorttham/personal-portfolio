import pytest
from app.database import get_session, Base, AsyncSessionLocal

def test_get_session_is_async_generator():
    import inspect
    assert inspect.isasyncgenfunction(get_session)

def test_base_is_declarative():
    from sqlalchemy.orm import DeclarativeBase
    assert issubclass(Base, DeclarativeBase)
