import os
import asyncpg
import pytest
import redis.asyncio as redis
from testcontainers.redis import RedisContainer
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

# отключение ryuk, т.к на windows
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as container:
        yield container


@pytest_asyncio.fixture
async def async_redis_client(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)

    url = f"redis://{host}:{port}/0"
    client = redis.Redis.from_url(url, decode_responses=True)

    await client.flushdb()

    yield client

    await client.flushdb()
    await client.aclose()


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        yield postgres


@pytest_asyncio.fixture
async def async_db_pool(postgres_container):
    database_url = postgres_container.get_connection_url().replace(
        "+asyncpg", ""
    )
    pool = await asyncpg.create_pool(database_url)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY,
                is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY,
                seller_id INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category_id INTEGER NOT NULL,
                images_qty INTEGER NOT NULL DEFAULT 0,
                is_closed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS moderation_results (
                id SERIAL PRIMARY KEY,
                item_id INTEGER NOT NULL REFERENCES ads (id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                is_violation BOOLEAN,
                probability DOUBLE PRECISION,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP WITH TIME ZONE
            );

            CREATE TABLE IF NOT EXISTS account (
                id SERIAL PRIMARY KEY,
                login TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                is_blocked BOOLEAN NOT NULL DEFAULT FALSE
            );
        """
        )

    yield pool

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE sellers CASCADE;")
        await conn.execute("TRUNCATE TABLE account CASCADE;")

    await pool.close()
