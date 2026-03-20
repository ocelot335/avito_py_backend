import asyncpg
import pytest
from repositories.ad_repository import AdRepository
from repositories.seller_repository import SellerRepository
from repositories.task_repository import ModerationTaskRepository
from repositories.account_repository import AccountRepository
import hashlib

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_seller_and_ad_creation(async_db_pool):
    seller_repo = SellerRepository(async_db_pool)
    ad_repo = AdRepository(async_db_pool)

    seller = await seller_repo.create_seller(seller_id=1, is_verified=True)
    assert seller.id == 1
    assert seller.is_verified is True

    ad = await ad_repo.create_ad(
        item_id=100,
        seller_id=1,
        title="Test iPhone 67",
        description="Good condition",
        category_id=10,
        images_qty=5,
    )
    assert ad.id == 100
    assert ad.title == "Test iPhone 67"
    assert ad.is_closed is False

    features = await ad_repo.get_ad_features(item_id=100)
    assert features is not None
    assert features.is_verified_seller is True
    assert features.category_id == 10


@pytest.mark.asyncio
async def test_close_ad_logic(async_db_pool):
    seller_repo = SellerRepository(async_db_pool)
    ad_repo = AdRepository(async_db_pool)
    task_repo = ModerationTaskRepository(async_db_pool)

    await seller_repo.create_seller(seller_id=2, is_verified=False)
    await ad_repo.create_ad(
        item_id=200,
        seller_id=2,
        title="Car",
        description="Fast",
        category_id=5,
        images_qty=1,
    )

    _ = await task_repo.create_moderation_task(item_id=200)
    _ = await task_repo.create_moderation_task(item_id=200)

    task_ids = await task_repo.get_task_ids_by_item_id(200)
    assert len(task_ids) == 2

    features = await ad_repo.get_ad_features(200)
    assert features is not None

    await ad_repo.close_ad(200)
    await task_repo.delete_tasks_by_item_id(200)

    ad = await ad_repo.get_ad_by_id(200)
    assert ad.is_closed is True

    closed_features = await ad_repo.get_ad_features(200)
    assert closed_features is None

    remaining_tasks = await task_repo.get_task_ids_by_item_id(200)
    assert len(remaining_tasks) == 0


@pytest.mark.asyncio
async def test_moderation_task_status_updates(async_db_pool):
    seller_repo = SellerRepository(async_db_pool)
    ad_repo = AdRepository(async_db_pool)
    task_repo = ModerationTaskRepository(async_db_pool)

    await seller_repo.create_seller(seller_id=3)
    await ad_repo.create_ad(
        item_id=300,
        seller_id=3,
        title="Cat",
        description="Meow",
        category_id=1,
        images_qty=1,
    )

    task_id = await task_repo.create_moderation_task(item_id=300)

    task = await task_repo.get_moderation_task(task_id)
    assert task.status == "pending"

    await task_repo.update_moderation_task_success(
        task_id=task_id, is_violation=True, probability=0.99
    )

    completed_task = await task_repo.get_moderation_task(task_id)
    assert completed_task.status == "completed"
    assert completed_task.is_violation is True
    assert completed_task.probability == 0.99


@pytest.mark.asyncio
async def test_db_edge_cases_nonexistent_ids(async_db_pool):
    repo = AccountRepository(async_db_pool)

    missing_user = await repo.get_by_id(999999)
    assert missing_user is None

    await repo.delete(999999)

    await repo.block(999999)

    still_missing = await repo.get_by_id(999999)
    assert still_missing is None


@pytest.mark.asyncio
async def test_account_create_and_get(async_db_pool):
    repo = AccountRepository(async_db_pool)

    account = await repo.create(login="test_user", password="secret_password")
    assert account.id is not None
    assert account.login == "test_user"

    expected_hash = hashlib.md5("secret_password".encode()).hexdigest()
    assert account.password == expected_hash

    assert account.is_blocked is False

    fetched = await repo.get_by_id(account.id)
    assert fetched is not None
    assert fetched.id == account.id
    assert fetched.login == "test_user"


@pytest.mark.asyncio
async def test_account_unique_login_conflict(async_db_pool):
    repo = AccountRepository(async_db_pool)

    await repo.create(login="admin", password="123")

    with pytest.raises(asyncpg.exceptions.UniqueViolationError):
        await repo.create(login="admin", password="456")


@pytest.mark.asyncio
async def test_get_by_login_and_password(async_db_pool):
    repo = AccountRepository(async_db_pool)
    await repo.create(login="auth_test", password="correct_pass")

    account = await repo.get_by_login_and_password("auth_test", "correct_pass")
    assert account is not None
    assert account.login == "auth_test"

    wrong_pwd = await repo.get_by_login_and_password("auth_test", "wrong_pass")
    assert wrong_pwd is None

    wrong_login = await repo.get_by_login_and_password(
        "nobody", "correct_pass"
    )
    assert wrong_login is None


@pytest.mark.asyncio
async def test_block_and_delete_account(async_db_pool):
    repo = AccountRepository(async_db_pool)
    acc = await repo.create(login="block_me", password="123")

    assert acc.is_blocked is False

    await repo.block(acc.id)
    blocked_acc = await repo.get_by_id(acc.id)
    assert blocked_acc.is_blocked is True

    await repo.delete(acc.id)
    deleted_acc = await repo.get_by_id(acc.id)
    assert deleted_acc is None
