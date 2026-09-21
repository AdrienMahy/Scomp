# 🎯 Scomp - Diagrammes Visuels Interactifs

---

## 📊 Diagramme 1: Architecture Globale (Couches)

```mermaid
graph TB
    User["👤 Utilisateur"]
    
    subgraph Frontend["🎨 FRONTEND (React + Vite)"]
        GamesList["📺 GamesList<br/>Liste des matchs"]
        GameDetail["📋 GameDetail<br/>Détails d'un match"]
        ScrapePage["🔄 ScrapePage<br/>Lancer un scrape"]
        TasksPage["📊 TasksPage<br/>Suivi des tâches"]
    end
    
    subgraph API["🔌 FASTAPI (Backend Python)"]
        GamesRoute["GET /api/games<br/>GET /api/games/rounds"]
        CompRoute["GET /api/competitions"]
        TasksRoute["POST/GET /api/tasks"]
        PlayersRoute["GET /api/players"]
    end
    
    subgraph Orchestration["🎯 ORCHESTRATION"]
        Coordinator["ScraperCoordinator<br/>Coordonne le scrape"]
        FilterSystem["🔧 Filter System<br/>GraphQL Builder"]
    end
    
    subgraph Clients["📡 API CLIENTS"]
        SportsDynClient["SportsDynamics<br/>Client"]
        PerformClient["Perform<br/>Client"]
        SSClient["SecondSpectrum<br/>Client"]
    end
    
    subgraph External["🌐 EXTERNAL APIs"]
        SportsDynAPI["SportsDynamics<br/>GraphQL API"]
        PerformAPI["Perform<br/>API"]
        SSAPI["SecondSpectrum<br/>API"]
    end
    
    subgraph Database["🗄️ POSTGRESQL 16"]
        Games["games<br/>Teams, Players<br/>Lineups, Events"]
        GameStatus["game_status<br/>(tracking)"]
        OutputFiles["output_files<br/>(raw responses)"]
    end
    
    User -->|interacts| GamesList
    GamesList -->|fetch| GamesRoute
    GameDetail -->|fetch| GamesRoute
    ScrapePage -->|trigger| TasksRoute
    TasksPage -->|poll| TasksRoute
    
    GamesRoute -->|query| Database
    CompRoute -->|query| Database
    TasksRoute -->|create async task| Coordinator
    PlayersRoute -->|query| Database
    
    Coordinator -->|uses| FilterSystem
    Coordinator -->|calls| SportsDynClient
    Coordinator -->|persist| Database
    
    SportsDynClient -->|GraphQL| SportsDynAPI
    PerformClient -->|REST| PerformAPI
    SSClient -->|REST| SSAPI
    
    FilterSystem -->|transforms| SportsDynClient
    
    style User fill:#90EE90
    style Frontend fill:#87CEEB
    style API fill:#FFB6C1
    style Orchestration fill:#FFD700
    style Clients fill:#DDA0DD
    style External fill:#F0E68C
    style Database fill:#FF6347
```

---

## 🔄 Diagramme 2: Flux Détaillé - Affichage des Matchs

```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    
    User->>React: Click "Games" page
    React->>API: GET /api/games/rounds
    API->>DB: SELECT DISTINCT round_name FROM games
    DB-->>API: ["Round 1", "Round 2", ...]
    API-->>React: Rounds list
    React-->>User: Display rounds dropdown
    
    User->>React: Select "Round 1"
    React->>API: GET /api/games?round_name=Round%201
    API->>DB: SELECT * FROM games WHERE round_name='Round 1'
    DB-->>API: [game1, game2, ...]
    API-->>React: Games data
    React-->>User: Display games list
    
    User->>React: Click on game
    React->>API: GET /api/games/{game_id}
    API->>DB: SELECT * FROM games WHERE id={game_id}<br/>+ JOIN squads, players, events
    DB-->>API: Complete game object
    API-->>React: Game details
    React-->>User: Display full game view
```

---

## 🔄 Diagramme 3: Flux Détaillé - Scraping avec GraphQL

