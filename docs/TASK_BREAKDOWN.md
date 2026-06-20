# TCG Store Management System — Task Breakdown

## How to Use This Document

Each task is self-contained with clear inputs, outputs, and acceptance criteria. Tasks are ordered by dependency — complete them sequentially within each phase, but phases can overlap where noted.

---

## Phase 0: Project Scaffolding

### T0.1: Initialize Backend Project

**Goal:** Set up FastAPI project structure with dependency management.

**Steps:**
1. Create project directory: `backend/`
2. Initialize with `pyproject.toml` (use Poetry or pip + requirements.txt)
3. Create directory structure:
   ```
   backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py              # FastAPI app entry
   │   ├── config.py            # Settings (pydantic-settings)
   │   ├── database.py          # SQLite connection + session
   │   ├── models/              # SQLAlchemy models
   │   ├── schemas/             # Pydantic request/response schemas
   │   ├── routers/             # API route modules
   │   ├── services/            # Business logic
   │   ├── adapters/            # Game-specific API adapters
   │   └── workers/             # Background tasks (price sync)
   ├── tests/
   ├── alembic/                 # DB migrations
   └── requirements.txt
   ```
4. Install core dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic-settings`, `alembic`, `httpx`
5. Create a health check endpoint: `GET /health` → `{"status": "ok"}`

**Acceptance:** `uvicorn app.main:app` starts and `/health` returns 200.

---

### T0.2: Initialize Frontend Project

**Goal:** Set up React + Vite + TypeScript project.

**Steps:**
1. Create project: `npm create vite@latest frontend -- --template react-ts`
2. Install dependencies: `react-router-dom`, `axios`, `tailwindcss`
3. Set up Tailwind CSS
4. Create directory structure:
   ```
   frontend/
   ├── src/
   │   ├── components/         # Shared UI components
   │   ├── pages/              # Route-level pages
   │   ├── hooks/              # Custom hooks
   │   ├── services/           # API client functions
   │   ├── i18n/               # Locale JSON files
   │   │   ├── es.json
   │   │   └── en.json
   │   ├── types/              # TypeScript interfaces
   │   └── App.tsx
   ```
5. Configure proxy to backend (`vite.config.ts` → proxy `/api` to `localhost:8000`)
6. Create basic layout shell with navigation sidebar

**Acceptance:** `npm run dev` starts, shows layout shell, proxies to backend.

---

### T0.3: Database Schema & Migrations

**Goal:** Define the core SQLite schema and set up Alembic migrations.

**Steps:**
1. Define SQLAlchemy models (see SYSTEM_DESIGN.md for full schema)
2. Configure Alembic with SQLite
3. Create initial migration
4. Seed script for development data

**Models to create:**
- `Game` — supported TCGs
- `CardSet` — sets/expansions per game
- `Card` — unified card catalog
- `CardName` — multilingual card names
- `InventoryItem` — store's stock
- `PriceRecord` — price history
- `Sale` / `SaleItem` — transactions
- `ScanSession` — batch scan tracking

**Acceptance:** `alembic upgrade head` creates all tables. Seed script inserts sample data.

---

## Phase 1: Card Catalog & Data Sync

### T1.1: Base Adapter Interface

**Goal:** Define the abstract interface all game adapters implement.

**Steps:**
1. Create `adapters/base.py` with abstract class:
   ```python
   class BaseAdapter:
       game_id: str
       async def sync_cards(self, sets: list[str] | None = None) -> int
       async def sync_prices(self, card_ids: list[str] | None = None) -> int
       async def search(self, query: str, locale: str = "en") -> list[CardResult]
       async def get_card_image_url(self, card_id: str, size: str = "small") -> str
   ```
2. Create `adapters/registry.py` — registry to discover/load adapters by game_id

**Acceptance:** Interface defined, registry loads adapters dynamically.

---

### T1.2: MTG Adapter (Scryfall)

**Goal:** Sync all Magic cards from Scryfall bulk data.

**Steps:**
1. Implement `adapters/mtg.py`
2. Download Scryfall bulk data JSON (~80 MB): `https://api.scryfall.com/bulk-data`
3. Parse and insert into `Card` / `CardName` / `CardSet` tables
4. Map Scryfall fields to unified schema
5. Handle multilingual names (Scryfall `printed_name` for Spanish)
6. Store image URIs (don't download images yet)
7. Implement incremental sync (Scryfall provides `updated_at`)

**Acceptance:** Full MTG catalog (~85K cards) in DB with Spanish names where available. Sync completes in < 5 min.

---

### T1.3: Pokémon Adapter

**Goal:** Sync Pokémon cards from pokemontcg.io.

**Steps:**
1. Implement `adapters/pokemon.py`
2. Register for API key at pokemontcg.io
3. Paginate through all cards (250 per page)
4. Map to unified schema
5. Handle: no native Spanish names → store English only, allow manual override

**Acceptance:** All Pokémon cards synced. Search by name returns results.

---

### T1.4: Flesh and Blood Adapter

**Goal:** Sync FaB cards from GitHub JSON repository.

**Steps:**
1. Implement `adapters/fab.py`
2. Clone/download: `https://github.com/the-fab-cube/flesh-and-blood-cards`
3. Parse JSON files into unified schema
4. Extract multilingual names where available

**Acceptance:** FaB catalog in DB.

---

### T1.5: Lorcana Adapter

**Goal:** Sync Lorcana cards from community API.

**Steps:**
1. Implement `adapters/lorcana.py`
2. Use LorcanaJSON or lorcana-api.com
3. Map to unified schema

**Acceptance:** Lorcana catalog in DB.

---

### T1.6: Riftbound Adapter (Manual)

**Goal:** Provide manual entry interface for games without APIs.

**Steps:**
1. Implement `adapters/riftbound.py` as a stub (no external sync)
2. Create API endpoint for manual card creation: `POST /api/cards/manual`
3. Support CSV bulk import for initial catalog entry

**Acceptance:** Can manually add Riftbound cards and import from CSV.

---

## Phase 2: Pricing Engine

### T2.1: CardMarket API Integration

**Goal:** Fetch prices from CardMarket for all supported games.

**Steps:**
1. Register for CardMarket API access (partner/seller program)
2. Implement `services/pricing/cardmarket.py`
3. Map CardMarket product IDs to local card IDs (by set + collector number)
4. Fetch: price_trend, price_low, price_avg
5. Store in `PriceRecord` table with timestamp
6. Handle rate limiting (CardMarket limits: 5000 requests/day)

**Acceptance:** Prices populated for MTG, Pokémon, Lorcana, FaB from CardMarket.

---

### T2.2: Scryfall Price Fallback

**Goal:** Use Scryfall prices as fallback for MTG.

**Steps:**
1. Scryfall bulk data includes `prices.usd`, `prices.eur`
2. During MTG sync, extract prices into `PriceRecord`
3. Mark source as "scryfall" to distinguish from CardMarket

**Acceptance:** MTG cards have price data even without CardMarket access.

---

### T2.3: Price Sync Background Worker

**Goal:** Automated periodic price updates.

**Steps:**
1. Create `workers/price_sync.py`
2. Use FastAPI `BackgroundTasks` or APScheduler
3. Configurable schedule (default: every 6 hours)
4. Sync priorities: CardMarket first, then fallbacks
5. Log sync results (cards updated, errors, duration)
6. Expose sync status via `GET /api/prices/sync-status`

**Acceptance:** Prices auto-update on schedule. Status endpoint shows last sync time.

---

### T2.4: Store Pricing Rules

**Goal:** Apply markup/discount rules to generate store-specific prices.

**Steps:**
1. Create `services/pricing/rules.py`
2. Support rules: `sell_price = market × multiplier` and `buy_price = market × multiplier`
3. Rules configurable per game, per rarity, or per card
4. Currency conversion support (USD → MXN via configurable rate or API)
5. API: `GET /api/pricing/rules`, `PUT /api/pricing/rules`

**Acceptance:** Cards display both market price and store sell/buy prices.

---

## Phase 3: Inventory Management

### T3.1: Inventory CRUD API

**Goal:** Core inventory operations.

**Endpoints:**
- `POST /api/inventory` — add card to inventory
- `GET /api/inventory` — list with filters (game, set, condition, in_stock)
- `GET /api/inventory/{id}` — single item detail
- `PATCH /api/inventory/{id}` — update quantity/condition/price
- `DELETE /api/inventory/{id}` — remove item

**Fields per inventory item:**
- card_id (FK), quantity, condition (NM/LP/MP/HP/DMG), language, is_foil, purchase_price, listed_price, notes

**Acceptance:** Full CRUD works. Filtering by game/set/condition returns correct results.

---

### T3.2: Inventory UI

**Goal:** Frontend for managing inventory.

**Steps:**
1. Card grid/table view with pagination
2. Filters sidebar: game, set, condition, price range, stock status
3. Quick-add modal (search card → set quantity/condition → save)
4. Inline edit for quantity and price
5. Bulk actions: select multiple → update condition / delete

**Acceptance:** Can browse, filter, add, edit, and remove inventory items through UI.

---

### T3.3: Bulk Import

**Goal:** Import inventory from CSV files.

**Steps:**
1. Define CSV format: `game, card_name, set_code, collector_number, quantity, condition, language, foil, purchase_price`
2. `POST /api/inventory/import` — accepts CSV upload
3. Fuzzy match card names to catalog (handle typos)
4. Report: matched, unmatched, duplicates
5. Preview before confirming import

**Acceptance:** CSV with 500 cards imports correctly with match report.

---

## Phase 4: Card Scanning

### T4.1: Perceptual Hash Index

**Goal:** Build the pHash lookup table for all cards.

**Steps:**
1. Download small card images (Scryfall: 146×204 for MTG)
2. Compute pHash (DCT-based, 64-bit) for each card image
3. Store in `card_hash` table: `card_id, phash_value`
4. Build in-memory BK-tree or VP-tree for fast nearest-neighbor lookup
5. Expose: `POST /api/scan/match` — accepts image, returns top-5 matches with confidence

**Acceptance:** Given a card image, returns correct card in top-3 results >90% of the time.

---

### T4.2: Webcam Capture & Card Detection

**Goal:** Frontend webcam integration with card isolation.

**Steps:**
1. Use `navigator.mediaDevices.getUserMedia()` for webcam access
2. Render live feed on canvas
3. On trigger (button or auto-detect): capture frame
4. Send frame to backend: `POST /api/scan/match` (as JPEG blob)
5. Backend: OpenCV contour detection → isolate card rectangle → perspective transform → hash

**Acceptance:** Webcam shows live feed, captures frame, backend returns card match.

---

### T4.3: CNN Fallback (MobileNetV2)

**Goal:** Higher-accuracy fallback for ambiguous matches.

**Steps:**
1. Download pre-trained MobileNetV2 (ONNX format)
2. Fine-tune or use as feature extractor (output: 512-dim embedding)
3. Precompute embeddings for all cards, store in `card_embedding` table
4. On ambiguous pHash match (confidence < threshold): run CNN → cosine similarity search
5. Use FAISS or numpy for fast vector search

**Acceptance:** Ambiguous cases resolved with >95% accuracy. Adds <200ms to scan time.

---

### T4.4: Scan Session UX

**Goal:** Smooth scanning workflow for buylist/intake sessions.

**Steps:**
1. "Scan Mode" page: full-screen webcam with overlay
2. After match: show card name + image for confirmation
3. Quick-add panel: set condition, quantity, foil → add to inventory
4. Running list of scanned cards in session
5. Batch save entire session
6. Sound feedback on successful scan

**Acceptance:** Can scan 20 cards in under 2 minutes with confirmation flow.

---

## Phase 5: Sales / POS

### T5.1: Sales API

**Goal:** Record sales transactions.

**Endpoints:**
- `POST /api/sales` — create sale (items, discounts, total, payment method)
- `GET /api/sales` — list sales with date range filter
- `GET /api/sales/{id}` — sale detail
- `GET /api/sales/reports/daily` — daily summary

**Steps:**
1. Sale model: items[], subtotal, discount, tax, total, payment_method, timestamp
2. On sale: decrement inventory quantities
3. Validate stock availability before confirming

**Acceptance:** Sales recorded, inventory decremented, daily report shows totals.

---

### T5.2: POS UI

**Goal:** Point-of-sale interface for checkout.

**Steps:**
1. Search/scan to add cards to cart
2. Cart sidebar with running total
3. Condition/quantity selector per item
4. Discount input (% or fixed)
5. Payment method selector (cash, card, transfer)
6. Complete sale button → confirmation
7. Optional: receipt generation (printable HTML)

**Acceptance:** Complete sale flow from search to confirmation.

---

## Phase 6: Search & Browse

### T6.1: Full-Text Search

**Goal:** Fast card search across all games.

**Steps:**
1. SQLite FTS5 virtual table on card names (all languages)
2. `GET /api/cards/search?q=...&game=...&set=...&locale=es`
3. Return: card data + inventory status + current price
4. Support filters: game, set, rarity, color/type, price range

**Acceptance:** Search "charizard" returns all Charizard variants. Search "rayo" (Spanish) returns Lightning Bolt.

---

### T6.2: Browse UI

**Goal:** Card catalog browsing interface.

**Steps:**
1. Search bar with instant results (debounced)
2. Filter panel: game, set, rarity, type, price range, in-stock toggle
3. Results as card image grid (lazy-loaded)
4. Card detail modal: all printings, price chart, inventory history
5. Mobile-responsive grid

**Acceptance:** Can browse full catalog, filter by multiple criteria, view card details.

---

## Phase 7: Internationalization

### T7.1: UI i18n Setup

**Goal:** All UI strings translatable.

**Steps:**
1. Install `react-i18next`
2. Extract all hardcoded strings into `es.json` and `en.json`
3. Language selector in settings
4. Persist preference in localStorage

**Acceptance:** Full UI renders in Spanish. Switching to English works.

---

### T7.2: Card Name Localization

**Goal:** Display card names in user's preferred language.

**Steps:**
1. `CardName` table stores per-locale names
2. API accepts `locale` param, returns localized name (fallback to English)
3. Search works across all stored locales

**Acceptance:** Spanish card names display where available. Search works in both languages.

---

## Phase 8: Buylist Management

### T8.1: Buylist Rules Engine

**Goal:** Configure what the store will buy and at what price.

**Steps:**
1. Rules: percentage of market price by condition grade
2. Per-game overrides (e.g., buy Pokémon at 70%, MTG at 60%)
3. Card-specific overrides (high-demand staples at higher %)
4. `GET/PUT /api/buylist/rules`

**Acceptance:** Buylist prices auto-calculated from market price × rule.

---

### T8.2: Trade-In Flow

**Goal:** Process customer trade-ins.

**Steps:**
1. Scan/search cards customer is selling
2. Show offered price per card (from buylist rules)
3. Customer confirms
4. Record as purchase transaction (adds to inventory)
5. Generate trade-in receipt with total payout

**Acceptance:** Complete trade-in flow, inventory updated, payout calculated.

---

## Dependency Graph

```
T0.1 ─┐
T0.2 ─┼─ T0.3 ─── T1.1 ─┬─ T1.2 (MTG)
      │                   ├─ T1.3 (Pokémon)
      │                   ├─ T1.4 (FaB)
      │                   ├─ T1.5 (Lorcana)
      │                   └─ T1.6 (Riftbound)
      │
      │            T2.1 ─┐
      │            T2.2 ─┼─ T2.3 ─── T2.4
      │                  │
      │     T1.x done ───┘
      │
      │     T0.3 + T2.4 ─── T3.1 ─── T3.2
      │                              T3.3
      │
      │     T4.1 ─── T4.2 ─── T4.3 ─── T4.4
      │     (needs T1.x for card images)
      │
      │     T3.1 + T6.1 ─── T5.1 ─── T5.2
      │
      │     T1.x ─── T6.1 ─── T6.2
      │
      │     T7.1 (can start anytime after T0.2)
      │     T7.2 (needs T1.x)
      │
      └──── T2.4 + T3.1 ─── T8.1 ─── T8.2
```

---

## Estimated Effort

| Phase | Tasks | Estimate |
|-------|-------|----------|
| 0: Scaffolding | 3 | 1–2 days |
| 1: Card Catalog | 6 | 3–5 days |
| 2: Pricing | 4 | 2–3 days |
| 3: Inventory | 3 | 2–3 days |
| 4: Scanning | 4 | 4–6 days |
| 5: Sales/POS | 2 | 2–3 days |
| 6: Search | 2 | 1–2 days |
| 7: i18n | 2 | 1 day |
| 8: Buylist | 2 | 2 days |
| **Total** | **28** | **~18–27 days** |
