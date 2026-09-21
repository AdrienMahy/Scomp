# 🔄 Scrape Flow - Diagramme Détaillé

## Vue d'ensemble du Pipeline Complet

```mermaid
graph TD
    A["🚀 START: POST /api/tasks<br/>scrape_competition"] --> B["1. Create Task<br/>(status: pending)"]
    B --> C["2. Verify/Create<br/>Competition"]
    C --> D["3. Verify/Create<br/>Season"]
    D --> E["4. Celery Job:<br/>Call Provider API"]
    
    E --> F["📥 API Response<br/>(SportsDynamics/Perform/SecondSpectrum)"]
    F --> G{Response<br/>Valid?}
    
    G -->|No| H["❌ Task FAILED<br/>Update DB"]
    H --> I["🔴 END: Error Status"]
    
    G -->|Yes| J["5. Parse & Transform<br/>API Data"]
    J --> K["Extract Teams<br/>Extract Players<br/>Extract Games"]
    
    K --> L["6. For Each Game:<br/>Check Update Conditions"]
    L --> M{Game Changed?<br/>hash_check}
    
    M -->|No| N["⏭️ Skip Game<br/>(No update needed)"]
    N --> O["7. Persist All Games"]
    
    M -->|Yes| P["🗑️ Delete Old Data<br/>(squads, players)"]
    P --> Q["📝 Create/Update<br/>Game Record"]
    Q --> R["👥 Create Squads<br/>(lineup_players)"]
    R --> S["⚽ Create Goals<br/>(game_goals)"]
    S --> T["🟨 Create Cards<br/>(game_cards)"]
    T --> U["🔄 Create Substitutions<br/>(game_substitutions)"]
    U --> V["📊 Upsert Game Summary<br/>(denormalized view)"]
    V --> O
    
    O --> W["8. Export to JSON<br/>(exports/ folder)"]
    W --> X["9. Update Alembic<br/>Version Tracking"]
    X --> Y["10. Commit Transaction"]
    Y --> Z["✅ Task COMPLETED<br/>Status: success"]
    Z --> AA["🟢 END: Success"]
```

---

## Détail des Étapes

### Phase 1️⃣: Initialisation (Étapes 1-4)

**Entrée:** 
```json
{
  "provider": "sportsdynamics",
  "competition_id": "comp-123"
}
```

**Processus:**
- Créer une Task Celery avec status `pending`
- Vérifier que la compétition existe (sinon créer)
- Vérifier que la saison existe (sinon créer)
- Préparer les headers API et credentials

**Sortie:** Task ID, ready to call API

---

### Phase 2️⃣: Récupération API (Étape 5)

**Providers supportés:**
- 🔵 **SportsDynamics** - API REST JSON
- 🟢 **Perform** - GraphQL
- 🟡 **SecondSpectrum** - REST/Tracking

**API Call:**
```python
# Exemple SportsDynamics
GET https://api.sportsdynamics.com/competitions/{id}?filters=...
Headers: {"Authorization": "Bearer {token}"}
Response: 
{
  "games": [...],
  "teams": [...],
  "players": [...]
}
```

**Status Updates:**
- `pending` → `processing`
- On error → `failed`
- On success → continue to Phase 3

---

### Phase 3️⃣: Transformation (Étapes 6-7)

**Transformation Pipelines:**

```mermaid
graph LR
    A["API Response<br/>Raw JSON"] --> B["Normalize<br/>Field Mapping"]
    B --> C["Create ORM<br/>Objects"]
    C --> D["Game<br/>Objects"]
    C --> E["Team<br/>Objects"]
    C --> F["Player<br/>Objects"]
    
    D --> G["Check if<br/>Game Changed"]
    E --> H["Persist<br/>Teams"]
    F --> I["Persist<br/>Players"]
```

**Détails:**
- Mapper les champs API → Modèles SQLAlchemy
- Normaliser les dates (UTC)
- Extraire les UUID depuis les réponses
- Gérer les champs optionnels avec defaults

---

### Phase 4️⃣: Change Detection (Étape 8)

**Hash-based Comparison:**

```
Game avant: {id, fileName, fileType, version}  → hash1
Game après: {id, fileName, fileType, version}  → hash2

hash1 == hash2 ?
  ✅ Oui  → Skip update (pas de changement)
  ❌ Non  → Update (données nouvelles)
```

**Conditions d'Update (`_should_update_game`):**
- ✅ `available` status changed
- ✅ `is_ugd_available` changed
- ✅ `rgd_status` changed
- ✅ `ugd_status` changed
- ✅ `output_files_hash` differs

---

### Phase 5️⃣: Persistence (Étapes 9-12)

**Pour chaque Game:**

```mermaid
graph TD
    A["Game Changed?"] -->|No| B["⏭️ Skip"]
    A -->|Yes| C["Delete Old:<br/>squads, players<br/>goals, cards, subs"]
    C --> D["Save Game<br/>Record"]
    D --> E["Create Lineup<br/>(position, jersey)"]
    E --> F["Create Events:<br/>Goals, Cards,<br/>Substitutions"]
    F --> G["Upsert<br/>Game Summary<br/>(denormalized)"]
    G --> H["✅ Game<br/>Persisted"]
```

**Ordre critique:**
1. `games` (DELETE first with CASCADE)
2. `lineup_teams`, `lineup_players`
3. `game_goals`, `game_cards`, `game_substitutions`
4. `game_summary` (denormalized view for fast queries)

---

### Phase 6️⃣: Export & Commit (Étapes 13-15)

**JSON Export:**
```
exports/
├── 1_Team1_vs_Team2.json
├── 2_Team3_vs_Team4.json
└── ...
```

