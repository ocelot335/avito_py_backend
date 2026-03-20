import asyncpg
from fastapi import APIRouter, Depends, status, HTTPException, Response
import logging

from fastapi import Request
from storages.account_redis_storage import (
    AccountRedisStorage,
    get_account_redis_storage,
)
from models.db import AccountDto

from models.account import (
    LoginRequestDto,
    AccountResponseDto,
    AccountCreateRequestDto,
)
from repositories.account_repository import (
    AccountRepository,
    get_account_repository,
)
from services.auth import AuthService
from config.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
auth_router = APIRouter(tags=["Auth"])


def get_auth_service() -> AuthService:
    return AuthService()


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Авторизация пользователя",
)
async def login(
    payload: LoginRequestDto,
    response: Response,
    account_repo: AccountRepository = Depends(get_account_repository),
    auth_service: AuthService = Depends(get_auth_service),
):
    account = await account_repo.get_by_login_and_password(
        login=payload.login, password=payload.password
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if account.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован",
        )

    access_token = auth_service.create_access_token(account_id=account.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        samesite="lax",
        secure=False,
    )

    logger.info(
        f"успешный вход пользователя {account.login} (ID: {account.id})"
    )

    return {"message": "Успешная авторизация, токен сохранен в cookies"}


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    account_redis: AccountRedisStorage = Depends(get_account_redis_storage),
    account_repo: AccountRepository = Depends(get_account_repository),
) -> AccountDto:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует токен авторизации",
        )

    account_id = auth_service.verify_access_token(token)
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истекший токен",
        )

    cached_account = await account_redis.get(account_id)

    if cached_account:
        account = AccountDto(**cached_account)
    else:
        account = await account_repo.get_by_id(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден",
            )
        await account_redis.set(account_id, account.model_dump())

    if account.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован",
        )

    return account


# для тестов
@auth_router.post(
    "/seed_account",
    response_model=AccountResponseDto,
    status_code=status.HTTP_201_CREATED,
    summary="сгенерировать тестовый аккаунт",
    description="Ручка для создания аккаунтов в бд(для тестов).",
)
async def seed_account(
    payload: AccountCreateRequestDto,
    account_repo: AccountRepository = Depends(get_account_repository),
):
    try:
        account = await account_repo.create(
            login=payload.login, password=payload.password
        )
        return AccountResponseDto(
            id=account.id, login=account.login, is_blocked=account.is_blocked
        )
    except asyncpg.exceptions.UniqueViolationError:
        logger.warning(
            f"попытка создать существующий аккаунт: {payload.login}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"аккаунт с логином '{payload.login}' уже существует",
        )
