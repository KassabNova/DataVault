# TCG Store Management System

Multi-TCG store inventory, pricing, POS, and card scanning system. Supports Magic: The Gathering, Pokémon, Lorcana, Flesh and Blood, and Riftbound.

## Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite 3.24+ (bundled via pysqlite3-binary)

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate        # bash/zsh
source .venv/bin/activate.fish   # fish

pip install -r requirements.txt
```

### Database

```bash
cd backend
alembic upgrade head
python -m seed
```

### Frontend

```bash
cd frontend
npm install
```

## Running

### Development (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate.fish  # or activate for bash
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:5173

### Sync Card Catalogs

After first startup, populate the card database:

```bash
# Sync all games (run each in sequence, MTG takes ~2 min)
curl -X POST "http://localhost:8000/api/v1/sync/cards?game_id=mtg"
curl -X POST "http://localhost:8000/api/v1/sync/cards?game_id=pokemon"
curl -X POST "http://localhost:8000/api/v1/sync/cards?game_id=lorcana"
curl -X POST "http://localhost:8000/api/v1/sync/cards?game_id=fab"
curl -X POST "http://localhost:8000/api/v1/sync/cards?game_id=riftbound"

# Build search index (after syncs complete)
curl -X POST "http://localhost:8000/api/v1/cards/search/rebuild-index"

# Sync prices
curl -X POST "http://localhost:8000/api/v1/prices/sync"

# Build card scanning hash index (run multiple times for more coverage)
curl -X POST "http://localhost:8000/api/v1/scan/build-index?batch_size=500"
```

## Project Structure

```
tcg-store/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings (env: TCG_*)
│   │   ├── database.py        # SQLite async engine
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Business logic (pricing, search, scanner)
│   │   ├── adapters/          # Game API integrations
│   │   └── workers/           # Background tasks (price sync)
│   ├── alembic/               # DB migrations
│   ├── data/                  # SQLite database file
│   ├── requirements.txt
│   └── seed.py
├── frontend/
│   ├── src/
│   │   ├── pages/             # Dashboard, Inventory, Scanner, Sales, Catalog
│   │   ├── components/        # AddCardModal, LangSwitcher
│   │   ├── services/          # API client
│   │   └── i18n/              # ES/EN locale files
│   └── vite.config.ts
└── docs/                      # Design documents
```

## API Endpoints

| Path | Description |
|------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/dashboard` | Dashboard stats |
| `GET /api/v1/games` | List supported games |
| `POST /api/v1/sync/cards?game_id=` | Trigger card sync |
| `GET /api/v1/cards/search?q=` | Search cards (FTS5) |
| `POST /api/v1/cards/import` | CSV import |
| `GET/POST/PATCH/DELETE /api/v1/inventory` | Inventory CRUD |
| `GET /api/v1/prices/{card_id}` | Card prices (market + store) |
| `POST /api/v1/prices/sync` | Trigger price sync |
| `GET/POST/DELETE /api/v1/pricing/rules` | Store pricing rules |
| `POST /api/v1/sales` | Create sale |
| `GET /api/v1/sales/reports/daily` | Daily sales report |
| `GET /api/v1/buylist/quote/{card_id}` | Buy price quote |
| `POST /api/v1/trade-ins` | Record trade-in |
| `POST /api/v1/scan/match` | Card image matching |
| `POST /api/v1/scan/build-index` | Build pHash index |

## Configuration

Environment variables (prefix `TCG_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `TCG_DATABASE_URL` | `sqlite+aiosqlite:///./data/store.db` | Database path |
| `TCG_DEFAULT_LOCALE` | `es` | Default language |
| `TCG_CURRENCY` | `MXN` | Display currency |
| `TCG_USD_TO_MXN` | `17.5` | Exchange rate |
| `TCG_SYNC_SCHEDULE_HOURS` | `6` | Price sync interval |

## Backup

The entire database is a single file:
```bash
cp backend/data/store.db backup/store-$(date +%Y%m%d).db
```
