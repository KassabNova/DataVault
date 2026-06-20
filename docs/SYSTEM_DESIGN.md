# TCG Store Management System — System Design

## Database Schema

### Entity Relationship Diagram

```
┌─────────┐       ┌──────────┐       ┌─────────────┐
│  Game   │1────N│  CardSet  │1────N│    Card      │
└─────────┘       └──────────┘       └──────┬──────┘
                                             │1
                         ┌───────────────────┼───────────────────┐
                         │N                  │N                   │N
                  ┌──────┴──────┐    ┌───────┴───────┐   ┌───────┴───────┐
                  │  CardName   │    │ InventoryItem │   │  PriceRecord  │
                  │  (i18n)     │    └───────┬───────┘   └───────────────┘
                  └─────────────┘            │N
                                     ┌───────┴───────┐
                                     │   SaleItem    │
                                     └───────┬───────┘
                                             │N
                                      ┌──────┴──────┐
                                      │    Sale     │
                                      └─────────────┘
```

### Table Definitions

```sql
-- Supported games
CREATE TABLE game (
    id          TEXT PRIMARY KEY,  -- 'mtg', 'pokemon', 'lorcana', 'fab', 'riftbound'
    name        TEXT NOT NULL,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Sets/expansions
CREATE TABLE card_set (
    id          TEXT PRIMARY KEY,  -- game_id + set_code, e.g. 'mtg:mh3'
    game_id     TEXT NOT NULL REFERENCES game(id),
    code        TEXT NOT NULL,     -- 'mh3', 'sv6', etc.
    name        TEXT NOT NULL,
    released_at TEXT,
    card_count  INTEGER,
    icon_url    TEXT,
    UNIQUE(game_id, code)
);

-- Unified card catalog
CREATE TABLE card (
    id              TEXT PRIMARY KEY,  -- game_id + set_code + collector_number
    game_id         TEXT NOT NULL REFERENCES game(id),
    set_id          TEXT NOT NULL REFERENCES card_set(id),
    collector_number TEXT NOT NULL,
    name_en         TEXT NOT NULL,     -- English canonical name
    rarity          TEXT,              -- 'common','uncommon','rare','mythic', etc.
    card_type       TEXT,              -- 'creature','spell','pokemon','hero', etc.
    subtypes        TEXT,              -- JSON array
    colors          TEXT,              -- JSON array (MTG), or type/element for others
    mana_cost       TEXT,              -- MTG specific, NULL for other games
    image_url_small TEXT,
    image_url_normal TEXT,
    image_url_large TEXT,
    external_ids    TEXT,              -- JSON: {"scryfall": "...", "cardmarket": "...", "tcgplayer": "..."}
    metadata        TEXT,              -- JSON: game-specific extra fields
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(game_id, set_id, collector_number)
);

-- Multilingual card names
CREATE TABLE card_name (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT NOT NULL REFERENCES card(id),
    locale  TEXT NOT NULL,          -- 'en', 'es', 'pt', 'ja', etc.
    name    TEXT NOT NULL,
    UNIQUE(card_id, locale)
);

-- Full-text search (FTS5)
CREATE VIRTUAL TABLE card_search USING fts5(
    card_id,
    name,
    locale,
    content=card_name,
    tokenize='unicode61'
);

-- Perceptual hash index for scanning
CREATE TABLE card_hash (
    card_id TEXT PRIMARY KEY REFERENCES card(id),
    phash   INTEGER NOT NULL       -- 64-bit perceptual hash stored as integer
);

-- CNN embeddings (optional, for fallback recognition)
CREATE TABLE card_embedding (
    card_id   TEXT PRIMARY KEY REFERENCES card(id),
    embedding BLOB NOT NULL        -- 512 × float32 = 2048 bytes per card
);

-- Store inventory
CREATE TABLE inventory_item (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id        TEXT NOT NULL REFERENCES card(id),
    quantity       INTEGER NOT NULL DEFAULT 1,
    condition      TEXT NOT NULL DEFAULT 'NM',  -- NM, LP, MP, HP, DMG
    language       TEXT NOT NULL DEFAULT 'en',
    is_foil        INTEGER NOT NULL DEFAULT 0,
    purchase_price REAL,            -- what we paid (MXN)
    listed_price   REAL,            -- what we're selling for (MXN)
    notes          TEXT,
    added_at       TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now')),
    UNIQUE(card_id, condition, language, is_foil)
);

-- Price history
CREATE TABLE price_record (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id    TEXT NOT NULL REFERENCES card(id),
    source     TEXT NOT NULL,       -- 'cardmarket', 'scryfall', 'tcgplayer'
    currency   TEXT NOT NULL,       -- 'EUR', 'USD', 'MXN'
    price_low  REAL,
    price_mid  REAL,
    price_high REAL,
    price_market REAL,              -- trend/average
    fetched_at TEXT DEFAULT (datetime('now'))
);

-- Store pricing rules
CREATE TABLE pricing_rule (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     TEXT REFERENCES game(id),  -- NULL = applies to all games
    rarity      TEXT,                       -- NULL = applies to all rarities
    card_id     TEXT REFERENCES card(id),   -- NULL = not card-specific
    sell_multiplier REAL NOT NULL DEFAULT 1.0,
    buy_multiplier  REAL NOT NULL DEFAULT 0.6,
    priority    INTEGER NOT NULL DEFAULT 0  -- higher = more specific
);

-- Sales
CREATE TABLE sale (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subtotal       REAL NOT NULL,
    discount       REAL DEFAULT 0,
    tax            REAL DEFAULT 0,
    total          REAL NOT NULL,
    payment_method TEXT NOT NULL,    -- 'cash', 'card', 'transfer'
    notes          TEXT,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE sale_item (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id          INTEGER NOT NULL REFERENCES sale(id),
    inventory_item_id INTEGER NOT NULL REFERENCES inventory_item(id),
    quantity         INTEGER NOT NULL DEFAULT 1,
    unit_price       REAL NOT NULL,
    condition        TEXT NOT NULL
);

-- Scan sessions
CREATE TABLE scan_session (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT DEFAULT (datetime('now')),
    ended_at    TEXT,
    cards_scanned INTEGER DEFAULT 0,
    cards_added   INTEGER DEFAULT 0
);

-- Buylist / trade-in transactions
CREATE TABLE trade_in (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    total_payout REAL NOT NULL,
    payment_method TEXT NOT NULL,
    notes        TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE trade_in_item (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_in_id INTEGER NOT NULL REFERENCES trade_in(id),
    card_id     TEXT NOT NULL REFERENCES card(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    condition   TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'en',
    is_foil     INTEGER NOT NULL DEFAULT 0,
    offered_price REAL NOT NULL    -- price paid to customer
);

-- Indexes
CREATE INDEX idx_card_game ON card(game_id);
CREATE INDEX idx_card_set ON card(set_id);
CREATE INDEX idx_inventory_card ON inventory_item(card_id);
CREATE INDEX idx_price_card ON price_record(card_id, fetched_at);
CREATE INDEX idx_sale_date ON sale(created_at);
CREATE INDEX idx_card_hash ON card_hash(phash);
```

