"""交易订单：PostgreSQL + asyncpg。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import asyncpg

from pay_api.db import get_pool


def _record_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    d = dict(row)
    for k in ("created_at", "updated_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


async def out_trade_no_exists(out_trade_no: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        v = await conn.fetchval(
            "SELECT 1 FROM pay_transactions WHERE out_trade_no = $1 LIMIT 1",
            out_trade_no,
        )
        return v is not None


async def insert_pending(*, out_trade_no: str, subject: str, total_amount: str) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO pay_transactions (
                out_trade_no, subject, total_amount, status,
                trade_no, trade_status, last_error
            ) VALUES ($1, $2, $3, 'PENDING', NULL, NULL, NULL)
            RETURNING id
            """,
            out_trade_no,
            subject,
            total_amount,
        )
        assert row is not None
        return int(row["id"])


async def list_transactions(*, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    pool = get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*)::bigint FROM pay_transactions")
        rows = await conn.fetch(
            """
            SELECT id, out_trade_no, subject, total_amount, status, trade_no, trade_status,
                   last_error, created_at, updated_at
            FROM pay_transactions
            ORDER BY id DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [_record_to_dict(r) for r in rows], int(total or 0)


async def get_by_out_trade_no(out_trade_no: str) -> dict[str, Any] | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, out_trade_no, subject, total_amount, status, trade_no, trade_status,
                   last_error, created_at, updated_at
            FROM pay_transactions WHERE out_trade_no = $1
            """,
            out_trade_no,
        )
        return _record_to_dict(row) if row else None


async def update_after_alipay_query(
    *,
    out_trade_no: str,
    status: str,
    trade_no: str | None,
    trade_status: str | None,
    last_error: str | None,
) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE pay_transactions
            SET status = $2,
                trade_no = COALESCE($3, trade_no),
                trade_status = $4,
                last_error = $5,
                updated_at = NOW()
            WHERE out_trade_no = $1
            RETURNING id
            """,
            out_trade_no,
            status,
            trade_no,
            trade_status,
            last_error,
        )
        return row is not None
