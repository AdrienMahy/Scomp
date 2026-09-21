# 📊 Scomp Data Pipeline Workflow

Diagrammes du workflow complet de traitement des données : depuis la récupération via les API externes jusqu'à la visualisation frontend.

## 1️⃣ Workflow Complet (End-to-End)

```mermaid
graph TD
    A["🌐 External API Providers"] --> B["SportsDynamics API"]
    A --> C["Perform API"]
    A --> D["SecondSpectrum API"]
    
    B --> E["Fetch Competition Data"]
    C --> E
    D --> E
    
    E --> F["API Response<br/>JSON"]
    
    F --> G["📥 Download Files Stage"]
    G --> G1["competition_info.json"]
    G --> G2["games_metadata.json"]
    G --> G3["lineups.json"]
    G --> G4["events.json"]
    G --> G5["distance_covered.json"]
    G --> G6["player_distance.json"]
    G --> G7["fitness_entities.json"]
    
    G1 --> H["🔄 ETL Processing Layer<br/>ScraperCoordinator"]
    G2 --> H
    G3 --> H
    G4 --> H
    G5 --> H
    G6 --> H
    G7 --> H
    
    H --> I["Transform & Validate"]
    I --> J1["Parse Lineups"]
    I --> J2["Parse Events"]
    I --> J3["Parse Distance Data"]
    I --> J4["Parse Fitness Entities"]
    I --> J5["Parse Metadata"]
    
    J1 --> K["🗄️ PostgreSQL Database Layer"]
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    
    K --> L1["games"]
    K --> L2["squads"]
    K --> L3["players"]
    K --> L4["teams"]
    K --> L5["events<br/>ball_in_play<br/>card<br/>goals"]
    K --> L6["distance_covered<br/>player_distance"]
    K --> L7["player_fitness_runs<br/>player_fitness_summary<br/>team_fitness_summary"]
    
    L1 --> M["📊 Analytics Layer"]
    L2 --> M
    L3 --> M
    L4 --> M
    L5 --> M
    L6 --> M
    L7 --> M
    
    M --> N1["v_team_matches_summary"]
    M --> N2["v_team_speed_zones"]
    M --> N3["v_player_speed_zones"]
    
    N1 --> O["🎯 API Endpoints"]
    N2 --> O
    N3 --> O
    L7 --> O
    L6 --> O
    L5 --> O
    
    O --> P1["GET /api/games"]
    O --> P2["GET /api/games/id/fitness"]
    O --> P3["GET /api/players/id/fitness"]
    O --> P4["GET /api/teams/id/fitness"]
    O --> P5["GET /api/events"]
    
    P1 --> Q["🖥️ Frontend<br/>React + Vite"]
    P2 --> Q
    P3 --> Q
    P4 --> Q
    P5 --> Q
    
    Q --> R1["GamesList View"]
    Q --> R2["GameDetail View"]
    Q --> R3["Fitness Analytics"]
    Q --> R4["Event Timeline"]
    
    style A fill:#e1f5ff
    style E fill:#fff3e0
    style F fill:#fff3e0
    style G fill:#f3e5f5
    style H fill:#e8f5e9
    style I fill:#e8f5e9
    style K fill:#fce4ec
    style M fill:#f1f8e9
    style O fill:#e0f2f1
    style Q fill:#ffe0b2
```

Maintenant, voici un diagramme détaillé de la phase **ETL spécifique** :

