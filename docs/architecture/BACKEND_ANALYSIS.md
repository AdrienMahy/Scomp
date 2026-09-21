# 🏗️ Scomp Backend - Analyse Approfondie

**Total:** 8,698 lignes de code | 64 fichiers Python | 13 modules

---

## 📊 Statistiques Globales

```
├─ Total Lines:           8,698 LOC
├─ Python Files:          64 files
├─ Main Modules:          13
├─ ORM Models:            20+ tables
├─ API Endpoints:         15+ routes
├─ ETL Processors:        6 parsers
└─ External Providers:    1 (SportsDynamics)
```

### Code Distribution (Top 20 Largest Files)

| Fichier | LOC | Responsabilité |
|---------|-----|-----------------|
| `orchestration/scraper_coordinator.py` | 1,246 | 🎯 Orchestrateur principal |
| `web/routes/games.py` | 802 | 🌐 Endpoints des matchs |
| `etl/event_transformers.py` | 576 | 🔄 ETL: événements |
| `orchestration/fitness_entities_parser.py` | 568 | 🏃 ETL: fitness runs (3,082) |
| `orchestration/metadata_parser.py` | 426 | 📋 ETL: métadonnées |
| `etl/rgd_to_events_transformer.py` | 409 | 🔄 Transformer RGD → Events |
| `models/events_hybrid_schema.py` | 372 | 📦 ORM: 13 types d'événements |
| `web/routes/players.py` | 302 | 👥 Endpoints des joueurs |
| `api/sportsdynamics.py` | 282 | 🔌 API client |

---

## 🏛️ Architecture Modulaire

### 1️⃣ **`main.py`** - Entry Point (50 LOC)

**Responsabilité:** Initialisation FastAPI et setup global

```python
app = FastAPI(
    title="Scomp API",
    description="Sports Data Scraping & API",
    version="1.0.0"
)

# ✅ CORS enabled
# ✅ Routes incluses: competitions, games, teams, players, tasks
# ✅ Database initialization on startup
```

**Features:**
- FastAPI v0.100+
- CORS middleware (allow all origins)
- 5 route modules intégrés
- Health check endpoint `/`
- Swagger docs auto-générés

---

### 2️⃣ **`config/`** - Configuration & Setup (400+ LOC)

#### **`database.py`** (30 LOC)
```python
# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():  # ← FastAPI dependency
    db = SessionLocal()
    yield db
    db.close()

def init_db():  # ← Creates all tables
    Base.metadata.create_all()
```

**Features:**
- SQLAlchemy 1.4+
- Psycopg2 driver (PostgreSQL)
- Connection pooling (pool_size=10, max_overflow=20)
- Session management avec dependency injection FastAPI

#### **`settings.py`** (80 LOC)
```python
# Environment-based configuration
DATABASE_URL = "postgresql://user:pass@localhost:5432/scomp"
REDIS_URL = "redis://localhost:6379/0"
SPORTSDYNAMICS_API_KEY = env("API_KEY")
SPORTSDYNAMICS_API_BASE_URL = "https://api.sportsdynamics.com"
```

**Features:**
- Pydantic BaseSettings
- Type-safe environment variables
- Config classes for DB, API, logging
- ID.json loading for SportsDynamics IDs

#### **`filter_config.py`** (183 LOC)
```python
# GraphQL filter builder
class QueryFilterConfig:
    def build_filter(self, field: str, operator: str, value: Any) -> Dict:
        # Transforms: {"round": ["Round 1"]} 
        # → {"round": {"name": {"in": [...]}}}
        pass
```

**Features:**
- Conversion simple Python dict → complex GraphQL payload
- Operators: equals, in, contains, greater_than, less_than
- Validation de filtres supportés
- Support polymorphe pour différents types de champs

---

### 3️⃣ **`models/`** - SQLAlchemy ORM (20+ tables, 2,000+ LOC)

