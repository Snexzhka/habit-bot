from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .crud_for_kd import (
    create_new_habit,
)
from .crud_for_kd import delete_habit as delete_habit_crud
from .crud_for_kd import (
    get_active_habits,
    get_all_habits,
    get_all_habits_without_filter,
    get_current_streak,
    set_habit_today_status,
)
from .crud_for_kd import update_habit as update_habit_crud
from .database import get_db
from .schemas import (
    HabitBase,
    HabitCreate,
    HabitResponse,
    HabitTodayStatusUpdate,
    HabitUpdate,
)

router_keyboard = APIRouter()

"http://localhost:8000"


@router_keyboard.get(
    "/api/users/{telegram_id}/habits", response_model=List[HabitResponse]
)
async def get_habits(telegram_id: int, db: AsyncSession = Depends(get_db)):
    try:
        habits = await get_all_habits(db, telegram_id)

        if habits:
            return habits

        return []
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении данных: {str(e)}"
        )


# @router_keyboard.get("/api/users/{telegram_id}/habits", response_model=List[HabitResponse])
# async def get_habits(telegram_id: int, db: AsyncSession = Depends(get_db)):
#     habit = await get_habit_by_id(db, telegram_id)
#     return habit


@router_keyboard.post("/api/users/{telegram_id}/habits", response_model=HabitCreate)
async def post_habit(
    telegram_id: int, habit: HabitBase, db: AsyncSession = Depends(get_db)
):
    try:
        new_habit = await create_new_habit(habit, telegram_id, db)
        return new_habit
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")


@router_keyboard.patch("/api/habits/{habit_id}")
async def edit_habit(
    habit_id: int, habit_data: HabitUpdate, db: AsyncSession = Depends(get_db)
):
    habit = await update_habit_crud(habit_id, habit_data, db)

    return habit


@router_keyboard.delete("/api/habits/{habit_id}")
async def delete_habit_endpoint(habit_id: int, db: AsyncSession = Depends(get_db)):
    result = await delete_habit_crud(db, habit_id)

    return result


@router_keyboard.put("/api/habits/{habit_id}/today-status")
async def update_today_status(
    habit_id: int,
    status_data: HabitTodayStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await set_habit_today_status(db, habit_id, status_data.completed)

    return result


@router_keyboard.get("/api/users/{telegram_id}/habits/stats")
async def get_habits_stats(telegram_id: int, db: AsyncSession = Depends(get_db)):
    habits = await get_all_habits_without_filter(telegram_id, db)
    result = []
    for habit in habits:
        streak = await get_current_streak(db, habit.id)
        remaining = max(0, habit.target_count - streak)
        result.append(
            {
                "id": habit.id,
                "name": habit.name,
                "target_count": habit.target_count,
                "streak": streak,
                "remaining": remaining,
                "completed": streak >= habit.target_count,
            }
        )
    return result


@router_keyboard.get(
    "/api/users/{telegram_id}/habits/active", response_model=List[HabitResponse]
)
async def get_habits_only_active(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await get_active_habits(telegram_id, db)
    if result:
        return result
    else:
        return []