**Structure JSON:**
```json
{
  "game_id": "uuid",
  "name": "Match Name",
  "teams": [...],
  "players": [...],
  "goals": [...],
  "cards": [...],
  "events": [...]
}
```

**Transaction Commit:**
- Alembic version tracking
- Permanent DB save
- Update Task status → `success`
- Update `completed_at` timestamp

---

## État du Task dans le Temps

```mermaid
stateDiagram-v2
    [*] --> pending: POST /api/tasks
    pending --> processing: Celery picks up
    processing --> success: All games saved
    processing --> failed: API error or validation
    success --> [*]: Task done
    failed --> [*]: Error logged
    
    note right of processing
        API call
        Transform
        Persist
        Export
    end note
```

---

## Flux de Données (Data Types)

```mermaid
graph LR
    A["API JSON<br/>(Raw)"] --> B["Python Dict<br/>(Parsed)"]
    B --> C["SQLAlchemy<br/>ORM Objects<br/>(Game, Team, Player)"]
    C --> D["PostgreSQL<br/>Database<br/>(Tables)"]
    D --> E["VIEWs<br/>(Analytics)"]
    D --> F["JSON Export<br/>(exports/ folder)"]
```

---

## Dépendances & Order of Operations

```mermaid
graph TD
    A["Competition<br/>(must exist)"] --> B["Season<br/>(must exist)"]
    B --> C["Teams<br/>(from API)"]
    C --> D["Games<br/>(linked to teams)"]
    D --> E["Lineup"]
    D --> F["Events"]
    E --> G["Game Summary<br/>(denormalized)"]
    F --> G
    G --> H["✅ Ready<br/>for Analytics"]
```

---

## Gestion des Erreurs

```mermaid
graph TD
    A["Scrape Start"] --> B{Try to fetch API}
    
    B -->|Connection Error| C["❌ Task FAILED"]
    B -->|Invalid Response| D["❌ Task FAILED"]
    B -->|Success| E["Parse Data"]
    
    E --> F{Validation}
    F -->|Missing Fields| G["❌ Task FAILED"]
    F -->|Valid| H["Save to DB"]
    
    H --> I{DB Commit}
    I -->|Constraint Violation| J["❌ Task FAILED"]
    I -->|Success| K["✅ Task COMPLETED"]
    
    C --> L["Log Error<br/>Update Task Status"]
    D --> L
    G --> L
    J --> L
    L --> M["User can retry"]
```

---

## Timeline d'Exécution (Typique)

| Phase | Durée | Action |
|-------|-------|--------|
| 1. Initialisation | ~100ms | Create task, verify competition |
| 2. API Call | ~2-5s | Fetch from SportsDynamics |
| 3. Transform | ~500ms | Parse & normalize data |
| 4. Change Detection | ~200ms | Hash comparison |
| 5. Persist | ~3-10s | INSERT/UPDATE 300+ games |
| 6. Export | ~1s | Write JSON files |
| 7. Commit | ~200ms | DB transaction commit |
| **Total** | **~7-17s** | Pour toute une compétition |

---

## Exemple Réel: Dunkerque vs Grenoble (J1)

```
START: POST /api/tasks
│
├─ 1. Create Task (ID: task-123)
├─ 2. Competition exists (Ligue 2)
├─ 3. Season exists (2024)
│
├─ 4. Call SportsDynamics API
│   └─ Response: 34 games + teams + players
│
├─ 5. Transform Data
│   ├─ Parse 34 games
│   ├─ Create 32 teams
│   └─ Create ~1000 players
│
├─ 6. For each game: Check hash
│   ├─ Game 1 (Boulogne vs Nancy): SKIP ✅ (already scraped)
│   ├─ Game 2 (Clermont vs Reims): SKIP ✅
│   ├─ ...
│   └─ Game 33 (Dunkerque vs Grenoble): UPDATE 🔄 (new round data)
│
├─ 7. Persist Game 33
│   ├─ Delete old squads/events
│   ├─ Create new squads
│   ├─ Create goals (4 for Dunkerque, 2 for Grenoble)
│   ├─ Create cards (7 yellows, 0 reds)
│   ├─ Create substitutions (4)
│   └─ Upsert game_summary (result: Dunkerque WIN)
│
├─ 8. Export JSON
│   └─ exports/1_Dunkerque_vs_Grenoble_Foot_38.json
│
├─ 9. Update Alembic version
├─ 10. Commit transaction
│
└─ END: Task COMPLETED ✅
   Status: success
   Duration: 12.5s
```

---

## 📁 Fichiers Impliqués

| Fichier | Rôle |
|---------|------|
| `backend/src/orchestration/scraper_coordinator.py` | Orchestrateur principal |
| `backend/src/api/sportsdynamics.py` | Client API |
| `backend/src/scraper/sportsdynamics_scraper.py` | Transformer |
| `backend/src/models/game.py` | ORM Game model |
| `backend/src/models/team.py` | ORM Team model |
| `backend/src/models/player.py` | ORM Player model |
| `backend/src/tasks/scraping_tasks.py` | Celery task definition |
| `backend/export_to_json.py` | JSON exporter |
| `backend/views.sql` | Analytics VIEWs |

---

## 🔗 Documentation Connexe

- [ARCHITECTURE.md](ARCHITECTURE.md) - Détail du filtre system & GraphQL
- [VISION_GLOBALE.md](backend/VISION_GLOBALE.md) - Philosophie de design
- [DB_SCHEMA.md](DB_SCHEMA.md) - Schéma détaillé des tables
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - État actuel

