## 🎮 POST /games/scrape - Complete Walkthrough

### ✨ What It Does

The `POST /games/scrape` endpoint orchestrates a complete end-to-end scraping flow:

```
User Request (HTTP POST)
    ↓
FastAPI Route validates input
    ↓
ScraperCoordinator orchestrates flow
    ↓
SportsDynamicsProvider validates & prepares filters
    ↓
SportsDynamicsClient queries GraphQL API
    ↓
Raw API response → Transform to ORM models
    ↓
Persist to PostgreSQL
    ↓
Return JSON response to client
```

---

### 🚀 Quick Start

**1. Start the FastAPI server:**

```bash
cd backend
python -m uvicorn src.main:app --reload
```

Server runs on `http://localhost:8000`

**2. Test the endpoint:**

```bash
# Simple scrape (just competition_id)
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": "comp-ligue1-2024",
    "limit": 10
  }'

# Scrape with filters
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": "comp-ligue1-2024",
    "season_id": "season-2024-2025",
    "round_names": ["Round 1", "Round 2"],
    "limit": 50
  }'
```

**3. Run automated tests:**

```bash
cd tests
python test_scrape_endpoint.py
```

---

### 📋 Request Schema

```json
{
  "competition_id": "string (required)",
  "season_id": "string (optional)",
  "round_names": ["array of strings (optional)"],
  "limit": "integer (default: 100)",
  "page": "integer (default: 1)"
}
```

**Example:**

```json
{
  "competition_id": "comp-ligue1-2024",
  "season_id": "season-2024-2025",
  "round_names": ["Round 1", "Round 2", "Round 3"],
  "limit": 50,
  "page": 1
}
```

---

### 📤 Response Schema

```json
{
  "status": "success",
  "count": 42,
  "games": [
    {
      "id": "game-12345",
      "name": "PSG vs Lyon",
      "result": "HOME_WIN",
      "home_score": 3,
      "away_score": 1,
      "starts_at": "2024-08-10T20:00:00",
      "played_at": "2024-08-10T22:15:00",
      "round_name": "Round 1",
      "home_team_id": "team-123",
      "away_team_id": "team-456",
      "home_team_formation": "4-3-3",
      "away_team_formation": "4-2-3-1",
      "created_at": "2024-08-12T10:30:00",
      "updated_at": "2024-08-12T10:30:00"
    },
    ...
  ],
  "message": "Successfully scraped 42 games"
}
```

---

### 🔍 Complete Flow Breakdown

#### 1️⃣ **Request Validation** (FastAPI Route)
- Validates JSON schema
- Checks required fields
- Returns 400 if invalid

#### 2️⃣ **Filter Building** (ScraperCoordinator)
```python
filters = {
    "available": True,  # Always filter for available games
    "competition_id": "comp-ligue1-2024",
    "season_id": "season-2024-2025",
    "round": ["Round 1", "Round 2"]
}
```

#### 3️⃣ **Filter Transformation** (SportsDynamicsProvider)
Uses `QueryFilterConfig` to transform simple values to GraphQL payload:

```python
# Input (simple)
{
  "competition_id": "comp-123",
  "round": ["Round 1", "Round 2"]
}

# Output (GraphQL)
{
  "available": {"equals": True},
  "competition": {"id": {"equals": "comp-123"}},
  "round": {"name": {"in": ["Round 1", "Round 2"]}}
}
```

#### 4️⃣ **API Call** (SportsDynamicsClient)
Sends GraphQL query to SportsDynamics:

```graphql
query getGames($filters: [GameFilter!], $pagination: PaginationInput) {
  getGames(filters: $filters, pagination: $pagination) {
    items {
      id
      name
      result
      startsAt
      homeScore
      awayScore
      homeTeamFormation
      awayTeamFormation
      homeTeam { id brand }
      awayTeam { id brand }
      round { name }
      ...
    }
  }
}
```

#### 5️⃣ **Transform & Persist** (ScraperCoordinator)

**Transform raw API data:**
```python
raw_game = {
  "id": "game-123",
  "name": "PSG vs Lyon",
  "startsAt": "2024-08-10T20:00:00Z",
  ...
}

# → ORM Model
game = Game(
  id="game-123",
  competition_id="comp-ligue1-2024",
  season_id="season-2024-2025",
  name="PSG vs Lyon",
  starts_at=datetime(...),
  ...
)
```

**Persist to PostgreSQL:**
- Upsert logic: if game exists (by ID), update it; otherwise, create new
- Automatically manages created_at/updated_at timestamps
- Stores raw API response in JSON column for reference

