import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { AddCardModal } from '../components/AddCardModal'
import { useConfirm } from '../components/ConfirmDialog'

interface InventoryItem {
  id: number
  card_id: string
  card_name: string | null
  quantity: number
  condition: string
  language: string
  is_foil: boolean
  purchase_price: number | null
  listed_price: number | null
  notes: string | null
  image_url: string | null
  market_price: number | null
}

interface Filters { game: string; condition: string; q: string; in_stock: boolean; sort: string; card_type: string }

export default function Inventory() {
  const { t } = useTranslation()
  const [items, setItems] = useState<InventoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({ game: '', condition: '', q: '', in_stock: false, sort: 'recent', card_type: '' })
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [editValues, setEditValues] = useState<Partial<InventoryItem>>({})
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const confirm = useConfirm()

  const toggleSelect = (id: number) => {
    setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  }
  const selectAll = () => setSelected(items.length === selected.size ? new Set() : new Set(items.map(i => i.id)))

  const bulkDelete = async () => {
    if (!await confirm({ message: `Delete ${selected.size} items?`, danger: true })) return
    for (const id of selected) await api.delete(`/inventory/${id}`)
    setSelected(new Set())
    fetchItems()
  }
  const bulkUpdate = async (field: string, value: any) => {
    for (const id of selected) await api.patch(`/inventory/${id}`, { [field]: value })
    setSelected(new Set())
    fetchItems()
  }
  const fetchItems = useCallback(async () => {
    const params: Record<string, string> = { page: String(page), per_page: '25', sort: filters.sort }
    if (filters.game) params.game = filters.game
    if (filters.condition) params.condition = filters.condition
    if (filters.q) params.q = filters.q
    if (filters.in_stock) params.in_stock = 'true'
    if (filters.card_type) params.card_type = filters.card_type
    const { data } = await api.get('/inventory', { params })
    setItems(data.items)
    setTotal(data.total)
  }, [page, filters])

  useEffect(() => { fetchItems() }, [fetchItems])

  const startEdit = (item: InventoryItem) => {
    setEditing(item.id)
    setEditValues({ quantity: item.quantity, listed_price: item.listed_price, condition: item.condition })
  }

  const saveEdit = async (id: number) => {
    await api.patch(`/inventory/${id}`, editValues)
    setEditing(null)
    fetchItems()
  }

  const deleteItem = async (id: number) => {
    if (!await confirm({ message: t('inventory.confirm_delete'), danger: true })) return
    await api.delete(`/inventory/${id}`)
    fetchItems()
  }

  const totalPages = Math.ceil(total / 25)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('inventory.title')}</h1>
        <button onClick={() => setShowAdd(true)} className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 text-sm">
          {t('inventory.add_card')}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <input
          placeholder={t('inventory.search_placeholder')}
          value={filters.q}
          onChange={e => { setFilters(f => ({ ...f, q: e.target.value })); setPage(1) }}
          className="border dark:border-gray-700 dark:bg-gray-800 rounded px-3 py-1.5 text-sm w-56"
        />
        <select value={filters.game} onChange={e => { setFilters(f => ({ ...f, game: e.target.value })); setPage(1) }} className="border dark:border-gray-700 dark:bg-gray-800 rounded px-3 py-1.5 text-sm">
          <option value="">{t('inventory.all_games')}</option>
          <option value="mtg">Magic: The Gathering</option>
          <option value="pokemon">Pokémon</option>
          <option value="lorcana">Lorcana</option>
          <option value="fab">Flesh and Blood</option>
          <option value="riftbound">Riftbound</option>
        </select>
        <select value={filters.condition} onChange={e => { setFilters(f => ({ ...f, condition: e.target.value })); setPage(1) }} className="border dark:border-gray-700 dark:bg-gray-800 rounded px-3 py-1.5 text-sm">
          <option value="">{t('inventory.all_conditions')}</option>
          {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-1 text-sm">
          <input type="checkbox" checked={filters.in_stock} onChange={e => { setFilters(f => ({ ...f, in_stock: e.target.checked })); setPage(1) }} />
          {t('inventory.in_stock')}
        </label>
        <select value={filters.sort} onChange={e => { setFilters(f => ({ ...f, sort: e.target.value })); setPage(1) }} className="border rounded px-3 py-1.5 text-sm dark:bg-gray-800 dark:border-gray-700">
          <option value="recent">{t('inventory.sort_recent')}</option>
          <option value="name">{t('inventory.sort_name')}</option>
          <option value="price_asc">{t('inventory.sort_price_asc')}</option>
          <option value="price_desc">{t('inventory.sort_price_desc')}</option>
          <option value="quantity">{t('inventory.sort_quantity')}</option>
        </select>
        <select value={filters.card_type} onChange={e => { setFilters(f => ({ ...f, card_type: e.target.value })); setPage(1) }} className="border rounded px-3 py-1.5 text-sm dark:bg-gray-800 dark:border-gray-700">
          <option value="">{t('inventory.all_types')}</option>
          <option value="creature">Creature</option>
          <option value="instant">Instant</option>
          <option value="sorcery">Sorcery</option>
          <option value="enchantment">Enchantment</option>
          <option value="artifact">Artifact</option>
          <option value="planeswalker">Planeswalker</option>
          <option value="land">Land</option>
        </select>
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700 rounded p-2 mb-3 flex items-center gap-3 text-sm">
          <span className="font-medium">{selected.size} selected</span>
          <select onChange={e => { if (e.target.value) bulkUpdate('condition', e.target.value); e.target.value = '' }} className="border rounded px-2 py-1 text-xs dark:bg-gray-800 dark:border-gray-700">
            <option value="">Set condition...</option>
            {['NM','LP','MP','HP','DMG'].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={bulkDelete} className="text-red-600 text-xs hover:underline">Delete</button>
          <button onClick={() => setSelected(new Set())} className="text-gray-400 text-xs ml-auto">Clear</button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-700 text-left">
            <tr>
              <th className="px-2 py-2 w-8"><input type="checkbox" checked={items.length > 0 && selected.size === items.length} onChange={selectAll} /></th>
              <th className="px-3 py-2">{t('inventory.card')}</th>
              <th className="px-3 py-2">{t('inventory.game')}</th>
              <th className="px-3 py-2">{t('inventory.qty')}</th>
              <th className="px-3 py-2">{t('inventory.condition')}</th>
              <th className="px-3 py-2">{t('inventory.foil')}</th>
              <th className="px-3 py-2">{t('inventory.price')}</th>
              <th className="px-3 py-2">{t('inventory.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={8} className="text-center py-8 text-gray-400">{t('inventory.empty')}</td></tr>
            )}
            {items.map(item => (
              <tr key={item.id} className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
                <td className="px-2 py-2"><input type="checkbox" checked={selected.has(item.id)} onChange={() => toggleSelect(item.id)} /></td>
                <td className="px-3 py-2 font-medium">
                  <div className="flex items-center gap-2">
                    {item.image_url && <img src={item.image_url} alt="" className="w-8 h-auto rounded" />}
                    <span>{item.card_name || item.card_id}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-gray-500">{item.card_id.split(':')[0]}</td>
                <td className="px-3 py-2">
                  {editing === item.id ? (
                    <input type="number" min={0} value={editValues.quantity ?? ''} onChange={e => setEditValues(v => ({ ...v, quantity: +e.target.value }))} className="border rounded w-16 px-1 py-0.5" />
                  ) : item.quantity}
                </td>
                <td className="px-3 py-2">
                  {editing === item.id ? (
                    <select value={editValues.condition} onChange={e => setEditValues(v => ({ ...v, condition: e.target.value }))} className="border rounded px-1 py-0.5">
                      {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                    </select>
                  ) : (
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${item.condition === 'NM' ? 'bg-green-100 text-green-800' : item.condition === 'LP' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>{item.condition}</span>
                  )}
                </td>
                <td className="px-3 py-2">{item.is_foil ? '✨' : '—'}</td>
                <td className="px-3 py-2">
                  {editing === item.id ? (
                    <input type="number" step="0.01" value={editValues.listed_price ?? ''} onChange={e => setEditValues(v => ({ ...v, listed_price: +e.target.value || null }))} className="border rounded w-20 px-1 py-0.5" placeholder="$" />
                  ) : (
                    <div>
                      {item.listed_price ? <span className="font-medium">${item.listed_price.toFixed(2)}</span> : <span className="text-gray-300">—</span>}
                      {item.market_price && <span className="text-[10px] text-gray-400 block">mkt ${item.market_price.toFixed(2)}</span>}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 flex gap-1">
                  {editing === item.id ? (
                    <>
                      <button onClick={() => saveEdit(item.id)} className="text-green-600 hover:underline text-xs">{t('inventory.save')}</button>
                      <button onClick={() => setEditing(null)} className="text-gray-400 hover:underline text-xs">{t('inventory.cancel')}</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEdit(item)} className="text-indigo-600 hover:underline text-xs">{t('inventory.edit')}</button>
                      <button onClick={() => deleteItem(item.id)} className="text-red-500 hover:underline text-xs">{t('inventory.delete')}</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-4">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-30">{t('inventory.prev')}</button>
          <span className="px-3 py-1 text-sm text-gray-600">{page} / {totalPages} ({total} {t('inventory.items')})</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded text-sm disabled:opacity-30">{t('inventory.next')}</button>
        </div>
      )}

      {showAdd && <AddCardModal onClose={() => setShowAdd(false)} onAdded={fetchItems} />}
    </div>
  )
}
