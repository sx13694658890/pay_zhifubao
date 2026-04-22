from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

_OUT_TRADE_NO_PATTERN = re.compile(r"^[0-9a-zA-Z_-]{1,64}$")


class CreatePagePayBody(BaseModel):
    subject: str = Field(min_length=1, max_length=256)
    total_amount: str = Field(description="单位：元，字符串，如 0.01")
    out_trade_no: str | None = Field(default=None, max_length=64)

    @field_validator("out_trade_no")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().replace(" ", "")
        if not s:
            return None
        if not _OUT_TRADE_NO_PATTERN.fullmatch(s):
            raise ValueError(
                "商户订单号 out_trade_no 仅允许字母、数字、下划线、连字符，长度 1～64，且不能含空格"
            )
        return s

    @field_validator("total_amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        s = v.strip()
        try:
            d = Decimal(s)
        except InvalidOperation as e:
            raise ValueError("金额格式不正确") from e
        if d <= 0:
            raise ValueError("金额必须大于 0")
        q = d.quantize(Decimal("0.01"))
        if q != d:
            raise ValueError("金额最多保留两位小数")
        return format(q, "f")


class CreatePagePayResponse(BaseModel):
    url: str | None = None
    form_html: str | None = None
    out_trade_no: str | None = None


class TransactionItem(BaseModel):
    id: int
    out_trade_no: str
    subject: str
    total_amount: str
    status: str
    trade_no: str | None = None
    trade_status: str | None = None
    last_error: str | None = None
    created_at: str
    updated_at: str


class TransactionListResponse(BaseModel):
    total: int
    items: list[TransactionItem]
    limit: int
    offset: int
