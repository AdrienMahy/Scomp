# � Scomp Frontend - React 19 + Vite + Tailwind CSS

**Complete redesign from scratch** - 3-page sports data analytics & scraping management dashboard.

## 🚀 Quick Start

### macOS with Docker Desktop

```bash
# Open the frontend
open http://localhost:3002
```

### Linux/Windows with Docker

```bash
# Frontend runs on port 3002
curl http://localhost:3002
```

## 📱 Pages

### 1️⃣ Scraping Management (`/scraping`)
- **Purpose:** Control data scraping pipeline
- **Features:**
  - Select multiple rounds (J1-J34) with checkboxes
  - Launch scrapes: Schedule, Weekly, Custom
  - Real-time event count tracking per game
  - Status badges (Pending, Running, Completed, Failed)
  - Fetches from `GET /games/stats/events-by-game`

### 2️⃣ Game List & Reports (`/games`)
- **Purpose:** Browse matches with filtering
- **Features:**
  - Filter by Round OR Team (toggle mode)
  - Game list with score, status, output files
  - Match reports with detailed statistics
  - Fetches from `GET /games` with query filters

### 3️⃣ Analytics Dashboard (`/analytics`)
- **Purpose:** Season statistics and trends
- **Features:**
  - Player stats (goals, assists, rating)
  - Team standings (W/D/L, points, goal diff)
  - Toggle between player/team views
  - Mock data (ready for API integration)

---

## 🎨 Design System

### Colors
- **Dark:** `#222f38` (primary bg), `#3a4a58` (cards)
- **Light:** `#ffffff` (bg), `#f8f8f8` (cards)
- **Primary:** `#10B981` (green - actions)
- **Accent:** `#EC3432` (red - alerts), `#ceab5d` (gold)
- **Text:** `#41505a` (dark), `#73828e` (secondary)

### Components
- `Card` - Container with border + dark mode
- `Button` - Primary/Secondary/Danger variants
- `Badge` - Success/Error/Warning styles
- `Input`, `Select` - Form controls
- `Loading` - Spinner animation
- `ErrorAlert`, `SuccessAlert` - Status messages

---

## 🔧 Development

### Environment Variables

The frontend uses the relative `/api` path. In production, Nginx proxies this path to the internal API service.

### Local Development

```bash
cd frontend

# Install dependencies
npm install

# Development server (hot reload)
npm run dev
# Runs on http://localhost:5173

# Production build
npm run build
# Generates dist/

# Preview production build
npm run preview
```

### Dark/Light Mode

- Toggle via navbar button (emoji)
- Persists to `localStorage` key: `theme`
- Applied via `<html class="dark">` attribute
- Tailwind v3 respects `dark:` prefix

---

## 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19, Vite 5.4 |
| **Styling** | Tailwind CSS v3, PostCSS |
| **HTTP Client** | Axios |
| **Build** | Node.js 20-alpine (Docker) |
| **Server** | Nginx Alpine (Docker) |
| **Port** | 3002 (macOS: use `docker.for.mac.localhost`) |

---

## 🔗 API Integration

All pages connect to FastAPI backend on port 8001:

- `GET /games/rounds` - Available rounds
- `GET /games/stats/events-by-game` - Event counts per game
- `GET /games` - Game list with filters
- `POST /scraping/start` - Launch scraping task
- `GET /tasks/{id}` - Task status

**API Base URL:** Relative `/api` path, proxied by Nginx.

---

## 🐳 Docker Deployment

### Build

```bash
docker-compose build frontend
```

Dockerfile uses **multi-stage build**:
1. **Stage 1 (builder):** Node 20-alpine → compiles React with Vite
2. **Stage 2 (runtime):** Nginx Alpine → serves dist/ folder

### Run

```bash
docker-compose up -d frontend

# Check logs
docker logs scomp_frontend

# Health check
docker exec scomp_frontend wget --quiet --tries=1 --spider http://localhost:3002/
```

---

## ⚙️ Nginx Configuration