```mermaid
graph LR
    A["📥 JSON Files<br/>Backend Exports"] --> B["ETL Pipeline<br/>ScraperCoordinator"]
    
    B --> C1["Extract Phase"]
    B --> C2["Transform Phase"]
    B --> C3["Load Phase"]
    
    C1 --> D1["Read JSON"]
    C1 --> D2["Validate Schema"]
    C1 --> D3["Parse IDs"]
    
    D1 --> E["Transform Phase"]
    D2 --> E
    D3 --> E
    
    E --> F1["Map IDs<br/>player → UUID<br/>team → UUID"]
    E --> F2["Calculate Metrics<br/>distance, speed<br/>acceleration"]
    E --> F3["Denormalize<br/>game_summary<br/>team results"]
    E --> F4["Create Relationships<br/>possession ↔ run<br/>phase_of_play ↔ run"]
    
    F1 --> G["Load Phase"]
    F2 --> G
    F3 --> G
    F4 --> G
    
    G --> H1["Batch Insert<br/>3,082 records"]
    G --> H2["Calculate Summaries<br/>PlayerFitnessSummary"]
    G --> H3["Aggregate by Team<br/>TeamFitnessSummary"]
    
    H1 --> I["✅ Database"]
    H2 --> I
    H3 --> I
    
    I --> J["Verify<br/>• Count records<br/>• Check FKs<br/>• Validate metrics"]
    
    J --> K["Export Results<br/>JSON export<br/>Analytics ready"]
    
    style A fill:#fff3e0
    style B fill:#e8f5e9
    style C1 fill:#c8e6c9
    style C2 fill:#a5d6a7
    style C3 fill:#81c784
    style E fill:#66bb6a
    style G fill:#4caf50
    style I fill:#2e7d32
    style J fill:#1b5e20
    style K fill:#f1f8e9
```

Et un diagramme du **flux par fichier** :

```mermaid
graph TD
    subgraph API["🌐 API Providers"]
        SD["SportsDynamics"]
        PF["Perform"]
        SS["SecondSpectrum"]
    end
    
    subgraph Download["📥 Download & Store"]
        D1["competition_info.json"]
        D2["lineups.json"]
        D3["events.json"]
        D4["distance_covered.json"]
        D5["player_distance.json"]
        D6["fitness_entities.json"]
    end
    
    subgraph Processing["🔄 ETL Processing"]
        P1["_process_competition_metadata"]
        P2["_process_lineups"]
        P3["_process_events"]
        P4["_process_distance_covered"]
        P5["_process_player_distance"]
        P6["_process_fitness_entities"]
    end
    
    subgraph Storage["💾 PostgreSQL"]
        S1["competitions<br/>seasons"]
        S2["squads<br/>players<br/>teams"]
        S3["events + 8 types<br/>ball_in_play, card, goals..."]
        S4["distance_covered"]
        S5["player_distance"]
        S6["player_fitness_runs<br/>+ summaries"]
    end
    
    subgraph Output["📊 Output"]
        O1["Exports JSON"]
        O2["Analytics VIEWs"]
        O3["API Ready"]
    end
    
    API --> Download
    D1 --> P1
    D2 --> P2
    D3 --> P3
    D4 --> P4
    D5 --> P5
    D6 --> P6
    
    P1 --> S1
    P2 --> S2
    P3 --> S3
    P4 --> S4
    P5 --> S5
    P6 --> S6
    
    S1 --> O1
    S2 --> O1
    S3 --> O2
    S4 --> O2
    S5 --> O2
    S6 --> O3
    
    O1 --> O2
    O2 --> O3
    
    style API fill:#e3f2fd
    style Download fill:#fff3e0
    style Processing fill:#f3e5f5
    style Storage fill:#fce4ec
    style Output fill:#e8f5e9
```

**Timing du Pipeline:**
```mermaid
timeline
    title Scraping Pipeline Timeline (per match/competition)
    
    section API & Download
        API Call : 0.5s : Call competition endpoint
        Parse Response : 0.2s : Extract game IDs
        Download Files : 2s : Fetch JSON exports
    
    section ETL Processing
        Transform Metadata : 0.3s : Parse competition/season
        Parse Lineups : 1s : Create squads & players
        Parse Events : 2s : Load 500+ events
        Parse Distance : 1.5s : Process distance data
        Parse Fitness : 3s : Load 3,082 fitness runs
    
    section Database Write
        Batch Insert : 1s : Write all records
        Calculate Summary : 0.5s : Aggregations
        Verify & Commit : 0.5s : Validation
    
    section Export
        Export JSON : 0.5s : Game export
        Total Time : ~13s : Complete pipeline
```

