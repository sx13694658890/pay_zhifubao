# pay_api 对接参考摘录

详细以 **`docs/前端对接API.md`** 为准；此处仅便于 Agent 快速对齐类型与路径。

## 创建支付

**POST** `/api/pay/alipay/page-pay/create`

```json
{
  "subject": "商品标题",
  "total_amount": "0.01",
  "out_trade_no": "可选，不传则后端生成"
}
```

**200**

```json
{
  "url": "https://openapi...",
  "out_trade_no": "P..."
}
```

## 订单列表

**GET** `/api/pay/orders?limit=20&offset=0`

**200**

```json
{
  "total": 100,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "out_trade_no": "P...",
      "subject": "...",
      "total_amount": "0.01",
      "status": "PENDING",
      "trade_no": null,
      "trade_status": null,
      "last_error": null,
      "created_at": "2026-01-01T00:00:00+00:00",
      "updated_at": "2026-01-01T00:00:00+00:00"
    }
  ]
}
```

`status` 常见值：`PENDING`、`PAID`、`CLOSED`（与 `pay_api/alipay_service.py` 中映射一致）。

## 查单同步

**POST** `/api/pay/orders/{out_trade_no}/sync`

**200**：与列表中单条 `items[]` 结构相同。

## TypeScript 类型（可与新前端对齐）

与 `client_pay/src/types/pay.ts` 一致即可：

- `CreatePagePayRequest` / `CreatePagePayResponse`
- `TransactionItem` / `TransactionListResponse`
