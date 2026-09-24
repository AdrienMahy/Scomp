"""Application settings and configuration"""
import json
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ENV_FILE = PROJECT_ROOT / "config" / ".env"


class DatabaseSettings(BaseSettings):
    """Database configuration - supports SQLite (dev) and PostgreSQL (prod)"""
    model_config = ConfigDict(case_sensitive=False, extra="allow", env_file=CONFIG_ENV_FILE)
    
    # TacticalData connection URL
    database_url: Optional[str] = Field(default=None, validation_alias="TACTICAL_DATABASE_URL")
    
    # Database type: "sqlite" or "postgresql"
    db_type: str = Field(default="sqlite", validation_alias="DB_TYPE")
    
    # PostgreSQL settings (with POSTGRES_ prefix)
    host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    db: str = Field(default="scomp", validation_alias="POSTGRES_DB")
    username: str = Field(default="scrapper", validation_alias="POSTGRES_USERNAME")
    password: str = Field(default="password", validation_alias="POSTGRES_PASSWORD")
    
    # SQLite settings
    sqlite_path: str = Field(default="./scomp.db", validation_alias="SQLITE_PATH")

    @property
    def url(self) -> str:
        """Database connection URL based on type"""
        # If TACTICAL_DATABASE_URL is set directly, use it (takes precedence)
        if self.database_url:
            return self.database_url
        
        # Otherwise construct from component parts
        if self.db_type == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        else:
            # PostgreSQL
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"


class SportsDynamicsSettings(BaseSettings):
    """SportsDynamics API configuration"""
    model_config = ConfigDict(case_sensitive=False, extra="allow", env_file=CONFIG_ENV_FILE, env_prefix="SPORTSDYNAMICS_")
    
    api_key: str = Field(default="")
    api_url: str = Field(default="https://api-v2.sportsdynamics.eu/graphql")


class Settings(BaseSettings):
    """Main application settings"""
    model_config = ConfigDict(env_file=CONFIG_ENV_FILE, case_sensitive=False, extra="allow")
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Database (will be initialized separately)
    database: Optional[DatabaseSettings] = None
    
    # APIs (will be initialized separately)
    sportsdynamics: Optional[SportsDynamicsSettings] = None
    
    # Paths
    project_root: Path = PROJECT_ROOT
    start_dir: Path = project_root / "start"
    ids_config_path_override: Optional[Path] = Field(
        default=None,
        validation_alias="SCOMP_IDS_CONFIG_PATH",
    )
    
    # IDs Configuration
    @property
    def ids_config_path(self) -> Path:
        """Path to ID.json"""
        return self.ids_config_path_override or self.start_dir / "ID.json"
    
    def load_ids_config(self) -> dict:
        """Load ID.json configuration"""
        if not self.ids_config_path.exists():
            raise FileNotFoundError(f"ID.json not found at {self.ids_config_path}")
        
        with open(self.ids_config_path, 'r') as f:
            return json.load(f)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize nested settings from environment
        if not self.database:
            self.database = DatabaseSettings()
        if not self.sportsdynamics:
            self.sportsdynamics = SportsDynamicsSettings()


# Global settings instance
settings = Settings()
