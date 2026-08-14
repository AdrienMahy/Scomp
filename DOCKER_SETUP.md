# 🐳 Docker Setup Guide

## 📋 Prérequis

- Docker (latest)
- Docker Compose (latest)

## 🚀 Lancer l'Infrastructure Docker

### 1️⃣ Build & Start Services

```bash
# À partir de la racine du projet
docker-compose up -d --build

# Vérifier que tout est lancé
docker-compose ps
```

### 2️⃣ Vérifier PostgreSQL

```bash
# Accéder au container PostgreSQL
docker-compose exec postgres psql -U scrapper -d scomp_dev

# Lister les tables
\dt

# Quitter
\q
```

### 3️⃣ Tester l'API

```bash
# Health check
curl http://localhost:8001/health

# Scraper games
curl -X POST http://127.0.0.1:8001/games/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "league_name": "Ligue 2",
    "season_name": "2026 - 2027",
    "round": "1",
    "limit": 1
  }'
```

## 🔧 Configuration

| Service | Host | Port |
|---------|------|------|
| PostgreSQL | localhost | 5432 |
| API (FastAPI) | localhost | 8001 |

**Credentials:**
- User: `scrapper`
- Password: `scomp_dev_password`
- Database: `scomp_dev`

## 📁 Volume Mounts

```
backend/          → /app/backend (auto-reload)
backend/exports/  → /app/backend/exports (persistant)
postgres_data/    → /var/lib/postgresql/data (persistant)
```

## 🛑 Arrêter les Services

```bash
# Stop without removing
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove volumes too (WARNING: loses data)
docker-compose down -v
```

## 📊 Visualiser les Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f backend

# Last 50 lines
docker-compose logs -f --tail=50
```

## 🔄 Migrations (à faire plus tard)

```bash
# Generate migration
docker-compose exec backend alembic revision --autogenerate -m "Add games table"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Downgrade
docker-compose exec backend alembic downgrade -1
```

## 🧹 Nettoyer

```bash
# Remove all containers and volumes
docker-compose down -v

# Clean Docker system
docker system prune -a
```

## 🚨 Troubleshooting

### PostgreSQL ne démarre pas

```bash
# Vérifier les logs
docker-compose logs postgres

# Reset postgres volume
docker volume rm scomp_postgres_data
docker-compose up postgres
```

### API ne se connecte pas à PostgreSQL

```bash
# Vérifier la connectivité
docker-compose exec backend ping postgres

# Check environment variables
docker-compose exec backend env | grep POSTGRES
```

### Port déjà en utilisation

```bash
# Trouver le process
lsof -i :5432
lsof -i :8001

# Kill et relancer
docker-compose restart
```
