"""Database session management"""
from ..config.database import engine, SessionLocal, Base


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def get_session():
    """Get database session"""
    return SessionLocal()
