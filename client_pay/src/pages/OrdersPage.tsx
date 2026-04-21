import { App, Button, Card, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchOrders, syncOrder } from '../api/pay'
import type { TransactionItem } from '../types/pay'

const PAGE_SIZE = 10

function statusTag(status: string) {
  const color =
    status === 'PAID'
      ? 'success'
      : status === 'PENDING'
        ? 'processing'
        : status === 'CLOSED'
          ? 'default'
          : 'warning'
  return <Tag color={color}>{status}</Tag>
}

export function OrdersPage() {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [items, setItems] = useState<TransactionItem[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const offset = (page - 1) * PAGE_SIZE
      const res = await fetchOrders({ limit: PAGE_SIZE, offset })
      setItems(res.items)
      setTotal(res.total)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [message, page])

  useEffect(() => {
    void load()
  }, [load])

  const onSync = async (outTradeNo: string) => {
    setSyncing(outTradeNo)
    try {
      await syncOrder(outTradeNo)
      message.success('已从支付宝同步状态')
      await load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '同步失败')
    } finally {
      setSyncing(null)
    }
  }

  const columns: ColumnsType<TransactionItem> = [
    { title: '商户订单号', dataIndex: 'out_trade_no', key: 'out_trade_no', ellipsis: true },
    { title: '标题', dataIndex: 'subject', key: 'subject', ellipsis: true },
    { title: '金额(元)', dataIndex: 'total_amount', key: 'total_amount', width: 100 },
    {
      title: '本地状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s: string) => statusTag(s),
    },
    {
      title: '支付宝状态',
      dataIndex: 'trade_status',
      key: 'trade_status',
      width: 140,
      render: (v: string | null) => v ?? '—',
    },
    {
      title: '支付宝流水号',
      dataIndex: 'trade_no',
      key: 'trade_no',
      ellipsis: true,
      render: (v: string | null) => v ?? '—',
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 200 },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, row) => (
        <Button
          type="link"
          size="small"
          loading={syncing === row.out_trade_no}
          onClick={() => void onSync(row.out_trade_no)}
        >
          同步状态
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <Typography.Title level={3} className="mb-2!">
          订单记录
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="mb-0! max-w-2xl">
          数据来自服务端 PostgreSQL（创建支付时写入）。支付完成后可点「同步状态」调用{' '}
          <code className="rounded bg-slate-100 px-1 text-sm">alipay.trade.query</code> 更新。
          <Link to="/" className="ml-2 text-blue-600">
            返回收银台
          </Link>
        </Typography.Paragraph>
      </div>

      <Card className="max-w-5xl shadow-sm">
        <Space className="mb-4!">
          <Button onClick={() => void load()} loading={loading}>
            刷新
          </Button>
        </Space>
        <Table<TransactionItem>
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={items}
          scroll={{ x: 960 }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p) => setPage(p),
          }}
        />
      </Card>
    </div>
  )
}
