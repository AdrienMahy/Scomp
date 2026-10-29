"""FastAPI main application"""
import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import init_db
from .config.database import SessionLocal
from .config.settings import settings
from .SportsDynamics.orchestration.task_retention import purge_task_history
from .SportsDynamics.api.routes import competitions, games, teams, players, automation
from .STATSport.api.routes import physical
from .auth import User, _hash_password, ensure_auth_tables, require_statsport_access, require_tactical_access
from .web.auth_routes import admin_router, router as auth_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Scomp API",
    description="Sports Data Scraping & API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(competitions.router, dependencies=[Depends(require_tactical_access)])
app.include_router(games.router, dependencies=[Depends(require_tactical_access)])
app.include_router(teams.router, dependencies=[Depends(require_tactical_access)])
app.include_router(players.router, dependencies=[Depends(require_tactical_access)])
app.include_router(automation.router, dependencies=[Depends(require_tactical_access)])
app.include_router(physical.router, dependencies=[Depends(require_statsport_access)])


@app.on_event("startup")
def startup():
    """Initialize database on startup"""
    try:
        init_db()
        ensure_auth_tables()
        db = SessionLocal()
        try:
            if settings.admin_password:
                admin = db.query(User).filter(User.username == settings.admin_username).first()
                if not admin:
                    db.add(User(
                        id=__import__('secrets').token_hex(16),
                        username=settings.admin_username,
                        password_hash=_hash_password(settings.admin_password),
                        is_admin=True,
                        tactical_access=True,
                        statsport_access=True,
                    ))
                    db.commit()
            retention_result = purge_task_history(db)
            logger.info("Task history retention completed: %s", retention_result)
        finally:
            db.close()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


@app.get("/", tags=["root"])
def read_root():
    """API health check"""
    return {
        "status": "ok",
        "service": "Scomp API",
        "version": "0.1.0"
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Scomp API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