#### 6️⃣ **Return Response**
Transforms ORM models back to JSON for API response

---

### 🧪 Testing Scenarios

**Scenario 1: Simple Scrape**
```bash
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{"competition_id": "comp-ligue1-2024", "limit": 5}'
```

**Scenario 2: With Season Filter**
```bash
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": "comp-ligue1-2024",
    "season_id": "season-2024-2025",
    "limit": 10
  }'
```

**Scenario 3: With Round/Matchday Filter**
```bash
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": "comp-ligue1-2024",
    "season_id": "season-2024-2025",
    "round_names": ["Round 1", "Round 2", "Round 3"],
    "limit": 15
  }'
```

**Scenario 4: Pagination**
```bash
# Get next page (page 2)
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "competition_id": "comp-ligue1-2024",
    "limit": 50,
    "page": 2
  }'
```

---

### 📊 Database

Games are persisted in PostgreSQL with this schema:

```sql
CREATE TABLE games (
  id VARCHAR(50) PRIMARY KEY,
  competition_id VARCHAR(50) NOT NULL REFERENCES competitions(id),
  season_id VARCHAR(50) NOT NULL REFERENCES seasons(id),
  name VARCHAR(255) NOT NULL,
  result VARCHAR(20),
  home_team_id VARCHAR(50) NOT NULL REFERENCES teams(id),
  away_team_id VARCHAR(50) NOT NULL REFERENCES teams(id),
  home_score INTEGER,
  away_score INTEGER,
  home_team_formation VARCHAR(50),
  away_team_formation VARCHAR(50),
  starts_at TIMESTAMP,
  played_at TIMESTAMP,
  round_name VARCHAR(100),
  raw_data JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes:**
- `competition_id` - for filtering by competition
- `season_id` - for filtering by season
- All foreign key columns for relationship queries

---

### 🔧 Additional Endpoints

**Get Available Filters:**
```bash
curl http://localhost:8000/games/filters
```

Returns all available filters for `get_games` query with types and operators.

**Quick Test:**
```bash
curl http://localhost:8000/games/scrape/test
```

Runs a quick test scrape (5 games) without complex filters.

**List Games from Database:**
```bash
curl http://localhost:8000/games?limit=10&skip=0
```

Returns games already persisted in the database.

---

### ❌ Error Handling

**Invalid Filters (400):**
```bash
curl -X POST http://localhost:8000/games/scrape \
  -H "Content-Type: application/json" \
  -d '{"round_names": ["Invalid"]}'  # Missing competition_id
```

Response:
```json
{
  "detail": "competition_id is required"
}
```

**API Failure (500):**
If SportsDynamics API fails, returns:
```json
{
  "detail": "Scraping failed: [error details]"
}
```

**Database Error (500):**
If database persistence fails, the transaction is rolled back and an error is returned.

---

### 🚀 Architecture Integration

This endpoint is part of the complete Scomp architecture:

```
┌─ WEB LAYER (FastAPI) ─────────────────────┐
│  POST /games/scrape                       │
│  GET /games/filters                       │
└─────────────────┬───────────────────────┘
                  │
┌─ ORCHESTRATION ─┴───────────────────────┐
│  ScraperCoordinator                       │
│  • Coordinates complete flow              │
│  • Handles transform & persist            │
└─────────────────┬───────────────────────┘
                  │
┌─ PROVIDERS ─────┴───────────────────────┐
│  SportsDynamicsProvider                   │
│  • Validates filters                      │
│  • Calls API client                       │
└─────────────────┬───────────────────────┘
                  │
┌─ API CLIENT ────┴───────────────────────┐
│  SportsDynamicsClient                     │
│  • Builds GraphQL query                   │
│  • Makes HTTP request                     │
└─────────────────┬───────────────────────┘
                  │
             SportsDynamics
                 GraphQL API
```

---

### 📝 Logs

Enable debug logging to see the complete flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

You'll see:
- Filter validation steps
- API call details
- Transformation progress
- Database persistence confirmation

---

### 💡 Next Steps

1. ✅ **Verify** the endpoint works with your SportsDynamics credentials
2. ✅ **Test** with different competition/season IDs from your `ID.json`
3. ✅ **Monitor** database to ensure games are being persisted correctly
4. ✅ **Implement** Celery tasks to run scraping in background
5. ✅ **Add** monitoring/alerting for failed scrapes

---

**Questions? Check the logs or review [VISION_GLOBALE.md](../backend/VISION_GLOBALE.md) for complete architecture details.**
