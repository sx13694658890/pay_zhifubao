import { Alert, App, Button, Card, Descriptions, Typography } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { syncOrder } from '../api/pay'

/** 同步返回页展示秒数，结束后进入订单记录 */
const REDIRECT_SECONDS = 3
/** 补偿异步 notify：用查单接口短轮询次数（与文档「前端与 notify 的配合」一致） */
const SYNC_ATTEMPTS = 5
const SYNC_INTERVAL_MS = 700

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

/**
 * 支付宝同步跳转 return_url 落地页（仅展示，不据此更新订单状态）。
 * 若 URL 含 out_trade_no，则轮询调用「同步状态」查单，补偿异步 notify 延迟。
 * 短暂展示后跳转至订单记录。
 */
export function PayReturnPage() {
  const { message } = App.useApp()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [secondsLeft, setSecondsLeft] = useState(REDIRECT_SECONDS)
  const [syncHint, setSyncHint] = useState<string | null>(null)
  const cancelledRef = useRef(false)

  const outTradeNo = useMemo(() => {
    const raw = params.get('out_trade_no')?.trim()
    return raw || undefined
  }, [params])

  useEffect(() => {
    cancelledRef.current = false
    if (!outTradeNo) {
      setSyncHint(null)
      return
    }

    setSyncHint('正在通过查单接口同步订单状态…')

    const run = async () => {
      for (let i = 0; i < SYNC_ATTEMPTS; i++) {
        if (cancelledRef.current) return
        try {
          const row = await syncOrder(outTradeNo)
          if (row.status === 'PAID' || row.status === 'CLOSED') {
            if (!cancelledRef.current) {
              setSyncHint(`订单状态已更新为 ${row.status}（查单结果；最终以服务端异步通知为准）`)
              message.success('订单状态已与支付宝核对')
            }
            return
          }
        } catch {
          /* 单次失败继续重试 */
        }
        if (i < SYNC_ATTEMPTS - 1) await sleep(SYNC_INTERVAL_MS)
      }
      if (!cancelledRef.current) {
        setSyncHint('订单可能仍在确认中，请在订单记录中查看或点击「同步状态」')
        message.info('订单仍在确认中，可稍后在订单记录中同步')
      }
    }

    void run()
    return () => {
      cancelledRef.current = true
    }
  }, [message, outTradeNo])

  useEffect(() => {
    const redirectTimer = window.setTimeout(
      () => navigate('/orders', { replace: true }),
      REDIRECT_SECONDS * 1000,
    )
    const tick = window.setInterval(() => {
      setSecondsLeft((s) => Math.max(0, s - 1))
    }, 1000)
    return () => {
      window.clearTimeout(redirectTimer)
      window.clearInterval(tick)
    }
  }, [navigate])

  const goOrdersNow = () => {
    navigate('/orders', { replace: true })
  }

  const entries = useMemo(() => {
    const list: { key: string; value: string }[] = []
    params.forEach((value, key) => {
      list.push({ key, value })
    })
    return list.sort((a, b) => a.key.localeCompare(b.key))
  }, [params])

  return (
    <div className="space-y-6">
      <div>
        <Typography.Title level={3} className="mb-2!">
          支付结果（同步返回）
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="mb-0!">
          本页由支付宝浏览器跳转打开，仅用于提示用户体验。
        </Typography.Paragraph>
      </div>

      <Alert
        type="warning"
        showIcon
        message="是否支付成功，请以订单详情为准"
        description="订单最终状态由服务端异步通知（notify）验签后更新；浏览器不会调用 notify 接口。若异步尚未到达，本页会尽量通过「查单」接口刷新状态，仍可能短暂显示处理中。"
      />

      {syncHint ? (
        <Alert type="info" showIcon message={syncHint} />
      ) : null}

      <Alert
        type="info"
        showIcon
        message={
          secondsLeft > 0 ? `${secondsLeft} 秒后自动进入订单记录` : '正在进入订单记录…'
        }
        action={
          <Button type="primary" size="small" onClick={goOrdersNow}>
            立即前往订单记录
          </Button>
        }
      />

      <Card title="同步回传参数（URL Query）" className="shadow-sm">
        {entries.length === 0 ? (
          <Typography.Text type="secondary">当前无查询参数（可直接访问本页做文案联调）。</Typography.Text>
        ) : (
          <Descriptions column={1} bordered size="small" items={entries.map((e) => ({
            key: e.key,
            label: e.key,
            children: e.value,
          }))} />
        )}
      </Card>
    </div>
  )
}
