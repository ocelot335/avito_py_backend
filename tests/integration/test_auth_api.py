import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from repositories.account_repository import AccountRepository
from db.database import get_db_pool

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def async_api_client(async_db_pool):
    def override_get_db_pool():
        return async_db_pool

    app.dependency_overrides[get_db_pool] = override_get_db_pool

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_login_success_sets_cookie(async_db_pool, async_api_client):
    repo = AccountRepository(async_db_pool)
    await repo.create(login="good_user", password="good_password")

    response = await async_api_client.post(
        "/auth/login", json={"login": "good_user", "password": "good_password"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Успешная авторизация, токен сохранен в cookies"
    }
    assert "access_token" in response.cookies
    token = response.cookies.get("access_token")
    assert len(token) > 0


@pytest.mark.asyncio
async def test_login_wrong_password(async_db_pool, async_api_client):
    repo = AccountRepository(async_db_pool)
    await repo.create(login="hacker_target", password="real_password")

    response = await async_api_client.post(
        "/auth/login",
        json={"login": "hacker_target", "password": "wrong_password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"
    assert "access_token" not in response.cookies


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_api_client):
    response = await async_api_client.post(
        "/auth/login", json={"login": "ghost", "password": "123"}
    )
    assert response.status_code == 401
    assert "access_token" not in response.cookies


@pytest.mark.asyncio
async def test_login_blocked_user(async_db_pool, async_api_client):
    repo = AccountRepository(async_db_pool)
    acc = await repo.create(login="bads", password="123")
    await repo.block(acc.id)

    response = await async_api_client.post(
        "/auth/login", json={"login": "bads", "password": "123"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Ваш аккаунт заблокирован"
    assert "access_token" not in response.cookies


@pytest.mark.asyncio
async def test_seed_account_api(async_api_client):
    response = await async_api_client.post(
        "/auth/seed_account",
        json={"login": "new_api_user", "password": "1234"},
    )
    assert response.status_code == 201
    assert response.json()["login"] == "new_api_user"
    assert response.json()["is_blocked"] is False

    response_conflict = await async_api_client.post(
        "/auth/seed_account",
        json={"login": "new_api_user", "password": "4567"},
    )
    assert response_conflict.status_code == 409
