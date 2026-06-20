import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { useCart } from './ShopCart'
import { useToast } from '../../components/Toast'

export default function ShopCheckout() {
  const { t } = useTranslation()
  const { items, removeItem, updateQty, clear, total } = useCart()
  const toast = useToast()
  const navigate = useNavigate()
  const [pickupDate, setPickupDate] = useState('')
  const [pickupTime, setPickupTime] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authForm, setAuthForm] = useState({ email: '', password: '', name: '' })

  const token = localStorage.getItem('customer_token')
  const minDate = new Date(Date.now() + 86400000).toISOString().split('T')[0]

  const doAuth = async () => {
    try {
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register'
      const body = authMode === 'login' ? { email: authForm.email, password: authForm.password } : authForm
      const { data } = await api.post(endpoint, body)
      localStorage.setItem('customer_token', data.token)
      localStorage.setItem('customer_name', data.customer.name)
      setShowAuth(false)
      toast(t('shop.logged_in'))
    } catch (e: any) {
      toast(e.response?.data?.detail || 'Error', 'error')
    }
  }

  const placeOrder = async () => {
    if (!token) { setShowAuth(true); return }
    if (!pickupDate) { toast(t('shop.select_date'), 'error'); return }

    setLoading(true)
    try {
      const orderItems = items.map(i => ({
        ...(i.type === 'card' ? { inventory_item_id: i.id } : { product_id: i.id }),
        quantity: i.quantity,
      }))
      const { data } = await api.post('/orders', {
        items: orderItems, pickup_date: pickupDate, pickup_time: pickupTime, notes,
      }, { headers: { Authorization: `Bearer ${token}` } })
      clear()
      navigate(`/shop/orders/${data.id}`)
    } catch (e: any) {
      toast(e.response?.data?.detail || 'Error', 'error')
    }
    setLoading(false)
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-4xl mb-4">🛒</p>
        <p className="text-gray-500">{t('shop.empty_cart')}</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Cart items */}
      <div className="lg:col-span-2 space-y-2">
        <h2 className="text-xl font-bold mb-3">{t('shop.your_cart')}</h2>
        {items.map(item => (
          <div key={`${item.type}-${item.id}`} className="flex items-center gap-3 bg-white dark:bg-gray-800 rounded p-3 shadow-sm">
            {item.image_url ? <img src={item.image_url} className="w-12 rounded" /> : <div className="w-12 h-16 bg-gray-200 rounded" />}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{item.name}</p>
              <p className="text-xs text-gray-400">{item.condition || item.type} · ${item.price.toFixed(2)}</p>
            </div>
            <input type="number" min={1} max={item.max_qty} value={item.quantity} onChange={e => updateQty(item.id, item.type, +e.target.value)} className="border rounded w-14 px-2 py-1 text-sm text-center dark:bg-gray-700 dark:border-gray-600" />
            <span className="font-medium text-sm w-20 text-right">${(item.price * item.quantity).toFixed(2)}</span>
            <button onClick={() => removeItem(item.id, item.type)} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        ))}
      </div>

      {/* Checkout sidebar */}
      <div className="bg-white dark:bg-gray-800 rounded shadow p-4 h-fit sticky top-20">
        <h3 className="font-bold mb-3">{t('shop.checkout')}</h3>
        <div className="space-y-3 mb-4">
          <div>
            <label className="text-xs text-gray-500 block mb-1">{t('shop.pickup_date')}</label>
            <input type="date" min={minDate} value={pickupDate} onChange={e => setPickupDate(e.target.value)} className="border rounded w-full px-2 py-1.5 text-sm dark:bg-gray-700 dark:border-gray-600" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">{t('shop.pickup_time')}</label>
            <select value={pickupTime} onChange={e => setPickupTime(e.target.value)} className="border rounded w-full px-2 py-1.5 text-sm dark:bg-gray-700 dark:border-gray-600">
              <option value="">{t('shop.any_time')}</option>
              {['10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00'].map(h => <option key={h} value={h}>{h}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">{t('shop.notes')}</label>
            <input value={notes} onChange={e => setNotes(e.target.value)} className="border rounded w-full px-2 py-1.5 text-sm dark:bg-gray-700 dark:border-gray-600" placeholder={t('shop.notes_placeholder')} />
          </div>
        </div>

        <div className="border-t pt-3 mb-3">
          <div className="flex justify-between text-lg font-bold">
            <span>Total</span><span>${total.toFixed(2)} MXN</span>
          </div>
        </div>

        <button onClick={placeOrder} disabled={loading} className="w-full bg-green-600 text-white py-2.5 rounded font-medium hover:bg-green-700 disabled:opacity-50">
          {loading ? '...' : token ? t('shop.place_order') : t('shop.login_to_order')}
        </button>

        {!token && <p className="text-[10px] text-gray-400 text-center mt-2">{t('shop.login_required')}</p>}
      </div>

      {/* Auth modal */}
      {showAuth && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowAuth(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
            <h3 className="font-bold mb-4">{authMode === 'login' ? t('shop.login') : t('shop.register')}</h3>
            <div className="space-y-3">
              {authMode === 'register' && (
                <input placeholder={t('shop.name')} value={authForm.name} onChange={e => setAuthForm(f => ({ ...f, name: e.target.value }))} className="border rounded w-full px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600" />
              )}
              <input type="email" placeholder="Email" value={authForm.email} onChange={e => setAuthForm(f => ({ ...f, email: e.target.value }))} className="border rounded w-full px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600" />
              <input type="password" placeholder={t('shop.password')} value={authForm.password} onChange={e => setAuthForm(f => ({ ...f, password: e.target.value }))} className="border rounded w-full px-3 py-2 text-sm dark:bg-gray-700 dark:border-gray-600" />
              <button onClick={doAuth} className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700">
                {authMode === 'login' ? t('shop.login') : t('shop.register')}
              </button>
              <button onClick={() => setAuthMode(m => m === 'login' ? 'register' : 'login')} className="w-full text-xs text-indigo-600 hover:underline">
                {authMode === 'login' ? t('shop.no_account') : t('shop.have_account')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
