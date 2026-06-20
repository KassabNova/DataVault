import { Link, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCart } from './ShopCart'

export default function ShopLayout() {
  const { t } = useTranslation()
  const { items } = useCart()
  const token = localStorage.getItem('customer_token')

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-gray-100">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/shop" className="text-xl font-bold text-indigo-600">🃏 TCG Store</Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/shop" className="hover:text-indigo-600">{t('shop.browse')}</Link>
            <Link to="/shop/cart" className="hover:text-indigo-600 relative">
              🛒 {items.length > 0 && <span className="absolute -top-1 -right-3 bg-indigo-600 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{items.length}</span>}
            </Link>
            {token ? (
              <Link to="/shop/orders" className="hover:text-indigo-600">{t('shop.my_orders')}</Link>
            ) : (
              <Link to="/shop/login" className="hover:text-indigo-600">{t('shop.login')}</Link>
            )}
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
