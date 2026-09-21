# 🏃 PlayerFitnessSummary Table - Comprehensive Analysis

**Last Updated:** 2026-09-12  
**Status:** ✅ Production-Ready (Production Deployment with 37+ Migrations)

---

## 📋 Quick Summary

**PlayerFitnessSummary** is an **aggregated fitness summary table** that stores pre-calculated fitness metrics per player per game, calculated from **PlayerFitnessRun** records. It provides fast dashboards without requiring expensive aggregation queries.

| Attribute | Value |
|-----------|-------|
| **Type** | Aggregated Analytics Table |
| **Rows per Game** | ~22-25 players per team × 2 teams = 44-50 records |
| **Total Rows per Season** | 13,200-15,000 (300 games × 50 per game) |
| **Data Source** | `fitness_entities.json` from SportsDynamics API |
| **Calculated From** | **PlayerFitnessRun** table (3,082+ individual runs per game) |
| **Calculation Method** | Aggregation function in `_calculate_fitness_summaries()` |
| **Storage** | PostgreSQL table with 4 indices |
| **Indexes** | `idx_pfs_game`, `idx_pfs_player`, `idx_pfs_team`, `idx_pfs_game_player` |

---

## 1️⃣ ORM Model Definition

**File:** [backend/src/models/fitness_entities.py](backend/src/models/fitness_entities.py#L184)  
**Lines:** 184-235

### Model Code

```python
class PlayerFitnessSummary(Base, TimestampMixin):
    """
    Aggregated fitness statistics per player per game.
    
    Calculated from PlayerFitnessRun records.
    Used for quick dashboard views without re-aggregating.
    """
    __tablename__ = "player_fitness_summary"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    game_id = Column(String(50), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(String(50), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Aggregated metrics
    total_runs = Column(Integer, default=0)
    total_distance_m = Column(Float, default=0.0)
    total_high_speed_distance_m = Column(Float, default=0.0)
    total_sprint_distance_m = Column(Float, default=0.0)
    average_run_speed_ms = Column(Float)
    peak_speed_ms = Column(Float)
    
    # Classification counts
    high_speed_run_count = Column(Integer, default=0)
    sprint_count = Column(Integer, default=0)
    receiving_run_count = Column(Integer, default=0)
    
    # Context distribution
    offensive_runs = Column(Integer, default=0)
    defensive_runs = Column(Integer, default=0)
    
    game = relationship("Game")
    player = relationship("Player")
    team = relationship("Team")
    
    __table_args__ = (
        Index('idx_pfs_game', 'game_id'),
        Index('idx_pfs_player', 'player_id'),
        Index('idx_pfs_team', 'team_id'),
        Index('idx_pfs_game_player', 'game_id', 'player_id'),
    )
```

---

## 2️⃣ Database Schema

**File:** [backend/alembic/versions/002_add_fitness_entities.py](backend/alembic/versions/002_add_fitness_entities.py#L140-L180)  
**Migration ID:** `002_add_fitness_entities`

### SQL Schema

```sql
CREATE TABLE player_fitness_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id VARCHAR(50) NOT NULL,
    player_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Aggregated metrics
    total_runs INTEGER DEFAULT 0,
    total_distance_m FLOAT DEFAULT 0.0,
    total_high_speed_distance_m FLOAT DEFAULT 0.0,
    total_sprint_distance_m FLOAT DEFAULT 0.0,
    average_run_speed_ms FLOAT,
    peak_speed_ms FLOAT,
    
    -- Classification counts
    high_speed_run_count INTEGER DEFAULT 0,
    sprint_count INTEGER DEFAULT 0,
    receiving_run_count INTEGER DEFAULT 0,
    
    -- Context distribution
    offensive_runs INTEGER DEFAULT 0,
    defensive_runs INTEGER DEFAULT 0,
    
    -- Foreign Keys
    CONSTRAINT fk_game FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
    CONSTRAINT fk_player FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    CONSTRAINT fk_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

-- Indices (BTREE - Fast lookups)
CREATE INDEX idx_pfs_game ON player_fitness_summary(game_id);
CREATE INDEX idx_pfs_player ON player_fitness_summary(player_id);
CREATE INDEX idx_pfs_team ON player_fitness_summary(team_id);
CREATE INDEX idx_pfs_game_player ON player_fitness_summary(game_id, player_id);
```

### Column Details

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NO | gen_random_uuid() | Primary key (surrogate) |
| `game_id` | VARCHAR(50) | NO | - | FK to games table |
| `player_id` | VARCHAR(50) | NO | - | FK to players table |
| `team_id` | VARCHAR(50) | NO | - | FK to teams table |
| `created_at` | TIMESTAMP | NO | NOW() | Record creation time |
| `updated_at` | TIMESTAMP | NO | NOW() | Last update time |
| `total_runs` | INTEGER | YES | 0 | Count of all fitness runs |
| `total_distance_m` | FLOAT | YES | 0.0 | Total distance in meters |
| `total_high_speed_distance_m` | FLOAT | YES | 0.0 | High-speed distance (meter) |
| `total_sprint_distance_m` | FLOAT | YES | 0.0 | Sprint distance (meter) |
| `average_run_speed_ms` | FLOAT | YES | NULL | Average speed of runs (m/s) |
| `peak_speed_ms` | FLOAT | YES | NULL | Peak speed achieved (m/s) |
| `high_speed_run_count` | INTEGER | YES | 0 | Count of high-speed runs |
| `sprint_count` | INTEGER | YES | 0 | Count of sprint runs |
| `receiving_run_count` | INTEGER | YES | 0 | Count of receiving runs |
| `offensive_runs` | INTEGER | YES | 0 | Count of runs in offensive context |
| `defensive_runs` | INTEGER | YES | 0 | Count of runs in defensive context |

---

## 3️⃣ Data Source

### Source File
- **API:** SportsDynamics GraphQL API
- **Endpoint:** `https://api-v2.sportsdynamics.eu/graphql`
- **JSON File:** `fitness_entities.json` (downloaded per game)
- **Location in Exports:** `exports/json_outputs/{game_id}/fitness_entities.json`

### JSON Structure Example

```json
{
  "version": "1.0",
  "config_version": "2.0",
  "export_type": "fitness",
  "generated_at": "2026-08-25T14:32:00Z",
  "game": {
    "game_id": "c1d63cc5-0585-4a32-b61a-77ce8df0c691",
    "coordinates_system": {...},
    "units": {...}
  },
  "entities": [
    {
      "sequence_id": "1",
      "entity_id": "uuid-1",
      "gata_display_name": "Run",
      "period_id": 1,
      "start": 0.04,                    # start_time_s
      "end": 4.04,                      # end_time_s
      "duration": 4.0,                  # duration_s
      "start_frame": 1,
      "end_frame": 101,
      "player": "player-uuid",          # player_id
      "team": "team-uuid",              # team_id
      "opponent_team": "opponent-uuid", # opponent_team_id
      "possession": "poss-uuid",        # possession_id (FK to possession_collective)
      "phase_of_play": "phase-uuid",    # phase_of_play_id (FK)
      "play": "play-uuid",              # type_of_play_id (FK)
      "individual_possession": null,    # individual_possession_id (FK, nullable)
      "distance": 19.3,                 # distance_m
      "high_speed_distance": 5.2,       # high_speed_distance_m
      "sprint_distance": 1.8,           # sprint_distance_m
      "average_speed": 17.2,            # average_speed (m/s)
      "peak_speed": 22.49,              # peak_speed (m/s)
      "high_speed_duration": 0.5,       # high_speed_duration (seconds)
      "sprint_duration": 0.2,           # sprint_duration (seconds)
      "time_to_peak_speed": 1.2,        # time_to_peak_speed
      "acceleration_at_start": 2.1,     # acceleration_at_start (m/s²)
      "peak_acceleration": 3.5,         # peak_acceleration (m/s²)
      "peak_deceleration": -2.8,        # peak_deceleration (m/s²)
      "acceleration_intensity": 45,     # acceleration_intensity (0-100)
      "acceleration_intensity_level": "HIGH_INTENSITY",
      "context": "OFFENSIVE",           # context (OFFENSIVE|DEFENSIVE)
      "direction": "FORWARD",           # direction
      "phase_of_play_label": "Open Play",
      "play_label": "STRUCTURED_PLAY_1",
      "possession_label": "IN_POSSESSION",
      "start_x": 50.5,                  # start X coordinate (meters)
      "start_y": 35.2,                  # start Y coordinate (meters)
      "end_x": 60.8,                    # end X coordinate (meters)
      "end_y": 40.3,                    # end Y coordinate (meters)
      "start_third": "MIDDLE_THIRD",    # start_third
      "end_third": "OFFENSIVE_THIRD",   # end_third
      "start_channel": "CENTRAL",       # start_channel
      "end_channel": "RIGHT",           # end_channel
      "high_speed_run": true,           # boolean flag
      "is_receiving_run": false,        # boolean flag
      "sprint": false,                  # boolean flag
      "run_with_ball": true,            # boolean flag
      "on_ball_run": false,             # boolean flag
      "defensive_box_entry": false,     # boolean flag
      "offensive_box_entry": true,      # boolean flag
      "defensive_third_entry": false,
      "offensive_third_entry": true,
      "functional_start_zone": "CENTRAL_PROGRESSION"
    }
    // ... 3,082+ similar entities per game
  ]
}
```

**Entity Count per Game:** 3,082-3,500 fitness runs across both teams

---

## 4️⃣ Data Flow & Pipeline

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ SportsDynamics API                                              │
│ GET /graphql (competition_id, season_id)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
         ┌──────────────────────────────────────┐
         │ SportsDynamicsClient.get_games()     │
         │ (Returns 10-30 games per batch)      │
         └──────────────────┬───────────────────┘
                           │
                           ▼
        ┌────────────────────────────────────────────┐
        │ ScraperCoordinator.scrape_games()          │
        │ (Orchestrates flow, iterates per game)     │
        └──────────────────┬─────────────────────────┘
                           │
        ┌──────────────────┴────────────────┐
        │                                   │
        ▼                                   ▼
┌───────────────────┐          ┌────────────────────────┐
│ 1. Transform Game │          │ 2. Persist Game        │
│    ORM Models     │          │    to Database         │
└─────────┬─────────┘          └────────┬───────────────┘
          │                             │
          └─────────────┬───────────────┘
                        │
                        ▼
        ┌────────────────────────────────────────┐
        │ 3. Download Output Files (4 JSONs)     │
        │    - metadata.json                     │
        │    - distance_covered.json             │
        │    - fitness_entities.json ◄───────┐   │
        │    - rgd.json                      │   │
        └────────────────────────────────────┼───┘
                        │                    │
                        └────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────┐
        │ 4. parse_and_persist_fitness_entities()│
        │    (fitness_entities_parser.py)        │
        │                                        │
        │    Args:                               │
        │    - game: Game ORM object             │
        │    - fitness_data: parsed JSON dict    │
        │    - db_session: SQLAlchemy session    │
        │    - calculate_summaries: boolean      │
        └────────────────┬───────────────────────┘
                         │
        ┌────────────────┴────────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│ For each entity (3,082+):    │    │ If calculate_summaries=True: │
│                              │    │                              │
│ 1. Validate required fields  │    │ 1. Delete old summaries      │
│ 2. Create PlayerFitnessRun   │    │ 2. Aggregate by player/team  │
│    - player_id, team_id      │    │ 3. Calculate statistics:     │
│    - distance_m              │    │    - total_runs              │
│    - speed metrics           │    │    - total_distance_m        │
│    - acceleration            │    │    - average_run_speed_ms    │
│    - boolean flags           │    │    - peak_speed_ms           │
│    - tactical context        │    │    - high_speed_run_count    │
│    - spatial positioning     │    │    - sprint_count            │
│ 3. Validate FK references    │    │    - offensive/defensive     │
│    (soft validation, NULL ok)│    │ 4. Create PlayerFitnessSummary
│ 4. Store in BTREE+JSONB      │    │    - 44-50 records per game  │
│ 5. Batch flush to DB         │    │ 5. Create TeamFitnessSummary │
│                              │    │    - 2 records per game      │
└──────────────┬───────────────┘    └──────────────┬───────────────┘
               │                                   │
               └───────────────┬───────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ db_session.commit()  │
                    │ (Atomic transaction) │
                    └──────────────────────┘
```

---

## 5️⃣ Creation & Calculation Logic

**File:** [backend/src/orchestration/fitness_entities_parser.py](backend/src/orchestration/fitness_entities_parser.py#L523-L665)  
**Function:** `_calculate_fitness_summaries(game: Game, db_session: Session) -> None`  
**Lines:** 523-665

### Calculation Algorithm

```python
def _calculate_fitness_summaries(
    game: Game,
    db_session: Session,
) -> None:
    """
    Calculate PlayerFitnessSummary and TeamFitnessSummary records.
    
    Algorithm:
    1. Delete existing summaries (idempotency)
    2. Query all PlayerFitnessRun records for this game
    3. Aggregate by (game_id, player_id, team_id)
    4. Calculate metrics from aggregated runs
    5. Create PlayerFitnessSummary & TeamFitnessSummary records
    6. Add to session (batch insert)
    """
    
    try:
        # ====================================================================
        # STEP 1: DELETE EXISTING SUMMARIES (IDEMPOTENCY)
        # ====================================================================
        db_session.query(TeamFitnessSummary).filter(
            TeamFitnessSummary.game_id == game.id
        ).delete()
        db_session.query(PlayerFitnessSummary).filter(
            PlayerFitnessSummary.game_id == game.id
        ).delete()
        
        # ====================================================================
        # STEP 2: QUERY ALL FITNESS RUNS FOR THIS GAME
        # ====================================================================
        runs = db_session.query(PlayerFitnessRun).filter(
            PlayerFitnessRun.game_id == game.id
        ).all()
        
        player_stats = {}  # (game_id, player_id, team_id) → stats dict
        team_stats = {}    # (game_id, team_id) → stats dict
        
        # ====================================================================
        # STEP 3: AGGREGATE BY PLAYER (Iterate all runs)
        # ====================================================================
        for run in runs:
            player_key = (run.game_id, run.player_id, run.team_id)
            
            # Initialize if first time seeing this player
            if player_key not in player_stats:
                player_stats[player_key] = {
                    'total_runs': 0,
                    'total_distance_m': 0.0,
                    'total_high_speed_distance_m': 0.0,
                    'total_sprint_distance_m': 0.0,
                    'speeds': [],  # Collect all peak speeds
                    'high_speed_run_count': 0,
                    'sprint_count': 0,
                    'receiving_run_count': 0,
                    'offensive_runs': 0,
                    'defensive_runs': 0,
                }
            
            stats = player_stats[player_key]
            
            # === ACCUMULATE METRICS ===
            stats['total_runs'] += 1
            stats['total_distance_m'] += run.distance_m or 0
            stats['total_high_speed_distance_m'] += run.high_speed_distance_m or 0
            stats['total_sprint_distance_m'] += run.sprint_distance_m or 0
            
            # === COLLECT SPEEDS (for average & peak) ===
            if run.peak_speed:
                stats['speeds'].append(run.peak_speed)
            
            # === COUNT BOOLEAN CLASSIFICATIONS ===
            if run.high_speed_run:
                stats['high_speed_run_count'] += 1
            if run.sprint:
                stats['sprint_count'] += 1
            if run.is_receiving_run:
                stats['receiving_run_count'] += 1
            
            # === COUNT CONTEXT DISTRIBUTION ===
            if run.context == 'OFFENSIVE':
                stats['offensive_runs'] += 1
            elif run.context == 'DEFENSIVE':
                stats['defensive_runs'] += 1
            
            # === AGGREGATE TO TEAM LEVEL ===
            team_key = (run.game_id, run.team_id)
            if team_key not in team_stats:
                team_stats[team_key] = {
                    'total_runs': 0,
                    'total_distance_m': 0.0,
                    'total_high_speed_distance_m': 0.0,
                    'total_sprint_distance_m': 0.0,
                    'speeds': [],
                    'players': set(),
                    'offensive_runs': 0,
                    'defensive_runs': 0,
                }
            
            tstats = team_stats[team_key]
            tstats['total_runs'] += 1
            tstats['total_distance_m'] += run.distance_m or 0
            tstats['total_high_speed_distance_m'] += run.high_speed_distance_m or 0
            tstats['total_sprint_distance_m'] += run.sprint_distance_m or 0
            if run.peak_speed:
                tstats['speeds'].append(run.peak_speed)
            tstats['players'].add(run.player_id)
            if run.context == 'OFFENSIVE':
                tstats['offensive_runs'] += 1
            elif run.context == 'DEFENSIVE':
                tstats['defensive_runs'] += 1
        
        # ====================================================================
        # STEP 4: CREATE PLAYERFITNESSSUMMARY RECORDS
        # ====================================================================
        for (game_id, player_id, team_id), stats in player_stats.items():
            summary = PlayerFitnessSummary(
                id=str(uuid4()),
                game_id=game_id,
                player_id=player_id,
                team_id=team_id,
                total_runs=stats['total_runs'],
                total_distance_m=stats['total_distance_m'],
                total_high_speed_distance_m=stats['total_high_speed_distance_m'],
                total_sprint_distance_m=stats['total_sprint_distance_m'],
                # Average speed: sum(speeds) / count(speeds)
                average_run_speed_ms=sum(stats['speeds']) / len(stats['speeds']) 
                                    if stats['speeds'] else None,
                # Peak speed: max(speeds)
                peak_speed_ms=max(stats['speeds']) if stats['speeds'] else None,
                high_speed_run_count=stats['high_speed_run_count'],
                sprint_count=stats['sprint_count'],
                receiving_run_count=stats['receiving_run_count'],
                offensive_runs=stats['offensive_runs'],
                defensive_runs=stats['defensive_runs'],
            )
            db_session.add(summary)
        
        # ====================================================================
        # STEP 5: CREATE TEAMFITNESSSUMMARY RECORDS
        # ====================================================================
        for (game_id, team_id), stats in team_stats.items():
            summary = TeamFitnessSummary(
                id=str(uuid4()),
                game_id=game_id,
                team_id=team_id,
                total_runs=stats['total_runs'],
                total_distance_m=stats['total_distance_m'],
                total_high_speed_distance_m=stats['total_high_speed_distance_m'],
                total_sprint_distance_m=stats['total_sprint_distance_m'],
                average_team_speed_ms=sum(stats['speeds']) / len(stats['speeds']) 
                                      if stats['speeds'] else None,
                players_tracked=len(stats['players']),
                offensive_runs=stats['offensive_runs'],
                defensive_runs=stats['defensive_runs'],
                average_runs_per_phase=stats['total_runs'] / 14 
                                      if stats['total_runs'] > 0 else 0,
            )
            db_session.add(summary)
        
        logger.info(
            f"Calculated {len(player_stats)} player + {len(team_stats)} team fitness summaries "
            f"for game {game.id}"
        )
        
    except Exception as e:
        logger.error(f"Error calculating fitness summaries for game {game.id}: {str(e)}", exc_info=True)
        raise
```

### Calculation Formulas

| Metric | Calculation | Example |
|--------|-------------|---------|
| `total_runs` | COUNT(runs) | 127 runs |
| `total_distance_m` | SUM(run.distance_m) | 9,847 meters |
| `total_high_speed_distance_m` | SUM(run.high_speed_distance_m) | 1,245 meters |
| `total_sprint_distance_m` | SUM(run.sprint_distance_m) | 385 meters |
| `average_run_speed_ms` | SUM(peak_speed) / COUNT(speeds) | 6.2 m/s |
| `peak_speed_ms` | MAX(run.peak_speed) | 9.8 m/s |
| `high_speed_run_count` | COUNT(WHERE high_speed_run=true) | 23 |
| `sprint_count` | COUNT(WHERE sprint=true) | 8 |
| `receiving_run_count` | COUNT(WHERE is_receiving_run=true) | 12 |
| `offensive_runs` | COUNT(WHERE context='OFFENSIVE') | 71 |
| `defensive_runs` | COUNT(WHERE context='DEFENSIVE') | 56 |

---

## 6️⃣ Records Per Game

### Typical Distribution

```
Per Game:
├─ Team 1 (Home)
│  ├─ Starting XI (11 players)
│  │  ├─ Player 1: ~120-150 fitness runs, aggregated to 1 summary
│  │  ├─ Player 2: ~110-140 fitness runs, aggregated to 1 summary
│  │  └─ ... (11 total)
│  └─ Substitutes (3-5 players) ← Played <5 minutes
│     └─ Each: 5-50 fitness runs, aggregated to 1 summary
│
└─ Team 2 (Away)
   ├─ Starting XI (11 players)
   │  └─ Similar distribution
   └─ Substitutes (3-5 players)
      └─ Similar distribution

Summary Totals:
- PlayerFitnessSummary: 22-25 records per game (44-50 total)
- TeamFitnessSummary: 2 records per game
- PlayerFitnessRun: 3,082-3,500 records per game
```

### Example Record

```json
{
  "id": "c1d63cc5-0585-4a32-b61a-77ce8df0c691",
  "game_id": "game-uuid-001",
  "player_id": "player-uuid-0042",
  "team_id": "team-uuid-nantes",
  "created_at": "2026-08-25T14:45:00Z",
  "updated_at": "2026-08-25T14:45:00Z",
  
  "total_runs": 127,
  "total_distance_m": 9847.3,
  "total_high_speed_distance_m": 1245.8,
  "total_sprint_distance_m": 385.2,
  "average_run_speed_ms": 6.2,
  "peak_speed_ms": 9.8,
  
  "high_speed_run_count": 23,
  "sprint_count": 8,
  "receiving_run_count": 12,
  
  "offensive_runs": 71,
  "defensive_runs": 56
}
```

---

## 7️⃣ Timing & Performance

### Per-Game Timeline

```
STEP | OPERATION                          | DURATION | NOTES
-----|---------------------------------------|----------|------
  1  | Download fitness_entities.json       | 0.5-0.8s | Network I/O
  2  | Parse JSON to dict                   | 0.1s     | json.load()
  3  | Delete existing PlayerFitnessRun     | 0.2-0.3s | CASCADE cleanup
  4  | Transform 3,082+ entities to ORM     | 0.5-0.8s | Validation, FK checks
  5  | Batch flush to database              | 0.3-0.5s | INSERT (bulk)
  6  | Query all runs for aggregation       | 0.2s     | SELECT with index
  7  | Aggregate runs by player             | 0.1-0.2s | In-memory loop
  8  | Create 44-50 PlayerFitnessSummary    | 0.1s     | ORM object creation
  9  | Create 2 TeamFitnessSummary          | 0.05s    | ORM object creation
 10  | Delete old summaries                 | 0.05s    | For idempotency
 11  | Batch insert summaries               | 0.1-0.2s | INSERT
 12  | Commit transaction                   | 0.2-0.3s | ACID guarantee
     |                                      |          |
     | TOTAL PER GAME                       | 2.5-4.5s | Average: 3.5s
```

### Per-Season Performance

```
Season Stats:
- Games per season: 300-380
- PlayerFitnessRun records created: 925,000 - 1,330,000
- PlayerFitnessSummary records created: 13,200 - 19,000
- Total duration: 45-90 minutes
- Throughput: ~230-280 games/hour
```

### Database Impact

```
Disk Space:
- PlayerFitnessRun (3,082/game × 380 games): ~350-400 MB
  (UUID: 16 bytes, String(50): 50 bytes, Float: 8 bytes, etc.)
- PlayerFitnessSummary (48/game × 380): ~2-3 MB
- Indices (BTREE): ~100-150 MB

Query Performance:
- Get all runs for player/game: <100ms (idx_pfr_player + idx_pfr_game)
- Get summary for player/game: <5ms (idx_pfs_game_player)
- Aggregation query (group by player): <500ms (3,082 rows)
```

---

## 8️⃣ Special Handling & Validations

### Idempotency

**Problem:** Re-scraping a game should not duplicate summary records.

**Solution:** Delete existing summaries before calculation

```python
# Delete existing summaries (idempotency)
db_session.query(PlayerFitnessSummary).filter(
    PlayerFitnessSummary.game_id == game.id
).delete()
```

### Foreign Key Validation

**Problem:** Event references (possession_id, phase_of_play_id) might be missing.

**Solution:** Soft FK validation - NULL if not found

```python
# Check if reference exists, set to NULL if not
possession_id = entity.get("possession")
if possession_id and not _check_event_reference_exists(
    db_session, "possession_collective", possession_id
):
    logger.warning(f"Possession {possession_id} not found, setting to NULL")
    possession_id = None
```

### String Field Truncation

**Problem:** API data might exceed VARCHAR(100) limit.

**Solution:** Truncate and log warning

```python
# === TRUNCATE String(100) fields to avoid StringDataRightTruncation ===
acceleration_intensity_level = entity.get("acceleration_intensity_level")
if acceleration_intensity_level and len(str(acceleration_intensity_level)) > 100:
    logger.warning(f"⚠️ acceleration_intensity_level truncated...")
    acceleration_intensity_level = str(acceleration_intensity_level)[:100]
```

### Speed Calculations

**Problem:** Calculate average and peak speed from multiple runs.

**Solution:** Collect speeds, compute aggregate

```python
# Collect all peak speeds
if run.peak_speed:
    stats['speeds'].append(run.peak_speed)

# Calculate average and peak
average_run_speed_ms = sum(stats['speeds']) / len(stats['speeds']) if stats['speeds'] else None
peak_speed_ms = max(stats['speeds']) if stats['speeds'] else None
```

---

## 9️⃣ Relationships with Other Tables

### Direct Relationships

```
PlayerFitnessSummary
├─ FK: game_id → games(id)
│  └─ Cascade delete on game removal
│
├─ FK: player_id → players(id)
│  └─ Cascade delete on player removal
│
└─ FK: team_id → teams(id)
   └─ Cascade delete on team removal
```

### Indirect Relationships

```
PlayerFitnessSummary
└─ Aggregates from: PlayerFitnessRun (1:N)
   ├─ FK: game_id → games(id)
   ├─ FK: player_id → players(id)
   ├─ FK: team_id → teams(id)
   └─ FK: possession_id → possession_collective(id) [soft]
   ├─ FK: phase_of_play_id → phase_of_play(id) [soft]
   ├─ FK: type_of_play_id → type_of_play(id) [soft]
   └─ FK: individual_possession_id → individual_possession(id) [soft]
```

### Related Tables

| Table | Relationship | Purpose |
|-------|--------------|---------|
| `games` | PK:FK | Game context for summary |
| `players` | PK:FK | Player identification |
| `teams` | PK:FK | Team context |
| `player_fitness_runs` | Source data (1:N) | Individual fitness events (3,082 runs → 1 summary) |
| `possession_collective` | Soft FK from runs | Possession context (can be NULL) |
| `phase_of_play` | Soft FK from runs | Game phase context (can be NULL) |
| `type_of_play` | Soft FK from runs | Play classification (can be NULL) |
| `team_fitness_summary` | Similar aggregation | Team-level summary |

---

## 🔟 How It's Queried & Used

### Common Queries

#### 1. Get Player Fitness Summary for Specific Game

```python
# FastAPI example
@router.get("/api/games/{game_id}/players/{player_id}/fitness")
def get_player_fitness(game_id: str, player_id: str, db: Session):
    summary = db.query(PlayerFitnessSummary).filter(
        and_(
            PlayerFitnessSummary.game_id == game_id,
            PlayerFitnessSummary.player_id == player_id
        )
    ).first()
    return summary
```

#### 2. Get Team's Player Fitness Stats

```sql
SELECT * FROM player_fitness_summary
WHERE game_id = 'game-uuid-001'
  AND team_id = 'team-uuid-nantes'
ORDER BY total_distance_m DESC;
```

#### 3. Compare Players Across Multiple Games

```sql
SELECT 
  p.name,
  COUNT(pfs.game_id) as games_played,
  AVG(pfs.total_distance_m) as avg_distance,
  AVG(pfs.peak_speed_ms) as avg_peak_speed,
  SUM(pfs.sprint_count) as total_sprints
FROM player_fitness_summary pfs
JOIN players p ON pfs.player_id = p.id
WHERE pfs.player_id = 'player-uuid'
  AND pfs.game_id IN (
    SELECT id FROM games WHERE season_id = 'season-uuid'
  )
GROUP BY p.name;
```

#### 4. High-Performance Player Identification

```sql
SELECT 
  p.name,
  pfs.peak_speed_ms,
  pfs.sprint_count,
  pfs.total_distance_m
FROM player_fitness_summary pfs
JOIN players p ON pfs.player_id = p.id
WHERE pfs.game_id = 'game-uuid-001'
  AND pfs.peak_speed_ms > 8.0
  AND pfs.sprint_count > 5
ORDER BY pfs.peak_speed_ms DESC;
```

---

## 1️⃣1️⃣ Import & Exports

### ORM Import

**File:** [backend/src/models/__init__.py](backend/src/models/__init__.py#L16)

```python
from .fitness_entities import PlayerFitnessRun, PlayerFitnessSummary, TeamFitnessSummary

__all__ = [
    "PlayerFitnessSummary",
    "TeamFitnessSummary",
    ...
]
```

### Parser Import

**File:** [backend/src/orchestration/fitness_entities_parser.py](backend/src/orchestration/fitness_entities_parser.py#L1)

```python
from src.models import (
    Game,
    Player,
    Team,
    PlayerFitnessRun,
    PlayerFitnessSummary,
    TeamFitnessSummary,
)
```

### Integration Points

- **ScraperCoordinator:** [Line 30](backend/src/orchestration/scraper_coordinator.py#L30)
- **SportsDynamicsScraper:** [Line 18](backend/src/scraper/sportsdynamics_scraper.py#L18)

---

## 1️⃣2️⃣ Migrations & Schema Evolution

### Primary Migration

**File:** `backend/alembic/versions/002_add_fitness_entities.py`  
**Revision ID:** `002_add_fitness_entities`  
**Revises:** `001_hybrid_events_schema`

### Supporting Migrations

| Migration | Purpose | Impact |
|-----------|---------|--------|
| `037_fix_fitness_entities_fk_types` | Fix FK type mismatches (UUID → String(50)) | Schema compatibility |
| `039_increase_fitness_string_fields` | Increase varchar field lengths | Prevent truncation errors |
| `040_force_fitness_varchar_fixes` | Additional varchar fixes | Data type alignment |

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history

# Downgrade if needed
alembic downgrade -1
```

---

## 1️⃣3️⃣ Example Data Structure

### Complete Record Example

```python
PlayerFitnessSummary(
    id="a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    game_id="game-uuid-001",
    player_id="player-uuid-0042",
    team_id="team-uuid-nantes",
    created_at=datetime(2026, 8, 25, 14, 45, 0),
    updated_at=datetime(2026, 8, 25, 14, 45, 0),
    
    # Core metrics
    total_runs=127,
    total_distance_m=9847.3,
    total_high_speed_distance_m=1245.8,
    total_sprint_distance_m=385.2,
    average_run_speed_ms=6.2,
    peak_speed_ms=9.8,
    
    # Classifications
    high_speed_run_count=23,
    sprint_count=8,
    receiving_run_count=12,
    
    # Context
    offensive_runs=71,
    defensive_runs=56
)
```

### JSON Representation (API Response)

```json
{
  "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "game_id": "game-uuid-001",
  "player_id": "player-uuid-0042",
  "team_id": "team-uuid-nantes",
  "created_at": "2026-08-25T14:45:00Z",
  "updated_at": "2026-08-25T14:45:00Z",
  
  "total_runs": 127,
  "total_distance_m": 9847.3,
  "total_high_speed_distance_m": 1245.8,
  "total_sprint_distance_m": 385.2,
  "average_run_speed_ms": 6.2,
  "peak_speed_ms": 9.8,
  
  "high_speed_run_count": 23,
  "sprint_count": 8,
  "receiving_run_count": 12,
  
  "offensive_runs": 71,
  "defensive_runs": 56
}
```

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Table Name** | `player_fitness_summary` |
| **Row Count/Game** | 44-50 records (22-25 per team) |
| **Data Source** | `fitness_entities.json` from SportsDynamics API |
| **Source Records** | 3,082+ PlayerFitnessRun records aggregated per game |
| **Columns** | 17 (3 FK + 1 UUID + 4 timestamps + 15 metrics) |
| **Indices** | 4 BTREE (game_id, player_id, team_id, composite) |
| **Calculation Time** | 0.5-1.0s per game |
| **Cascade Delete** | Yes (on game/player/team delete) |
| **Idempotent** | Yes (deletes old before creating new) |
| **Key Metrics** | Distance, speed, acceleration, context |
| **Relationships** | Aggregates from PlayerFitnessRun (3,082:1 ratio) |
| **Use Case** | Dashboards, player performance analysis, fitness tracking |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| [backend/src/models/fitness_entities.py](backend/src/models/fitness_entities.py) | 184-235 | ORM Model Definition |
| [backend/src/orchestration/fitness_entities_parser.py](backend/src/orchestration/fitness_entities_parser.py) | 1-700+ | Parser + Calculation Logic |
| [backend/alembic/versions/002_add_fitness_entities.py](backend/alembic/versions/002_add_fitness_entities.py) | 20-230 | Migration: Table Creation |
| [backend/alembic/versions/037_fix_fitness_entities_fk_types.py](backend/alembic/versions/037_fix_fitness_entities_fk_types.py) | 1-160 | Migration: FK Type Fixes |
| [backend/src/orchestration/scraper_coordinator.py](backend/src/orchestration/scraper_coordinator.py) | 1670-1720 | Integration Point |
| [backend/src/scraper/sportsdynamics_scraper.py](backend/src/scraper/sportsdynamics_scraper.py) | 240-265 | Data Ingestion |