```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant API as FastAPI
    participant Celery as Celery Task
    participant Coordinator as Orchestration
    participant Filter as Filter System
    participant Client as SportsDynamics Client
    participant GraphQL as SportsDynamics API
    participant DB as PostgreSQL
    
    User->>React: Click "Scrape Ligue 2"
    React->>API: POST /api/tasks<br/>{ provider, competition_id, season_id }
    
    API->>Celery: Queue scraping_task(...)
    API-->>React: { task_id, status: "pending" }
    React-->>User: Redirect to Tasks page
    
    Celery->>Coordinator: scrape_competition(...)
    
    Coordinator->>Filter: build_payload_from_values({<br/>competition_id: "comp-123",<br/>season: "2024"<br/>})
    
    Filter-->>Coordinator: { competition: {id: {equals: "comp-123"}},<br/>season: {season: {equals: [2024, 2025]}} }
    
    Coordinator->>Client: get_games(competition_id, season_id)
    
    Client->>GraphQL: POST /graphql<br/>{<br/>  query: "query getGames(...)",<br/>  variables: { filters, pagination }<br/>}
    
    GraphQL-->>Client: {<br/>  data: {<br/>    getGames: {<br/>      items: [{...}, {...}]<br/>    }<br/>  }<br/>}
    
    Client-->>Coordinator: [game1, game2, ...]
    
    Coordinator->>DB: BEGIN transaction
    Coordinator->>DB: INSERT INTO games (id, name, ...)
    Coordinator->>DB: INSERT INTO teams (...)
    Coordinator->>DB: INSERT INTO players (...)
    Coordinator->>DB: INSERT INTO lineup_players (...)
    Coordinator->>DB: INSERT INTO game_goals, game_cards (...)
    Coordinator->>DB: COMMIT
    
    DB-->>Coordinator: ✅ Committed
    
    React->>API: GET /api/tasks/{task_id}
    API->>DB: SELECT * FROM scraping_tasks WHERE id={task_id}
    DB-->>API: { status: "completed", progress: 100 }
    API-->>React: Task status
    React-->>User: "✅ Scraping complete!"
    
    User->>React: Go back to Games
    React->>API: GET /api/games
    DB-->>API: [... new games ...]
    React-->>User: Display updated games
```

---

## 📊 Diagramme 4: Transformation GraphQL (Filter System)

```mermaid
graph LR
    Input["📝 INPUT<br/>{<br/>  round: ['Round 1', 'Round 2'],<br/>  competition_id: 'comp-123',<br/>  available: true<br/>}"]
    
    Config["⚙️ CONFIG<br/>graphql_filters.json<br/>predefined_filters.json"]
    
    Processor["🔄 PROCESSOR<br/>QueryFilterConfig<br/>.build_payload_from_values"]
    
    Output["🎯 OUTPUT<br/>{<br/>  round: {name: {in: [...]}},<br/>  competition: {id: {equals: '...'}},<br/>  available: {equals: true}<br/>}"]
    
    API["📡 API CALL<br/>POST /graphql<br/>variables: {filters: {...}}"]
    
    Input -->|read| Config
    Input -->|transform| Processor
    Config -->|guide| Processor
    Processor -->|produces| Output
    Output -->|sent to| API
    
    style Input fill:#87CEEB
    style Config fill:#FFD700
    style Processor fill:#FFB6C1
    style Output fill:#90EE90
    style API fill:#F0E68C
```

---

## 📈 Diagramme 5: Modèle de Données (Entities + Relations)

