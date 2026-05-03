from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_authenticated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    update_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    token: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    habits: Mapped[List["Habit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "telegram_id": self.telegram_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "update_at": self.update_at.isoformat() if self.update_at else None,
            "is_authenticated": self.is_authenticated,
            "token": self.token,
        }


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=True)
    frequency: Mapped[str] = mapped_column(String(50), default="daily")
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    update_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="habits")
    progress_records: Mapped[List["ProgressRecord"]] = relationship(
        back_populates="habits", cascade="all, delete-orphan"
    )


class ProgressRecord(Base):
    __tablename__ = "progress_records"
    __table_args__ = (
        UniqueConstraint("habit_id", "completion_date", name="unique_habit_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    completion_date: Mapped[date] = mapped_column(
        Date, default=date.today
    )  # Дата выполнения
    notes: Mapped[str] = mapped_column(
        String(200), nullable=True
    )  # Заметки пользователя
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    habit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("habits.id"), nullable=False
    )
    habits: Mapped["Habit"] = relationship(back_populates="progress_records")