---

## 2️⃣ ETL Détaillé (Extract → Transform → Load)

```mermaid
graph LR
    A["📥 JSON Files<br/>Backend Exports"] --> B["ETL Pipeline<br/>ScraperCoordinator"]
    
    B --> C1["Extract Phase"]
    B --> C2["Transform Phase"]
    B --> C3["Load Phase"]
    
    C1 --> D1["Read JSON"]
    C1 --> D2["Validate Schema"]
    C1 --> D3["Parse IDs"]
    
    D1 --> E["Transform Phase"]
    D2 --> E
    D3 --> E
    
    E --> F1["Map IDs<br/>player → UUID<br/>team → UUID"]
    E --> F2["Calculate Metrics<br/>distance, speed<br/>acceleration"]
    E --> F3["Denormalize<br/>game_summary<br/>team results"]
    E --> F4["Create Relationships<br/>possession ↔ run<br/>phase_of_play ↔ run"]
    
    F1 --> G["Load Phase"]
    F2 --> G
    F3 --> G
    F4 --> G
    
    G --> H1["Batch Insert<br/>3,082 records"]
    G --> H2["Calculate Summaries<br/>PlayerFitnessSummary"]
    G --> H3["Aggregate by Team<br/>TeamFitnessSummary"]
    
    H1 --> I["✅ Database"]
    H2 --> I
    H3 --> I
    
    I --> J["Verify<br/>• Count records<br/>• Check FKs<br/>• Validate metrics"]
    
    J --> K["Export Results<br/>JSON export<br/>Analytics ready"]
    
    style A fill:#fff3e0
    style B fill:#e8f5e9
    style C1 fill:#c8e6c9
    style C2 fill:#a5d6a7
    style C3 fill:#81c784
    style E fill:#66bb6a
    style G fill:#4caf50
    style I fill:#2e7d32
    style J fill:#1b5e20
    style K fill:#f1f8e9
```

---

## 3️⃣ Flux par Fichier JSON

```mermaid
graph TD
    subgraph API["🌐 API Providers"]
        SD["SportsDynamics"]
        PF["Perform"]
        SS["SecondSpectrum"]
    end
    
    subgraph Download["📥 Download & Store"]
        D1["competition_info.json"]
        D2["lineups.json"]
        D3["events.json"]
        D4["distance_covered.json"]
        D5["player_distance.json"]
        D6["fitness_entities.json"]
    end
    
    subgraph Processing["🔄 ETL Processing"]
        P1["_process_competition_metadata"]
        P2["_process_lineups"]
        P3["_process_events"]
        P4["_process_distance_covered"]
        P5["_process_player_distance"]
        P6["_process_fitness_entities"]
    end
    
    subgraph Storage["💾 PostgreSQL"]
        S1["competitions<br/>seasons"]
        S2["squads<br/>players<br/>teams"]
        S3["events + 8 types<br/>ball_in_play, card, goals..."]
        S4["distance_covered"]
        S5["player_distance"]
        S6["player_fitness_runs<br/>+ summaries"]
    end
    
    subgraph Output["📊 Output"]
        O1["Exports JSON"]
        O2["Analytics VIEWs"]
        O3["API Ready"]
    end
    
    API --> Download
    D1 --> P1
    D2 --> P2
    D3 --> P3
    D4 --> P4
    D5 --> P5
    D6 --> P6
    
    P1 --> S1
    P2 --> S2
    P3 --> S3
    P4 --> S4
    P5 --> S5
    P6 --> S6
    
    S1 --> O1
    S2 --> O1
    S3 --> O2
    S4 --> O2
    S5 --> O2
    S6 --> O3
    
    O1 --> O2
    O2 --> O3
    
    style API fill:#e3f2fd
    style Download fill:#fff3e0
    style Processing fill:#f3e5f5
    style Storage fill:#fce4ec
    style Output fill:#e8f5e9
```

