"""FastAPI main application"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.database import init_db
from .web.routes import competitions, games, tasks

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Scomp API",
    description="Sports Data Scraping & API",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(competitions.router)
app.include_router(games.router)
app.include_router(tasks.router)


@app.on_event("startup")
def startup():
    """Initialize database on startup"""
    try:
        init_db()
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
