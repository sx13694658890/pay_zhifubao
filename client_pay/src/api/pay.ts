import type {
  CreatePagePayRequest,
  CreatePagePayResponse,
  TransactionItem,
  TransactionListResponse,
} from '../types/pay'

const DEFAULT_CREATE_PATH = '/api/pay/alipay/page-pay/create'

function apiBase(): string {
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
  return base
}

/**
 * 调用后端创建「电脑网站支付」会话。
 * 后端应返回 `url` 或 `form_html`（与《支付宝网页支付需求说明》一致）。
 */
export async function createAlipayPagePay(
  body: CreatePagePayRequest,
  options?: { path?: string; signal?: AbortSignal },
): Promise<CreatePagePayResponse> {
  const path = options?.path ?? DEFAULT_CREATE_PATH
  const url = `${apiBase()}${path.startsWith('/') ? path : `/${path}`}`

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
    signal: options?.signal,
  })

  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`创建支付失败：响应不是 JSON（HTTP ${res.status}）`)
  }

  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `创建支付失败（HTTP ${res.status}）`
    throw new Error(msg)
  }

  return data as CreatePagePayResponse
}

const ORDERS_LIST_PATH = '/api/pay/orders'

export async function fetchOrders(
  params: { limit?: number; offset?: number } = {},
  options?: { signal?: AbortSignal },
): Promise<TransactionListResponse> {
  const sp = new URLSearchParams()
  if (params.limit != null) sp.set('limit', String(params.limit))
  if (params.offset != null) sp.set('offset', String(params.offset))
  const q = sp.toString()
  const url = `${apiBase()}${ORDERS_LIST_PATH}${q ? `?${q}` : ''}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  })
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`获取订单列表失败：响应不是 JSON（HTTP ${res.status}）`)
  }
  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `获取订单列表失败（HTTP ${res.status}）`
    throw new Error(msg)
  }
  return data as TransactionListResponse
}

/** 与 fetchOrders 相同数据，请求 `/api/pay/transactions` */
export async function fetchTransactions(
  params: { limit?: number; offset?: number } = {},
  options?: { signal?: AbortSignal },
): Promise<TransactionListResponse> {
  const sp = new URLSearchParams()
  if (params.limit != null) sp.set('limit', String(params.limit))
  if (params.offset != null) sp.set('offset', String(params.offset))
  const q = sp.toString()
  const url = `${apiBase()}/api/pay/transactions${q ? `?${q}` : ''}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  })
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`获取交易记录失败：响应不是 JSON（HTTP ${res.status}）`)
  }
  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `获取交易记录失败（HTTP ${res.status}）`
    throw new Error(msg)
  }
  return data as TransactionListResponse
}

export async function fetchOrderDetail(
  outTradeNo: string,
  options?: { signal?: AbortSignal },
): Promise<TransactionItem> {
  const url = `${apiBase()}/api/pay/orders/${encodeURIComponent(outTradeNo)}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  })
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`获取订单详情失败：响应不是 JSON（HTTP ${res.status}）`)
  }
  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `获取订单详情失败（HTTP ${res.status}）`
    throw new Error(msg)
  }
  return data as TransactionItem
}

export async function syncOrder(
  outTradeNo: string,
  options?: { signal?: AbortSignal },
): Promise<TransactionItem> {
  const path = `/api/pay/orders/${encodeURIComponent(outTradeNo)}/sync`
  const url = `${apiBase()}${path}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  })
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`同步订单失败：响应不是 JSON（HTTP ${res.status}）`)
  }
  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `同步订单失败（HTTP ${res.status}）`
    throw new Error(msg)
  }
  return data as TransactionItem
}

/** 与 syncOrder 相同逻辑，请求 `/api/pay/transactions/.../sync` */
export async function syncTransaction(
  outTradeNo: string,
  options?: { signal?: AbortSignal },
): Promise<TransactionItem> {
  const path = `/api/pay/transactions/${encodeURIComponent(outTradeNo)}/sync`
  const url = `${apiBase()}${path}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { Accept: 'application/json' },
    signal: options?.signal,
  })
  const text = await res.text()
  let data: unknown
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`同步订单失败：响应不是 JSON（HTTP ${res.status}）`)
  }
  if (!res.ok) {
    const msg =
      typeof data === 'object' &&
      data !== null &&
      'detail' in data &&
      typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `同步订单失败（HTTP ${res.status}）`
    throw new Error(msg)
  }
  return data as TransactionItem
}
