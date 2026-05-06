import logging
from datetime import datetime

from asyncpg.pgproto.pgproto import timedelta
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload
from starlette import status

from config import settings

from .database import AsyncSession
from .models import Habit, ProgressRecord, User
from .schemas import HabitBase, HabitUpdate

logger = logging.getLogger(__name__)


async def get_all_habits(db: AsyncSession, telegram_id: int):

    try:
        logger.info(f"Поиск привычек {telegram_id}")
        completion_counts_subq = (
            select(
                ProgressRecord.habit_id,
                func.count(ProgressRecord.id).label("completed_count"),
            )
            .group_by(ProgressRecord.habit_id)
            .subquery()
        )
        result = await db.execute(
            select(Habit)
            .join(User)
            .outerjoin(
                completion_counts_subq, completion_counts_subq.c.habit_id == Habit.id
            )
            .where(User.telegram_id == telegram_id)
            .where(
                func.coalesce(completion_counts_subq.c.completed_count, 0)
                < settings.habit_completion_target
            )
            .options(joinedload(Habit.user).load_only(User.username))
        )

        return result.scalars().all()

    except Exception as e:
        print(f"Тип ошибки {type (e).__name__}")
        print(f"Сообщение {str(e)}")
        await db.rollback()

        raise


async def get_habit_by_name(db: AsyncSession, name: str):
    habit = await db.execute(select(Habit).where(Habit.name == name))
    result = habit.scalars().one_or_none()

    return result


async def create_new_habit(
    habit: HabitBase,
    telegram_id: int,
    db: AsyncSession,
):

    user = await db.execute(select(User.id).where(User.telegram_id == telegram_id))
    user_id = user.scalar_one_or_none()

    if user_id is None:
        raise HTTPException(status_code=400, detail="Пользователь не найден")
    existing = await db.execute(
        select(Habit).where(Habit.user_id == user_id, Habit.name == habit.name)
    )
    if existing.scalars().one_or_none():
        raise HTTPException(status_code=400, detail="Такая привычка уже есть")

    new_habit = Habit(
        name=habit.name,
        description=habit.description,
        frequency=habit.frequency,
        target_count=habit.target_count,
        user_id=user_id,
    )

    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)

    return {
        "id": new_habit.id,
        "name": new_habit.name,
        "target_count": new_habit.target_count,
        "frequency": new_habit.frequency,
        "description": new_habit.description,
    }


async def get_habit_by_id(db: AsyncSession, telegram_id: int):

    habit = await db.execute(
        select(Habit).join(User).where(User.telegram_id == telegram_id)
    )

    return habit.scalars().all()


async def get_habit_by_habit_id(db: AsyncSession, habit_id: int):
    habit = await db.execute(select(Habit).where(Habit.id == habit_id))
    return habit.scalars().one_or_none()


async def delete_habit(db: AsyncSession, habit_id: int):
    habit = await get_habit_by_habit_id(db, habit_id)
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Привычка не найдена"
        )

    await db.execute(delete(Habit).where(Habit.id == habit_id))
    await db.commit()
    return {
        "status": "success",
        "message": f"Привычка '{habit.name}' (ID: {habit_id}) успешно удалена",
        "deleted_habit_id": habit_id,
    }


async def update_habit(habit_id, update_data: HabitUpdate, db: AsyncSession):
    habit = await get_habit_by_habit_id(db, habit_id)
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Привычка не найдена"
        )

    if not hasattr(habit, update_data.field):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Поле '{update_data.field}' не существует в модели привычки",
        )

    try:
        if update_data.field == "target_count":
            value = int(update_data.value)
            if value <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Цель должна быть положительным числом",
                )
        else:
            value = str(update_data.value).strip()  # type: ignore
            if not value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Значение для поля '{update_data.field}' не может быть пустым",
                )
        setattr(habit, update_data.field, value)

        await db.commit()
        await db.refresh(habit)
        return habit
        # return {
        #     "id": habit.id,
        #     "name": habit.name,
        #     "target_count": habit.target_count,
        #     "frequency": habit.frequency,
        #     "description": habit.description
        # }

        # return  {"id": update_data.id,
        #         "name": habit.name,
        #         "description": habit.description,
        #         "frequency": habit.frequency,
        #         "target_count": habit.target_count,
        #         "is_active": habit.is_active
        #     }

    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка преобразования данных: {str(e)}",
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}",
        )


