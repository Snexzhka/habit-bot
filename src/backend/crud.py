from sqlalchemy import select

from .database import AsyncSession
from .models import User


async def authorized_user(
    db: AsyncSession, username: str, password: str, telegram_id: int | None = None
):

    user = User(
        username=username,
        hashed_password=password,
        telegram_id=telegram_id,
        is_authenticated=True,
        token=None,
    )
    db.add(user)
    await db.commit()
    await db.flush()
    print(user.token)
    return user


async def check_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    db_user = result.scalars().first()

    return db_user


async def check_for_token(db: AsyncSession, username):
    user = await db.execute(select(User).where(User.username == username))
    db_user = user.scalars().first()

    return db_user


async def create_telegram_id(db: AsyncSession, telegram_id: int, user):
    user.telegram_id = telegram_id
    await db.commit()

    return "ok"


async def get_user_by_telegram(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().one_or_none()
    return user


async def is_user_authenticated(db: AsyncSession, telegram_id: int) -> bool:
    """Проверить, авторизован ли пользователь"""
    user = await get_user_by_telegram(db, telegram_id)
    return user is not None and user.is_authenticated


async def create_or_update_user(
    db: AsyncSession,
    telegram_id: int,
    username: str,
):
    existing_user = await get_user_by_telegram(db, telegram_id)
    if existing_user:

        existing_user.telegram_id = telegram_id
        existing_user.username = username
        await db.commit()
        await db.refresh(existing_user)

        return existing_user

    new_user = User(
        telegram_id=telegram_id,
        username=username,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


async def create_token(db: AsyncSession, username, token):
    user = await db.execute(select(User).where(User.username == username))
    db_user = user.scalars().first()
    if db_user:
        db_user.token = token
        await db.commit()
        await db.refresh(db_user)

        return db_user
    return None