---

## API Design

### Base URL: `/api/v1`

### Authentication

Phase 1: None (local network only, single-store).
Phase 2+: JWT-based auth with roles (owner, staff).

### Endpoints

#### Cards / Catalog

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cards` | List cards (paginated, filterable) |
| GET | `/cards/{id}` | Card detail with all printings |
| GET | `/cards/search?q=&game=&locale=` | Full-text search |
| POST | `/cards/manual` | Add card manually (for games without API) |
| POST | `/cards/import` | Bulk import from CSV |

**Query params for GET /cards:**
- `game` — filter by game_id
- `set` — filter by set_id
- `rarity` — filter by rarity
- `locale` — preferred language for names (default: `es`)
- `page`, `per_page` — pagination (default: 1, 50)

**Response:**
```json
{
  "items": [
    {
      "id": "mtg:mh3:42",
      "game_id": "mtg",
      "name": "Relámpago / Lightning Bolt",
      "set": {"code": "mh3", "name": "Modern Horizons 3"},
      "rarity": "uncommon",
      "image_url": "https://cards.scryfall.io/small/...",
      "price": {"market": 45.00, "currency": "MXN"},
      "inventory": {"quantity": 3, "conditions": ["NM", "LP"]}
    }
  ],
  "total": 1234,
  "page": 1,
  "per_page": 50
}
```

#### Inventory

| Method | Path | Description |
|--------|------|-------------|
| GET | `/inventory` | List inventory (filterable) |
| GET | `/inventory/{id}` | Single item |
| POST | `/inventory` | Add item |
| PATCH | `/inventory/{id}` | Update quantity/condition/price |
| DELETE | `/inventory/{id}` | Remove item |
| POST | `/inventory/import` | CSV bulk import |
| GET | `/inventory/export` | Export to CSV |
| GET | `/inventory/valuation` | Total inventory value report |

**POST /inventory body:**
```json
{
  "card_id": "mtg:mh3:42",
  "quantity": 4,
  "condition": "NM",
  "language": "en",
  "is_foil": false,
  "purchase_price": 35.00
}
```

#### Scanning

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scan/match` | Upload image, get top-N matches |
| POST | `/scan/sessions` | Start scan session |
| PATCH | `/scan/sessions/{id}` | End session |
| GET | `/scan/sessions/{id}` | Session details |