**File:** `nginx.conf`

- **Listen:** Port 3002
- **Root:** `/usr/share/nginx/html` (dist/ copied here)
- **Cache:** 1 year for assets (`.js`, `.css`, images)
- **SPA Routing:** All non-file routes → `index.html`
- **API Proxy:** `/api/*` → `http://api:8001/`

---

## 🐛 Troubleshooting

### "Cannot connect to localhost:3002"

**Issue:** macOS Docker Desktop limitation
**Solution:** Use `docker.for.mac.localhost:3002` instead
**Why:** Docker Desktop on macOS uses a VM with special DNS routing

### Build fails with "dark:text-primary-400 class doesn't exist"

**Issue:** Tailwind v4 vs v3 color config mismatch
**Solution:** Ensure `tailwindcss@3` is installed (not v4)
```bash
npm list tailwindcss
# Should show: tailwindcss@3.4.x
```

### Frontend shows blank page

**Cause 1:** Build failed (check `npm run build`)
**Cause 2:** dist/ not in Docker image (rebuild)
**Cause 3:** Nginx not serving index.html (check nginx.conf)

---

## 📚 Files

| File | Purpose |
|------|---------|
| `src/App.jsx` | Root component, routing, theme management |
| `src/components/Navbar.jsx` | Navigation tabs + dark/light toggle |
| `src/components/index.jsx` | Reusable UI component library |
| `src/pages/*.jsx` | Page components (Scraping, Games, Analytics) |
| `src/index.css` | Tailwind directives + custom utilities |
| `tailwind.config.js` | Extended color palette |
| `postcss.config.js` | Tailwind + Autoprefixer config |
| `vite.config.js` | Vite build config + React plugin |
| `nginx.conf` | Nginx server configuration |
| `Dockerfile` | Multi-stage Docker build |
| `.env` | Environment variables (API URL) |

---

## 🎯 Next Steps

- [ ] Connect Analytics page to real API endpoints
- [ ] Add player performance detail views
- [ ] Implement real-time score updates (WebSocket)
- [ ] Add match video player
- [ ] Export reports (PDF/CSV)
- [ ] Mobile responsive design refinements
- [ ] Add search functionality
- [ ] Implement data pagination

---

**Version:** 1.0.0  
**Last Updated:** 2026-09-04  
**Status:** ✅ Production-Ready

L'app sera disponible sur `http://localhost:3000`

### Build Production
```bash
npm run build
npm run preview
```

## 📁 Structure du Projet

```
frontend/
├── src/
│   ├── App.jsx                    # Composant principal
│   ├── App.css
│   ├── main.jsx                   # Entry point
│   ├── index.css                  # Styles globaux
│   ├── pages/
│   │   ├── GamesList.jsx          # Liste des jeux
│   │   └── GameDetail.jsx         # Détail d'un jeu
│   └── styles/
│       ├── GamesList.css
│       └── GameDetail.css
├── index.html
├── vite.config.js
├── package.json
└── .gitignore
```

## 🔄 Fonctionnement

### GamesList
- Affiche tous les jeux de la DB
- Click sur une carte → ouvre les détails
- Affiche le score et le nombre de fichiers

### GameDetail
- Affiche tous les détails du jeu
- Liste les fichiers de sortie (XML, JSON)
- Filtre par type de fichier
- Affiche les URLs S3 complètes
- Indique les statuts (disponible, obsolète, version)

## 🔌 API Backend

L'app consomme ces endpoints :

- `GET /games` - Liste tous les jeux
- `GET /games/{game_id}` - Détail d'un jeu

## 🎨 Style

- Gradient violet/bleu
- Design responsive
- Cartes interactives
- Dark theme header

## 📝 Notes

- Frontend lit-only (pas de POST/scrape)
- CORS proxy configuré dans vite.config.js
- Backend doit être accessible sur `http://localhost:8001`

## 🔗 Dépendances

- **React** - UI library
- **Axios** - HTTP client
- **Vite** - Build tool
