# 🎯 Scomp - Architecture Complète et Relations

> **Vue précise des relations entre Interface Web, Base de Données, API FastAPI et Requêtes GraphQL SportsDynamics**

---

## 📊 Diagramme Global de Flux de Données

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                        UTILISATEUR / NAVIGATEUR                             │
│                                                                              │
└─────────────────────────┬──────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────────┐
        │       FRONTEND REACT (React + Vite)         │
        │  http://localhost:3000                      │
        │                                             │
        │  Pages:                                     │
        │  • GamesList.jsx      → List games          │
        │  • GameDetail.jsx     → Game details        │
        │  • TeamsPlayersPage   → Teams & players     │
        │  • ScrapePage         → Trigger scraping    │
        │  • TasksPage          → Task monitoring     │
        └────┬────────────────────────────────────────┘
             │
             │ HTTP Requests (axios)
             │ CORS: Allow-Origin: *
             │
             ▼
  ┌──────────────────────────────────────────────────────┐
  │      FASTAPI BACKEND (Python)                        │
  │      http://localhost:8001                           │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │           ROUTES / ENDPOINTS                    │ │
  │  │                                                 │ │
  │  │  GET    /api/games              → List games  │ │
  │  │  GET    /api/games/rounds       → Get rounds  │ │
  │  │  GET    /api/games/{id}         → Game detail │ │
  │  │  GET    /api/competitions       → Leagues     │ │
  │  │  GET    /api/teams              → All teams   │ │
  │  │  GET    /api/players            → All players │ │
  │  │  GET    /api/tasks              → Tasks list  │ │
  │  │  POST   /api/tasks              → New task    │ │
  │  │  GET    /api/tasks/{id}         → Task status │ │
  │  │  POST   /api/scraping/start     → Start scrap │ │
  │  │                                                 │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │     ORCHESTRATION LAYER                        │ │
  │  │  ScraperCoordinator                            │ │
  │  │  • Fetch from external API                     │ │
  │  │  • Transform data                              │ │
  │  │  • Persist to DB                               │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │     API CLIENTS                                │ │
  │  │  SportsDynamicsClient (main)                   │ │
  │  │  PerformClient                                 │ │
  │  │  SecondSpectrumClient                          │ │
  │  │                                                 │ │
  │  │  ↓ executes GraphQL queries ↓                  │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │    FILTER SYSTEM (GraphQL Builder)             │ │
  │  │  QueryFilterConfig                             │ │
  │  │  • Converts simple values → GraphQL filters    │ │
  │  │  • Handles complex nested structures           │ │
  │  └────────────────────────────────────────────────┘ │
  │                                                      │
  │  ┌────────────────────────────────────────────────┐ │
  │  │     DATABASE LAYER (SQLAlchemy ORM)            │ │
  │  │  • Session management                          │ │
  │  │  • Query execution                             │ │
  │  │  • Transaction handling                        │ │
  │  └────────────────────────────────────────────────┘ │
  └──────┬───────────────────────────────────────────────┘
         │
         │ GraphQL Queries
         │ (POST requests)
         │
         ▼
  ┌────────────────────────────────────────────────────┐
  │   EXTERNAL APIS                                    │
  │                                                    │
  │   SportsDynamics GraphQL API                       │
  │   https://api.sportsdynamics.com/graphql           │
  │   Headers: x-sd-api-key: {API_KEY}                 │
  │                                                    │
  │   Perform API (similar)                            │
  │   SecondSpectrum API (similar)                     │
  └────────────────────────────────────────────────────┘
         │
         │ Returns JSON
         │
         ▼
  ┌────────────────────────────────────────────────────┐
  │   POSTGRESQL DATABASE (PostgreSQL 16)              │
  │   postgres://localhost:5432/scomp                  │
  │                                                    │
  │   Tables:                                          │
  │   • games                  (core data)             │
  │   • teams                  (team info)             │
  │   • players                (player info)           │
  │   • squads / lineups       (game lineups)          │
  │   • competitions           (league info)           │
  │   • seasons                (season data)           │
  │   • game_status            (scrape tracking)       │
  │   • output_files           (API responses)         │
  │   • goals, cards, subs     (match events)          │
  │   • distances              (analytics)             │
  │                                                    │
  │   Views (Analytics):                               │
  │   • v_team_speed_zones_by_interval                 │
  │   • v_player_speed_zones_by_interval               │
  │   • v_team_matches_summary                         │
  └────────────────────────────────────────────────────┘
         ▲
         │ SQL Queries
         │ Persists data
         │
         ├─── Cached back to Frontend


