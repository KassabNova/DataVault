import { useRef } from 'react'

interface Props {
  items: { card_name: string; quantity: number; unit_price: number }[]
  total: number
  discount: number
}

export function useCustomerDisplay() {
  const winRef = useRef<Window | null>(null)

  const open = () => {
    winRef.current = window.open('', 'customer_display', 'width=600,height=400,toolbar=no,menubar=no')
    if (winRef.current) {
      winRef.current.document.write(`
        <html><head><title>TCG Store</title>
        <style>body{font-family:system-ui;background:#111;color:#fff;padding:2rem;margin:0}
        #total{font-size:4rem;font-weight:bold;text-align:center;color:#22c55e;margin:1rem 0}
        #items{font-size:1.1rem;max-height:200px;overflow-y:auto}
        .item{display:flex;justify-content:space-between;padding:0.3rem 0;border-bottom:1px solid #333}
        h1{text-align:center;font-size:1.5rem;opacity:0.6}</style></head>
        <body><h1>🃏 TCG Store</h1><div id="total">$0.00</div><div id="items"></div></body></html>
      `)
    }
  }

  const update = ({ items, total, discount }: Props) => {
    if (!winRef.current || winRef.current.closed) return
    const doc = winRef.current.document
    const totalEl = doc.getElementById('total')
    const itemsEl = doc.getElementById('items')
    if (totalEl) totalEl.textContent = `$${total.toFixed(2)} MXN`
    if (itemsEl) {
      itemsEl.innerHTML = items.map(i =>
        `<div class="item"><span>${i.card_name} ×${i.quantity}</span><span>$${(i.unit_price * i.quantity).toFixed(2)}</span></div>`
      ).join('') + (discount > 0 ? `<div class="item" style="color:#f59e0b"><span>Descuento</span><span>-$${discount.toFixed(2)}</span></div>` : '')
    }
  }

  const close = () => { winRef.current?.close(); winRef.current = null }

  return { open, update, close, isOpen: () => !!winRef.current && !winRef.current.closed }
}