async def set_habit_today_status(db: AsyncSession, habit_id: int, completed: bool):
    habit = await get_habit_by_habit_id(db, habit_id)
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Привычка не найдена"
        )

    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    existing = await db.execute(
        select(ProgressRecord).where(
            ProgressRecord.habit_id == habit_id,
            ProgressRecord.completion_date >= day_start,
            ProgressRecord.completion_date < day_end,
        )
    )
    today_records = existing.scalars().all()

    if completed:
        if not today_records:
            db.add(ProgressRecord(habit_id=habit_id, completion_date=now))
            await db.commit()

        return {
            "message": f"привычка '{habit.name}' отмечена как выполненная за сегодня"
        }

    if today_records:
        await db.execute(
            delete(ProgressRecord)
            .where(
                ProgressRecord.habit_id == habit_id,
                ProgressRecord.completion_date >= day_start,
                ProgressRecord.completion_date < day_end,
            )
            .execution_options(synchronize_session=False)
        )
        await db.commit()

    return {"message": f"Привычка '{habit.name}' отмечена как невыполненная"}


async def get_users_pending_habits_for_today(db: AsyncSession):
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    completion_counts_subq = (
        select(
            ProgressRecord.habit_id,
            func.count(ProgressRecord.id).label("completed_count"),
        )
        .group_by(ProgressRecord.habit_id)
        .subquery()
    )

    today_done_subq = (
        select(ProgressRecord.habit_id)
        .where(
            ProgressRecord.completion_date >= day_start,
            ProgressRecord.completion_date < day_end,
        )
        .subquery()
    )

    query = (
        select(User.telegram_id, Habit.name)
        .join(Habit, Habit.user_id == User.id)
        .outerjoin(
            completion_counts_subq, completion_counts_subq.c.habit_id == Habit.id
        )
        .outerjoin(today_done_subq, today_done_subq.c.habit_id == Habit.id)
        .where(today_done_subq.c.habit_id.is_(None))
        .where(
            func.coalesce(completion_counts_subq.c.completed_count, 0)
            < settings.habit_completion_target
        )
        .order_by(User.telegram_id, Habit.id)
    )

    result = await db.execute(query)

    grouped = {}  # type: ignore
    for telegram_id, habit_name in result.all():
        grouped.setdefault(telegram_id, []).append(habit_name)

    return grouped


async def get_current_streak(db: AsyncSession, habit_id: int) -> int:
    result = await db.execute(
        select(ProgressRecord.completion_date)
        .where(ProgressRecord.habit_id == habit_id)
        .order_by(ProgressRecord.completion_date.desc())
    )
    rows = result.all()
    if not rows:
        return 0
    dates = []
    for row in rows:
        val = row[0]
        if hasattr(val, "date"):
            dates.append(val.date())
        else:
            dates.append(val)

    today = datetime.now().date()
    streak = 0
    current = today
    while current in dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


async def get_all_habits_without_filter(telegram_id: int, db: AsyncSession):
    result = await db.execute(
        select(Habit)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .options(joinedload(Habit.user).load_only(User.username))
    )
    return result.scalars().all()


async def get_active_habits(telegram_id: int, db: AsyncSession):
    habits = await get_all_habits_without_filter(telegram_id, db)

    active = []

    for habit in habits:
        streak = await get_current_streak(db, habit.id)
        if streak < habit.target_count:
            active.append(habit)

    return active
