import hashlib
import asyncpg
from fastapi import Depends
from db.database import get_db_pool
from models.db import AccountDto
from metrics import measure_db_query


def get_password_hash(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


class AccountRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    @measure_db_query(query_type="insert")
    async def create(self, login: str, password: str) -> AccountDto:
        hashed_password = get_password_hash(password)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO account (login, password)
                VALUES ($1, $2)
                RETURNING id, login, password, is_blocked
                """,
                login,
                hashed_password,
            )
            return AccountDto(**dict(row))

    @measure_db_query(query_type="select")
    async def get_by_id(self, account_id: int) -> AccountDto | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, login, password, is_blocked FROM account WHERE id = $1",
                account_id,
            )
            return AccountDto(**dict(row)) if row else None

    @measure_db_query(query_type="delete")
    async def delete(self, account_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM account WHERE id = $1", account_id)

    @measure_db_query(query_type="update")
    async def block(self, account_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE account SET is_blocked = TRUE WHERE id = $1",
                account_id,
            )

    @measure_db_query(query_type="select")
    async def get_by_login_and_password(
        self, login: str, password: str
    ) -> AccountDto | None:
        hashed_password = get_password_hash(password)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, login, password, is_blocked FROM account WHERE login = $1 AND password = $2
                """,
                login,
                hashed_password,
            )
            return AccountDto(**dict(row)) if row else None


def get_account_repository(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> AccountRepository:
    return AccountRepository(pool)
