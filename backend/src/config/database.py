"""Database connection and session management"""
from sqlalchemy.orm import sessionmaker
from ..SportsDynamics.models.base import Base
from .database_engine import create_configured_engine
from .settings import settings

# Create database engine
engine = create_configured_engine(
    settings.database.url,
    env_prefix="TACTICAL_DB",
    default_pool_size=10,
    default_max_overflow=20,
    echo=settings.debug,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - verify connection (migrations handle table creation)"""
    try:
        # Just verify connection is working
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        print("✅ Database connection verified")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
