from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
import logging
from starlette import status
from .schemas import Token, UserCreate, UserSchema, UserResponse
from .database import AsyncSession, get_db

from src.utils.jwt import get_password_hash, create_access_token, verify_password, verify_token
from .crud import (
    authorized_user,
    check_user,
    check_for_token,
    get_user_by_telegram,
    create_telegram_id,
    create_or_update_user
)

from config import settings


logger = logging.getLogger(__name__)

register_router = APIRouter()

URL = "http://localhost:8000"

@register_router.get("/api/start/{telegram_id}", response_model=UserResponse)
async def start(
        telegram_id: int,
        db: AsyncSession = Depends(get_db)
        ):
    try:
        print("TG", telegram_id)
        user = await get_user_by_telegram(db, telegram_id)
        logger.info(f"Найден пользователь: {user}")
        if user:
            print("TG user", user.telegram_id)
            user_data = user.to_dict()
            print("user_data", user_data)
            return UserResponse(**user_data)
            #return UserResponse(**user.to_dict())

        else:
            # Явно возвращаем статус, что пользователь не найден
            logger.info(f"Пользователь с telegram_id={telegram_id} не найден")
            return UserResponse(
                is_authenticated=False,
                token=None,
                username=None,
                user_id=None,
                message="Пользователь не найден"
            )
    except Exception as e:
        await db.rollback()
        # Логируем реальную ошибку для отладки
        logger.error(f"Ошибка в start для telegram_id {telegram_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )

    finally:
        # Гарантированно закрываем сессию
        await db.close()


@register_router.post("/api/registers", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь
    print(user.username)
    db_user = await check_user(db, user.username)

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    if len(user.password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be longer than 72 bytes"
        )

    # Хешируем пароль
    hashed_password = get_password_hash(user.password)

    # Создаём пользователя
    try:
        await authorized_user(
                db=db,
                username=user.username,
                password=hashed_password,
                telegram_id=user.telegram_id,

            )
        user.is_authenticated = True
        await db.commit()
        logger.info(f"{user.username}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании пользователя")

    # Выдаём токен
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@register_router.post("/api/verify-token")
async def verify_token_endpoint(token: str):
    try:
        payload = verify_token(token)  # Из utils/jwt.py
        username = payload.get("sub")
        return {"valid": True, "username": username}
    except JWTError:
        return {"valid": False, "error": "Invalid or expired token"}


@register_router.post("/link-telegram")
async def link_telegram(telegram_id: int, username: str, db: AsyncSession = Depends(get_db)):
    await create_or_update_user(db, telegram_id, username)

    return {"status": "linked"}


# SECRET_KEY = "your-secret-ke
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# @register_router.post("/token")
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     # Здесь должна быть логика проверки пользователя в БД
#     user = authenticate_user(fake_users_db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=401,
#             detail="Неверное имя пользователя или пароль",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user.username}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}
@register_router.post("/login", response_model=Token)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await check_user(db, user.username)

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}



@register_router.post("/link-telegram")
async def link_telegram(telegram_id: int, token: dict = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    username = token["sub"]
    db_user = await check_for_token(db, username)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await create_telegram_id(db, telegram_id, username)
    # db_user.telegram_id = telegram_id
    # db.commit()

    return {"status": "success", "message": "Telegram ID linked"}


@register_router.get("/check-auth/{telegram_id}")
async def check_auth(telegram_id: int, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_telegram(db, telegram_id)

    if user:
        return {"authenticated": True, "username": user.username}
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

# Защищённый эндпоинт
@register_router.get("/protected")
async def protected_route(token: dict = Depends(verify_token)):
    return {"message": f"Hello {token['sub']}! You are authenticated."}


@register_router.get("/{telegram_id}")
async def get_user(telegram_id: int, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_telegram(db, telegram_id)

    if user:
        return {"authenticated": True, "username": user.username}
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")


@register_router.get("/login")
async def get_login(user: UserSchema, db:AsyncSession = Depends(get_db)):

    user = await check_user(db, user.username)

    if user:
        return