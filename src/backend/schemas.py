from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    telegram_id: int | None = None

    class Config:
        model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str

    class Config:
        model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    username: str
    token: str

    class Config:
        model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    username: str

    class Config:
        model_config = ConfigDict(from_attributes=True)


class UserAll(BaseModel):

    id: int
    token: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)


class HabitBase(BaseModel):
    name: str
    description: Optional[str] = None
    frequency: str = "daily"
    target_count: int = 1

    class Config:
        model_config = ConfigDict(from_attributes=True)


class HabitResponse(HabitBase):
    user: User
    id: int

    class Config:
        model_config = ConfigDict(from_attributes=True)


class HabitCreate(HabitBase):
    id: int
    is_active: bool = True

    class Config:
        model_config = ConfigDict(from_attributes=True)


class HabitUpdate(BaseModel):
    field: str  # поле для обновления: name, description, frequency, target_count
    value: str | int  # значение для обновления

    class Config:
        model_config = ConfigDict(from_attributes=True)


class Habit(HabitBase):
    id: int
    user_id: int
    is_active: bool = True
    # created_at: datetime
    # updated_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)


class HabitTodayStatusUpdate(BaseModel):
    completed: bool

    class Config:
        model_config = ConfigDict(from_attributes=True)


class ProgressRecordBase(BaseModel):
    completed: bool = False
    completiondate: datetime
    notes: Optional[str] = None


class ProgressRecordCreate(ProgressRecordBase):
    habit_id: int


class ProgressRecord(ProgressRecordBase):
    id: int
    habit_id: int
    created_at: datetime

    class Config:
        model_config = ConfigDict(from_attributes=True)


class UserResponse1(BaseModel):
    id: int
    username: str
    telegram_id: int
    created_at: Optional[datetime] = None
    update_at: Optional[datetime] = None
    is_authenticated: bool
    token: Optional[str] = None

    class Config:
        model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    created_at: Optional[datetime] = None
    update_at: Optional[datetime] = None
    is_authenticated: bool = False
    token: Optional[str] = None
    message: Optional[str] = None

    class Config:
        model_config = ConfigDict(from_attributes=True)