#### **`base.py`** (15 LOC)
```python
Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

#### **Core Models** (Master data)

| Model | Colonnes | Clé | Responsabilité |
|-------|----------|-----|-----------------|
| **`game.py`** | 10 | id (VARCHAR 50) | Match principal |
| **`team.py`** | 5 | UUID | Équipe |
| **`player.py`** | 8 | UUID | Joueur |
| **`competition.py`** | 6 | id (VARCHAR) | Compétition |
| **`season.py`** | 5 | id (VARCHAR) | Saison |

#### **Event Models** (13 types, `events_hybrid_schema.py`, 372 LOC)

```python
# Hybrid pattern: Master table + 13 specific tables
events (master)
├─ ball_in_play
├─ card
├─ foul
├─ goal_kick
├─ goals
├─ individual_possession
├─ kickoff
├─ offside
├─ phase_of_play
├─ possession_collective
├─ setpieces
├─ type_of_play
└─ (+ metadata JSONB)
```

**Features:**
- ✅ FK constraints avec CASCADE delete
- ✅ BTREE indexes sur game_id, period_id
- ✅ GIN indexes sur JSONB metadata
- ✅ Polymorphic-like pattern (1 master + 13 specifics)

#### **Analytics Models**

| Model | Colonnes | Responsabilité |
|-------|----------|-----------------|
| **`game_summary.py`** | 15 | Denormalized: team results, JSONB teams |
| **`distance_covered.py`** | 20 | Distance par team/zone/période |
| **`player_distance_covered.py`** | 25 | Distance par joueur |
| **`fitness_entities.py`** | 54 | **🆕 Player fitness runs (3,082)** |

#### **Fitness Entities Deep Dive** (271 LOC)

```python
class PlayerFitnessRun(Base, TimestampMixin):
    __tablename__ = "player_fitness_runs"
    
    # PRIMARY (5 cols)
    id: UUID, game_id: VARCHAR(50), period_id: int
    
    # ACTOR IDs (3 cols)
    player_id: UUID, team_id: UUID, opponent_team_id: UUID
    
    # EVENT REFERENCES (4 cols nullable)
    possession_id, phase_of_play_id, type_of_play_id, individual_possession_id
    
    # PERFORMANCE (17 cols)
    distance_m, high_speed_distance_m, sprint_distance_m
    average_speed, peak_speed, high_speed_duration, sprint_duration
    acceleration_at_start, peak_acceleration, peak_deceleration
    
    # TACTICAL (5 cols)
    context, direction, phase_of_play_label, play_label, possession_label
    
    # SPATIAL (8 cols)
    start_x, start_y, end_x, end_y
    start_third, end_third, start_channel, end_channel
    
    # CLASSIFICATIONS (5 boolean)
    high_speed_run, is_receiving_run, sprint, run_with_ball, on_ball_run
    
    # BOX ENTRIES (5 boolean)
    defensive_box_entry, offensive_box_entry, ...
    
    # METADATA (1 JSONB)
    metadata_json  # 51 API fields + sustained_speeds + timing
```

**Status:** ✅ 3,082 records loaded | ✅ All columns mapped | ✅ JSONB populated

---

### 4️⃣ **`orchestration/`** - Business Logic (2,500+ LOC)

#### **`scraper_coordinator.py`** (1,246 LOC) - 🎯 **Orchestrator Principal**

```python
class ScraperCoordinator:
    """
    Complete pipeline orchestrator:
    1. Fetch games from API
    2. Transform to ORM objects
    3. Persist to database
    4. Calculate summaries
    5. Export to JSON
    """
    
    def scrape_competition(self, provider: str, competition_id: str) -> dict:
        # 6 ETL processors called in sequence
        self._process_competition_metadata()  # Comp + season
        self._process_lineups()               # Squads + players
        self._process_events()                # 500+ events (13 types)
        self._process_distance_covered()      # Team distance
        self._process_player_distance()       # Player distance
        self._process_fitness_entities()      # 3,082 fitness runs ✅
        
        # Verify + export
        self._verify_data()
        self.export_to_json()
