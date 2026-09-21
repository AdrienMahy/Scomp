# Scomp Backend

Sports data scraping and API service for aggregating football competition data from multiple providers.

## Architecture

- **API**: FastAPI REST API for data access and task management
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Scraper**: Modular scrapers for different providers (SportsDynamics, Perform, SecondSpectrum)
- **Queue**: Celery with Redis for async scraping tasks
- **UI**: React frontend (future) for monitoring and control

## Quick Start

### Local Development

1. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**
   ```bash
   python -c "from src.database import init_db; init_db()"
   ```

4. **Run development server**
   ```bash
   uvicorn src.main:app --reload
   ```

Access API at `http://localhost:8000/docs`

### Docker Compose

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache/broker
- FastAPI backend (http://localhost:8000)
- Celery worker for scraping
- Celery Beat for scheduling

## Project Structure

```
backend/
├── src/
│   ├── config/          # Configuration & DB setup
│   ├── models/          # SQLAlchemy ORM models
│   ├── api/             # API clients (SportsDynamics, etc.)
│   ├── scraper/         # Scraper implementations
│   ├── web/             # FastAPI routes & schemas
│   ├── tasks/           # Celery tasks
│   ├── database/        # DB utilities
│   └── main.py          # FastAPI app
└── requirements.txt
```

## API Endpoints

### Competitions
- `GET /competitions` - List all competitions
- `GET /competitions/{id}` - Get competition details

### Games
- `GET /games` - List games (with filtering)
- `GET /games/{id}` - Get game details

### Tasks
- `GET /tasks` - List scraping tasks
- `GET /tasks/{id}` - Get task status
- `POST /tasks` - Create new scraping task

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `POSTGRES_*` - Database connection
- `SPORTSDYNAMICS_API_KEY` - API credentials
- `CELERY_BROKER_URL` - Redis connection

## Development

### Run tests
```bash
pytest
```

### Format code
```bash
black src/
```

### Lint
```bash
flake8 src/
```

## Deployment

See main project README for deployment strategies (Docker, Kubernetes, etc.)
