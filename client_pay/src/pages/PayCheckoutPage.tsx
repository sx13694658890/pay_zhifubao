import { App, Button, Card, Form, Input, InputNumber, Typography } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { createAlipayPagePay } from '../api/pay'
import { openAlipayPayUrl, submitAlipayFormHtml } from '../lib/alipayRedirect'

type FormValues = {
  subject: string
  total_amount: number
  out_trade_no?: string
}

export function PayCheckoutPage() {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: FormValues) => {
    setLoading(true)
    try {
      const payload = {
        subject: values.subject.trim(),
        total_amount: Number(values.total_amount).toFixed(2),
        ...(values.out_trade_no?.trim()
          ? { out_trade_no: values.out_trade_no.trim() }
          : {}),
      }

      const res = await createAlipayPagePay(payload)

      if (res.url) {
        openAlipayPayUrl(res.url)
        return
      }
      if (res.form_html) {
        submitAlipayFormHtml(res.form_html)
        return
      }

      message.error('后端未返回 url 或 form_html，请对照需求文档检查接口约定')
    } catch (e) {
      const err = e instanceof Error ? e.message : '创建支付失败'
      message.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Typography.Title level={3} className="mb-2!">
          发起支付
        </Typography.Title>
        <Typography.Paragraph type="secondary" className="mb-0! max-w-2xl">
          点击「去支付」将请求<strong>自有后端</strong>创建订单并签名，随后跳转到支付宝收银台。请在开放平台配置
          <code className="mx-1 rounded bg-slate-100 px-1.5 py-0.5 text-sm">return_url</code>
          指向本站
          <code className="mx-1 rounded bg-slate-100 px-1.5 py-0.5 text-sm">/pay/return</code>
          （示例路径，可按部署调整）。
        </Typography.Paragraph>
      </div>

      <Card className="shadow-sm">
        <Form<FormValues>
          layout="vertical"
          requiredMark="optional"
          onFinish={onFinish}
          initialValues={{ subject: '测试商品', total_amount: 0.01 }}
        >
          <Form.Item
            label="订单标题"
            name="subject"
            rules={[{ required: true, message: '请输入订单标题' }]}
          >
            <Input placeholder="展示在支付宝收银台的商品说明" maxLength={256} />
          </Form.Item>

          <Form.Item
            label="金额（元）"
            name="total_amount"
            rules={[
              { required: true, message: '请输入金额' },
              {
                validator: async (_, v) => {
                  if (v === undefined || v === null) return
                  if (Number(v) <= 0) throw new Error('金额必须大于 0')
                },
              },
            ]}
          >
            <InputNumber className="w-full!" min={0.01} step={0.01} precision={2} />
          </Form.Item>

          <Form.Item label="商户订单号（可选）" name="out_trade_no">
            <Input placeholder="留空则由后端生成 out_trade_no" allowClear />
          </Form.Item>

          <Form.Item className="mb-0!">
            <Button type="primary" htmlType="submit" loading={loading} size="large" block>
              去支付
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Typography.Paragraph type="secondary" className="text-sm">
        开发环境已将 <code className="rounded bg-slate-100 px-1">/api</code> 代理到{' '}
        <code className="rounded bg-slate-100 px-1">http://127.0.0.1:8000</code>
        ，请确保后端提供{' '}
        <code className="rounded bg-slate-100 px-1">POST /api/pay/alipay/page-pay/create</code>
        或在前端环境变量中修改请求路径逻辑。创建支付后可在{' '}
        <Link to="/orders" className="text-blue-600">
          订单记录
        </Link>{' '}
        查看本地订单（返回 <code className="rounded bg-slate-100 px-1">out_trade_no</code> 时可在列表中同步状态）。
      </Typography.Paragraph>
    </div>
  )
}
