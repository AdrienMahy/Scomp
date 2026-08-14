# 🏛️ Architecture Globale de Scomp - Ma vision

## 🎯 Contexte du Projet

**Objectif:** Scraper des données de sports (GameS, Compétitions, Équipes, Joueurs) depuis **plusieurs providers** (SportsDynamics, Perform, SecondSpectrum) et les centraliser dans une **base de données unique** avec une **interface web**.

---

## 🏗️ Architecture Global (Comment JE l'organisérais)

```
┌─────────────────────────────────────────────────────────────────┐
│                       UTILISATEUR / ADMIN                        │
│              (Web UI + Système de Monitoring)                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴───────────────┐
        │                              │
        ▼                              ▼
    ┌─────────────┐            ┌─────────────┐
    │  WEB LAYER  │            │  CLI TASKS  │
    │  (FastAPI)  │            │  (Commands) │
    └──────┬──────┘            └──────┬──────┘
           │                         │
           └────────────┬───────────┘
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
┌────────────────────┐        ┌──────────────────┐
│  ORCHESTRATION     │        │  CELERY TASKS    │
│  LAYER             │        │  (Async Jobs)    │
│  ┌──────────────┐  │        │  ┌────────────┐  │
│  │ Scrape Flow  │  │        │  │ Scrap Tasks│  │
│  │ Coordinator  │  │        │  │ Beat Sched │  │
│  └──────────────┘  │        │  │ Transformers   │
└────────┬───────────┘        └────────┬─────────┘
         │                            │
         └────────────┬───────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌──────────────────────┐   ┌──────────────────────┐
│ PROVIDER LAYER       │   │ DATABASE LAYER       │
│ ┌────────────────┐   │   │ ┌────────────────┐   │
│ │ SportsDynamics │   │   │ │ SQLAlchemy ORM │   │
│ │ Perform        │   │   │ │ Models         │   │
│ │ SecondSpectrum │   │   │ │ Session Mgmt   │   │
│ └────────────────┘   │   │ └────────────────┘   │
│ ┌────────────────┐   │   └──────────────────────┘
│ │ API Clients    │   │            │
│ │ Transformers   │   │            ▼
│ │ Cache Layer    │   │   ┌──────────────────────┐
│ └────────────────┘   │   │ PostgreSQL 16        │
└─────────┬────────────┘   │ (Persistent Storage) │
          │                └──────────────────────┘
          ▼
┌──────────────────────┐
│ EXTERNAL APIs        │
│ (SportsDynamics, ..) │
└──────────────────────┘
```

---

## 📊 Les 5 COUCHES en détail

### 1️⃣ COUCHE PRÉSENTATION (FastAPI + Web)

```python
# backend/src/main.py
app = FastAPI()

@app.get("/api/competitions")
def list_competitions():
    """Affiche les compétitions scrappées"""
    
@app.post("/api/scraping/start")
def start_scraping_task(provider: str, competition_id: str):
    """Lance une tâche de scraping asynchrone"""
    # Envoie à Celery
    scrape_task.delay(provider, competition_id)
    
@app.get("/api/scraping/status/{task_id}")
def check_scraping_status(task_id: str):
    """Retourne le statut d'une tâche"""
    # Cherche dans Redis/Base de données
```

**Responsabilité:** Fournir une interface REST pour contrôler/monitorer le système

---

### 2️⃣ COUCHE ORCHESTRATION (Coordinateur des scrapes)

```python
# backend/src/orchestration/scraper_coordinator.py

class ScraperCoordinator:
    """Orchestre le scraping multi-provider"""
    
    def __init__(self):
        self.providers = {
            "sportsdynamics": SportsDynamicsProvider(),
            "perform": PerformProvider(),
            "secondspectrum": SecondSpectrumProvider()
        }
        self.db = DatabaseSession()
    
    def scrape_competition(self, provider: str, competition_id: str):
        """
        Orchestration complète:
        1. Vérifie que la compétition existe
        2. Lance le scraping du provider
        3. Transforme les données
        4. Persiste en BD
        5. Mets à jour le statut
        """
        # Étape 1: Load ou crée la compétition
        competition = self.db.get_or_create_competition(competition_id)
        
        # Étape 2: Get provider
        provider_client = self.providers.get(provider)
        if not provider_client:
            raise ValueError(f"Provider {provider} not found")
        
        # Étape 3: Scrape
        try:
            raw_data = provider_client.fetch_games(competition_id)
            
            # Étape 4: Transform
            games = [
                transform_game(g, competition_id)
                for g in raw_data
            ]
            
            # Étape 5: Persist
            self.db.bulk_insert_games(games)
            self.db.commit()
            
            # Étape 6: Update task
            return {"status": "COMPLETED", "games_count": len(games)}
            
        except Exception as e:
            self.db.update_task_status("FAILED", str(e))
            raise
```

