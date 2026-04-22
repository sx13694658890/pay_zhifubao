"""PostgreSQL 连接池（asyncpg），在应用 lifespan 中创建与关闭。"""

from __future__ import annotations

import asyncpg

_pool: asyncpg.Pool | None = None


async def open_pool(dsn: str, *, min_size: int = 1, max_size: int = 10) -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化，请确认 lifespan 已执行 open_pool")
    return _pool
