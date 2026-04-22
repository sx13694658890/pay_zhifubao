from __future__ import annotations

import logging
from typing import Annotated

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from pay_api import trade_repository
from pay_api.alipay_notify import handle_alipay_async_notify
from pay_api.alipay_service import (
    build_page_pay_get_url,
    map_alipay_trade_status_to_internal,
    new_out_trade_no,
    query_trade_by_out_trade_no,
)
from pay_api.schemas import (
    CreatePagePayBody,
    CreatePagePayResponse,
    TransactionItem,
    TransactionListResponse,
)

router = APIRouter(tags=["pay"])
log = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/pay/alipay/notify")
async def alipay_async_notify(request: Request) -> PlainTextResponse:
    """
    支付宝异步通知（`notify_url`）。
    须公网 HTTPS 可达；验签通过后更新订单状态，须返回纯文本 success / fail。
    """
    form = await request.form()
    params = {str(k): str(v) for k, v in form.multi_items()}
    result = await handle_alipay_async_notify(params)
    return PlainTextResponse(result)


@router.post("/pay/alipay/page-pay/create", response_model=CreatePagePayResponse)
async def create_alipay_page_pay(body: CreatePagePayBody) -> CreatePagePayResponse:
    out_trade_no = body.out_trade_no or new_out_trade_no()
    if body.out_trade_no and await trade_repository.out_trade_no_exists(out_trade_no):
        raise HTTPException(status_code=409, detail="out_trade_no 已存在，请更换商户订单号")

    try:
        url = build_page_pay_get_url(
            subject=body.subject,
            total_amount=body.total_amount,
            out_trade_no=out_trade_no,
        )
    except Exception as e:
        log.exception("创建支付宝电脑网站支付失败")
        raise HTTPException(status_code=502, detail=str(e)) from e

    try:
        await trade_repository.insert_pending(
            out_trade_no=out_trade_no,
            subject=body.subject,
            total_amount=body.total_amount,
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="out_trade_no 已存在") from None
    except Exception as e:
        log.exception("写入交易订单失败")
        raise HTTPException(
            status_code=500,
            detail=f"支付链接已生成，但数据库写入失败: {e}。请检查 DATABASE_URL 与库权限。",
        ) from e

    return CreatePagePayResponse(url=url, out_trade_no=out_trade_no)


@router.get("/pay/transactions", response_model=TransactionListResponse)
@router.get("/pay/orders", response_model=TransactionListResponse)
async def list_transactions(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListResponse:
    rows, total = await trade_repository.list_transactions(limit=limit, offset=offset)
    items = [TransactionItem.model_validate(r) for r in rows]
    return TransactionListResponse(total=total, items=items, limit=limit, offset=offset)


@router.get("/pay/transactions/{out_trade_no}", response_model=TransactionItem)
@router.get("/pay/orders/{out_trade_no}", response_model=TransactionItem)
async def get_transaction(out_trade_no: str) -> TransactionItem:
    row = await trade_repository.get_by_out_trade_no(out_trade_no)
    if not row:
        raise HTTPException(status_code=404, detail="订单不存在")
    return TransactionItem.model_validate(row)


@router.post("/pay/transactions/{out_trade_no}/sync", response_model=TransactionItem)
@router.post("/pay/orders/{out_trade_no}/sync", response_model=TransactionItem)
async def sync_transaction(out_trade_no: str) -> TransactionItem:
    row = await trade_repository.get_by_out_trade_no(out_trade_no)
    if not row:
        raise HTTPException(status_code=404, detail="本地无该 out_trade_no 记录")

    q = query_trade_by_out_trade_no(out_trade_no)
    if not q.get("ok"):
        err = str(q.get("error") or "查询失败")
        await trade_repository.update_after_alipay_query(
            out_trade_no=out_trade_no,
            status=row["status"],
            trade_no=row.get("trade_no"),
            trade_status=row.get("trade_status"),
            last_error=err[:2000],
        )
        raise HTTPException(status_code=502, detail=err)

    internal = map_alipay_trade_status_to_internal(q.get("trade_status"))
    await trade_repository.update_after_alipay_query(
        out_trade_no=out_trade_no,
        status=internal,
        trade_no=q.get("trade_no"),
        trade_status=q.get("trade_status"),
        last_error=None,
    )
    updated = await trade_repository.get_by_out_trade_no(out_trade_no)
    assert updated is not None
    return TransactionItem.model_validate(updated)
