import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'

interface CardItem {
  id: string; name: string; game_id: string; set_id: string
  rarity: string | null; collector_number: string; image_url: string | null; card_type: string | null
}

const GAMES = [
  { id: '', label: 'All' },
  { id: 'mtg', label: 'MTG' },
  { id: 'pokemon', label: 'Pokémon' },
  { id: 'yugioh', label: 'Yu-Gi-Oh' },
  { id: 'lorcana', label: 'Lorcana' },
  { id: 'onepiece', label: 'One Piece' },
  { id: 'swu', label: 'Star Wars' },
  { id: 'fab', label: 'FaB' },
  { id: 'riftbound', label: 'Riftbound' },
]

export default function Catalog() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [game, setGame] = useState('')
  const [cards, setCards] = useState<CardItem[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<CardItem | null>(null)
  const [priceData, setPriceData] = useState<any>(null)
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('recent_searches') || '[]') } catch { return [] }
  })

  const saveSearch = (q: string) => {
    if (q.length < 2) return
    const updated = [q, ...recentSearches.filter(s => s !== q)].slice(0, 8)
    setRecentSearches(updated)
    localStorage.setItem('recent_searches', JSON.stringify(updated))
  }

  const search = useCallback(async () => {
    setLoading(true)
    if (query.length >= 2) {
      saveSearch(query)
      const params: Record<string, string> = { q: query, per_page: '24', page: String(page) }
      if (game) params.game = game
      const { data } = await api.get('/cards/search', { params })
      setCards(data)
    } else {
      // Show recent cards from catalog when no search
      const params: Record<string, string> = { per_page: '24', page: String(page) }
      if (game) params.game = game
      const { data } = await api.get('/cards/search', { params: { q: game ? `${game}*` : 'a', ...params } }).catch(() => ({ data: [] }))
      setCards(data)
    }
    setLoading(false)
  }, [query, game, page])

  useEffect(() => {
    const timer = setTimeout(search, 300)
    return () => clearTimeout(timer)
  }, [search])

  const openDetail = async (card: CardItem) => {
    setSelected(card)
    setPriceData(null)
    try {
      const { data } = await api.get('/prices/lookup', { params: { card_id: card.id } })
      setPriceData(data)
    } catch { setPriceData({ store: {} }) }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">{t('catalog.title')}</h1>

      {/* Search + filters */}
      <div className="flex gap-3 mb-3 flex-wrap">
        <input
          autoFocus
          placeholder={t('catalog.search_placeholder')}
          value={query}
          onChange={e => { setQuery(e.target.value); setPage(1) }}
          className="border dark:border-gray-700 dark:bg-gray-800 rounded px-3 py-2 w-72"
        />
      </div>

      {/* Game filter chips */}
      <div className="flex gap-1.5 mb-4 flex-wrap">
        {GAMES.map(g => (
          <button
            key={g.id}
            onClick={() => { setGame(g.id); setPage(1) }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${game === g.id ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-indigo-100 dark:hover:bg-indigo-900'}`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {loading && <p className="text-gray-400 text-sm">{t('catalog.searching')}</p>}

      {/* Card Grid */}
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
        {cards.map(card => (
          <button key={card.id} onClick={() => openDetail(card)} className="group relative rounded overflow-hidden border dark:border-gray-700 hover:border-indigo-400 hover:shadow-md transition">
            {card.image_url ? (
              <img src={card.image_url} alt={card.name} className="w-full h-auto" loading="lazy" />
            ) : (
              <div className="aspect-[2.5/3.5] bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-[10px] text-gray-400 p-1 text-center">{card.name}</div>
            )}
            <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-[9px] px-1 py-0.5 opacity-0 group-hover:opacity-100 transition truncate">
              {card.name}
            </div>
          </button>
        ))}
      </div>

      {cards.length === 24 && (
        <div className="flex justify-center mt-4 gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border dark:border-gray-700 rounded text-sm disabled:opacity-30">{t('inventory.prev')}</button>
          <span className="text-sm text-gray-500 py-1">{t('catalog.page')} {page}</span>
          <button onClick={() => setPage(p => p + 1)} className="px-3 py-1 border dark:border-gray-700 rounded text-sm">{t('inventory.next')}</button>
        </div>
      )}

      {query.length >= 2 && !loading && cards.length === 0 && (
        <p className="text-gray-400 text-center py-12">{t('add_modal.no_results')}</p>
      )}

      {query.length < 2 && !game && recentSearches.length > 0 && cards.length === 0 && (
        <div className="py-4">
          <p className="text-xs text-gray-400 mb-2">Recent searches</p>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map(s => (
              <button key={s} onClick={() => setQuery(s)} className="text-xs bg-gray-100 dark:bg-gray-800 px-3 py-1 rounded hover:bg-indigo-100 dark:hover:bg-indigo-900">{s}</button>
            ))}
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full p-6" onClick={e => e.stopPropagation()}>
            <div className="flex gap-4">
              {selected.image_url && <img src={selected.image_url} alt={selected.name} className="w-36 rounded" />}
              <div className="flex-1">
                <h2 className="text-lg font-bold">{selected.name}</h2>
                <p className="text-sm text-gray-500">{selected.set_id} · #{selected.collector_number}</p>
                <p className="text-sm text-gray-500 mb-3">{selected.rarity} · {selected.card_type}</p>

                {priceData?.store?.market_price && (
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3 space-y-1 text-sm">
                    <div className="flex justify-between"><span>{t('catalog.market')}</span><span className="font-medium">${priceData.store.market_price} MXN</span></div>
                    <div className="flex justify-between"><span>{t('catalog.sell')}</span><span className="font-medium text-green-600">${priceData.store.sell_price} MXN</span></div>
                    <div className="flex justify-between"><span>{t('catalog.buy')}</span><span className="font-medium text-blue-600">${priceData.store.buy_price} MXN</span></div>
                  </div>
                )}
                {priceData && !priceData.store?.market_price && (
                  <p className="text-xs text-gray-400">{t('catalog.no_price')}</p>
                )}
              </div>
            </div>
            <button onClick={() => setSelected(null)} className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-700">{t('add_modal.cancel')}</button>
          </div>
        </div>
      )}
    </div>
  )
}
