import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function Kiosk() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [price, setPrice] = useState<any>(null)

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const t = setTimeout(async () => {
      const { data } = await api.get('/cards/search', { params: { q: query, per_page: 12 } })
      setResults(data)
    }, 300)
    return () => clearTimeout(t)
  }, [query])

  const selectCard = async (card: any) => {
    setSelected(card)
    try { const { data } = await api.get(`/prices/${card.id}`); setPrice(data) } catch { setPrice(null) }
  }

  const reset = () => { setSelected(null); setPrice(null); setQuery(''); setResults([]) }

  // Fullscreen on click
  const goFullscreen = () => document.documentElement.requestFullscreen?.()

  if (selected) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center p-8" onClick={reset}>
        <div className="flex gap-8 items-center max-w-3xl">
          {selected.image_url && <img src={selected.image_url} className="w-64 rounded-lg shadow-2xl" />}
          <div>
            <h1 className="text-3xl font-bold mb-2">{selected.name}</h1>
            <p className="text-gray-400 mb-4">{selected.set_id} · #{selected.collector_number} · {selected.rarity}</p>
            {price?.store?.sell_price ? (
              <div className="space-y-2">
                <div className="text-5xl font-bold text-green-400">${price.store.sell_price} MXN</div>
                <p className="text-gray-400 text-sm">Precio de venta</p>
                <div className="text-xl text-blue-400 mt-2">${price.store.buy_price} MXN <span className="text-sm text-gray-500">compramos</span></div>
              </div>
            ) : (
              <p className="text-gray-500 text-lg">Precio no disponible</p>
            )}
          </div>
        </div>
        <p className="text-gray-600 text-sm mt-12">Toca para buscar otra carta</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center p-8">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2" onClick={goFullscreen}>🃏 Consulta de Precios</h1>
          <p className="text-gray-500">Busca una carta para ver su precio</p>
        </div>

        <input
          autoFocus
          placeholder="Nombre de la carta..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-lg mb-6 focus:border-indigo-500 outline-none"
        />

        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
          {results.map(card => (
            <button key={card.id} onClick={() => selectCard(card)} className="rounded-lg overflow-hidden border border-gray-800 hover:border-indigo-500 transition">
              {card.image_url ? (
                <img src={card.image_url} className="w-full" loading="lazy" />
              ) : (
                <div className="aspect-[2.5/3.5] bg-gray-800 flex items-center justify-center text-xs text-gray-500">{card.name}</div>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
