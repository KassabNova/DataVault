import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { useToast } from '../components/Toast'

interface CardResult {
  id: string; name: string; game_id: string; set_id: string
  rarity: string | null; collector_number: string; image_url: string | null; card_type: string | null
}

interface Props { onClose: () => void; onAdded: () => void }

const GAMES = [
  { id: '', label: 'All' }, { id: 'mtg', label: 'MTG' }, { id: 'pokemon', label: 'Pokémon' },
  { id: 'yugioh', label: 'Yu-Gi-Oh' }, { id: 'lorcana', label: 'Lorcana' },
  { id: 'onepiece', label: 'One Piece' }, { id: 'swu', label: 'Star Wars' },
  { id: 'fab', label: 'FaB' }, { id: 'riftbound', label: 'Riftbound' },
]

export function AddCardModal({ onClose, onAdded }: Props) {
  const { t } = useTranslation()
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [game, setGame] = useState('')
  const [results, setResults] = useState<CardResult[]>([])
  const [selected, setSelected] = useState<CardResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ quantity: 1, condition: 'NM', is_foil: false, language: 'en', purchase_price: '' as string | number })
  const [submitting, setSubmitting] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>(null!)

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const params: Record<string, string> = { q: query, per_page: '24' }
        if (game) params.game = game
        const { data } = await api.get('/cards/search', { params })
        setResults(data)
      } catch { setResults([]) }
      setLoading(false)
    }, 300)
    return () => clearTimeout(timer.current)
  }, [query, game])

  const submit = async () => {
    if (!selected) return
    setSubmitting(true)
    try {
      await api.post('/inventory', {
        card_id: selected.id, quantity: form.quantity, condition: form.condition,
        is_foil: form.is_foil, language: form.language,
        purchase_price: form.purchase_price ? +form.purchase_price : null,
      })
      onAdded(); onClose(); toast(`✓ ${selected.name} added`)
    } catch (e: any) { alert(e.response?.data?.detail || t('add_modal.error')) }
    setSubmitting(false)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">{t('add_modal.title')}</h2>

        {!selected ? (
          <>
            <input autoFocus placeholder={t('add_modal.search_placeholder')} value={query} onChange={e => setQuery(e.target.value)} className="w-full border dark:border-gray-700 dark:bg-gray-900 rounded px-3 py-2 mb-2" />

            {/* Game filter chips */}
            <div className="flex gap-1 mb-3 flex-wrap">
              {GAMES.map(g => (
                <button key={g.id} onClick={() => setGame(g.id)} className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${game === g.id ? 'bg-indigo-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                  {g.label}
                </button>
              ))}
            </div>

            {loading && <p className="text-sm text-gray-400">{t('add_modal.searching')}</p>}
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2 max-h-96 overflow-y-auto">
              {results.map(card => (
                <button key={card.id} onClick={() => setSelected(card)} className="border dark:border-gray-700 rounded p-1.5 hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-left flex flex-col items-center">
                  {card.image_url ? (
                    <img src={card.image_url} alt={card.name} className="w-full h-auto rounded mb-1" loading="lazy" />
                  ) : (
                    <div className="w-full aspect-[2.5/3.5] bg-gray-200 dark:bg-gray-700 rounded mb-1 flex items-center justify-center text-[9px] text-gray-400">{t('add_modal.no_image')}</div>
                  )}
                  <span className="text-[10px] font-medium text-center leading-tight">{card.name}</span>
                  <span className="text-[9px] text-gray-400">{card.set_id.replace(`${card.game_id}:`, '')} · {card.rarity}</span>
                </button>
              ))}
            </div>
            {query.length >= 2 && !loading && results.length === 0 && <p className="text-sm text-gray-400 mt-3">{t('add_modal.no_results')}</p>}
          </>
        ) : (
          <>
            <div className="flex gap-4 mb-4">
              {selected.image_url && <img src={selected.image_url} alt={selected.name} className="w-28 rounded" />}
              <div>
                <h3 className="font-bold">{selected.name}</h3>
                <p className="text-sm text-gray-500">{selected.set_id} · #{selected.collector_number}</p>
                <p className="text-sm text-gray-500">{selected.rarity} · {selected.card_type}</p>
                <button onClick={() => setSelected(null)} className="text-xs text-indigo-600 mt-2 hover:underline">{t('add_modal.change_card')}</button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1">{t('add_modal.quantity')}</label>
                <input type="number" min={1} value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: +e.target.value }))} className="border dark:border-gray-700 dark:bg-gray-900 rounded w-full px-2 py-1.5" />
              </div>
              <div>
                <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1">{t('add_modal.condition')}</label>
                <select value={form.condition} onChange={e => setForm(f => ({ ...f, condition: e.target.value }))} className="border dark:border-gray-700 dark:bg-gray-900 rounded w-full px-2 py-1.5">
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1">{t('add_modal.language')}</label>
                <select value={form.language} onChange={e => setForm(f => ({ ...f, language: e.target.value }))} className="border dark:border-gray-700 dark:bg-gray-900 rounded w-full px-2 py-1.5">
                  <option value="en">English</option><option value="es">Español</option><option value="ja">日本語</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-600 dark:text-gray-400 block mb-1">{t('add_modal.purchase_price')}</label>
                <input type="number" step="0.01" value={form.purchase_price} onChange={e => setForm(f => ({ ...f, purchase_price: e.target.value }))} className="border dark:border-gray-700 dark:bg-gray-900 rounded w-full px-2 py-1.5" placeholder="0.00" />
              </div>
              <label className="flex items-center gap-2 col-span-2">
                <input type="checkbox" checked={form.is_foil} onChange={e => setForm(f => ({ ...f, is_foil: e.target.checked }))} />
                <span className="text-sm">{t('add_modal.foil')}</span>
              </label>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="px-4 py-2 text-sm border dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-700">{t('add_modal.cancel')}</button>
              <button onClick={submit} disabled={submitting} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50">
                {submitting ? t('add_modal.saving') : t('add_modal.add')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
