import { App as AntApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layouts/AppShell'
import { OrdersPage } from './pages/OrdersPage'
import { PayCheckoutPage } from './pages/PayCheckoutPage'
import { PayReturnPage } from './pages/PayReturnPage'

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<PayCheckoutPage />} />
              <Route path="orders" element={<OrdersPage />} />
              <Route path="pay/return" element={<PayReturnPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  )
}
