import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { useCart } from './ShopCart'
import { useToast } from '../../components/Toast'

export default function ShopBrowse() {
  const { t } = useTranslation()
  const { addItem } = useCart()
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [game, setGame] = useState('')
  const [cards, setCards] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [tab, setTab] = useState<'cards' | 'products'>('cards')

  useEffect(() => {
    const timer = setTimeout(async () => {
      const params: Record<string, string> = { per_page: '24' }
      if (query) params.q = query
      if (game) params.game = game
      if (tab === 'cards') {
        const { data } = await api.get('/shop/cards', { params })
        setCards(data.items)
      } else {
        const { data } = await api.get('/shop/products', { params })
        setProducts(data.items)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query, game, tab])

  const addCard = (item: any) => {
    addItem({ id: item.id, type: 'card', name: item.name, image_url: item.image_url, price: item.price || 0, max_qty: item.available, condition: item.condition })
    toast(`${item.name} → 🛒`)
  }

  const addProduct = (item: any) => {
    addItem({ id: item.id, type: 'product', name: item.name, image_url: item.image_url, price: item.price || 0, max_qty: item.available })
    toast(`${item.name} → 🛒`)
  }

  return (
    <div>
      {/* Tabs */}
      <div className="flex gap-4 mb-4 border-b">
        <button onClick={() => setTab('cards')} className={`pb-2 text-sm font-medium ${tab === 'cards' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'}`}>
          🃏 {t('shop.cards_tab')}
        </button>
        <button onClick={() => setTab('products')} className={`pb-2 text-sm font-medium ${tab === 'products' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'}`}>
          📦 {t('shop.products_tab')}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input placeholder={t('shop.search_placeholder')} value={query} onChange={e => setQuery(e.target.value)} className="border rounded px-3 py-2 flex-1 dark:bg-gray-800 dark:border-gray-700" />
        <select value={game} onChange={e => setGame(e.target.value)} className="border rounded px-3 py-2 dark:bg-gray-800 dark:border-gray-700">
          <option value="">{t('inventory.all_games')}</option>
          <option value="mtg">Magic: The Gathering</option>
          <option value="pokemon">Pokémon</option>
          <option value="lorcana">Lorcana</option>
          <option value="fab">Flesh and Blood</option>
          <option value="riftbound">Riftbound</option>
        </select>
      </div>

      {/* Cards grid */}
      {tab === 'cards' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {cards.map(item => (
            <div key={item.id} className="border rounded overflow-hidden bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition">
              {item.image_url ? <img src={item.image_url} alt={item.name} className="w-full" loading="lazy" /> : <div className="aspect-[2.5/3.5] bg-gray-200 dark:bg-gray-700" />}
              <div className="p-2">
                <p className="text-xs font-medium truncate">{item.name}</p>
                <p className="text-[10px] text-gray-400">{item.condition}{item.is_foil ? ' ✨' : ''} · {item.available} disp.</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-sm font-bold">${item.price?.toFixed(2)}</span>
                  <button onClick={() => addCard(item)} className="bg-indigo-600 text-white text-[10px] px-2 py-0.5 rounded hover:bg-indigo-700">+ 🛒</button>
                </div>
              </div>
            </div>
          ))}
          {cards.length === 0 && <p className="col-span-full text-center text-gray-400 py-12">{t('shop.no_items')}</p>}
        </div>
      )}

      {/* Products grid */}
      {tab === 'products' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {products.map(item => (
            <div key={item.id} className="border rounded overflow-hidden bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition">
              {item.image_url ? <img src={item.image_url} alt={item.name} className="w-full aspect-square object-cover" /> : <div className="aspect-square bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-4xl">📦</div>}
              <div className="p-3">
                <p className="text-sm font-medium">{item.name}</p>
                <p className="text-xs text-gray-400">{item.product_type} · {item.available} disp.</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-lg font-bold">${item.price?.toFixed(2)}</span>
                  <button onClick={() => addProduct(item)} className="bg-indigo-600 text-white text-xs px-3 py-1 rounded hover:bg-indigo-700">+ 🛒</button>
                </div>
              </div>
            </div>
          ))}
          {products.length === 0 && <p className="col-span-full text-center text-gray-400 py-12">{t('shop.no_items')}</p>}
        </div>
      )}
    </div>
  )
}