**Responsabilité:** Orchestre le flux complet scrape → transform → persist

---

### 3️⃣ COUCHE TÂCHES ASYNC (Celery Workers)

```python
# backend/src/tasks/celery_config.py
from celery import Celery

app = Celery('scomp')
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# backend/src/tasks/scrape_tasks.py

@app.task(bind=True, max_retries=3)
def scrape_sportsdynamics_competition(self, task_id: str, comp_id: str):
    """Tâche Celery: Scrape SportsDynamics"""
    try:
        coordinator = ScraperCoordinator()
        result = coordinator.scrape_competition("sportsdynamics", comp_id)
        
        # Update task with result
        db.update_task(task_id, "COMPLETED", result)
        return result
        
    except Exception as exc:
        # Retry avec exponential backoff
        raise self.retry(exc=exc, countdown=60)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    """Tâches planifiées (Celery Beat)"""
    # Scrape SportsDynamics toutes les 6 heures
    sender.add_periodic_task(21600, scrape_sportsdynamics_competition.s())
    
    # Monitoring de santé toutes les 30 minutes
    sender.add_periodic_task(1800, check_provider_health.s())
```

**Responsabilité:** Exécuter les scrapes en arrière-plan, gérer les retries, planifier les jobs

---

### 4️⃣ COUCHE PROVIDERS (API Clients)

```
backend/src/providers/
├── __init__.py
├── base_provider.py          ← Interface abstraite
├── sportsdynamics_provider.py
├── perform_provider.py
└── secondspectrum_provider.py
```

```python
# backend/src/providers/base_provider.py

class BaseProvider(ABC):
    """Interface commune pour tous les providers"""
    
    @abstractmethod
    def fetch_competitions(self) -> List[Dict]:
        pass
    
    @abstractmethod
    def fetch_games(self, competition_id: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def fetch_teams(self, competition_id: str) -> List[Dict]:
        pass

# backend/src/providers/sportsdynamics_provider.py

class SportsDynamicsProvider(BaseProvider):
    """Client pour l'API SportsDynamics"""
    
    def __init__(self):
        self.client = SportsDynamicsClient()
        self.filter_config = get_filter_config()
        self.cache = RedisCache()  # Pour les requêtes répétées
    
    def fetch_games(self, competition_id: str, filters: Dict = None):
        """
        Fetch des games avec gestion du cache
        """
        cache_key = f"sportsdynamics:games:{competition_id}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Construct filter payload
        filter_values = {
            "available": True,
            "competition_id": competition_id,
            **(filters or {})
        }
        
        payload = self.filter_config.build_payload_from_values(
            "get_games",
            filter_values
        )
        
        # Query API
        query = """query GetGames($filters: GameFilters, $limit: Int) {
            games(filters: $filters, limit: $limit) {
                id name startsAt homeTeam { id name }
                awayTeam { id name } homeScore awayScore
            }
        }"""
        
        result = self.client.query(query, {
            "filters": payload,
            "limit": 100
        })
        
        games = result.get("games", [])
        
        # Cache pour 1 heure
        self.cache.set(cache_key, games, ttl=3600)
        
        return games
```

**Responsabilité:** Intéragir avec les APIs externes, gérer l'authentification, le cache

---

### 5️⃣ COUCHE DONNÉES (ORM + BD)