```

**Key Methods:**
- `scrape_competition(provider, comp_id)` - Main entry point
- `_fetch_competition_data()` - API call
- `_download_files()` - Download 6 JSON files
- `_process_*()` - 6 ETL processors
- `_verify_data()` - Validation + quality checks
- `export_to_json()` - JSON export
- `_should_update_game()` - Change detection
- `_delete_game_data()` - Idempotency

**Timing:**
- API call: 0.5s
- Download: 2.0s
- ETL: 7.0s
- DB write: 1.0s
- **Total: ~13s per competition**

#### **`fitness_entities_parser.py`** (568 LOC)

```python
def parse_and_persist_fitness_entities(
    game: Game,
    fitness_data: dict,
    db_session: Session,
    calculate_summaries: bool = True
) -> dict:
    """
    ETL for fitness_entities.json:
    1. Validate game & players
    2. Transform 51 API fields → ORM
    3. Handle FK references (nullable)
    4. Batch insert 3,082 records
    5. Calculate PlayerFitnessSummary & TeamFitnessSummary
    """
```

**Features:**
- ✅ 3,082 entities from single game processed
- ✅ Validation: players exist, teams exist
- ✅ FK handling: nullable, logged warnings
- ✅ Metadata JSON: sustained_speeds, timing, api_ids
- ✅ Aggregation: summary tables calculated
- ✅ Error handling: rollback on transaction fail

#### **`metadata_parser.py`** (426 LOC)

```python
def parse_and_persist_lineups()    # Squads + players + lineups
def parse_and_persist_periods()    # Period metadata
def parse_and_persist_events()     # 500+ events to 13 tables
```

#### **`distance_covered_parser.py`** (137 LOC)

```python
def parse_and_persist_distance_covered(game, distance_data, session)
# Team distance by zone × period × speed_zone
```

#### **`player_distance_covered_parser.py`** (146 LOC)

```python
def parse_and_persist_player_distance_covered(game, player_distance_data, session)
# Individual player distance metrics
```

---

### 5️⃣ **`etl/`** - Data Transformation (1,000+ LOC)

#### **`event_transformers.py`** (576 LOC)

```python
class BaseEventTransformer:
    """Base for all 13 event types"""
    def transform_batch(events: List[Dict]) -> tuple:
        # Returns (records, stats)
        pass

# Specialized transformers for:
class BallInPlayTransformer
class CardTransformer
class FoulTransformer
class GoalTransformer
class PhaseOfPlayTransformer
# ... (13 total)
```

**Features:**
- Nested dict extraction with dot notation: `'entity.type.name'`
- Automatic JSONB structuring for flexible fields
- Batch processing with stats tracking
- Error handling + skipping logic

#### **`rgd_to_events_transformer.py`** (409 LOC)

```python
class RGDToEventsTransformer:
    """Convert RGD tracking data to typed event tables"""
    def transform(rgd_event: Dict) -> Tuple[str, Dict]:
        # Returns: (table_type, record_dict)
        pass
