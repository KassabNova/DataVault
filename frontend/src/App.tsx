import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import './i18n'
import { LangSwitcher } from './components/LangSwitcher'
import { ThemeToggle } from './components/ThemeToggle'
import { ToastProvider } from './components/Toast'
import { ConfirmProvider } from './components/ConfirmDialog'
import Dashboard from './pages/Dashboard'
import Inventory from './pages/Inventory'
import Sales from './pages/Sales'
import Catalog from './pages/Catalog'
import Scanner from './pages/Scanner'
import Kiosk from './pages/Kiosk'
import ShopLayout from './pages/shop/ShopLayout'
import { CartProvider } from './pages/shop/ShopCart'
import ShopBrowse from './pages/shop/ShopBrowse'
import ShopCheckout from './pages/shop/ShopCheckout'
import { OrderDetail, MyOrders } from './pages/shop/ShopOrders'

// Lazy placeholder for pages we'll build out
function Placeholder({ title }: { title: string }) {
  return <div className="p-8"><h2 className="text-2xl font-bold">{title}</h2><p className="text-gray-500 mt-2">En construcción...</p></div>
}

function Sidebar() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  const navSections = [
    { items: [
      { to: '/', label: `📊 ${t('nav.dashboard')}` },
    ]},
    { items: [
      { to: '/inventory', label: `📦 ${t('nav.inventory')}` },
      { to: '/products', label: '🎁 Productos' },
      { to: '/catalog', label: `🃏 ${t('nav.catalog')}` },
    ]},
    { items: [
      { to: '/sales', label: `💰 ${t('nav.sales')}` },
      { to: '/orders', label: '📋 Pedidos' },
      { to: '/buylist', label: '💸 Compras' },
    ]},
    { items: [
      { to: '/scanner', label: `📷 ${t('nav.scanner')}` },
      { to: '/tournaments', label: '🏆 Torneos' },
    ]},
  ]

  return (
    <>
      <button onClick={() => setOpen(true)} className="md:hidden fixed top-3 left-3 z-50 bg-gray-900 text-white p-2 rounded">☰</button>
      {open && <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={() => setOpen(false)} />}

      <nav className={`fixed md:static z-50 w-56 bg-gray-900 dark:bg-gray-950 text-white min-h-screen p-4 flex flex-col transition-transform md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <h1 className="text-xl font-bold mb-4 px-2">TCG Store</h1>

        <div className="flex flex-col gap-0.5 flex-1">
          {navSections.map((section, si) => (
            <div key={si} className={si > 0 ? 'mt-3 pt-3 border-t border-gray-800' : ''}>
              {section.items.map(({ to, label }) => (
                <NavLink key={to} to={to} onClick={() => setOpen(false)}
                  className={({ isActive }) => `px-3 py-1.5 rounded text-sm block ${isActive ? 'bg-indigo-600' : 'hover:bg-gray-800'}`}
                >{label}</NavLink>
              ))}
            </div>
          ))}
        </div>

        {/* Quick links to other views */}
        <div className="text-[10px] text-gray-500 space-y-1 mb-3">
          <a href="/shop" className="block hover:text-gray-300">→ Tienda online</a>
          <a href="/kiosk" className="block hover:text-gray-300">→ Modo kiosko</a>
        </div>

        <div className="pt-3 border-t border-gray-700 flex items-center justify-between">
          <LangSwitcher />
          <ThemeToggle />
        </div>
      </nav>
    </>
  )
}

function StaffLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-gray-100">
      <Sidebar />
      <main className="flex-1 md:ml-0">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/products" element={<Placeholder title="Productos Sellados" />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/sales" element={<Sales />} />
          <Route path="/orders" element={<Placeholder title="Pedidos Online" />} />
          <Route path="/buylist" element={<Placeholder title="Compras / Trade-In" />} />
          <Route path="/scanner" element={<Scanner />} />
          <Route path="/tournaments" element={<Placeholder title="Torneos" />} />
        </Routes>
      </main>
    </div>
  )
}

// Simple login page for shop
function ShopLogin() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 w-full max-w-sm">
        <h2 className="text-xl font-bold mb-4 text-center">🃏 TCG Store</h2>
        <p className="text-sm text-gray-500 text-center mb-4">Inicia sesión o <Link to="/shop/cart" className="text-indigo-600">continúa al carrito</Link> para crear tu cuenta.</p>
        <Link to="/shop" className="block text-center bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700">Ir a la tienda</Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
    <ConfirmProvider>
    <CartProvider>
    <BrowserRouter>
      <Routes>
        {/* Standalone views */}
        <Route path="/kiosk" element={<Kiosk />} />
        <Route path="/shop/login" element={<ShopLogin />} />

        {/* Customer storefront */}
        <Route path="/shop" element={<ShopLayout />}>
          <Route index element={<ShopBrowse />} />
          <Route path="cart" element={<ShopCheckout />} />
          <Route path="orders" element={<MyOrders />} />
          <Route path="orders/:id" element={<OrderDetail />} />
        </Route>

        {/* Store management (staff) */}
        <Route path="/*" element={<StaffLayout />} />
      </Routes>
    </BrowserRouter>
    </CartProvider>
    </ConfirmProvider>
    </ToastProvider>
  )
}
