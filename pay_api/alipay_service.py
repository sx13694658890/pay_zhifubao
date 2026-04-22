from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import Any

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
from alipay.aop.api.domain.AlipayTradeQueryModel import AlipayTradeQueryModel
from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest
from alipay.aop.api.request.AlipayTradeQueryRequest import AlipayTradeQueryRequest
from alipay.aop.api.response.AlipayTradeQueryResponse import AlipayTradeQueryResponse

from pay_api.key_util import (
    normalize_for_alipay_sdk_private_key,
    normalize_for_alipay_sdk_public_key,
)
from pay_api.settings import Settings, get_settings

logger = logging.getLogger("alipay")


def _is_usable_http_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        return False
    if "你的域名" in u or "example.com" in u.lower():
        return False
    return True


def _effective_return_url(s: Settings) -> str | None:
    """同步跳转地址：优先 ALIPAY_RETURN_URL；未配时用 CORS 第一个源 + /pay/return（本地联调）。"""
    configured = s.alipay_return_url
    if configured and _is_usable_http_url(configured):
        return configured.strip()
    origins = s.cors_origins_list()
    if not origins:
        return None
    candidate = f"{origins[0].rstrip('/')}/pay/return"
    if _is_usable_http_url(candidate):
        return candidate
    return None


def _effective_notify_url(s: Settings) -> str | None:
    """异步通知地址：优先 ALIPAY_NOTIFY_URL；否则 PUBLIC_API_BASE_URL + /api/pay/alipay/notify。"""
    configured = s.alipay_notify_url
    if configured and _is_usable_http_url(configured):
        return configured.strip()
    base = s.public_api_base_url
    if base and _is_usable_http_url(base):
        return f"{base.rstrip('/')}/api/pay/alipay/notify"
    return None


@lru_cache(maxsize=1)
def get_alipay_client() -> DefaultAlipayClient:
    s = get_settings()
    cfg = AlipayClientConfig()
    cfg.server_url = s.effective_server_url()
    cfg.app_id = s.alipay_app_id
    cfg.app_private_key = normalize_for_alipay_sdk_private_key(s.resolved_app_private_key())
    cfg.alipay_public_key = normalize_for_alipay_sdk_public_key(s.alipay_public_key.strip())
    return DefaultAlipayClient(cfg, logger)


def build_page_pay_get_url(
    *,
    subject: str,
    total_amount: str,
    out_trade_no: str,
    settings: Settings | None = None,
) -> str:
    """电脑网站支付：返回带签名的 GET 跳转 URL（前端 `window.location` 使用）。"""
    s = settings or get_settings()
    model = AlipayTradePagePayModel()
    model.out_trade_no = out_trade_no
    model.total_amount = total_amount
    model.subject = subject
    model.product_code = "FAST_INSTANT_TRADE_PAY"

    request = AlipayTradePagePayRequest(biz_model=model)
    ret = _effective_return_url(s)
    if ret:
        request.return_url = ret
        if not _is_usable_http_url(s.alipay_return_url):
            logger.info("未配置 ALIPAY_RETURN_URL，已使用 CORS 源推导 return_url: %s", ret)
    else:
        logger.warning(
            "未设置可用的同步跳转 return_url（请配置 ALIPAY_RETURN_URL，"
            "或设置 CORS_ORIGINS 为可访问的前端地址）；"
            "支付完成后浏览器可能停留在支付宝结果页，无法回到商户站点。"
        )
    nurl = _effective_notify_url(s)
    if nurl:
        request.notify_url = nurl
        if not (s.alipay_notify_url and _is_usable_http_url(s.alipay_notify_url)):
            logger.info("未配置 ALIPAY_NOTIFY_URL，已使用 PUBLIC_API_BASE_URL 推导 notify_url: %s", nurl)
    else:
        logger.warning(
            "未设置可用的异步通知 notify_url（请配置 ALIPAY_NOTIFY_URL，"
            "或配置公网可访问的 PUBLIC_API_BASE_URL 以自动拼接 /api/pay/alipay/notify）；"
            "支付成功后订单不会自动变为已支付。"
        )

    client = get_alipay_client()
    return client.page_execute(request, http_method="GET")


def new_out_trade_no(prefix: str = "P") -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def map_alipay_trade_status_to_internal(trade_status: str | None) -> str:
    if not trade_status:
        return "UNKNOWN"
    return {
        "TRADE_SUCCESS": "PAID",
        "TRADE_FINISHED": "PAID",
        "WAIT_BUYER_PAY": "PENDING",
        "TRADE_CLOSED": "CLOSED",
    }.get(trade_status, trade_status)


def query_trade_by_out_trade_no(out_trade_no: str) -> dict[str, Any]:
    """调用 alipay.trade.query。"""
    model = AlipayTradeQueryModel()
    model.out_trade_no = out_trade_no
    request = AlipayTradeQueryRequest(biz_model=model)
    client = get_alipay_client()
    try:
        raw = client.execute(request)
    except Exception as e:
        logger.exception("alipay.trade.query 调用异常")
        return {"ok": False, "error": str(e)}

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    response = AlipayTradeQueryResponse()
    response.parse_response_content(raw)
    if not response.is_success():
        parts = [
            str(response.code or ""),
            str(response.msg or ""),
            str(response.sub_code or ""),
            str(response.sub_msg or ""),
        ]
        return {"ok": False, "error": ",".join(p for p in parts if p)}

    return {
        "ok": True,
        "trade_no": response.trade_no,
        "trade_status": response.trade_status,
        "total_amount": response.total_amount,
    }

