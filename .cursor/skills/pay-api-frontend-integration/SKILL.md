---
name: pay-api-frontend-integration
description: >-
  Integrates new frontends with the pay_zhifubao FastAPI pay_api (Alipay page
  pay create, orders CRUD, trade sync, CORS, return_url vs async notify). Use
  when wiring a web/mobile/other client to this backend, implementing checkout
  or order screens, or when the user mentions /api/pay, Alipay redirect,
  notify_url, return_url, or replacing client_pay.
---

# pay_api 与新前端对接

后端代码目录：`pay_api/`。所有业务路由挂载在 **`/api`** 下（见 `pay_api/main.py` 的 `include_router(..., prefix="/api")`）。

## 必读文档（仓库内）

- 完整 HTTP 契约与字段：`docs/前端对接API.md`
- 业务与风控：`docs/支付宝网页支付需求说明.md`
- 总览与流程图：根目录 `README.md`

对接新前端时**优先打开** `docs/前端对接API.md`，避免与实现漂移。

## 基址与 CORS

| 项 | 规则 |
| --- | --- |
| API 根 | `{BACKEND_ORIGIN}/api`，例如 `http://127.0.0.1:8000/api` |
| 浏览器跨域 | 后端 `CORS_ORIGINS`（`.env`）须包含前端源，如 `http://localhost:5173` |
| 鉴权 | 当前示例**无**用户登录与 API Token；新前端直接 `fetch` 即可 |

## 端点速查（新前端最小集）

| 用途 | 方法 | 路径 |
| --- | --- | --- |
| 创建支付 | POST | `/api/pay/alipay/page-pay/create` |
| 订单分页 | GET | `/api/pay/orders?limit=&offset=` |
| 订单详情 | GET | `/api/pay/orders/{out_trade_no}` |
| 查单同步 | POST | `/api/pay/orders/{out_trade_no}/sync` |
| 存活 | GET | `/api/health` |

等价别名：`/api/pay/transactions` 与 `orders` 对称；`sync` 同理。

**禁止**：浏览器调用 `POST /api/pay/alipay/notify`（仅支付宝服务端 POST；无合法签名）。支付完成后由前端调用 **`sync`** 做体验补偿，见 `docs/前端对接API.md`「前端与 notify 的配合」。

## 创建支付后的跳转（整页）

响应为 JSON：`url` 或 `form_html` 二选一（当前多为 `url`）。

- 有 **`url`**：`window.location.assign(url)` 或等价整页跳转，**不要用** XHR/fetch 打开（会丢收银台上下文）。
- 有 **`form_html`**：将 HTML 注入隐藏容器后 **`form.submit()`**，`target` 建议 `_self`（参考 `client_pay/src/lib/alipayRedirect.ts`）。

保存响应中的 **`out_trade_no`**，供回跳页查单、订单详情使用。

## 同步回跳 `return_url`

后端在下单时写入 `return_url`（配置见 `pay_api/.env.example`：`ALIPAY_RETURN_URL` 或由 `CORS_ORIGINS` 推导 `.../pay/return`）。

新前端须提供**可被支付宝 GET 打开**的绝对 URL 对应页面；该页可从 Query 读取 **`out_trade_no`**，再调用 **`POST .../sync`** 轮询刷新状态（参考 `client_pay/src/pages/PayReturnPage.tsx`）。

## 请求与错误约定

- 创建支付：`Content-Type: application/json`，Body 字段 `subject`、`total_amount`（字符串元）、可选 `out_trade_no`。
- 失败时多为 JSON：`{ "detail": "..." }`；HTTP 状态 `409`（订单号冲突）、`502`（网关/签名）、`500`（写库失败）等见文档。

## 实现落点（改后端时）

| 主题 | 文件 |
| --- | --- |
| 路由与入参模型 | `pay_api/routes.py`、`pay_api/schemas.py` |
| 签名与 return/notify URL | `pay_api/alipay_service.py` |
| 异步通知验签与更新 | `pay_api/alipay_notify.py` |
| 订单表读写 | `pay_api/trade_repository.py` |
| 环境变量 | `pay_api/settings.py`、`pay_api/.env.example` |

## 参考实现

本仓库 **`client_pay/`** 可作为官方参考：`src/api/pay.ts`、`src/types/pay.ts`、收银台与回跳页。

更多请求/响应字段与示例见 [reference.md](reference.md)。