```mermaid
erDiagram
    COMPETITIONS ||--o{ SEASONS : has
    COMPETITIONS ||--o{ TEAMS : has
    SEASONS ||--o{ GAMES : contains
    GAMES ||--o{ PERIODS : divides
    GAMES ||--o{ LINEUPS : has
    GAMES ||--o{ GAME_GOALS : contains
    GAMES ||--o{ GAME_CARDS : contains
    GAMES ||--o{ GAME_STATUS : tracks
    GAMES ||--o{ OUTPUT_FILES : has
    
    TEAMS ||--o{ PLAYERS : has
    LINEUPS ||--o{ LINEUP_PLAYERS : contains
    LINEUP_PLAYERS }o--|| PLAYERS : "maps to"
    LINEUP_PLAYERS }o--|| TEAMS : "assigned to"
    
    GAME_GOALS }o--|| PLAYERS : "scored by"
    GAME_CARDS }o--|| PLAYERS : "received by"
    
    GAMES ||--o{ DISTANCE_ANALYTICS : measures

    COMPETITIONS : string id PK
    COMPETITIONS : string name
    COMPETITIONS : string region
    
    SEASONS : string id PK
    SEASONS : string season
    SEASONS : string competition_id FK
    
    GAMES : string id PK
    GAMES : string name
    GAMES : datetime starts_at
    GAMES : datetime played_at
    GAMES : int home_score
    GAMES : int away_score
    GAMES : string round_name
    GAMES : string competition_id FK
    GAMES : string season_id FK
    
    TEAMS : string id PK
    TEAMS : string name
    TEAMS : string brand
    TEAMS : string competition_id FK
    
    PLAYERS : string id PK
    PLAYERS : string firstName
    PLAYERS : string lastName
    PLAYERS : string position
    
    LINEUPS : string id PK
    LINEUPS : string game_id FK
    LINEUPS : string team_id FK
    
    LINEUP_PLAYERS : string id PK
    LINEUP_PLAYERS : string game_id FK
    LINEUP_PLAYERS : string team_id FK
    LINEUP_PLAYERS : string player_id FK
    LINEUP_PLAYERS : int jerseyNumber
    LINEUP_PLAYERS : boolean isStarting
    
    GAME_GOALS : string id PK
    GAME_GOALS : string game_id FK
    GAME_GOALS : string player_id FK
    GAME_GOALS : float timestamp
    
    GAME_CARDS : string id PK
    GAME_CARDS : string game_id FK
    GAME_CARDS : string player_id FK
    GAME_CARDS : string card_type
    
    GAME_STATUS : string game_id PK
    GAME_STATUS : boolean available
    GAME_STATUS : json output_files
    GAME_STATUS : string output_files_hash
    
    OUTPUT_FILES : string id PK
    OUTPUT_FILES : string game_id FK
    OUTPUT_FILES : string fileName
    OUTPUT_FILES : string fileType
    OUTPUT_FILES : text file_url
    
    DISTANCE_ANALYTICS : string id PK
    DISTANCE_ANALYTICS : string game_id FK
    DISTANCE_ANALYTICS : float distance_m
```

---

## 🔗 Diagramme 6: Routes API et Leurs Dépendances

```mermaid
graph TB
    subgraph Client["🎨 Frontend"]
        GamesList["GamesList.jsx"]
        GameDetail["GameDetail.jsx"]
        TeamsPage["TeamsPlayersPage.jsx"]
        ScrapePage["ScrapePage.jsx"]
        TasksPage["TasksPage.jsx"]
    end
    
    subgraph Endpoints["🔌 FastAPI Routes"]
        GetGames["GET /api/games<br/>GET /api/games/rounds"]
        GetGame["GET /api/games/{id}"]
        GetComps["GET /api/competitions"]
        GetTeams["GET /api/teams"]
        GetPlayers["GET /api/players"]
        PostTask["POST /api/tasks"]
        GetTasks["GET /api/tasks"]
        GetTaskDetail["GET /api/tasks/{id}"]
    end
    
    subgraph Handlers["📦 Business Logic"]
        GameHandler["GameHandler"]
        CompHandler["CompetitionHandler"]
        TaskHandler["TaskHandler"]
    end
    
    subgraph Persistence["💾 Database Layer"]
        QueryGames["query(Game).filter(...)<br/>.all()"]
        QueryComps["query(Competition).all()"]
        QueryTeams["query(Team).all()"]
        QueryTasks["query(ScrapingTask)<br/>.filter(...)"]
    end
    
    GamesList -->|GET /games/rounds| GetGames
    GamesList -->|GET /games| GetGames
    GameDetail -->|GET /games/{id}| GetGame
    TeamsPage -->|GET /competitions| GetComps
    TeamsPage -->|GET /teams| GetTeams
    TeamsPage -->|GET /players| GetPlayers
    ScrapePage -->|POST /tasks| PostTask
    TasksPage -->|GET /tasks| GetTasks
    TasksPage -->|GET /tasks/{id}| GetTaskDetail
    
    GetGames -->|uses| GameHandler
    GetGame -->|uses| GameHandler
    GetComps -->|uses| CompHandler
    GetTeams -->|uses| CompHandler
    PostTask -->|uses| TaskHandler
    GetTasks -->|uses| TaskHandler
    GetTaskDetail -->|uses| TaskHandler
    
    GameHandler -->|executes| QueryGames
    CompHandler -->|executes| QueryComps
    CompHandler -->|executes| QueryTeams
    TaskHandler -->|executes| QueryTasks
    
    style Client fill:#87CEEB
    style Endpoints fill:#FFB6C1
    style Handlers fill:#FFD700
    style Persistence fill:#FF6347
```