```python
# backend/src/models/game.py

class Game(Base):
    __tablename__ = "games"
    
    id = Column(UUID, primary_key=True)
    competition_id = Column(UUID, ForeignKey("competitions.id"))
    season_id = Column(UUID, ForeignKey("seasons.id"))
    home_team_id = Column(UUID, ForeignKey("teams.id"))
    away_team_id = Column(UUID, ForeignKey("teams.id"))
    
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    
    starts_at = Column(DateTime)
    played_at = Column(DateTime, nullable=True)
    
    # Relations
    competition = relationship("Competition", back_populates="games")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    
    raw_data = Column(JSON)  # Stocke les données brutes du provider

# backend/src/database.py

class Database:
    """Gestion des sessions et transactions"""
    
    def __init__(self):
        self.SessionLocal = sessionmaker(bind=engine)
    
    def bulk_insert_games(self, games: List[Game]):
        """Insert/Update plusieurs games de façon efficace"""
        session = self.SessionLocal()
        try:
            # Bulk insert
            session.bulk_save_objects(games)
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_games_by_competition(self, comp_id: str):
        """Query les games d'une compétition"""
        session = self.SessionLocal()
        return session.query(Game).filter(
            Game.competition_id == comp_id
        ).all()
```

**Responsabilité:** Persister et récupérer les données

---

## 🔄 FLUX COMPLET D'UN SCRAPE

```
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 1: USER ACTION                                         │
│ Admin clique "Scrape SportsDynamics - Ligue 1"              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 2: WEB LAYER (FastAPI)                                │
│ POST /api/scraping/start                                     │
│  ├── Reçoit: provider="sportsdynamics", comp_id="ligue1"    │
│  ├── Crée ScrapingTask (status=PENDING)                     │
│  └── Envoie à Celery                                         │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 3: CELERY WORKER (Background)                         │
│ scrape_sportsdynamics_competition(task_id, comp_id)         │
│  ├── Update: status = RUNNING                               │
│  └── Appelle: ScraperCoordinator.scrape_competition()       │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 4: ORCHESTRATOR                                       │
│ ScraperCoordinator.scrape_competition()                     │
│  1. Load/Create Competition ORM                             │
│  2. Get SportsDynamicsProvider                              │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 5: PROVIDER (API Client)                              │
│ SportsDynamicsProvider.fetch_games()                        │
│  1. Check Redis cache (miss)                                │
│  2. Build filter payload                                    │
│     {"available": {"equals": true}, ...}                   │
│  3. Execute GraphQL query                                   │
│  4. Cache result (TTL: 1h)                                  │
│  5. Return raw games data                                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 6: API EXTERNAL (SportsDynamics)                      │
│ POST https://api-v2.sportsdynamics.eu/graphql               │
│ {                                                            │
│   "query": "query GetGames {...}",                          │
│   "variables": {                                            │
│     "filters": {...},  ← Notre payload magique             │
│     "limit": 100                                            │
│   }                                                          │
│ }                                                            │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼ Response: [{id, name, homeTeam, ...}, ...]
                   │
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 7: ORCHESTRATOR (Transform)                           │
│ Pour chaque game:                                            │
│  1. Parse JSON response                                      │
│  2. Create Game ORM object                                   │
│  3. Resolve team_ids (lookup ou create)                      │
│  4. Set timestamps, scores                                   │
│  5. Store raw_data (JSON)                                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 8: DATABASE LAYER (Persist)                           │
│ bulk_insert_games(games)                                    │
│  1. Session start                                            │
│  2. Bulk insert 50+ games                                   │
│  3. Commit transaction                                       │
│  └─→ PostgreSQL ✅                                           │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 9: CELERY COMPLETES                                   │
│ Update ScrapingTask                                         │
│  ├── status = COMPLETED                                     │
│  ├── games_count = 47                                       │
│  └── ended_at = now()                                       │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ ÉTAPE 10: WEB LAYER RESPONSE                                │
│ User polls /api/scraping/status/{task_id}                   │
│ Response:                                                    │
│ {                                                            │
│   "status": "COMPLETED",                                    │
│   "games_count": 47,                                        │
│   "started_at": "2026-08-12T10:00:00Z",                    │
│   "ended_at": "2026-08-12T10:05:30Z"                       │
│ }                                                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Gestion d'erreurs et Resilience

```python
# RETRY STRATEGY
@app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def scrape_task(self, comp_id):
    try:
        return scraper.scrape(comp_id)
    except APITimeoutError as exc:
        # Retry après 60s
        raise self.retry(exc=exc, countdown=60)
    except APIPermissionError as exc:
        # Pas de retry (erreur d'authentification)
        update_task_status("FAILED_PERMISSION", str(exc))
    except Exception as exc:
        # Log et fail
        logger.exception(exc)
        raise

