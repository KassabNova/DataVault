import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { playSuccess } from '../services/sound'
import { useCustomerDisplay } from '../components/CustomerDisplay'

interface CartItem {
  inventory_item_id: number
  card_name: string
  condition: string
  unit_price: number
  quantity: number
  max_qty: number
}

export default function Sales() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [gameFilter, setGameFilter] = useState('')
  const [cart, setCart] = useState<CartItem[]>([])
  const [discount, setDiscount] = useState(0)
  const [payMethod, setPayMethod] = useState('cash')
  const [loading, setLoading] = useState(false)
  const [saleComplete, setSaleComplete] = useState<any>(null)
  const customerDisplay = useCustomerDisplay()
  const timer = useRef<ReturnType<typeof setTimeout>>(null!)
  const searchRef = useRef<HTMLInputElement>(null!)
  const barcodeBuffer = useRef('')

  // Barcode scanner: captures rapid keystrokes into hidden field
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>
    const handler = (e: KeyboardEvent) => {
      // Hardware scanners type fast and end with Enter
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return
      if (e.key === 'Enter' && barcodeBuffer.current.length > 3) {
        e.preventDefault()
        lookupBarcode(barcodeBuffer.current)
        barcodeBuffer.current = ''
      } else if (e.key.length === 1) {
        barcodeBuffer.current += e.key
        clearTimeout(timeout)
        timeout = setTimeout(() => { barcodeBuffer.current = '' }, 100)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const lookupBarcode = async (barcode: string) => {
    try {
      const { data } = await api.get('/products/lookup', { params: { barcode } })
      if (data) addToCart({ ...data, card_name: data.name, quantity: data.quantity, listed_price: data.listed_price })
    } catch {
      try {
        const { data } = await api.get('/products/lookup', { params: { sku: barcode } })
        if (data) addToCart({ ...data, card_name: data.name, quantity: data.quantity, listed_price: data.listed_price })
      } catch { /* not found */ }
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // F2 or Ctrl+K: focus search
      if (e.key === 'F2' || (e.ctrlKey && e.key === 'k')) {
        e.preventDefault()
        searchRef.current?.focus()
      }
      // F8 or Ctrl+Enter: complete sale
      if (e.key === 'F8' || (e.ctrlKey && e.key === 'Enter')) {
        e.preventDefault()
        if (cart.length > 0) completeSale()
      }
      // Escape: clear search or dismiss sale complete
      if (e.key === 'Escape') {
        if (saleComplete) setSaleComplete(null)
        else { setQuery(''); setResults([]) }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [cart, saleComplete])

  // Search inventory for items to sell — show recent items by default
  useEffect(() => {
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      const params: Record<string, string> = { in_stock: 'true', per_page: '16', sort: 'recent' }
      if (query.length >= 2) params.q = query
      if (gameFilter) params.game = gameFilter
      const { data } = await api.get('/inventory', { params })
      setResults(data.items)
    }, query.length >= 2 ? 300 : 0)
    return () => clearTimeout(timer.current)
  }, [query, gameFilter])

  const addToCart = (item: any) => {
    const existing = cart.find(c => c.inventory_item_id === item.id)
    if (existing) {
      if (existing.quantity < existing.max_qty)
        setCart(cart.map(c => c.inventory_item_id === item.id ? { ...c, quantity: c.quantity + 1 } : c))
    } else {
      setCart([...cart, {
        inventory_item_id: item.id,
        card_name: item.card_name || item.card_id,
        condition: item.condition,
        unit_price: item.listed_price || 0,
        quantity: 1,
        max_qty: item.quantity,
      }])
    }
    setQuery('')
    setResults([])
  }

  const removeFromCart = (id: number) => setCart(cart.filter(c => c.inventory_item_id !== id))
  const updateQty = (id: number, qty: number) => setCart(cart.map(c => c.inventory_item_id === id ? { ...c, quantity: Math.min(qty, c.max_qty) } : c))
  const updatePrice = (id: number, price: number) => setCart(cart.map(c => c.inventory_item_id === id ? { ...c, unit_price: price } : c))

  const subtotal = cart.reduce((sum, c) => sum + c.unit_price * c.quantity, 0)
  const total = subtotal - discount

  // Update customer display
  useEffect(() => {
    customerDisplay.update({ items: cart, total, discount })
  }, [cart, discount, total])

  const completeSale = async () => {
    if (cart.length === 0) return
    setLoading(true)
    try {
      const { data } = await api.post('/sales', {
        items: cart.map(c => ({ inventory_item_id: c.inventory_item_id, quantity: c.quantity, unit_price: c.unit_price })),
        discount,
        payment_method: payMethod,
      })
      setSaleComplete(data)
      setCart([])
      setDiscount(0)
      playSuccess()
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Error')
    }
    setLoading(false)
  }

  if (saleComplete) {
    const undoSale = async () => {
      if (!confirm(t('sales.confirm_void'))) return
      await api.post(`/sales/${saleComplete.id}/void`)
      setSaleComplete(null)
    }
    return (
      <div className="p-6 max-w-md mx-auto text-center">
        <div className="text-5xl mb-4">✅</div>
        <h2 className="text-xl font-bold mb-2">{t('sales.complete')}</h2>
        <p className="text-3xl font-bold text-green-600 mb-2">${saleComplete.total.toFixed(2)} MXN</p>
        <p className="text-gray-500 text-sm mb-6">{saleComplete.payment_method} · #{saleComplete.id}</p>
        <div className="flex gap-2 justify-center">
          <button onClick={() => setSaleComplete(null)} className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700">
            {t('sales.new_sale')}
          </button>
          <button onClick={undoSale} className="border border-red-300 text-red-600 px-4 py-2 rounded hover:bg-red-50 text-sm">
            {t('sales.void')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 flex gap-6 h-[calc(100vh-2rem)]">
      {/* Left: search + results */}
      <div className="flex-1 flex flex-col">
        <h1 className="text-2xl font-bold mb-4">{t('sales.title')}</h1>
        <button onClick={() => customerDisplay.open()} className="text-xs text-indigo-600 hover:underline mb-2 block">📺 Customer Display</button>
        <input
          ref={searchRef}
          autoFocus
          placeholder={t('sales.search_placeholder')}
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="border rounded px-3 py-2 mb-2 w-full dark:bg-gray-800 dark:border-gray-700"
        />
        <div className="flex gap-1 mb-3 flex-wrap">
          {[{ id: '', label: 'All' }, { id: 'mtg', label: 'MTG' }, { id: 'pokemon', label: 'Pokémon' }, { id: 'yugioh', label: 'YGO' }, { id: 'lorcana', label: 'Lorcana' }, { id: 'onepiece', label: 'OP' }, { id: 'swu', label: 'SWU' }, { id: 'fab', label: 'FaB' }].map(g => (
            <button key={g.id} onClick={() => setGameFilter(g.id)} className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${gameFilter === g.id ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>{g.label}</button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto space-y-1">
          {results.map(item => (
            <button
              key={item.id}
              onClick={() => addToCart(item)}
              className="w-full flex items-center gap-3 border rounded p-2 hover:bg-indigo-50 text-left"
            >
              {item.image_url && <img src={item.image_url} className="w-8 h-auto rounded" />}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{item.card_name}</div>
                <div className="text-xs text-gray-400">{item.condition} · qty: {item.quantity}</div>
              </div>
              <span className="text-sm font-medium">{item.listed_price ? `$${item.listed_price.toFixed(2)}` : '—'}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Right: cart */}
      <div className="w-80 bg-white dark:bg-gray-800 rounded shadow flex flex-col p-4">
        <h2 className="font-bold mb-3">{t('sales.cart')} ({cart.length})</h2>
        <div className="flex-1 overflow-y-auto space-y-2 mb-3">
          {cart.length === 0 && <p className="text-gray-300 text-sm text-center py-8">{t('sales.empty_cart')}</p>}
          {cart.map(item => (
            <div key={item.inventory_item_id} className="border rounded p-2 text-sm">
              <div className="flex justify-between items-start">
                <span className="font-medium leading-tight">{item.card_name}</span>
                <button onClick={() => removeFromCart(item.inventory_item_id)} className="text-red-400 text-xs ml-1">✕</button>
              </div>
              <div className="flex gap-2 mt-1 items-center">
                <span className="text-xs text-gray-400">{item.condition}</span>
                <input type="number" min={1} max={item.max_qty} value={item.quantity} onChange={e => updateQty(item.inventory_item_id, +e.target.value)} className="border rounded w-12 px-1 text-xs" />
                <span className="text-xs">×</span>
                <input type="number" step="0.01" value={item.unit_price} onChange={e => updatePrice(item.inventory_item_id, +e.target.value)} className="border rounded w-16 px-1 text-xs" />
                <span className="ml-auto font-medium">${(item.unit_price * item.quantity).toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Totals */}
        <div className="border-t pt-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm items-center">
            <span>{t('sales.discount')}</span>
            <input type="number" step="0.01" min={0} value={discount} onChange={e => setDiscount(+e.target.value)} className="border rounded w-20 px-2 py-0.5 text-right text-sm" />
          </div>
          <div className="flex justify-between font-bold text-lg">
            <span>Total</span><span>${total.toFixed(2)}</span>
          </div>
          <select value={payMethod} onChange={e => setPayMethod(e.target.value)} className="w-full border rounded px-2 py-1.5 text-sm">
            <option value="cash">{t('sales.cash')}</option>
            <option value="card">{t('sales.card')}</option>
            <option value="transfer">{t('sales.transfer')}</option>
          </select>
          <button
            onClick={completeSale}
            disabled={cart.length === 0 || loading}
            className="w-full bg-green-600 text-white py-2.5 rounded font-medium hover:bg-green-700 disabled:opacity-40"
          >
            {loading ? '...' : t('sales.complete_sale')}
          </button>
          <p className="text-[10px] text-gray-400 text-center mt-1">F2: buscar · F8: completar · Esc: limpiar</p>
        </div>
      </div>
    </div>
  )
}
