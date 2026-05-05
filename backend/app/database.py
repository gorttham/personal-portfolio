from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import os


def _fix_asyncpg_url(url: str) -> str:
    """Convert sslmode to ssl for asyncpg compatibility."""
    parsed = urlparse(url)
    if "sslmode" in parsed.query:
        params = parse_qs(parsed.query)
        ssl_value = params.pop("sslmode", [None])
        if ssl_value and "ssl" not in params:
            params["ssl"] = ssl_value
        new_query = urlencode(params, doseq=True)
        parsed = parsed._replace(query=new_query)
    return urlunparse(parsed)


DATABASE_URL = _fix_asyncpg_url(
    os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/portfolio")
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
