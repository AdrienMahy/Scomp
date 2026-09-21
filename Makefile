.PHONY: help install dev stop logs test migrate migration clean docker-build docker-up docker-down backend-shell frontend-shell db-shell frontend install-backend install-frontend docker-down status restart version scrape-ligue2 api-status db-reset lint test-scrape logs-api logs-db automation automation-help automation-test automation-run automation-monitor automation-config automation-setup automation-logs automation-stats

# ============================================================================
# VARIABLES
# ============================================================================
DOCKER_COMPOSE = docker compose -f config/docker-compose.yml
BACKEND_PORT = 8001
FRONTEND_PORT = 3002
POSTGRES_PORT = 5432

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
RED = \033[0;31m
NC = \033[0m # No Color

# ============================================================================
# HELP
# ============================================================================
help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║              SCOMP - Development Commands                      ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 STARTUP$(NC)"
	@echo "  make dev                 Start all services (Docker + Frontend)"
	@echo "  make docker-up           Start Docker containers only"
	@echo "  make frontend            Start React dev server (port 3002)"
	@echo ""
	@echo "$(GREEN)🛑 SHUTDOWN$(NC)"
	@echo "  make stop                Stop all services"
	@echo "  make docker-down         Stop Docker containers"
	@echo ""
	@echo "$(GREEN)📦 INSTALLATION$(NC)"
	@echo "  make install             Install backend & frontend dependencies"
	@echo "  make install-backend     Install Python dependencies"
	@echo "  make install-frontend    Install Node dependencies"
	@echo ""
	@echo "$(GREEN)🗄️  DATABASE$(NC)"
	@echo "  make migrate             Run database migrations (Alembic)"
	@echo "  make migration MSG=...   Create new migration with message"
	@echo "  make db-shell            Connect to PostgreSQL shell"
	@echo "  make db-reset            Reset database (drop all tables)"
	@echo ""
	@echo "$(GREEN)🧪 TESTING & QUALITY$(NC)"
	@echo "  make test                Run pytest suite"
	@echo "  make test-scrape         Test scrape endpoint specifically"
	@echo "  make lint                Run linting checks (if configured)"
	@echo ""
	@echo "$(GREEN)📊 DEBUGGING$(NC)"
	@echo "  make logs                Show Docker container logs (live)"
	@echo "  make logs-api            Show API logs only"
	@echo "  make logs-db             Show PostgreSQL logs only"
	@echo "  make backend-shell       Connect to backend container shell"
	@echo "  make frontend-shell      Connect to frontend container shell"
	@echo ""
	@echo "$(GREEN)🔨 BUILD$(NC)"
	@echo "  make docker-build        Build Docker images"
	@echo "  make clean               Clean build artifacts & caches"
	@echo ""
	@echo "$(GREEN)📝 API COMMANDS$(NC)"
	@echo "  make scrape-ligue2       Scrape Ligue 2 2026-2027 season"
	@echo "  make api-status          Check API health"
	@echo ""
	@echo "$(GREEN)🤖 AUTOMATION & SCRAPING$(NC)"
	@echo "  make automation          Show automation help & commands"
	@echo "  make automation-test     Test smart scraper (interactive)"
	@echo "  make automation-monitor  View monitoring dashboard"
	@echo "  make automation-logs     Show Celery Beat logs"
	@echo ""

# ============================================================================
# STARTUP
# ============================================================================

dev: docker-up
	@echo "$(GREEN)✅ Docker services started$(NC)"
	@echo "$(GREEN)✨ Starting React frontend...$(NC)"
	cd frontend && npm run dev

docker-up:
	@echo "$(BLUE)🐳 Starting Docker containers...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Containers started$(NC)"
	@sleep 5
	@echo "$(BLUE)📋 Checking services:$(NC)"
	@echo "  API:        http://localhost:$(BACKEND_PORT)"
	@echo "  Frontend:   http://localhost:$(FRONTEND_PORT)"
	@echo "  PostgreSQL: localhost:$(POSTGRES_PORT)"

frontend:
	@echo "$(BLUE)🚀 Starting React dev server...$(NC)"
	cd frontend && npm run dev

# ============================================================================
# SHUTDOWN
# ============================================================================

stop: docker-down
	@echo "$(RED)✅ All services stopped$(NC)"

docker-down:
	@echo "$(RED)🛑 Stopping Docker containers...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(RED)✅ Containers stopped$(NC)"

# ============================================================================
# INSTALLATION
# ============================================================================

install: install-backend install-frontend
	@echo "$(GREEN)✅ All dependencies installed$(NC)"

install-backend:
	@echo "$(BLUE)📦 Installing Python dependencies...$(NC)"
	cd backend && pip install -r requirements.txt
	@echo "$(GREEN)✅ Backend dependencies installed$(NC)"

install-frontend:
	@echo "$(BLUE)📦 Installing Node dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(NC)"

# ============================================================================
# DATABASE
# ============================================================================

migrate:
	@echo "$(BLUE)🗄️  Running migrations...$(NC)"
	$(DOCKER_COMPOSE) exec -T api alembic upgrade head
	@echo "$(GREEN)✅ Migrations applied$(NC)"

migration:
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ Error: Please provide a message with MSG=<message>$(NC)"; \
		echo "   Example: make migration MSG='Add user table'"; \
		exit 1; \
	fi
	@echo "$(BLUE)✏️  Creating migration: $(MSG)...$(NC)"
	$(DOCKER_COMPOSE) exec -T api alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✅ Migration created$(NC)"

db-shell:
	@echo "$(BLUE)🐘 Connecting to PostgreSQL...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U scrapper -d scomp_dev

db-reset:
	@echo "$(RED)⚠️  WARNING: This will drop all tables!$(NC)"
	@read -p "Continue? (y/N) " confirm && [ "$${confirm}" = "y" ] || exit 1
	@echo "$(RED)🗑️  Resetting database...$(NC)"
	$(DOCKER_COMPOSE) exec -T postgres psql -U scrapper -d scomp_dev << EOF
		DROP SCHEMA public CASCADE;
		CREATE SCHEMA public;
	EOF
	@echo "$(BLUE)🗄️  Running migrations...$(NC)"
	$(DOCKER_COMPOSE) exec -T api alembic upgrade head
	@echo "$(GREEN)✅ Database reset complete$(NC)"

# ============================================================================
# TESTING
# ============================================================================

test:
	@echo "$(BLUE)🧪 Running tests...$(NC)"
	cd backend && python -m pytest -v
	@echo "$(GREEN)✅ Tests complete$(NC)"

test-scrape:
	@echo "$(BLUE)🧪 Testing scrape endpoint...$(NC)"
	cd backend && python -m pytest tests/test_scrape_endpoint.py -v
	@echo "$(GREEN)✅ Scrape tests complete$(NC)"

lint:
	@echo "$(BLUE)📝 Running linting...$(NC)"
	cd backend && python -m pylint src/ || echo "Install pylint with: pip install pylint"
	@echo "$(GREEN)✅ Linting complete$(NC)"

# ============================================================================
# DEBUGGING
# ============================================================================

logs:
	@echo "$(BLUE)📊 Showing live logs (Ctrl+C to exit)...$(NC)"
	$(DOCKER_COMPOSE) logs -f

logs-api:
	@echo "$(BLUE)📊 API logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f api

logs-db:
	@echo "$(BLUE)📊 Database logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f postgres

backend-shell:
	@echo "$(BLUE)💻 Connecting to backend container...$(NC)"
	$(DOCKER_COMPOSE) exec api bash

frontend-shell:
	@echo "$(BLUE)💻 Connecting to frontend container...$(NC)"
	$(DOCKER_COMPOSE) exec -e CI=true frontend sh

# ============================================================================
# BUILD
# ============================================================================

docker-build:
	@echo "$(BLUE)🔨 Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✅ Images built$(NC)"

clean:
	@echo "$(BLUE)🧹 Cleaning build artifacts...$(NC)"
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf backend/build/ backend/dist/ backend/*.egg-info/
	@rm -rf frontend/dist/ frontend/build/
	@rm -rf .pytest_cache/ .coverage htmlcov/
	@echo "$(GREEN)✅ Cleaned$(NC)"

# ============================================================================
# API COMMANDS
# ============================================================================

scrape-ligue2:
	@echo "$(BLUE)📊 Scraping Ligue 2 2026-2027...$(NC)"
	curl -X POST http://localhost:$(BACKEND_PORT)/games/scrape \
		-H "Content-Type: application/json" \
		-d '{"league_name": "Ligue 2", "season_name": "2026 - 2027", "limit": 50, "page": 1}' | python3 -m json.tool
	@echo "$(GREEN)✅ Scrape complete$(NC)"

api-status:
	@echo "$(BLUE)🏥 Checking API health...$(NC)"
	@curl -s http://localhost:$(BACKEND_PORT)/docs > /dev/null && echo "$(GREEN)✅ API is running$(NC)" || echo "$(RED)❌ API is down$(NC)"
	@echo "  Swagger UI: http://localhost:$(BACKEND_PORT)/docs"

# ============================================================================
# UTILITY
# ============================================================================

status:
	@echo "$(BLUE)📊 Services Status:$(NC)"
	@$(DOCKER_COMPOSE) ps

restart: stop docker-up
	@echo "$(GREEN)✅ Services restarted$(NC)"

version:
	@echo "$(BLUE)📦 SCOMP Version Info:$(NC)"
	@echo "  Python: $$(python3 --version)"
	@echo "  Node: $$(node --version)"
	@echo "  Docker: $$(docker --version)"
	@echo "  Docker Compose: $$(docker-compose --version)"

# ============================================================================
# 🤖 AUTOMATION & SCRAPING
# ============================================================================

automation-help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║            SCOMP Scraping Automation Commands                  ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)🤖 SMART SCRAPING$(NC)"
	@echo "  make automation-test     Test smart scraper (interactive menu)"
	@echo "  make automation-run      Run ONE scraping cycle immediately"
	@echo "  make automation-monitor  View monitoring dashboard"
	@echo ""
	@echo "$(GREEN)⚙️  CONFIGURATION$(NC)"
	@echo "  make automation-config   Show current automation config"
	@echo "  make automation-setup    View setup guide"
	@echo ""
	@echo "$(GREEN)📊 MONITORING$(NC)"
	@echo "  make automation-logs     Show last Celery Beat logs (1 hour)"
	@echo "  make automation-stats    Show scraping statistics (24 hours)"
	@echo ""

automation-test:
	@echo "$(BLUE)🧪 Opening Smart Scraper Test Suite...$(NC)"
	cd backend && python -m src.automation.test_automation

automation-run:
	@echo "$(BLUE)🚀 Running ONE scraping cycle immediately...$(NC)"
	cd backend && python -c \
		"from src.automation import SmartScraper; import logging; logging.basicConfig(level=logging.INFO); SmartScraper().run()"

automation-monitor:
	@echo "$(BLUE)📊 Opening Monitoring Dashboard...$(NC)"
	cd backend && python -m src.automation.monitor

automation-config:
	@cd backend && python -c 'from src.automation.scheduler_config import AutomationConfig; print("Scrape Interval: " + str(AutomationConfig.SCRAPE_INTERVAL) + " min"); active = AutomationConfig.get_active_competitions(); print("Active Competitions: " + str(len(active))); [print("  - " + c.get("name", "") + " (" + c.get("id", "") + ")") for c in active]'

automation-setup:
	@cat AUTOMATION_SETUP_GUIDE.md

automation-logs:
	@echo "$(BLUE)📋 Celery Beat Logs (Last 1 Hour)$(NC)"
	@$(DOCKER_COMPOSE) logs --since=1h scomp_celery_beat | grep -E "(Smart Scraping|smart_scrape|ERROR)" || echo "No logs found"

automation-stats:
	@cd backend && python -c 'from src.automation.monitor import ScrapingMonitor; m = ScrapingMonitor(); s = m.get_statistics(24); print("Total Scrapes: " + str(s.get("total_scrapes", 0))); print("Successful: " + str(s.get("successful", 0))); print("Failed: " + str(s.get("failed", 0))); print("Success Rate: " + str(s.get("success_rate", "N/A"))); print("Games Processed: " + str(s.get("total_games_processed", 0)))'

# Quick alias
automation: automation-help
