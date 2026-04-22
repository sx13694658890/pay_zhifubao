"""支付宝交易异步通知：验签、金额与 app_id 校验、幂等更新订单。"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Literal

from alipay.aop.api.util.SignatureUtils import get_sign_content, verify_with_rsa
from rsa.pkcs1 import VerificationError

from pay_api import trade_repository
from pay_api.alipay_service import map_alipay_trade_status_to_internal
from pay_api.key_util import normalize_for_alipay_sdk_public_key
from pay_api.settings import Settings, get_settings

logger = logging.getLogger("alipay")


def _params_for_notify_signing(params: dict[str, str]) -> dict[str, str]:
    """参与签名的参数：除 sign、sign_type 外均参与（与支付宝开放平台说明一致）。"""
    out: dict[str, str] = {}
    for k, v in params.items():
        if k in ("sign", "sign_type"):
            continue
        if v is None:
            continue
        out[k] = str(v)
    return out


def verify_async_notify_signature(params: dict[str, str], *, settings: Settings | None = None) -> bool:
    """使用支付宝公钥对异步通知验签（RSA / RSA2 由签名块自动识别）。"""
    s = settings or get_settings()
    sign_b64 = (params.get("sign") or "").strip()
    if not sign_b64:
        return False
    payload = _params_for_notify_signing(params)
    if not payload:
        return False
    try:
        pk = normalize_for_alipay_sdk_public_key(s.alipay_public_key.strip())
        sign_content = get_sign_content(payload)
        message = sign_content.encode("utf-8")
        verify_with_rsa(pk, message, sign_b64)
    except VerificationError:
        return False
    except Exception:
        logger.exception("支付宝异步通知验签过程异常")
        return False
    return True


async def handle_alipay_async_notify(
    params: dict[str, str],
    *,
    settings: Settings | None = None,
) -> Literal["success", "fail"]:
    """
    处理 `alipay.trade.page.pay` 等接口的异步通知。
    验签与业务校验失败返回 `fail`（支付宝会重试）；逻辑上已处理返回 `success`。
    """
    s = settings or get_settings()
    if not verify_async_notify_signature(params, settings=s):
        logger.warning("alipay.notify 验签失败")
        return "fail"

    app_id = (params.get("app_id") or "").strip()
    if app_id != str(s.alipay_app_id).strip():
        logger.warning("alipay.notify app_id 不匹配 notify=%s config=%s", app_id, s.alipay_app_id)
        return "fail"

    out_trade_no = (params.get("out_trade_no") or "").strip()
    if not out_trade_no:
        return "fail"

    trade_no = (params.get("trade_no") or "").strip() or None
    trade_status = (params.get("trade_status") or "").strip() or None
    total_amount_raw = (params.get("total_amount") or "").strip()

    row = await trade_repository.get_by_out_trade_no(out_trade_no)
    if not row:
        logger.warning("alipay.notify 本地无订单 out_trade_no=%s", out_trade_no)
        return "fail"

    try:
        if not total_amount_raw or Decimal(total_amount_raw) != Decimal(str(row["total_amount"])):
            logger.warning(
                "alipay.notify 金额与本地不一致 out_trade_no=%s notify=%s local=%s",
                out_trade_no,
                total_amount_raw,
                row["total_amount"],
            )
            return "fail"
    except (InvalidOperation, TypeError):
        logger.warning("alipay.notify total_amount 非法 out_trade_no=%s", out_trade_no)
        return "fail"

    if not trade_status:
        return "success"

    internal = map_alipay_trade_status_to_internal(trade_status)
    current = str(row["status"])

    if internal not in ("PAID", "PENDING", "CLOSED"):
        logger.info("alipay.notify 未映射的 trade_status=%s，忽略写库", trade_status)
        return "success"

    if current == "PAID" and internal == "PENDING":
        logger.info("alipay.notify 已支付订单忽略待付状态 out_trade_no=%s", out_trade_no)
        return "success"

    new_status = internal
    await trade_repository.update_after_alipay_query(
        out_trade_no=out_trade_no,
        status=new_status,
        trade_no=trade_no,
        trade_status=trade_status,
        last_error=None,
    )
    logger.info(
        "alipay.notify 已更新订单 out_trade_no=%s status=%s trade_status=%s",
        out_trade_no,
        new_status,
        trade_status,
    )
    return "success"