# CIRCUIT BREAKER
class ProviderHealthCheck:
    def __init__(self, provider_name):
        self.provider = provider_name
        self.failures = 0
        self.last_failure = None
    
    def check_health(self):
        """Avant chaque requête, vérifie si le provider est alive"""
        if self.failures >= 5:  # 5 erreurs
            if (time.time() - self.last_failure) < 300:  # Moins de 5 min
                raise ProviderDownError(f"{self.provider} is down")
        
        # Réinitialise après 5 minutes
        if (time.time() - self.last_failure) > 300:
            self.failures = 0
```

---

## 📈 Scalabilité et Performances

```
┌─────────────────────────────────────────────────────────────┐
│ BOTTLENECKS et SOLUTIONS                                    │
├─────────────────────────────────────────────────────────────┤
│ 1. API Rate Limiting                                        │
│    → Implémente une queue avec throttling                   │
│    → Scrape un provider à la fois                           │
│                                                             │
│ 2. Base de données lente                                    │
│    → Bulk insert 100 records par batch                      │
│    → Index sur (competition_id, season_id)                 │
│    → Partitioning par année si nécessaire                   │
│                                                             │
│ 3. Données dupliquées                                       │
│    → Upsert avec "ON CONFLICT DO UPDATE"                   │
│    → Compare raw_data pour détecter les changements        │
│                                                             │
│ 4. Cache inefficace                                         │
│    → Redis avec TTL intelligent                             │
│    → Invalidate au scrape                                   │
│                                                             │
│ 5. Workers insuffisant                                      │
│    → Horizontal scaling: 1 → 10 workers                     │
│    → Load balance avec Redis                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Monitoring et Observabilité

```python
# backend/src/monitoring/metrics.py

class ScrapeMetrics:
    """Collecte les stats des scrapes"""
    
    def record_scrape(self, provider: str, status: str, duration: float):
        """Enregistre une scrape"""
        metrics = {
            "provider": provider,
            "status": status,  # COMPLETED, FAILED, TIMEOUT
            "duration_seconds": duration,
            "timestamp": datetime.now()
        }
        # Envoie à Prometheus
        prometheus_client.histogram(
            'scrape_duration_seconds',
            duration,
            labels={'provider': provider}
        )

# Dashboards (Grafana)
# - Success rate par provider
# - Temps moyen de scrape
# - Nombre de games scrappés
# - Erreurs par type
```

---

## 🔗 Intégration Complète

```python
# Tests
┌────────────────┐     ┌─────────────┐     ┌──────────────┐
│ test_provider  │────→│ test_scraper│────→│ test_database│
└────────────────┘     └─────────────┘     └──────────────┘

# Déploiement
docker-compose up  # Lance:
  ├── PostgreSQL
  ├── Redis
  ├── FastAPI (port 8000)
  ├── Celery Worker × 3
  └── Celery Beat
  
# Monitoring
http://localhost:8000/docs        # FastAPI Swagger
http://localhost:3000             # Grafana (metrics)
redis-cli                         # Redis CLI
```

---

## 📋 Résumé: Mes 5 Principes

| Principe | Implémentation |
|----------|-----------------|
| **Separation of Concerns** | 5 couches distinctes |
| **Scalability** | Celery workers + queue |
| **Resilience** | Retry + circuit breaker + cache |
| **Observability** | Metrics + logging + monitoring |
| **Maintainability** | Config-driven filters + ORM |

---

## 🚀 Étapes de déploiement (Mon ordre)

```
1. ✅ API Client + Filter System (FAIT)
2. ⏳ Database models + migrations (Alembic)
3. ⏳ Orchestrator + Provider classes
4. ⏳ Celery tasks + Beat scheduler
5. ⏳ Web routes + API endpoints
6. ⏳ Monitoring + error handling
7. ⏳ Tests e2e
8. ⏳ Docker deployment
9. ⏳ Frontend React UI
10. ⏳ Production scale
```

---

**C'est la vision d'un système production-ready, modulaire et scalable !** 🚀

Des questions sur une couche spécifique?