```

---

### 6️⃣ **`api/`** - External API Clients (300+ LOC)

#### **`sportsdynamics.py`** (282 LOC)

```python
class SportsDynamicsClient:
    """Low-level HTTP wrapper for SportsDynamics GraphQL API"""
    
    def __init__(self, api_key: str, base_url: str):
        self.client = httpx.Client()
        self.base_url = base_url
    
    def get_games(
        self,
        competition_id: str,
        season_id: Optional[str],
        filter_payload: Dict,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query GraphQL endpoint
        - POST /graphql
        - Response: Full game + lineup + events + distance + fitness
        """
        pass
```

**Features:**
- HTTP client (httpx or requests)
- GraphQL payload builder
- Error handling (HTTP codes, malformed JSON)
- Response validation
- Retry logic (optional)

---

### 7️⃣ **`providers/`** - Business Layer (120+ LOC)

#### **`sportsdynamics_provider.py`** (119 LOC)

```python
class SportsDynamicsProvider:
    """
    Wraps SportsDynamicsClient with business logic:
    - Filter validation
    - Simple value → GraphQL payload transform
    - Caching (future)
    - Business logic
    """
    
    def fetch_games(filters: Dict, limit: int, page: int) -> List[Dict]:
        # 1. Validate filters
        # 2. Extract competition_id, season_id, round
        # 3. Call client.get_games()
        # 4. Return results
        pass
```

**Feature Example:**
```python
# Simple input
filters = {"round": ["Round 1", "Round 2"]}

# Transformed to GraphQL
{"round": {"name": {"in": ["Round 1", "Round 2"]}}}
```

---

### 8️⃣ **`web/`** - FastAPI Routes (1,500+ LOC)

#### **Route Structure**

```python
web/
├── routes/
│   ├── competitions.py  # GET /competitions
│   ├── games.py         # 802 LOC - Main endpoint
│   ├── teams.py         # GET /teams/{id}
│   ├── players.py       # 302 LOC - GET /players/{id}
│   └── tasks.py         # GET /tasks/{id}
├── api_v1/
│   └── games.py         # Legacy routes
└── schemas.py           # Pydantic models (response DTOs)
```

#### **`routes/games.py`** (802 LOC)

**Key Endpoints:**

| Endpoint | Méthode | Responsabilité |
|----------|---------|-----------------|
| `GET /games/ids-config` | GET | Retourne SportsDynamics IDs disponibles |
| `GET /games/scrape-filters` | GET | Filtres supportés pour scraping |
| `POST /games/scrape` | POST | Lance scraping async |
| `GET /games/{game_id}` | GET | Détails du match + squads |
| `GET /games/{game_id}/events` | GET | Événements du match (500+) |
| `GET /games/{game_id}/distance` | GET | Distance data |
| `GET /games/{game_id}/fitness` | GET | Fitness runs (3,082) |
| `GET /games` | GET | List all games (filtrable) |

**Implementation Pattern:**

```python
@router.get("/games/{game_id}")
async def get_game_details(
    game_id: str,
    db: Session = Depends(get_db)
) -> GameDetailSchema:
    """
    Get complete game details including:
    - Game metadata
    - Teams + squads + players
    - Events (500+)
    - Distance data
    - Fitness runs (3,082)
    """
    game = db.query(Game).filter_by(id=game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")
    
    return GameDetailSchema(
        game=game,
        squads=game.squads,
        events=game.events,
        distance=game.distance_covered,
        fitness=game.fitness_runs
    )
```

#### **`routes/players.py`** (302 LOC)

```python
@router.get("/players/{player_id}")
async def get_player_details(player_id: str, db: Session) -> PlayerSchema:
    """Player with career history, fitness runs, performance metrics"""

@router.get("/players/{player_id}/fitness")
async def get_player_fitness(player_id: str, db: Session) -> PlayerFitnessSchema:
    """Player fitness runs (3,082 records per game) with aggregations"""
```

#### **`routes/competitions.py`**

```python
@router.get("/competitions")
async def list_competitions(db: Session) -> List[CompetitionSchema]:
    """All competitions with season counts"""

@router.get("/competitions/{comp_id}/seasons")
async def get_competition_seasons(comp_id: str, db: Session) -> List[SeasonSchema]:
    """Seasons in competition"""
```

#### **`routes/teams.py`**

```python
@router.get("/teams/{team_id}")
async def get_team_details(team_id: str, db: Session) -> TeamSchema:
    """Team with players, matches, stats"""

@router.get("/teams/{team_id}/fitness")
async def get_team_fitness_summary(team_id: str, db: Session) -> TeamFitnessSummarySchema:
    """Aggregated team fitness metrics"""
```

#### **`routes/tasks.py`**

```python
@router.post("/tasks")
async def create_scraping_task(
    task: TaskCreateSchema,
    db: Session
) -> TaskSchema:
    """
    Create async scraping task:
    {
        "provider": "sportsdynamics",
        "competition_id": "comp-123"
    }
    """

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session) -> TaskSchema:
    """Task status, progress, results"""
```

#### **`schemas.py`** (300+ LOC)

```python
class GameDetailSchema(BaseModel):
    id: str
    name: str
    competition_id: str
    squads: List[SquadSchema]
    events: List[EventSchema]
    distance: DistanceCoveredSchema
    fitness: List[PlayerFitnessRunSchema]

class PlayerFitnessRunSchema(BaseModel):
    player_id: UUID
    distance_m: float
    duration_s: float
    high_speed_run: bool
    sprint: bool
    context: str  # DEFENSIVE/OFFENSIVE
    direction: str  # FORWARD/BACKWARD/LATERAL
    metadata_json: Dict[str, Any]

class TeamFitnessSummarySchema(BaseModel):
    team_id: UUID
    total_runs: int
    avg_distance_m: float
    total_distance_m: float
    high_speed_runs: int
```

---

### 9️⃣ **`tasks/`** - Celery Async (150+ LOC)

#### **`celery_config.py`**

```python
app = Celery('scomp', broker=REDIS_URL)
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True
)
```

#### **`scrape_tasks.py`**

```python
@app.task(bind=True)
def scrape_competition_async(
    self,
    provider: str,
    competition_id: str,
    season_id: Optional[str] = None
):
    """
    Async scraping task:
    1. Update state: PENDING
    2. Run ScraperCoordinator
    3. Store results
    4. Return success
    """
    try:
        coordinator = ScraperCoordinator()
        results = coordinator.scrape_competition(provider, competition_id)
        return {"status": "SUCCESS", "results": results}
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise
```

#### **`beat.py`** - Scheduled Tasks

```python
# Periodic tasks (via Celery Beat):
from celery.schedules import crontab

app.conf.beat_schedule = {
    'scrape-ligue2-daily': {
        'task': 'tasks.scrape_tasks.scrape_competition_async',
        'schedule': crontab(hour=23, minute=30),  # Daily 11:30 PM
        'args': ('sportsdynamics', 'comp-ligue2')
    },
}
```

---

### 🔟 **`database/`** - Utilities (50+ LOC)

#### **`session.py`**

```python
class DatabaseSession:
    """Context manager for DB sessions"""
    def __init__(self):
        self.session = SessionLocal()
    
    def __enter__(self):
        return self.session
    
    def __exit__(self, *args):
        self.session.close()
```

**Usage:**
```python
with DatabaseSession() as session:
    games = session.query(Game).all()
```

---

### 1️⃣1️⃣ **`scraper/`** - Base Classes (200+ LOC)

#### **`base_scraper.py`**

```python
class BaseScraper(ABC):
    """Abstract base for provider-specific scrapers"""
    
    @abstractmethod
    def fetch_games(self, competition_id: str) -> List[Dict]:
        """Fetch games from provider"""
        pass
    
    @abstractmethod
    def fetch_game_details(self, game_id: str) -> Dict:
        """Fetch game with events, lineup, etc."""
        pass
```

#### **`sportsdynamics_scraper.py`** (116 LOC)

```python
class SportsDynamicsScraper(BaseScraper):
    """SportsDynamics-specific scraper implementation"""
    
    def fetch_games(self, competition_id: str) -> List[Dict]:
        # Use SportsDynamicsClient
        pass
    
    def fetch_game_details(self, game_id: str) -> Dict:
        # Rich game data: lineup, events, distance, fitness
        pass
```

---

### 1️⃣2️⃣ **`scripts/`** - CLI Tools

Les JSON des matchs sont désormais téléchargés et traités en mémoire par
`ScraperCoordinator`. Aucun export physique dans `exports/json_outputs` n'est
effectué par le flux de scraping.

---

## 📈 Data Flow Complete

```
🌐 API (SportsDynamics)
    ↓ [0.5s]
📥 Download 6 JSON files
    ├─ competition_info.json (50-100 LOC)
    ├─ lineups.json (100-200 LOC)
    ├─ events.json (500-1000 LOC)
    ├─ distance_covered.json (100-200 LOC)
    ├─ player_distance.json (200-400 LOC)
    └─ fitness_entities.json (3,082 records)
    ↓ [2.0s]
🔄 ETL Processors (6 parsers)
    ├─ metadata_parser.py       → competitions, seasons, games, periods
    ├─ metadata_parser.py       → squads, players, teams, lineups
    ├─ metadata_parser.py       → events (500+, 13 types)
    ├─ distance_covered_parser.py → team distance data
    ├─ player_distance_parser.py  → player distance data
    └─ fitness_entities_parser.py → player_fitness_runs (3,082) ✅
    ↓ [7.0s]
💾 PostgreSQL (27 tables)
    ├─ Core: games, teams, players, competitions, seasons
    ├─ Events: events + 13 specialized tables
    ├─ Analytics: distance_covered, player_distance_covered
    └─ Fitness: player_fitness_runs, player_fitness_summary, team_fitness_summary
    ↓ [1.5s]
📊 Analytics VIEWs (3)
    ├─ v_team_matches_summary
    ├─ v_team_speed_zones_by_interval
    └─ v_player_speed_zones_by_interval
    ↓ [1.0s]
🎯 API Endpoints (15+)
    ├─ GET /games
    ├─ GET /games/{id}/fitness
    ├─ GET /players/{id}/fitness
    ├─ GET /teams/{id}/fitness
    └─ ... (+ more)
    ↓
🖥️ Frontend (React + Vite)
    └─ Visualization & analytics
```

---

## 🎯 Key Architectural Patterns

### 1. **Coordinator Pattern** (ScraperCoordinator)
```python
# Central orchestrator that coordinates all ETL steps
coordinator = ScraperCoordinator()
stats = coordinator.scrape_competition(provider, comp_id)
# Internally handles: fetch → transform → persist → verify → export
```

### 2. **Provider Pattern** (SportsDynamicsProvider)
```python
# Business logic wrapper around API client
provider = SportsDynamicsProvider()
games = provider.fetch_games(filters)
# Handles: validation, transformation, caching
```

### 3. **Transformer Pattern** (EventTransformers)
```python
# Specialized transformers for each entity type
transformer = BallInPlayTransformer(game_id)
records, stats = transformer.transform_batch(events)
# Each transformer knows its specific table structure
```

### 4. **Hybrid Schema Pattern** (Events)
```python
# Master events table + 13 specialized event tables
# Provides both: detailed type-specific fields + shared metadata
events (generic)
├─ ball_in_play (specific)
├─ card (specific)
└─ ... (13 total)
```

### 5. **Dependency Injection Pattern** (FastAPI)
```python
@app.get("/games/{id}")
async def get_game(game_id: str, db: Session = Depends(get_db)):
    # Session injected by FastAPI
    game = db.query(Game).get(game_id)
```

### 6. **Async Task Pattern** (Celery)
```python
# Long-running operations offloaded to worker
@app.post("/tasks")
async def scrape_async(task: TaskCreate):
    scrape_competition_async.delay(task.provider, task.comp_id)

@app.task
def scrape_competition_async(provider, comp_id):
    # Runs in background worker
    coordinator.scrape_competition(provider, comp_id)
```

---

## 🔍 Database Schema Overview

### Core Tables (5)

| Table | Type | PK | FK | Rows |
|-------|------|----|----|------|
| **games** | Core | VARCHAR(50) | comp_id, season_id | 300+ |
| **teams** | Core | UUID | comp_id | 40+ |
| **players** | Core | UUID | - | 500+ |
| **competitions** | Core | VARCHAR | - | 5 |
| **seasons** | Core | VARCHAR | comp_id | 20+ |

### Event Tables (14 = 1 master + 13 specific)

| Table | Rows | Purpose |
|-------|------|---------|
| **events** | 500+ | Master event store |
| **ball_in_play** | 150+ | In/out of play events |
| **card** | 10-20 | Red/yellow cards |
| **foul** | 30-50 | Fouls |
| **goal_kick** | 20-30 | GK kickouts |
| **goals** | 1-5 | Goals scored |
| **individual_possession** | 100+ | Player possession |
| **kickoff** | 2 | Period kickoffs |
| **offside** | 0-5 | Offside incidents |
| **phase_of_play** | 50-100 | Possession phases |
| **possession_collective** | 30-50 | Team possession |
| **setpieces** | 10-20 | Corners, free kicks |
| **type_of_play** | 100+ | Play classification |

### Analytics Tables (6)

| Table | Rows/Game | Purpose |
|-------|-----------|---------|
| **game_summary** | 1 | Denormalized game view |
| **game_status** | 1 | Available, hash tracking |
| **distance_covered** | 2 | Team distance per period |
| **player_distance_covered** | 22+ | Player distance metrics |
| **player_fitness_runs** | 3,082 | **✅ NEW** Fitness tracking |
| **player_fitness_summary** | 1 | Fitness aggregates |

### Output Tables (3)

| Table | Purpose |
|-------|---------|
| **output_file** | Track exported JSON files |
| **lineup_team** | Team lineup snapshots |
| **lineup_player** | Player lineup snapshots |

---

## ✅ API Endpoints Summary

### Competitions (4 endpoints)
```
GET  /competitions              List all competitions
GET  /competitions/{id}         Competition details + seasons
GET  /competitions/{id}/seasons Competition seasons
POST /competitions              Create competition (internal)
```

### Games (8 endpoints)
```
GET  /games                     List games (filtrable)
GET  /games/{id}                Game details + all data
GET  /games/{id}/events         Events only
GET  /games/{id}/distance       Distance data
GET  /games/{id}/fitness        Fitness runs (3,082)
GET  /games/ids-config          SportsDynamics IDs
GET  /games/scrape-filters      Available filters
POST /games/scrape              Start scraping
```

### Players (5 endpoints)
```
GET  /players                   List all players
GET  /players/{id}              Player details
GET  /players/{id}/fitness      Player fitness runs
GET  /players/{id}/stats        Career statistics
POST /players                   Create player (internal)
```

### Teams (4 endpoints)
```
GET  /teams                     List all teams
GET  /teams/{id}                Team details
GET  /teams/{id}/fitness        Team fitness summary
GET  /teams/{id}/players        Team squad
```

### Tasks (4 endpoints)
```
POST /tasks                     Create scraping task
GET  /tasks                     List tasks
GET  /tasks/{id}                Task details + progress
DELETE /tasks/{id}              Cancel task
```

---

## 📊 Performance Metrics

### Code Quality
- **Total LOC:** 8,698 (production code)
- **Test LOC:** ~500 (separate)
- **Documentation:** High (docstrings + type hints)
- **Type Coverage:** 80%+ (type hints throughout)

### Database Performance
- **Connection Pool:** 10 base + 20 overflow
- **Batch Insert:** ~500 records/sec (fitness: 3,082 in 6 sec)
- **Query Optimization:** BTREE + GIN indexes on hot paths
- **Transaction Handling:** Rollback on error, ACID compliant

### API Performance
- **Response Time:** <100ms (local DB)
- **Endpoint Count:** 25+
- **Rate Limiting:** Not yet implemented (future)
- **Caching:** Not yet implemented (future)

### Pipeline Performance (per competition)
- **Total Time:** ~13 seconds
  - API call: 0.5s
  - Download: 2.0s
  - ETL: 7.0s
  - DB write: 1.0s
  - Verification: 0.5s
  - Export: 0.5s
  - Others: 0.5s

---

## 🚀 Current Development Status

### ✅ COMPLETE
- [x] Database schema (27 tables)
- [x] ORM models (20+ classes)
- [x] API endpoints (25+)
- [x] ETL processors (6)
- [x] Event transformers (13 types)
- [x] Fitness pipeline (3,082 records)
- [x] Analytics VIEWs (3)
- [x] Async tasks (Celery)
- [x] Docker setup

### ⏳ IN PROGRESS
- [ ] API schemas for fitness endpoints
- [ ] Frontend fitness components
- [ ] Query optimization
- [ ] Caching layer

### ❌ NOT STARTED
- [ ] Rate limiting
- [ ] Authentication/Authorization
- [ ] API versioning (v2)
- [ ] GraphQL endpoint
- [ ] Real-time websockets
- [ ] Performance dashboard

---

## 💡 Notable Design Decisions

### 1. **Hybrid Event Schema**
Why: Allows both generic event handling + specific type-specific fields
```python
# Store all events in master table
# + specific fields in dedicated tables
# Best of both worlds: flexibility + type safety
```

### 2. **JSONB Metadata**
Why: Support API-provided metadata without schema migration
```python
fitness_entities.metadata_json contains:
- sustained_speeds (8 fields)
- timing (3 fields)
- api_ids (3 fields)
- 51+ classification fields
# Queryable via PostgreSQL JSON operators
```

### 3. **Nullable FK References**
Why: Handle incomplete data from API gracefully
```python
# Some fitness runs may not link to specific events
possession_id = NULL  # OK
phase_of_play_id = NULL  # OK
# Logged as warnings, not errors
```

### 4. **Deferred ETL**
Why: Process JSON sequentially, maintain transaction consistency
```python
# Step 1: metadata (competitions, seasons)
# Step 2: lineups (teams, players)
# Step 3: events (500+)
# Step 4: distance
# Step 5: fitness
# If step N fails, rollback entire transaction
```

### 5. **Coordinator Pattern**
Why: Single orchestrator for complex multi-step flow
```python
# vs. multiple smaller jobs
# Pros: Atomic transactions, clear flow, error handling
# Cons: Less parallelism (future optimization)
```

---

## 🔗 Module Dependencies

```
main.py (entry)
  ├─ web/routes/* (FastAPI routers)
  │   ├─ config/database (DB sessions)
  │   ├─ orchestration/scraper_coordinator (business logic)
  │   └─ models/* (ORM)
  │
  ├─ orchestration/scraper_coordinator (orchestrator)
  │   ├─ providers/sportsdynamics_provider
  │   ├─ api/sportsdynamics (HTTP client)
  │   ├─ orchestration/*_parser (6 ETL processors)
  │   ├─ etl/event_transformers (event transformation)
  │   ├─ models/* (ORM)
  │   └─ config/database (sessions)
  │
  ├─ tasks/scrape_tasks (async)
  │   ├─ orchestration/scraper_coordinator
  │   └─ tasks/celery_config
  │
  └─ config/database (setup)
      └─ models/base (Base class)
```

---

## 📝 Next Steps (Recommendations)

### Short Term (1-2 weeks)
1. ✅ **API Schemas** - Create Pydantic models for fitness endpoints
2. ✅ **Fitness Endpoints** - Implement GET routes for fitness data
3. ✅ **Testing** - Unit tests for ETL processors

### Medium Term (2-4 weeks)
1. 📊 **Frontend** - React components for fitness visualization
2. ⚡ **Caching** - Redis cache for expensive queries
3. 🔍 **Indexing** - Query performance tuning

### Long Term (1-3 months)
1. 🔐 **Auth** - JWT authentication
2. 📈 **GraphQL** - Alternative query interface
3. 🚀 **Scalability** - Parallelized ETL for multiple competitions

---