```

---

## 🔄 Flux Détaillé: Exemple Complet

### ✅ Scénario: L'utilisateur clique sur "Charger les matchs de la journée 1"

#### **ÉTAPE 1: Frontend → API**

```javascript
// GamesList.jsx
const response = await axios.get('/api/games?round_name=Round 1&limit=100')
// ↓ HTTP GET request

/*
Request:
  URL: http://localhost:8001/api/games?round_name=Round%201&limit=100
  Method: GET
  Headers: Accept: application/json
*/
```

#### **ÉTAPE 2: FastAPI reçoit et répond**

```python
# backend/src/web/routes/games.py

@router.get("")
def list_games(
    round_name: Optional[str] = None,
    competition_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get games with optional filtering
    """
    query = db.query(Game)
    
    if round_name:
        query = query.filter(Game.round_name == round_name)
    
    games = query.limit(limit).all()
    
    # Convert to Pydantic schemas
    return [game.to_dict() for game in games]
```

#### **ÉTAPE 3: FastAPI interroge la DB**

```sql
-- Query générée par SQLAlchemy
SELECT * FROM games 
WHERE round_name = 'Round 1' 
LIMIT 100;
```

#### **ÉTAPE 4: Frontend reçoit et affiche**

```json
[
  {
    "id": "game-123",
    "name": "Grenoble vs Dunkerque",
    "round_name": "Round 1",
    "competition_name": "Ligue 2",
    "season_name": "2024-2025",
    "home_team": "Grenoble",
    "away_team": "Dunkerque",
    "home_score": 2,
    "away_score": 1,
    "starts_at": "2024-08-09T20:00:00Z",
    "played_at": "2024-08-09T21:45:00Z"
  },
  ...
]
```

---

## 🔄 Flux Détaillé: Scraping avec GraphQL

### ✅ Scénario: L'utilisateur clique sur "Scraper Ligue 2 - Saison 2024-2025"

#### **ÉTAPE 1: Frontend → API (Trigger Scraping)**

```javascript
// ScrapePage.jsx
const response = await axios.post('/api/tasks', {
  provider: 'sportsdynamics',
  competition_id: 'comp-123',
  season_id: '2024'
})
// ↓ Response: { task_id: 'task-456', status: 'pending' }
```

#### **ÉTAPE 2: API crée une tâche Celery**

```python
# backend/src/web/routes/tasks.py

@router.post("")
def create_scraping_task(
    provider: str,
    competition_id: str,
    season_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new scraping task"""
    
    # Create task record
    task = ScrapingTask(
        id=str(uuid.uuid4()),
        provider=provider,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    
    # Enqueue Celery task
    scraping_task.delay(task.id, provider, competition_id, season_id)
    
    return {"task_id": task.id, "status": task.status}
```

#### **ÉTAPE 3: Celery exécute → Orchestration**

```python
# backend/src/tasks/scraping_tasks.py

@celery_app.task
def scraping_task(task_id, provider, competition_id, season_id):
    """Async scraping task"""
    
    coordinator = ScraperCoordinator()
    coordinator.scrape_competition(
        provider=provider,
        competition_id=competition_id,
        season_id=season_id,
        task_id=task_id
    )
```

#### **ÉTAPE 4: Orchestration → API Client + Filter System**

```python
# backend/src/orchestration/scraper_coordinator.py

def scrape_competition(self, provider, competition_id, season_id):
    """
    Main scraping orchestration
    """
    
    if provider == "sportsdynamics":
        client = SportsDynamicsClient()
        
        # Step 1: Build GraphQL payload using filter system
        filter_config = QueryFilterConfig()
        
        filter_values = {
            "competition_id": competition_id,
            "season": season_id
        }
        
        graphql_payload = filter_config.build_payload_from_values(
            "get_games",
            filter_values
        )
        # ↓ Transforms simple values to complex GraphQL filters
        
        # Step 2: Execute GraphQL query
        games_data = client.get_games(
            competition_id=competition_id,
            season_id=season_id
        )
        # ↓ Internal API call with GraphQL
        
        # Step 3: Transform and persist
        self._transform_and_save(games_data)
```

#### **ÉTAPE 5: API Client → GraphQL Query to SportsDynamics**

```python
# backend/src/api/sportsdynamics.py

def get_games(self, competition_id, season_id):
    """Fetch games from SportsDynamics API"""
    
    query = """
    query getGames(
        $filters: [GameFilter!]
        $pagination: PaginationInput
        $sort: [GameSortPaginationInput!]
    ) {
        getGames(filters: $filters, pagination: $pagination, sort: $sort) {
            items {
                id name result startsAt playedAt available
                isUGDAvailable rgdStatus ugdStatus
                round { name }
                homeScore awayScore
                homeTeamFormation awayTeamFormation
                homeTeam { brand id }
                awayTeam { brand id }
                outputFiles(pagination: { limit: 30 }) {
                    items {
                        id fileName fileType version isOutdated
                        file { name size url }
                    }
                }
                squads {
                    teamId players {
                        items {
                            id isStarting isCaptain jerseyNumber
                            player { id firstName lastName }
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {
        "filters": [{
            "competition": {"id": {"equals": competition_id}},
            "season": {"season": {"equals": [int(season_id), int(season_id)+1]}}
        }],
        "pagination": {"limit": 100, "page": 1}
    }
    
    # Execute POST to SportsDynamics
    response = self.query(query, variables)
    # ↓ Returns parsed GraphQL response
    
    return response.get("getGames", {}).get("items", [])
```

#### **ÉTAPE 6: GraphQL Request Structure (to SportsDynamics)**

```json
{
  "query": "query getGames($filters: [GameFilter!]...) { ... }",
  "variables": {
    "filters": [
      {
        "competition": {
          "id": {
            "equals": "comp-123"
          }
        },
        "season": {
          "season": {
            "equals": [2024, 2025]
          }
        }
      }
    ],
    "pagination": {
      "limit": 100,
      "page": 1
    }
  }
}
```

**HTTP Details:**
```
POST https://api.sportsdynamics.com/graphql
Headers:
  x-sd-api-key: {API_KEY}
  Content-Type: application/json
Body: { query, variables }
```

#### **ÉTAPE 7: SportsDynamics Returns Data**

```json
{
  "data": {
    "getGames": {
      "items": [
        {
          "id": "game-123",
          "name": "Grenoble vs Dunkerque",
          "startsAt": "2024-08-09T20:00:00Z",
          "homeTeam": { "id": "team-1", "brand": "Grenoble" },
          "awayTeam": { "id": "team-2", "brand": "Dunkerque" },
          "homeScore": 2,
          "awayScore": 1,
          "squads": [
            {
              "teamId": "team-1",
              "players": {
                "items": [
                  {
                    "id": "player-1",
                    "jerseyNumber": 1,
                    "isStarting": true,
                    "player": { "id": "p-1", "firstName": "John", "lastName": "Doe" }
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  }
}
```

#### **ÉTAPE 8: Transform and Persist to PostgreSQL**

```python
# backend/src/orchestration/scraper_coordinator.py

def _transform_and_save(self, games_data):
    """Transform API data and save to database"""
    
    with get_session() as db:
        for game_data in games_data:
            
            # Create Game ORM object
            game = Game(
                id=game_data["id"],
                name=game_data["name"],
                competition_id=competition_id,
                season_id=season_id,
                home_score=game_data["homeScore"],
                away_score=game_data["awayScore"],
                starts_at=datetime.fromisoformat(game_data["startsAt"]),
                round_name=game_data["round"]["name"]
            )
            
            # Create Team objects (if not exists)
            home_team = Team(
                id=game_data["homeTeam"]["id"],
                name=game_data["homeTeam"]["brand"],
                competition_id=competition_id
            )
            away_team = Team(
                id=game_data["awayTeam"]["id"],
                name=game_data["awayTeam"]["brand"],
                competition_id=competition_id
            )
            
            # Create Player + Lineup objects
            for squad in game_data["squads"]:
                for player_data in squad["players"]["items"]:
                    player = Player(
                        id=player_data["player"]["id"],
                        firstName=player_data["player"]["firstName"],
                        lastName=player_data["player"]["lastName"]
                    )
                    lineup = LineupPlayer(
                        game_id=game.id,
                        team_id=squad["teamId"],
                        player_id=player.id,
                        jerseyNumber=player_data["jerseyNumber"],
                        isStarting=player_data["isStarting"]
                    )
                    db.add(player)
                    db.add(lineup)
            
            db.add(home_team)
            db.add(away_team)
            db.add(game)
        
        db.commit()
```

#### **ÉTAPE 9: Frontend polls task status**

```javascript
// TasksPage.jsx
const checkStatus = async () => {
  const response = await axios.get(`/api/tasks/${taskId}`)
  console.log(response.data)
  // { id: 'task-456', status: 'completed', progress: 100 }
}

// After scraping complete, GamesList auto-refreshes
```

---

## 📌 Endpoints API Complets

### **Competitions**
```
GET    /api/competitions              → List all leagues
GET    /api/competitions/{id}         → League details
```

### **Games**
```
GET    /api/games                     → List games (filtrable)
GET    /api/games/rounds              → Get all available rounds
GET    /api/games/{id}                → Game details + squads + events
GET    /api/games/{id}/export         → Export game as JSON
```

**Query Parameters:**
```
?round_name=Round 1
?competition_id=comp-123
?season_name=2024-2025
?limit=100
?page=1
```

### **Teams**
```
GET    /api/teams                     → List all teams
GET    /api/teams/{id}                → Team details
GET    /api/teams/{id}/players        → Team players
```

### **Players**
```
GET    /api/players                   → List all players
GET    /api/players/{id}              → Player details + stats
GET    /api/players/{id}/distances    → Player distance analytics
```

### **Scraping Tasks**
```
POST   /api/tasks                     → Create new scraping task
GET    /api/tasks                     → List all tasks
GET    /api/tasks/{id}                → Task details + progress
GET    /api/tasks/{id}/logs           → Task execution logs
```

**POST body:**
```json
{
  "provider": "sportsdynamics",
  "competition_id": "comp-123",
  "season_id": "2024"
}
```

---

## 🗄️ Database Schema (Simplified View)

```
games (Primary entity)
├─ id (UUID)
├─ name (VARCHAR)
├─ competition_id → competitions
├─ season_id → seasons
├─ home_team_id → teams
├─ away_team_id → teams
├─ home_score (INT)
├─ away_score (INT)
├─ starts_at (TIMESTAMP)
├─ played_at (TIMESTAMP)
└─ round_name (VARCHAR)

teams
├─ id (UUID)
├─ name (VARCHAR)
├─ brand (VARCHAR)
├─ competition_id → competitions
└─ country (VARCHAR)

players
├─ id (UUID)
├─ firstName (VARCHAR)
├─ lastName (VARCHAR)
├─ position (VARCHAR)

lineup_players (Association)
├─ id (UUID)
├─ game_id → games
├─ team_id → teams
├─ player_id → players
├─ jerseyNumber (INT)
├─ isStarting (BOOL)

competitions
├─ id (UUID)
├─ name (VARCHAR)
├─ region (VARCHAR)

seasons
├─ id (UUID)
├─ competition_id → competitions
├─ season (VARCHAR) e.g., "2024"

game_status (Change tracking)
├─ game_id → games
├─ available (BOOL)
├─ output_files (JSONB)
├─ output_files_hash (VARCHAR) [hash-based detection]
└─ last_checked_at (TIMESTAMP)

output_files (Raw API responses)
├─ id (UUID)
├─ game_id → games
├─ fileName (VARCHAR)
├─ fileType (VARCHAR)
├─ file_url (TEXT)

game_goals (Match events)
├─ id (UUID)
├─ game_id → games
├─ player_id → players
├─ team_id → teams
├─ timestamp (FLOAT)
└─ goal_type (VARCHAR) [own, penalty, etc.]

game_cards (Match events)
├─ id (UUID)
├─ game_id → games
├─ player_id → players
├─ team_id → teams
├─ card_type (VARCHAR) [yellow, red]
└─ timestamp (FLOAT)

Distance Analytics Tables
├─ team_distance_covered
├─ player_distance_covered
├─ team_distance_breakdown
├─ player_distance_breakdown
```

---

## 🔄 Filter System Deep Dive

### **Problem It Solves**

SportsDynamics API requires **complex GraphQL filters**. We want simple Python values.

### **Solution: QueryFilterConfig**

```python
# backend/src/config/filter_config.py

class QueryFilterConfig:
    """Transforms simple values → complex GraphQL payloads"""
    
    def build_payload_from_values(self, query_name, values):
        """
        Example:
            Input:  { "round": ["Round 1", "Round 2"] }
            Output: { "round": { "name": { "in": ["Round 1", "Round 2"] } } }
        """
```

### **Configuration Files**

**`graphql_filters.json`** - Defines query structures:
```json
{
  "queries": {
    "get_games": {
      "filters": {
        "available_filters": ["competition", "season", "round", "available"]
      },
      "example_filters": { ... },
      "pagination": { "limit": 100 }
    }
  }
}
```

**`predefined_filters.json`** - Defines field mappings:
```json
{
  "queries": {
    "get_games": {
      "filters": {
        "round": {
          "path": ["round", "name"],
          "operator": "in"
        },
        "competition_id": {
          "path": ["competition", "id"],
          "operator": "equals"
        }
      }
    }
  }
}
```

### **Example Transformation**

```python
# Simple input
filter_values = {
    "round": ["Round 1", "Round 2"],
    "competition_id": "comp-123",
    "available": True
}

# Transformation
payload = config.build_payload_from_values("get_games", filter_values)

# Complex output (GraphQL-ready)
{
    "round": { "name": { "in": ["Round 1", "Round 2"] } },
    "competition": { "id": { "equals": "comp-123" } },
    "available": { "equals": True }
}
```

---

## 🎨 Frontend Structure

```
frontend/src/
├─ App.jsx                      # Main router
│
├─ pages/
│  ├─ GamesList.jsx             # Displays games by round
│  │  └─ Calls: GET /api/games/rounds
│  │            GET /api/games?round_name=...
│  │
│  ├─ GameDetail.jsx            # Single game + squads
│  │  └─ Calls: GET /api/games/{id}
│  │
│  ├─ TeamsPlayersPage.jsx       # Teams & player listing
│  │  └─ Calls: GET /api/teams
│  │            GET /api/players
│  │
│  ├─ ScrapePage.jsx             # Trigger scraping
│  │  └─ Calls: POST /api/tasks (with provider + competition_id)
│  │
│  └─ TasksPage.jsx              # Monitor scraping jobs
│     └─ Calls: GET /api/tasks
│               GET /api/tasks/{id}
│
├─ components/                  # Reusable components
│
└─ styles/                      # CSS files
```

**Communication Pattern:**
```javascript
import axios from 'axios'

// Setup (in component)
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api'

// GET request
const response = await axios.get(`${apiBase}/games?round_name=Round 1`)

// POST request
const response = await axios.post(`${apiBase}/tasks`, {
  provider: 'sportsdynamics',
  competition_id: 'comp-123'
})

// Handle response
setGames(response.data)
```

---

## 🔗 Real-World Example: Complete User Journey

### **User Interaction:**

1. ✅ Opens Web App → React loads
2. ✅ Clicks "Games" → `GamesList.jsx` renders
3. ✅ Component mounts → fetches `GET /api/games/rounds`
4. ✅ API queries DB → returns list of round names
5. ✅ Frontend displays round selector → User picks "Round 1"
6. ✅ Triggers `GET /api/games?round_name=Round 1`
7. ✅ API queries DB → returns 10 games
8. ✅ Frontend displays game list
9. ✅ User clicks on "Grenoble vs Dunkerque"
10. ✅ Triggers `GET /api/games/game-123`
11. ✅ API returns full game with squads/events
12. ✅ `GameDetail.jsx` renders details
13. ✅ User clicks "Scrape New Data"
14. ✅ Triggers `POST /api/tasks { provider, competition_id }`
15. ✅ API creates Celery task → returns task_id
16. ✅ Frontend redirects to `TasksPage`
17. ✅ Polls `GET /api/tasks/{id}` every 2s
18. ✅ Backend scrapes from SportsDynamics GraphQL
19. ✅ Transform & saves to PostgreSQL
20. ✅ Task completes → Frontend updates
21. ✅ User clicks back to Games → Sees new data

---

## 📡 API Request/Response Examples

### **Example 1: Get Rounds**

```http
GET /api/games/rounds HTTP/1.1
Host: localhost:8001
Accept: application/json
```

```json
{
  "rounds": [
    "Round 1",
    "Round 2",
    "Round 3"
  ]
}
```

### **Example 2: Get Games for Round**

```http
GET /api/games?round_name=Round%201&limit=100 HTTP/1.1
Host: localhost:8001
Accept: application/json
```

```json
[
  {
    "id": "game-001",
    "name": "Grenoble vs Dunkerque",
    "round_name": "Round 1",
    "competition_name": "Ligue 2",
    "season_name": "2024-2025",
    "home_team": "Grenoble",
    "away_team": "Dunkerque",
    "home_score": 2,
    "away_score": 1,
    "starts_at": "2024-08-09T20:00:00Z",
    "played_at": "2024-08-09T21:45:00Z"
  }
]
```

### **Example 3: Create Scraping Task**

```http
POST /api/tasks HTTP/1.1
Host: localhost:8001
Content-Type: application/json

{
  "provider": "sportsdynamics",
  "competition_id": "comp-123",
  "season_id": "2024"
}
```

```json
{
  "task_id": "task-456",
  "status": "pending",
  "created_at": "2024-09-01T10:00:00Z"
}
```

### **Example 4: Check Task Status**

```http
GET /api/tasks/task-456 HTTP/1.1
Host: localhost:8001
Accept: application/json
```

```json
{
  "id": "task-456",
  "status": "in_progress",
  "progress": 45,
  "total_games": 380,
  "processed_games": 171,
  "started_at": "2024-09-01T10:00:00Z",
  "updated_at": "2024-09-01T10:15:30Z",
  "provider": "sportsdynamics",
  "competition_id": "comp-123"
}
```

---

## 🔐 Configuration & Environment

**`.env` file** (must be created):
```env
# Database
DATABASE_URL=postgresql://scomp_user:password@localhost:5432/scomp

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# SportsDynamics API
SPORTSDYNAMICS_API_KEY=your-api-key-here
SPORTSDYNAMICS_API_URL=https://api.sportsdynamics.com/graphql

# Frontend
VITE_API_BASE_URL=http://localhost:8001/api

# Logging
LOG_LEVEL=INFO
```

---

## 📈 Data Flow Summary

| Component | Role | Technology |
|-----------|------|-----------|
| **Frontend** | User interface & data display | React + Vite + Axios |
| **API Layer** | HTTP endpoints & request handling | FastAPI |
| **Orchestration** | Coordinates data flow | Python (ScraperCoordinator) |
| **API Clients** | Communicates with external APIs | requests library (HTTP + GraphQL) |
| **Filter System** | Transforms values → GraphQL | QueryFilterConfig (JSON config) |
| **Database Layer** | ORM & persistence | SQLAlchemy |
| **Database** | Data storage | PostgreSQL 16 |
| **Message Queue** | Async task execution | Celery + Redis |
| **External APIs** | Data sources | SportsDynamics GraphQL, Perform, SecondSpectrum |

---

## 🚀 Key Takeaways

✅ **Frontend → API**: Simple REST calls (GET/POST)  
✅ **API → Database**: SQLAlchemy ORM queries (async via Celery)  
✅ **API → External APIs**: GraphQL queries (transformed via filter system)  
✅ **Database → Frontend**: JSON responses with nested data  
✅ **Filter System**: Bridge between simple Python values and complex GraphQL  
✅ **Async**: Long scraping tasks handled by Celery workers  
✅ **Persistence**: Hash-based change detection to avoid duplication  

---

## 📚 Related Documentation

- [VISION_GLOBALE.md](./VISION_GLOBALE.md) - Architecture philosophy
- [DB_SCHEMA.md](../docs/database/DB_SCHEMA.md) - Database details
- [VIEWS_DOCUMENTATION.md](../docs/database/VIEWS_DOCUMENTATION.md) - Analytics queries
- [SCRAPE_FLOW_DIAGRAM.md](../docs/pipeline/SCRAPE_FLOW_DIAGRAM.md) - Detailed pipeline
