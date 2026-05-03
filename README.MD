# Telegram Habit Tracker Bot

Бот для формирования полезных привычек по методу «21 день подряд». Пользователь регистрируется, создаёт привычки, 
отмечает их выполнение каждый день, смотрит статистику и получает напоминания.

## 🚀 Функционал

- Регистрация и аутентификация через JWT (токен хранится в БД)
- Создание / редактирование / удаление привычек
- Ежедневная отметка выполнения (✅ / ❌)
- Отслеживание непрерывной серии (streak) для каждой привычки
- Статистика прогресса (сколько дней осталось до цели)
- Автоматические напоминания (ежедневно в заданное время)
- Команда `/cancel` для отмены ошибочной регистрации
- Гибкие настройки через переменные окружения

## 🛠 Технологии

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic
- **Database**: PostgreSQL
- **Bot**: python-telegram-bot (pyTelegramBotAPI)
- **Auth**: JWT (python-jose)
- **Containerization**: Docker, Docker Compose
- **Additional**: asyncio, httpx, pytz, apscheduler

## 📦 Установка и запуск

### 1. Клонировать репозиторий
```bash
git clone https://https://github.com/Snexzhka/habit-bot.git
cd habit-bot


### 2. Переменные окружения

#### Создать файл .env в корне проекта (см. .env.example):

POSTGRES_USER=...        # пользователь БД
POSTGRES_PASSWORD=...    # пароль БД
POSTGRES_DB=...          # имя БД
SECRET_KEY=...           # секретный ключ для JWT
ALGORITHM=HS256
BOT_TOKEN=...            # токен телеграм-бота

### 3. Запуск через Docker Compose (рекомендуется)

docker compose up -d --build

После запуска:

    - API доступно по адресу http://localhost:8000/docs

    - Бот запускается автоматически (polling)

### 4. Локальный запуск (без Docker)

 - python -m venv .venv
 - source .venv/bin/activate   # Windows: .venv\Scripts\activate
 - pip install -r requirements.txt
 - alembic upgrade head        # применить миграции
 - python src/main.py          # запуск API и бота (или отдельно)

## Миграции базы данных
После изменения моделей SQLAlchemy:

alembic revision --autogenerate -m "description"
alembic upgrade head

##  Команды бота

🤖 Команды бота

    /start — приветствие и проверка авторизации

    /register — начало регистрации (запрос имени пользователя)

    /cancel — отмена ошибочной регистрации

    Кнопки главного меню:
    
        Создать - сощдание новой привычки
        
        Редактировать - изменение существующей привычки
        
        Удалить - удаление привычки

        Просмотреть весь список — просмотр списка

        Отметить выполнение — отметить выполнение за сегодня

        Статистика — прогресс по каждой привычке

##  Структура проекта

.
├── src/
│   ├── backend/           # FastAPI app, models, routers, database
│   ├── frontend/          # Telegram bot handlers, keyboards
│   ├── utils/             # JWT, password hashing
│   └── main.py            # точка входа FastAPI + lifespan с ботом
├── alembic/               # миграции
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md


👩‍💻 Автор

Селюк Снежана
GitHub: Snexzhka
Telegram: @Snezhok1890 (вот такая я старуха!!! Ленина помню!)
