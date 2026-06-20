import { createContext, useContext, useState } from 'react'

export interface CartItem {
  id: number  // inventory_item_id or product_id
  type: 'card' | 'product'
  name: string
  image_url: string | null
  price: number
  quantity: number
  max_qty: number
  condition?: string
}

interface CartCtx {
  items: CartItem[]
  addItem: (item: Omit<CartItem, 'quantity'>) => void
  removeItem: (id: number, type: string) => void
  updateQty: (id: number, type: string, qty: number) => void
  clear: () => void
  total: number
}

const CartContext = createContext<CartCtx>({} as CartCtx)
export const useCart = () => useContext(CartContext)

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(() => {
    try { return JSON.parse(localStorage.getItem('shop_cart') || '[]') } catch { return [] }
  })

  const persist = (next: CartItem[]) => { setItems(next); localStorage.setItem('shop_cart', JSON.stringify(next)) }

  const addItem = (item: Omit<CartItem, 'quantity'>) => {
    const existing = items.find(i => i.id === item.id && i.type === item.type)
    if (existing) {
      persist(items.map(i => i.id === item.id && i.type === item.type ? { ...i, quantity: Math.min(i.quantity + 1, i.max_qty) } : i))
    } else {
      persist([...items, { ...item, quantity: 1 }])
    }
  }

  const removeItem = (id: number, type: string) => persist(items.filter(i => !(i.id === id && i.type === type)))
  const updateQty = (id: number, type: string, qty: number) => persist(items.map(i => i.id === id && i.type === type ? { ...i, quantity: Math.max(1, Math.min(qty, i.max_qty)) } : i))
  const clear = () => persist([])
  const total = items.reduce((s, i) => s + i.price * i.quantity, 0)

  return <CartContext.Provider value={{ items, addItem, removeItem, updateQty, clear, total }}>{children}</CartContext.Provider>
}