---

## 🎯 Diagramme 7: Cycle de Scraping Complet

```mermaid
graph TB
    Start["▶️ USER TRIGGERS SCRAPING"] -->|POST /api/tasks| CreateTask["1️⃣ Create Task<br/>status: PENDING"]
    
    CreateTask -->|Queue| Celery["2️⃣ Celery Worker<br/>Picks up task"]
    
    Celery -->|Call| Coordinator["3️⃣ ScraperCoordinator<br/>.scrape_competition()"]
    
    Coordinator -->|Build| FilterSys["4️⃣ Filter System<br/>Transform values→GraphQL"]
    
    FilterSys -->|Returns| Client["5️⃣ SportsDynamicsClient<br/>.get_games()"]
    
    Client -->|GraphQL Query| GraphQLAPI["6️⃣ SportsDynamics API<br/>POST /graphql"]
    
    GraphQLAPI -->|JSON Response| Parse["7️⃣ Parse Response<br/>Extract games, squads, events"]
    
    Parse -->|Transform| Transform["8️⃣ Transform to ORM<br/>Game, Team, Player objects"]
    
    Transform -->|Persist| SaveDB["9️⃣ Save to Database<br/>BEGIN TRANSACTION"]
    
    SaveDB -->|INSERT| Insert["↳ games<br/>↳ teams<br/>↳ players<br/>↳ lineups<br/>↳ goals<br/>↳ cards"]
    
    Insert -->|COMMIT| Complete["🔟 Complete<br/>COMMIT TRANSACTION"]
    
    Complete -->|Update| UpdateTask["1️⃣1️⃣ Update Task<br/>status: COMPLETED"]
    
    UpdateTask -->|Poll| Frontend["1️⃣2️⃣ Frontend detects<br/>GET /api/tasks/{id}"]
    
    Frontend -->|Refresh| Display["1️⃣3️⃣ Display Updated Data<br/>Show new games"]
    
    Display -->|✅ Done| End["🎉 SCRAPING COMPLETE"]
    
    style Start fill:#90EE90
    style Celery fill:#FFD700
    style Coordinator fill:#FFB6C1
    style FilterSys fill:#87CEEB
    style GraphQLAPI fill:#F0E68C
    style SaveDB fill:#FF6347
    style End fill:#90EE90
```

---

## 📡 Diagramme 8: GraphQL Request / Response Flow

```mermaid
graph LR
    App["📱 App<br/>Calls<br/>client.get_games()"]
    
    Client["🔌 Client<br/>Builds<br/>GraphQL payload"]
    
    Payload["📦 Payload<br/>{<br/>  query: '...',<br/>  variables: {<br/>    filters: [...],<br/>    pagination: {...}<br/>  }<br/>}"]
    
    HTTP["📡 HTTP POST<br/>https://api.sportsdynamics.com/graphql<br/>Headers: x-sd-api-key: ..."]
    
    GQL["🔍 GraphQL<br/>Parse query<br/>Execute resolvers<br/>Join data"]
    
    Result["📨 Response<br/>{<br/>  data: {<br/>    getGames: {<br/>      items: [...games...]<br/>    }<br/>  }<br/>}"]
    
    Parse["🔄 Parse JSON<br/>Extract items<br/>Build Python objects"]
    
    Return["✅ Return<br/>List[Game]"]
    
    App -->|calls| Client
    Client -->|builds| Payload
    Payload -->|sent via| HTTP
    HTTP -->|reaches| GQL
    GQL -->|executes| Result
    Result -->|received by| Parse
    Parse -->|transforms| Return
    
    style App fill:#87CEEB
    style Client fill:#FFB6C1
    style Payload fill:#FFD700
    style HTTP fill:#F0E68C
    style GQL fill:#FFB347
    style Result fill:#90EE90
    style Parse fill:#DDA0DD
    style Return fill:#90EE90
```

---

## 🗄️ Diagramme 9: Database Queries (Common Patterns)

