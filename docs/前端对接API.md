# 前端对接 API 说明

本文描述 `pay_api`（FastAPI）对外暴露的 HTTP 接口，供 `client_pay` 或其它前端联调。所有业务接口均带有前缀 **`/api`**（由应用挂载路由时统一添加）。

## 环境与跨域

| 项 | 说明 |
| --- | --- |
| 开发默认后端 | `http://127.0.0.1:8000` |
| 前端环境变量 | `VITE_API_BASE_URL`：可为空（同源或由 Vite 代理到后端），或填完整根地址（无末尾 `/`），例如 `http://127.0.0.1:8000` |
| CORS | 由后端 `CORS_ORIGINS` 配置；开发常见为 `http://localhost:5173` |

错误响应一般为 JSON，字段 `detail`（字符串）为可读说明；HTTP 4xx/5xx 与业务约定见各接口。

---

## 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 存活探测，响应示例：`{"status":"ok"}` |

---

## 创建电脑网站支付

用于拉起支付宝收银台：后端生成签名后的跳转 URL，前端再 `window.location` 或提交表单跳转。

| 方法 | 路径 |
| --- | --- |
| POST | `/api/pay/alipay/page-pay/create` |

**请求头**：`Content-Type: application/json`，`Accept: application/json`

**请求体（JSON）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| subject | string | 是 | 订单标题，1～256 字符 |
| total_amount | string | 是 | 金额（元），如 `"0.01"`，最多两位小数 |
| out_trade_no | string | 否 | 商户订单号；不传则由后端生成。仅字母、数字、`_`、`-`，长度 1～64 |

**成功响应（200）JSON**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| url | string | 与 `form_html` 二选一；带签名的 GET 跳转地址 |
| form_html | string | 与 `url` 二选一；自动提交表单的 HTML |
| out_trade_no | string | 商户订单号（便于前端落库或展示） |

当前实现主要返回 **`url`**。

**常见错误**：`409`（`out_trade_no` 重复）、`502`（支付宝网关/签名异常）、`500`（支付链接已生成但写库失败等）。

---

## 订单列表

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/pay/orders` | 推荐 |
| GET | `/api/pay/transactions` | 与上者等价，仅路径不同 |

**查询参数**

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| limit | int | 20 | 每页条数，1～100 |
| offset | int | 0 | 偏移 |

**成功响应（200）JSON**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| total | number | 总条数 |
| limit | number | 本次 limit |
| offset | number | 本次 offset |
| items | array | 订单对象列表，元素结构见下表 |

**`items[]` 单条字段**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | number | 主键 |
| out_trade_no | string | 商户订单号 |
| subject | string | 标题 |
| total_amount | string | 金额（元） |
| status | string | 本地状态，如 `PENDING`、`PAID`、`CLOSED` |
| trade_no | string \| null | 支付宝交易号 |
| trade_status | string \| null | 支付宝交易状态原文 |
| last_error | string \| null | 最近一次错误摘要 |
| created_at | string | ISO 时间 |
| updated_at | string | ISO 时间 |

---

## 订单详情

| 方法 | 路径 |
| --- | --- |
| GET | `/api/pay/orders/{out_trade_no}` |
| GET | `/api/pay/transactions/{out_trade_no}` | 与上者等价 |

路径中的 `out_trade_no` 需 URL 编码。

**成功响应（200）**：与列表中 **单条 `items[]` 元素** 结构相同。

**错误**：`404`（本地无该订单）。

---

## 同步订单状态（查单）

调用支付宝 **`alipay.trade.query`**，用结果更新本地订单展示。

| 方法 | 路径 |
| --- | --- |
| POST | `/api/pay/orders/{out_trade_no}/sync` |
| POST | `/api/pay/transactions/{out_trade_no}/sync` | 与上者等价 |

**请求头**：建议 `Accept: application/json`。

**成功响应（200）**：与订单详情结构相同。

**错误**：`404`（本地无订单）、`502`（支付宝查询失败等）。

---

## 支付宝异步通知（非前端调用）

| 方法 | 路径 |
| --- | --- |
| POST | `/api/pay/alipay/notify` |

由 **支付宝服务器** 以 `application/x-www-form-urlencoded` **POST**；用于验签后更新订单为已支付等。**浏览器前端不要请求此地址**（无合法签名、且不应把验签压力暴露给浏览器）。配置方式见 `pay_api/.env.example` 中 `ALIPAY_NOTIFY_URL`、`PUBLIC_API_BASE_URL` 说明。

### 前端与 notify 的配合（推荐做法）

异步通知可能晚于用户回到站点几秒甚至更久。为尽快展示「已支付」，在用户经 **`return_url`** 回到前端时（例如路由 **`/pay/return`**，URL 上通常带有支付宝回传的 **`out_trade_no`**）应：

1. 读取查询参数中的 **`out_trade_no`**（若无则跳过）。
2. 调用 **`POST /api/pay/orders/{out_trade_no}/sync`**（即本仓库的 `syncOrder`），必要时 **短轮询** 数次，直到 `status` 为 `PAID` / `CLOSED` 或达到次数上限。
3. 仍提示用户：最终状态以服务端 **notify** 为准；轮询查单仅为体验优化。

本仓库示例：`client_pay` 中 **`PayReturnPage`** 已按上述方式在同步返回后触发查单。

---

## 与本仓库前端的对应关系

`client_pay/src/api/pay.ts` 中封装与上表一致，例如：

- `createAlipayPagePay` → `POST /api/pay/alipay/page-pay/create`
- `fetchOrders` → `GET /api/pay/orders`
- `fetchTransactions` → `GET /api/pay/transactions`
- `fetchOrderDetail` → `GET /api/pay/orders/{out_trade_no}`
- `syncOrder` / `syncTransaction` → 对应上述 sync 路径（**用于替代浏览器直连 notify 的补偿逻辑**）

类型定义见 `client_pay/src/types/pay.ts`。

---

## 支付完成后的前端页面

- 同步回跳：由支付宝跳转至商户配置的 **`return_url`**（示例前端路由 **`/pay/return`**），见后端 `ALIPAY_RETURN_URL` 与 `CORS_ORIGINS` 说明。
- 订单列表页路径（示例）：**`/orders`**。

更完整的业务与风控说明见同目录下的《支付宝网页支付需求说明》。
