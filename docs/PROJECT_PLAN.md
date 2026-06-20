# TCG Store Management System — Project Plan

## Overview

A local-first, multi-TCG store management system for inventory tracking, pricing, sales, and card scanning. Built initially as a desktop web app for in-store use, with a mobile app (Phase 2+) planned for customers and on-the-go scanning.

**Target user:** TCG store owner in Guadalajara, Mexico.
**Primary language:** Spanish (with i18n extensibility).
**Supported TCGs at launch:** Magic: The Gathering, Pokémon TCG, Lorcana, Flesh and Blood, Riftbound.

---

## Architecture

### Phase 1: Desktop Store App

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React + Vite)                                     │
│  • Inventory UI        • POS / Sales                        │
│  • Card Scanner (webcam) • Search & Filters                 │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI, Python 3.12+)                            │
│  • REST API            • Card recognition engine            │
│  • Price sync workers  • Game adapters (plugin system)      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  SQLite Database                                            │
│  • Unified card catalog  • Inventory                        │
│  • Sales records         • Price history                    │
│  • pHash index           • CNN embeddings (optional)        │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2+: Mobile & SaaS

- Flutter mobile app with on-device TFLite scanning
- Backend extracted to a cloud-deployable service (multi-tenant)
- Per-game downloadable add-ons
- Freemium model with Store Edition tier

---

## Technical Decisions

### Backend: FastAPI (Python)

**Why:**
- Fastest Python framework for REST APIs
- Native async support for concurrent price syncing
- Excellent ecosystem for ML (OpenCV, ONNX, Pillow)
- Easy to prototype, easy to maintain solo

**Alternatives considered:**
- Node.js/Express — weaker ML ecosystem, would need Python sidecar anyway
- Go — faster runtime but slower development for a solo project

### Database: SQLite

**Why:**
- Zero-config, single-file, trivial backups (copy the file)
- Handles 100K+ cards and store-level traffic easily
- WAL mode supports concurrent reads during price sync
- Portable — move the DB between machines by copying one file

**Migration path:** If multi-store/SaaS is needed, migrate to PostgreSQL. SQLAlchemy abstracts this.

### Frontend: React + Vite + TypeScript

**Why:**
- Component-based UI ideal for card grids, filters, modals
- Vite for instant dev reloads
- TypeScript catches bugs early in a data-heavy app
- Large ecosystem of camera/barcode libraries

### Card Recognition: Perceptual Hashing + CNN Fallback

**Primary:** pHash (DCT-based perceptual hash) — precomputed for all cards.
- Storage: ~50 MB for all TCGs
- Speed: <100ms lookup
- Accuracy: 90–95%

**Fallback:** MobileNetV2 (ONNX Runtime on CPU) for ambiguous matches.
- Storage: ~14 MB model + ~400 MB embeddings
- Speed: <200ms on Ryzen 7 9700
- Accuracy: 98%+

**Image source:** Webcam via browser MediaDevices API → frame capture → card detection (OpenCV contour) → hash/classify.

### Price Data Sources

| Priority | Source | Coverage |
|----------|--------|----------|
| 1 | CardMarket API | All games, EU/MX pricing, Spanish names |
| 2 | Scryfall | MTG card data + USD prices |
| 3 | pokemontcg.io | Pokémon card data |
| 4 | TCGPlayer API | US pricing fallback |

Price sync runs as a background worker on a configurable schedule (default: every 6 hours).

### Internationalization (i18n)

- Backend serves card names in requested locale (`Accept-Language` header or user preference)
- UI strings stored in JSON locale files (`es.json`, `en.json`)
- Card names: sourced from APIs where available, fallback to English
- Currency: MXN primary, USD secondary (configurable)

### Game Adapter Plugin System

Each TCG is a self-contained adapter module:

```
adapters/
├── base.py          # Abstract adapter interface
├── mtg.py           # Scryfall integration
├── pokemon.py       # pokemontcg.io integration
├── lorcana.py       # LorcanaJSON / Lorcana API
├── fab.py           # FaBDB / GitHub repo
└── riftbound.py     # Manual entry (no API yet)
```

Adding a new game = implement `sync_cards()`, `fetch_price()`, and `search()`.

---

## Feature Breakdown

### F1: Card Catalog & Data Sync

- Download/sync card databases from external APIs
- Normalize into unified schema (game-agnostic)
- Store card images URLs, fetch on demand
- Track set, rarity, collector number, multilingual names

### F2: Inventory Management

- Add cards to inventory (quantity, condition, language, foil status)
- Bulk import via CSV or scan session
- Track purchase price vs. market price
- Low-stock alerts
- Inventory valuation reports

### F3: Card Scanning (Webcam)

- Live webcam feed with card detection overlay
- Capture frame → isolate card → identify
- Show top-N matches for confirmation
- One-click add to inventory after scan
- Batch scanning mode (rapid fire for buylist sessions)

### F4: Pricing Engine

- Scheduled sync from CardMarket/Scryfall/TCGPlayer
- Store price history (track trends)
- Support multiple price points: market, low, mid, high
- Apply store markup rules (e.g., market × 0.85 for buylist, × 1.10 for sell)
- Currency conversion (USD → MXN)

### F5: Sales / POS

- Create sale transactions (multiple cards per sale)
- Apply discounts (percentage or fixed)
- Daily/weekly/monthly sales reports
- Cash drawer tracking
- Receipt generation (thermal printer support optional)

### F6: Search & Browse

- Full-text search across all games
- Filter by: game, set, color/type, rarity, price range, stock status
- Sort by: name, price, quantity, date added
- Card detail view with image, prices, inventory history

### F7: Buylist Management

- Define buylist rules (percentage of market price by condition)
- Customer-facing buylist view
- Track trade-ins as purchase transactions
- Auto-suggest prices during trade-in based on current market

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Scan-to-result latency | < 500ms |
| Price sync (full catalog) | < 30 min |
| Startup time | < 3s |
| Database size (all games) | < 500 MB |
| Offline operation | Full functionality except price sync |
| Concurrent users | 1–3 (store staff) |
| Backup | Single file copy (SQLite) |

---

## Deployment

### Development
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

### Production (store machine)
- Backend: systemd service running uvicorn
- Frontend: static build served by backend (or nginx)
- Auto-start on boot
- Nightly SQLite backup to external drive / cloud

---

## Future Considerations (Phase 2+)

- Flutter mobile app with TFLite on-device scanning
- Multi-store support (cloud backend, PostgreSQL)
- Customer-facing price lookup kiosk
- Online storefront integration
- Tournament management module
- Marketplace listing sync (CardMarket seller tools)
