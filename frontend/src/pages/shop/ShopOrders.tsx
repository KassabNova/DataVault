import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'

export function OrderDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const [order, setOrder] = useState<any>(null)
  const token = localStorage.getItem('customer_token')

  useEffect(() => {
    api.get(`/orders/${id}`, { headers: { Authorization: `Bearer ${token}` } }).then(r => setOrder(r.data))
  }, [id])

  if (!order) return <p className="text-gray-400 py-8">{t('shop.loading')}</p>

  return (
    <div className="max-w-lg mx-auto">
      <div className="text-center mb-6">
        <div className="text-5xl mb-3">✅</div>
        <h2 className="text-xl font-bold">{t('shop.order_confirmed')}</h2>
        <p className="text-gray-500">#{order.id}</p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded shadow p-4 space-y-3">
        <div className="flex justify-between"><span className="text-gray-500">{t('shop.status')}</span><span className="font-medium capitalize">{order.status}</span></div>
        <div className="flex justify-between"><span className="text-gray-500">{t('shop.pickup_date')}</span><span className="font-medium">{order.pickup_date} {order.pickup_time || ''}</span></div>
        <div className="flex justify-between"><span className="text-gray-500">Total</span><span className="font-bold text-lg">${order.total.toFixed(2)} MXN</span></div>
        {order.items && order.items.length > 0 && (
          <div className="border-t pt-2">
            {order.items.map((i: any) => (
              <div key={i.id} className="flex justify-between text-sm py-1">
                <span>{i.item_name} ×{i.quantity}</span>
                <span>${(i.unit_price * i.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <Link to="/shop/orders" className="block text-center text-indigo-600 text-sm mt-4 hover:underline">{t('shop.view_all_orders')}</Link>
    </div>
  )
}

export function MyOrders() {
  const { t } = useTranslation()
  const [orders, setOrders] = useState<any[]>([])
  const token = localStorage.getItem('customer_token')

  useEffect(() => {
    if (token) api.get('/orders/my', { headers: { Authorization: `Bearer ${token}` } }).then(r => setOrders(r.data))
  }, [])

  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    confirmed: 'bg-blue-100 text-blue-800',
    ready: 'bg-green-100 text-green-800',
    picked_up: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-800',
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">{t('shop.my_orders')}</h2>
      {orders.length === 0 && <p className="text-gray-400 py-8 text-center">{t('shop.no_orders')}</p>}
      <div className="space-y-2">
        {orders.map(o => (
          <Link key={o.id} to={`/shop/orders/${o.id}`} className="flex items-center justify-between bg-white dark:bg-gray-800 rounded shadow-sm p-3 hover:shadow-md transition">
            <div>
              <span className="font-medium">#{o.id}</span>
              <span className={`ml-2 text-xs px-2 py-0.5 rounded ${statusColors[o.status] || ''}`}>{o.status}</span>
            </div>
            <div className="text-right">
              <p className="font-medium">${o.total.toFixed(2)}</p>
              <p className="text-xs text-gray-400">{t('shop.pickup')}: {o.pickup_date}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
