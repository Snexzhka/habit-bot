from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

DATABASE_URL = settings.get_url_for_db

engine = create_async_engine(
    DATABASE_URL, pool_pre_ping=True, echo=True, echo_pool=True
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:

            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class Base(DeclarativeBase):
    pass


async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
