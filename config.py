from dotenv import load_dotenv
from pydantic import BaseModel, Field, PostgresDsn
from pydantic_settings import BaseSettings

load_dotenv()


class PostgresDB(BaseModel):
    url: PostgresDsn


class Settings(BaseSettings):
    # fasapi
    port: int = Field(default=8000, ge=1, le=65535)
    host: str = Field(default="0.0.0.0")
    prefix: str = Field(default="/api/users")
    url: str = Field(default="http://localhost:8000")
    # db: PostgresDB
    port_db: int = Field(default=5432)
    host_db: str = Field(default="localhost")
    user_db: str = Field(default="postgres")
    password: str = Field(default="postgres")
    name_db: str = Field(default="habit_base")
    # bot
    token: str = Field(default="")
    habit_completion_target: int = Field(default=21, ge=1)
    reminders_enabled: bool = Field(default=True)
    reminders_hour: int = Field(default=20, ge=0, le=23)
    reminders_minute: int = Field(default=0, ge=0, le=59)
    reminders_timezone: str = Field(default="Europe/Moscow")

    @property
    def get_url_for_db(self):
        return f"postgresql+asyncpg://{self.user_db}:{self.password}@{self.host_db}:{self.port_db}/{self.name_db}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