---

## 📋 Résumé des Étapes

| Étape | Composant | Fichiers | Traitement | Sortie |
|-------|-----------|----------|-----------|--------|
| **1. API Call** | API Providers | - | Fetch competition data | JSON responses |
| **2. Download** | ScraperCoordinator | 6 fichiers | Store in `/exports/json_outputs/{game_id}/` | Files saved |
| **3. Extract** | Parser modules | `.json` | Read & validate schema | In-memory objects |
| **4. Transform** | Orchestrators | Objects | Map IDs, calculate metrics | Mapped data |
| **5. Load** | Database writer | Mapped data | Batch insert + FK checks | PostgreSQL tables |
| **6. Aggregate** | Summary calculator | DB records | PlayerFitnessSummary & TeamFitnessSummary | Aggregated metrics |
| **7. Verify** | Validator | DB state | Count records, check metrics | Quality report |
| **8. Export** | JSON exporter | Aggregations | Create match exports | JSON files |
| **9. Visualize** | API + Frontend | API calls | React components display | Web UI |

---

## ⚡ Performance Timeline

```
🌐 API Call & Response           : 0.5s
📥 Download 6 JSON Files         : 2.0s
🔄 ETL Processing                : 7.0s
   ├─ Parse lineups              : 1.0s
   ├─ Parse events (500+)        : 2.0s
   ├─ Parse distance             : 1.5s
   └─ Parse fitness (3,082)      : 3.0s
💾 Database Insert               : 1.0s
📊 Calculate Summaries           : 0.5s
✅ Verify & Commit               : 0.5s
📤 Export JSON                   : 0.5s
─────────────────────────────────────
📈 **TOTAL TIME PER COMPETITION** : ~13 seconds
```

---

## 🎯 Utilisation dans le Code

### Appel du pipeline:
```python
# backend/src/orchestration/scraper_coordinator.py
coordinator = ScraperCoordinator()
stats = coordinator.scrape_competition(
    provider='sportsdynamics',
    competition_id='comp_123'
)
```

### Pipeline complet exécuté:
1. **_fetch_competition_data()** → Appel API
2. **_download_files()** → Télécharge 6 fichiers JSON
3. **_process_competition_metadata()** → ETL métadonnées
4. **_process_lineups()** → ETL squads & joueurs
5. **_process_events()** → ETL événements (500+)
6. **_process_distance_covered()** → ETL distance
7. **_process_fitness_entities()** → ETL fitness (3,082 runs) ✅
8. **_verify_data()** → Validation
9. **export_to_json()** → Export résultats

---

## 📊 Fichiers JSON du Pipeline

| Fichier | Lignes | Contenu | Processeur |
|---------|--------|---------|-----------|
| **competition_info.json** | 50-100 | Meta: competition, season, dates | `_process_competition_metadata()` |
| **lineups.json** | 100-200 | Squads, players, positions | `_process_lineups()` |
| **events.json** | 500-1000 | Passes, shots, cards, goals | `_process_events()` |
| **distance_covered.json** | 100-200 | Team distance by zone & period | `_process_distance_covered()` |
| **player_distance.json** | 200-400 | Individual player distance data | `_process_player_distance()` |
| **fitness_entities.json** | 3,082 | Run tracking with 51 fields | `_process_fitness_entities()` |

---

## 💡 Notes Importantes

- ✅ **Idempotent**: Le pipeline peut être réexécuté sans dupliquer données
- ✅ **Transactionnel**: Rollback sur erreur
- ✅ **Validé**: FK constraints + data quality checks
- ⚡ **Performant**: Batch insert ~500 records/s
- 📊 **Analytics-Ready**: VIEWs créées automatiquement après load

