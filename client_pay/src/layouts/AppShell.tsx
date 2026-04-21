import { Link, Outlet } from 'react-router-dom'

export function AppShell() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight text-slate-800">
            支付宝网页收银台
          </Link>
          <nav className="flex items-center gap-3 text-sm text-slate-600">
            <Link to="/" className="hover:text-blue-600">
              去支付
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/orders" className="hover:text-blue-600">
              订单记录
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/pay/return" className="hover:text-blue-600">
              同步返回示例
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