**POST /scan/match:**
- Content-Type: `multipart/form-data`
- Body: `image` (JPEG blob)
- Response:
```json
{
  "matches": [
    {"card_id": "mtg:mh3:42", "confidence": 0.97, "name": "Lightning Bolt", "image_url": "..."},
    {"card_id": "mtg:2ed:42", "confidence": 0.82, "name": "Lightning Bolt", "image_url": "..."}
  ],
  "method": "phash",
  "processing_ms": 87
}
```

#### Pricing

| Method | Path | Description |
|--------|------|-------------|
| GET | `/prices/{card_id}` | Current prices from all sources |
| GET | `/prices/{card_id}/history` | Price history (chart data) |
| GET | `/prices/sync-status` | Last sync info |
| POST | `/prices/sync` | Trigger manual sync |
| GET | `/pricing/rules` | List pricing rules |
| PUT | `/pricing/rules` | Update rules |

#### Sales

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sales` | Create sale |
| GET | `/sales` | List sales (date range filter) |
| GET | `/sales/{id}` | Sale detail |
| GET | `/sales/reports/daily?date=` | Daily report |
| GET | `/sales/reports/range?from=&to=` | Range report |

**POST /sales body:**
```json
{
  "items": [
    {"inventory_item_id": 123, "quantity": 1, "unit_price": 45.00}
  ],
  "discount": 5.00,
  "payment_method": "cash",
  "notes": "Regular customer"
}
```

#### Buylist / Trade-ins

| Method | Path | Description |
|--------|------|-------------|
| GET | `/buylist/rules` | Current buylist rules |
| PUT | `/buylist/rules` | Update rules |
| GET | `/buylist/quote` | Get buy price for a card |
| POST | `/trade-ins` | Record trade-in |
| GET | `/trade-ins` | List trade-ins |

#### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/games` | List supported games |
| PATCH | `/games/{id}` | Enable/disable a game |
| GET | `/settings` | App settings |
| PUT | `/settings` | Update settings |
| POST | `/sync/cards` | Trigger card catalog sync |
| GET | `/sync/status` | Sync status for all adapters |

---

## Component Architecture

### Backend Components

```
app/
├── main.py                  # FastAPI app, middleware, startup events
├── config.py                # Settings: DB path, sync schedule, currency, locale
├── database.py              # SQLite engine, session factory, WAL mode
│
├── models/                  # SQLAlchemy ORM models
│   ├── game.py
│   ├── card.py
│   ├── inventory.py
│   ├── price.py
│   ├── sale.py
│   └── trade_in.py
│
├── schemas/                 # Pydantic schemas (request/response validation)
│   ├── card.py
│   ├── inventory.py
│   ├── price.py
│   ├── sale.py
│   └── scan.py
│
├── routers/                 # API route handlers
│   ├── cards.py
│   ├── inventory.py
│   ├── prices.py
│   ├── sales.py
│   ├── scan.py
│   ├── buylist.py
│   └── system.py
│
├── services/                # Business logic layer
│   ├── card_service.py      # Catalog operations
│   ├── inventory_service.py
│   ├── pricing/
│   │   ├── engine.py        # Apply rules, calculate store prices
│   │   ├── rules.py         # Rule CRUD
│   │   └── currency.py      # MXN/USD conversion
│   ├── sales_service.py
│   ├── scanner/
│   │   ├── detector.py      # Card isolation from frame (OpenCV)
│   │   ├── hasher.py        # pHash computation
│   │   ├── matcher.py       # Hash lookup + CNN fallback
│   │   └── session.py       # Scan session management
│   └── search_service.py    # FTS5 queries
│
├── adapters/                # External API integrations (one per game)
│   ├── base.py              # Abstract interface
│   ├── registry.py          # Dynamic adapter loading
│   ├── mtg.py               # Scryfall
│   ├── pokemon.py           # pokemontcg.io
│   ├── fab.py               # FaBDB / GitHub
│   ├── lorcana.py           # LorcanaJSON
│   └── riftbound.py         # Manual/stub
│
├── workers/                 # Background tasks
│   ├── price_sync.py        # Scheduled price updates
│   ├── card_sync.py         # Catalog sync orchestrator
│   └── hash_builder.py      # pHash/embedding computation
│
└── i18n/                    # Backend locale support
    ├── es.py
    └── en.py
```

### Frontend Components

