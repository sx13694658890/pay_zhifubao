/** 创建电脑网站支付：与后端约定的请求体（字段名可与 FastAPI 模型对齐） */
export interface CreatePagePayRequest {
  subject: string
  /** 单位：元，字符串，如 "0.01" */
  total_amount: string
  /** 可选；不传则由后端生成 */
  out_trade_no?: string
}

/** 创建支付响应：后端返回「跳转 URL」或「自动提交表单 HTML」二选一 */
export interface CreatePagePayResponse {
  url?: string
  form_html?: string
  out_trade_no?: string
}

/** 交易订单（GET /api/pay/transactions） */
export interface TransactionItem {
  id: number
  out_trade_no: string
  subject: string
  total_amount: string
  status: string
  trade_no: string | null
  trade_status: string | null
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface TransactionListResponse {
  total: number
  items: TransactionItem[]
  limit: number
  offset: number
}
