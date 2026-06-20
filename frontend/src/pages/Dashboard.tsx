import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'

interface DashboardData {
  inventory: { total_items: number; total_cards: number; estimated_value: number; low_stock_count: number }
  catalog: { total_cards: number; by_game: Record<string, number> }
  sales: { today_count: number; today_revenue: number; all_time_count: number; all_time_revenue: number }
}

const GAME_NAMES: Record<string, string> = {
  mtg: 'Magic: The Gathering',
  pokemon: 'Pokémon TCG',
  lorcana: 'Disney Lorcana',
  fab: 'Flesh and Blood',
  riftbound: 'Riftbound',
}

export default function Dashboard() {
  const { t } = useTranslation()
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    api.get('/dashboard').then(r => setData(r.data)).catch(() => {})
  }, [])

  if (!data) return <div className="p-8 text-gray-400">{t('dashboard.loading')}</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">{t('dashboard.title')}</h1>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label={t('dashboard.today_revenue')} value={`$${data.sales.today_revenue.toFixed(2)}`} sub={`${data.sales.today_count} ${t('dashboard.sales')}`} color="green" />
        <StatCard label={t('dashboard.inventory_value')} value={`$${data.inventory.estimated_value.toFixed(2)}`} sub={`${data.inventory.total_cards} ${t('dashboard.cards_in_stock')}`} color="indigo" />
        <StatCard label={t('dashboard.catalog_size')} value={data.catalog.total_cards.toLocaleString()} sub={t('dashboard.cards_indexed')} color="blue" />
        <StatCard label={t('dashboard.low_stock')} value={String(data.inventory.low_stock_count)} sub={t('dashboard.items_low')} color="amber" />
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Catalog by game */}
        <div className="bg-white dark:bg-gray-800 rounded shadow p-4">
          <h2 className="font-bold mb-3">{t('dashboard.catalog_by_game')}</h2>
          <div className="space-y-2">
            {Object.entries(data.catalog.by_game).sort((a, b) => b[1] - a[1]).map(([game, count]) => (
              <div key={game} className="flex items-center gap-3">
                <span className="text-sm w-40 truncate">{GAME_NAMES[game] || game}</span>
                <div className="flex-1 bg-gray-100 rounded h-5 relative overflow-hidden">
                  <div className="bg-indigo-500 h-full rounded" style={{ width: `${(count / data.catalog.total_cards) * 100}%` }} />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sales summary */}
        <div className="bg-white dark:bg-gray-800 rounded shadow p-4">
          <h2 className="font-bold mb-3">{t('dashboard.sales_summary')}</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-2xl font-bold text-green-700">{data.sales.today_count}</div>
              <div className="text-xs text-gray-500">{t('dashboard.sales_today')}</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-2xl font-bold text-green-700">${data.sales.today_revenue.toFixed(2)}</div>
              <div className="text-xs text-gray-500">{t('dashboard.revenue_today')}</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-2xl font-bold">{data.sales.all_time_count}</div>
              <div className="text-xs text-gray-500">{t('dashboard.total_sales')}</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-2xl font-bold">${data.sales.all_time_revenue.toFixed(2)}</div>
              <div className="text-xs text-gray-500">{t('dashboard.total_revenue')}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  const colors: Record<string, string> = {
    green: 'bg-green-50 border-green-200',
    indigo: 'bg-indigo-50 border-indigo-200',
    blue: 'bg-blue-50 border-blue-200',
    amber: 'bg-amber-50 border-amber-200',
  }
  return (
    <div className={`rounded border p-4 ${colors[color] || ''}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{sub}</div>
    </div>
  )
}
