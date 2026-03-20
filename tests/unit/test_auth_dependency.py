import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from models.db import AccountDto
from routers.auth import get_current_user

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_request():
    request = MagicMock()
    request.cookies = {}
    return request


@pytest.fixture
def mock_auth_service():
    service = MagicMock()
    service.verify_access_token.return_value = 42
    return service


@pytest.fixture
def mock_account_redis():
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set = AsyncMock()
    return redis


@pytest.fixture
def mock_account_repo():
    repo = AsyncMock()
    repo.get_by_id.return_value = AccountDto(
        id=42, login="test_user", password="hashed", is_blocked=False
    )
    return repo


async def test_get_current_user_no_cookie(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            account_redis=mock_account_redis,
            account_repo=mock_account_repo,
        )
    assert exc.value.status_code == 401
    assert "Отсутствует токен" in exc.value.detail


async def test_get_current_user_invalid_token(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    mock_request.cookies["access_token"] = "fake_token"
    mock_auth_service.verify_access_token.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            account_redis=mock_account_redis,
            account_repo=mock_account_repo,
        )
    assert exc.value.status_code == 401
    assert "Недействительный" in exc.value.detail


async def test_get_current_user_redis_hit(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    mock_request.cookies["access_token"] = "valid_token"
    mock_account_redis.get.return_value = {
        "id": 42,
        "login": "redis_user",
        "password": "123",
        "is_blocked": False,
    }

    user = await get_current_user(
        request=mock_request,
        auth_service=mock_auth_service,
        account_redis=mock_account_redis,
        account_repo=mock_account_repo,
    )

    assert user.id == 42
    assert user.login == "redis_user"
    mock_account_repo.get_by_id.assert_not_called()


async def test_get_current_user_db_hit_and_cache(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    mock_request.cookies["access_token"] = "valid_token"
    mock_account_redis.get.return_value = None

    user = await get_current_user(
        request=mock_request,
        auth_service=mock_auth_service,
        account_redis=mock_account_redis,
        account_repo=mock_account_repo,
    )

    assert user.id == 42
    assert user.login == "test_user"

    mock_account_repo.get_by_id.assert_called_once_with(42)
    mock_account_redis.set.assert_called_once()
    assert mock_account_redis.set.call_args[0][0] == 42


async def test_get_current_user_not_found_in_db(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    mock_request.cookies["access_token"] = "valid_token"
    mock_account_redis.get.return_value = None
    mock_account_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            account_redis=mock_account_redis,
            account_repo=mock_account_repo,
        )
    assert exc.value.status_code == 401
    assert "Пользователь не найден" in exc.value.detail


async def test_get_current_user_blocked(
    mock_request, mock_auth_service, mock_account_redis, mock_account_repo
):
    mock_request.cookies["access_token"] = "valid_token"
    mock_account_redis.get.return_value = None
    mock_account_repo.get_by_id.return_value = AccountDto(
        id=42, login="bad_user", password="123", is_blocked=True
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=mock_request,
            auth_service=mock_auth_service,
            account_redis=mock_account_redis,
            account_repo=mock_account_repo,
        )
    assert exc.value.status_code == 403
    assert "заблокирован" in exc.value.detail