```
src/
├── App.tsx                  # Root layout + routing
├── pages/
│   ├── Dashboard.tsx        # Overview: stock value, recent sales, alerts
│   ├── Inventory.tsx        # Inventory management
│   ├── Scanner.tsx          # Webcam scanning mode
│   ├── Sales.tsx            # POS / checkout
│   ├── Buylist.tsx          # Trade-in flow
│   ├── Catalog.tsx          # Browse all cards
│   ├── CardDetail.tsx       # Single card view
│   ├── Reports.tsx          # Sales/inventory reports
│   └── Settings.tsx         # Configuration
│
├── components/
│   ├── CardGrid.tsx         # Card image grid with lazy loading
│   ├── CardRow.tsx          # Table row for list view
│   ├── FilterPanel.tsx      # Sidebar filters
│   ├── SearchBar.tsx        # Instant search with debounce
│   ├── WebcamFeed.tsx       # Camera + capture logic
│   ├── ScanResult.tsx       # Match confirmation dialog
│   ├── CartSidebar.tsx      # POS cart
│   ├── PriceDisplay.tsx     # Price with currency
│   └── ConditionBadge.tsx   # NM/LP/MP/HP/DMG visual badge
│
├── services/
│   ├── api.ts               # Axios instance + interceptors
│   ├── cards.ts             # Card API calls
│   ├── inventory.ts         # Inventory API calls
│   ├── sales.ts             # Sales API calls
│   └── scan.ts              # Scanner API calls
│
├── hooks/
│   ├── useWebcam.ts         # Webcam access + frame capture
│   ├── useSearch.ts         # Debounced search with results
│   ├── useInventory.ts      # Inventory state management
│   └── useCart.ts           # Shopping cart state
│
├── i18n/
│   ├── index.ts             # i18next configuration
│   ├── es.json              # Spanish strings
│   └── en.json              # English strings
│
└── types/
    ├── card.ts
    ├── inventory.ts
    ├── sale.ts
    └── scan.ts
```

---

## Data Flow Diagrams

### Card Scanning Flow

```
[Webcam] → capture frame
    ↓
[Card Detector] → OpenCV contour detection → crop + perspective transform
    ↓
[pHash Compute] → 64-bit DCT hash
    ↓
[Hash Matcher] → BK-tree nearest neighbor (Hamming distance)
    ↓
[Confidence > 0.90?]
    ├── YES → return top match
    └── NO → [CNN Fallback] → MobileNetV2 embedding → cosine similarity
                  ↓
              return top-N matches
    ↓
[UI] → show match for confirmation → user confirms → add to inventory
```

### Price Sync Flow

```
[Scheduler] → trigger every 6 hours
    ↓
[Price Sync Worker] → for each enabled game:
    ├── [CardMarket Adapter] → fetch batch prices → store PriceRecord
    ├── [Scryfall Adapter] → MTG prices from bulk data → store PriceRecord
    └── [TCGPlayer Adapter] → fallback prices → store PriceRecord
    ↓
[Pricing Engine] → apply rules → update inventory_item.listed_price
    ↓
[Log] → sync complete: 45,000 prices updated, 3 errors, 4m 23s
```

### Sale Transaction Flow

```
[POS UI] → search/scan cards → add to cart
    ↓
[Cart] → items + quantities + prices
    ↓
[Apply Discount] → percentage or fixed amount
    ↓
[Confirm Sale] → POST /api/sales
    ↓
[Sales Service]:
    1. Validate stock (all items in inventory with sufficient quantity)
    2. Create Sale record
    3. Create SaleItem records
    4. Decrement inventory quantities
    5. Return sale confirmation
    ↓
[UI] → show receipt → option to print
```

---

## Configuration

### `config.yaml` (or environment variables)

```yaml
database:
  path: "./data/store.db"
  wal_mode: true

server:
  host: "0.0.0.0"
  port: 8000

locale:
  default: "es"
  currency: "MXN"
  currency_conversion:
    usd_to_mxn: 17.5   # or "auto" to fetch from API

sync:
  schedule_hours: 6
  on_startup: false

games:
  mtg:
    enabled: true
    adapter: "scryfall"
  pokemon:
    enabled: true
    adapter: "pokemontcgio"
  lorcana:
    enabled: true
    adapter: "lorcanajson"
  fab:
    enabled: true
    adapter: "fabdb"
  riftbound:
    enabled: true
    adapter: "manual"

scanning:
  phash_threshold: 10          # max Hamming distance for confident match
  cnn_fallback: true
  cnn_model_path: "./models/mobilenetv2.onnx"
  confidence_threshold: 0.85

pricing:
  default_sell_multiplier: 1.10
  default_buy_multiplier: 0.60
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Single DB file | SQLite WAL | Simple backups, good enough for single-store load |
| Unified card schema | Game-agnostic with `metadata` JSON | Extensible without schema changes per game |
| Image storage | URLs only, fetch on demand | Saves 12+ GB local storage |
| Hash storage | Integer in SQLite | Fast BK-tree operations, compact |
| Embeddings | BLOB in SQLite | Avoids external vector DB dependency |
| Price history | Append-only | Enables trend charts, no data loss |
| Inventory dedup | UNIQUE(card_id, condition, language, foil) | Same card different conditions are separate rows |
| i18n approach | `card_name` table + UI locale files | Clean separation, searchable across languages |
| Plugin system | Python modules loaded by registry | Add new game = add one .py file |
