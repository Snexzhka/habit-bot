import logging

from fastapi import APIRouter, Depends, HTTPException

from src.utils.jwt import create_access_token, get_password_hash

from .crud import authorized_user, check_user, create_token, get_user_by_telegram
from .database import AsyncSession, get_db
from .schemas import Token, UserCreate, UserResponse

router = APIRouter()
URL = "http://localhost:8000"

logger = logging.getLogger(__name__)


@router.get("/api/start/{telegram_id}", response_model=UserResponse)
async def start(telegram_id: int, db: AsyncSession = Depends(get_db)):
    try:
        print("TG", telegram_id)
        user = await get_user_by_telegram(db, telegram_id)
        logger.info(f"Найден пользователь: {user}")
        if user:
            print("TG user", user.telegram_id)
            user_data = user.to_dict()
            print("user_data", user_data)
            return UserResponse(**user_data)
            # return UserResponse(**user.to_dict())

        else:
            # Явно возвращаем статус, что пользователь не найден
            logger.info(f"Пользователь с telegram_id={telegram_id} не найден")
            return UserResponse(
                is_authenticated=False,
                token=None,
                username=None,
                # user_id=None,
                message="Пользователь не найден",
            )
    except Exception as e:
        await db.rollback()
        # Логируем реальную ошибку для отладки
        logger.error(f"Ошибка в start для telegram_id {telegram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
    finally:
        # Гарантированно закрываем сессию
        await db.close()


@router.post("/api/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем, существует ли пользователь
    try:
        db_user = await check_user(db, user.username)

        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        if len(user.password.encode("utf-8")) > 72:
            raise HTTPException(
                status_code=400, detail="Password cannot be longer than 72 bytes"
            )

        # Хешируем пароль
        hashed_password = get_password_hash(user.password)

        # Создаём пользователя

        await authorized_user(
            db=db,
            username=user.username,
            password=hashed_password,
            telegram_id=user.telegram_id,
        )
        await db.commit()

        # Выдаём токен
        access_token = create_access_token(data={"sub": user.username})
        await create_token(db, user.username, access_token)
        await db.commit()

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# @router.post("/login", response_model=Token)
# async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     db_user = await check_user(db, user.username)
#
#     if not db_user or not verify_password(user.password, db_user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     access_token = create_access_token(data={"sub": db_user.username})
#     return {"access_token": access_token, "token_type": "bearer"}
#
#
#
# @router.post("/link-telegram")
# async def link_telegram(telegram_id: int, token: dict = Depends(verify_token), db: AsyncSession = Depends(get_db)):
#     username = token["sub"]
#     db_user = await check_for_token(db, username)
#
#     if not db_user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     await create_telegram_id(db, telegram_id, username)
#     # db_user.telegram_id = telegram_id
#     # db.commit()
#
#     return {"status": "success", "message": "Telegram ID linked"}
#
#
# @router.get("/check-auth/{telegram_id}")
# async def check_auth(telegram_id: int, db: AsyncSession = Depends(get_db)):
#
#     user = await get_user_by_telegram(db, telegram_id)
#
#     if user:
#         return {"authenticated": True, "username": user.username}
#     else:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#
# # Защищённый эндпоинт
# @router.get("/protected")
# async def protected_route(token: dict = Depends(verify_token)):
#     return {"message": f"Hello {token['sub']}! You are authenticated."}
#
#
# @router.get("/{telegram_id}")
# async def get_user(telegram_id: int, db: AsyncSession = Depends(get_db)):
#
#     user = await get_user_by_telegram(db, telegram_id)
#
#     if user:
#         return {"authenticated": True, "username": user.username}
#     else:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#
#
# @router.get("/login")
# async def get_login(user: UserSchema, db:AsyncSession = Depends(get_db)):
#
#     user = await check_user(db, user.username)
#
#     if user:
#     return
