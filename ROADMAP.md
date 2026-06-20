# TCG Store — Roadmap & Future Improvements

## Staff UI Pages (Backend exists, need frontend)
- [ ] Products page (`/products`) — CRUD for sealed products, set online availability
- [ ] Orders page (`/orders`) — view/manage online orders, update status (pending→confirmed→ready→picked_up)
- [ ] Buylist page (`/buylist`) — search cards, get buy quotes, record trade-ins
- [ ] Tournaments page (`/tournaments`) — create tournament, register players, run rounds, view standings
- [ ] Settings page — pricing rules management, game sync controls, currency config

## Payment Integration
- [ ] MercadoPago integration (preferred for Mexico — lower fees than Stripe)
- [ ] Payment webhook to auto-confirm orders on successful payment
- [ ] Refund flow when orders are cancelled
- [ ] Receipt generation (PDF or thermal printer)

## Authentication & Accounts
- [ ] Google OAuth login (alongside email/password)
- [ ] Password reset via email
- [ ] Staff/admin role separation (store owner vs. employee vs. customer)
- [ ] Rate limiting on auth endpoints

## Online Storefront
- [x] Customer-facing storefront UI (browse online inventory, add to cart, checkout)
- [x] Pickup date/time scheduling (min 1 day ahead)
- [x] Customer login/register modal in checkout flow
- [x] Order confirmation page + My Orders list
- [ ] Order confirmation email notifications
- [ ] Order status update notifications (ready for pickup → email/SMS)
- [ ] Storefront SEO meta tags + Open Graph
- [ ] Product image gallery (multiple images per product)
- [ ] "Recently viewed" cards section
- [ ] Wishlist / save for later
- [ ] Estimated pickup availability indicator (calendar view)
- [ ] Share card/product link (social media preview)
- [ ] Guest checkout (order without full account)

## Inventory & Products
- [x] Barcode/SKU lookup for sealed products (GET /products/lookup?barcode=&sku=)
- [x] Bulk price updates (POST /inventory/bulk-price-update)
- [ ] Low stock alerts/notifications
- [x] Inventory valuation reports (GET /inventory/valuation)
- [x] CSV export of full inventory (GET /inventory/export/csv)
- [ ] CSV import for inventory (bulk add from spreadsheet)
- [x] Inventory adjustment log (track who changed what and when)
- [ ] Stock count / reconciliation tool
- [ ] Product bundles (sell multiple items as one SKU)

## Pricing
- [ ] CardMarket API integration (EU/MX pricing, better than Scryfall for sell prices)
- [ ] TCGPlayer API integration (US market fallback)
- [ ] Auto-update listed prices when market prices change (based on rules)
- [ ] Currency conversion via live API (USD/EUR → MXN)
- [ ] Price history charts in UI

## Card Scanning
- [x] Build full pHash index for all 107K+ cards (background job)
- [ ] CNN fallback (MobileNetV2/ONNX) for ambiguous matches
- [x] Auto-detect card in frame (auto-capture mode every 2s)
- [x] Batch scanning mode (rapid-fire for buylist sessions)
- [x] Mobile camera support (responsive scanner page, rear camera)

## Deployment & Ops
- [ ] Dockerize backend + frontend
- [ ] systemd service for production (auto-start on boot)
- [ ] Nightly SQLite backup to cloud (Google Drive / S3)
- [ ] Frontend served as static build from backend (single process)
- [ ] HTTPS via Let's Encrypt / Caddy reverse proxy

## Multi-Store / SaaS (Phase 2+)
- [ ] Migrate SQLite → PostgreSQL
- [ ] Multi-tenant support (one DB per store or schema separation)
- [ ] Cloud deployment (AWS/GCP/DO)
- [ ] Per-store custom domains
- [ ] Freemium model with Store Edition tier

## Mobile App (Phase 2+)
- [ ] Flutter mobile app with on-device TFLite scanning
- [ ] Customer-facing mobile app for browsing/ordering
- [ ] Push notifications for order status

## Game-Specific
- [ ] Riot API key for official Riftbound data (replace gist stopgap)
- [ ] Pokémon API key for faster sync (remove rate limiting)
- [x] One Piece TCG adapter (Bandai TCG Plus API, 4,686 cards)
- [x] Star Wars Unlimited adapter (swu-db.com, 1,297 cards)
- [x] Yu-Gi-Oh adapter (YGOProDeck, 14,417 cards)
- [ ] Digimon TCG adapter (Bandai TCG Plus API game_title_id=2)
- [ ] Dragon Ball Super adapter (Bandai TCG Plus API game_title_id=3)

## Quality of Life
- [x] Dark mode toggle
- [x] Keyboard shortcuts for POS (F2: search, F8: complete, Esc: clear)
- [x] Undo/void last sale
- [x] Toast notifications
- [x] Dark mode support across all pages (tables, modals, cards)
- [x] Confirm dialog component (replace browser confirm())
- [x] Loading skeleton states for tables/grids
- [x] POS: scan barcode to add item to cart (hardware scanner input)
- [x] POS: customer display (second screen showing cart total)
- [x] Inventory: batch edit (select multiple → change condition/delete)
- [ ] Inventory: drag-and-drop reorder (deferred — needs rank column + dnd-kit)
- [x] Search: recent searches memory
- [x] Search: search by set code (e.g., "mh3:42")
- [x] Responsive/mobile layout for sidebar navigation
- [x] Sound feedback on scan match / sale complete
- [x] Auto-focus on page navigation
- [x] Catalog: default content on load (not empty)
- [x] Game filter chips on Catalog, AddCard modal, and POS
- [x] Increased search results (24 in catalog/add, 16 in POS)
- [x] Customer-facing price lookup kiosk mode (/kiosk)
- [x] Tournament management module
- [ ] Marketplace listing sync (CardMarket seller tools)