```mermaid
graph TB
    subgraph Queries["COMMON SQL QUERIES"]
        Q1["Get games by round<br/>SELECT * FROM games<br/>WHERE round_name = ?"]
        
        Q2["Get game with squads<br/>SELECT g.* FROM games g<br/>LEFT JOIN lineup_teams lt ON g.id = lt.game_id<br/>LEFT JOIN lineup_players lp ON lt.id = lp.lineup_id<br/>LEFT JOIN players p ON lp.player_id = p.id<br/>WHERE g.id = ?"]
        
        Q3["Get available rounds<br/>SELECT DISTINCT round_name<br/>FROM games<br/>ORDER BY round_name"]
        
        Q4["Get player stats<br/>SELECT p.id, p.firstName, p.lastName,<br/>  COUNT(g.id) as games_played,<br/>  COUNT(gg.id) as goals,<br/>  COUNT(gc.id) as cards<br/>FROM players p<br/>LEFT JOIN lineup_players lp ON p.id = lp.player_id<br/>LEFT JOIN games g ON lp.game_id = g.id<br/>LEFT JOIN game_goals gg ON p.id = gg.player_id<br/>LEFT JOIN game_cards gc ON p.id = gc.player_id<br/>GROUP BY p.id"]
    end
    
    SQLAlchemy["🐍 SQLAlchemy ORM<br/>.query(Model)<br/>.filter(...)<br/>.all()"]
    
    Session["💾 DB Session<br/>Connection pool<br/>Transaction mgmt"]
    
    PostgreSQL["🗄️ PostgreSQL 16<br/>Execute SQL<br/>Return rows"]
    
    Queries -->|translate to| SQLAlchemy
    SQLAlchemy -->|uses| Session
    Session -->|executes| PostgreSQL
    PostgreSQL -->|returns| SQLAlchemy
    
    style Queries fill:#FFD700
    style SQLAlchemy fill:#87CEEB
    style Session fill:#FFB6C1
    style PostgreSQL fill:#FF6347
```

---

## 📊 Diagramme 10: Task Monitoring Flow

```mermaid
graph LR
    TaskCreated["📌 Task Created<br/>status: PENDING<br/>progress: 0"]
    
    TaskStarted["▶️ Task Started<br/>status: IN_PROGRESS<br/>progress: 5"]
    
    TaskProcessing["⚙️ Processing<br/>status: IN_PROGRESS<br/>progress: 25-75"]
    
    TaskCompleting["🏁 Finalizing<br/>status: IN_PROGRESS<br/>progress: 90"]
    
    TaskDone["✅ Done<br/>status: COMPLETED<br/>progress: 100"]
    
    TaskError["❌ Error<br/>status: FAILED<br/>error_msg: ..."]
    
    FrontendPoll["🎨 Frontend<br/>Polls every 2s<br/>GET /api/tasks/{id}"]
    
    UpdateUI["🖥️ Update UI<br/>Show progress bar<br/>Display status"]
    
    TaskCreated -->|Celery picks up| TaskStarted
    TaskStarted -->|API calls SD| TaskProcessing
    TaskProcessing -->|Transform & Save| TaskCompleting
    TaskCompleting -->|Commit DB| TaskDone
    
    TaskStarted -->|If error| TaskError
    TaskProcessing -->|If error| TaskError
    
    FrontendPoll -->|reads| TaskCreated
    FrontendPoll -->|reads| TaskStarted
    FrontendPoll -->|reads| TaskProcessing
    FrontendPoll -->|reads| TaskCompleting
    FrontendPoll -->|reads| TaskDone
    FrontendPoll -->|reads| TaskError
    
    TaskDone -->|detected by| FrontendPoll
    FrontendPoll -->|triggers| UpdateUI
    
    UpdateUI -->|shows| CompletionMsg["'Scraping complete!'<br/>Refresh games list"]
    
    style TaskCreated fill:#FFD700
    style TaskStarted fill:#FFA500
    style TaskProcessing fill:#FFB6C1
    style TaskCompleting fill:#87CEEB
    style TaskDone fill:#90EE90
    style TaskError fill:#FF6347
    style FrontendPoll fill:#87CEEB
    style UpdateUI fill:#90EE90
```

---

## 🔑 Key Points from Diagrams

1. **Frontend sends simple HTTP requests** (GET/POST) to FastAPI
2. **FastAPI queries database** via SQLAlchemy ORM
3. **Scraping is triggered asynchronously** via Celery
4. **Filter System transforms simple values** to complex GraphQL payloads
5. **GraphQL queries are sent to SportsDynamics** via HTTP POST
6. **Results are transformed** and persisted to PostgreSQL
7. **Frontend polls task status** and updates when complete
8. **Database schema is normalized** with proper relationships
9. **All data flows through layers** (Frontend → API → Orchestration → Clients → DB)
10. **Error handling and monitoring** at each layer

