"""Database configuration settings."""
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Database settings
    DB_DRIVER: str = Field(default="sqlite", env="DB_DRIVER")
    DB_USER: Optional[str] = Field(default=None, env="DB_USER")
    DB_PASSWORD: Optional[SecretStr] = Field(default=None, env="DB_PASSWORD")
    DB_HOST: Optional[str] = Field(default=None, env="DB_HOST")
    DB_PORT: Optional[int] = Field(default=None, env="DB_PORT")
    DB_NAME: str = Field(default="health_assistant.db", env="DB_NAME")
    DB_PATH: Path = Field(default=Path("db") / "health_assistant.db", env="DB_PATH")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    # Application settings
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    @model_validator(mode='before')
    @classmethod
    def assemble_db_connection(cls, data: Any) -> Any:
        """Assemble the database connection string if not provided."""
        if not isinstance(data, dict) or "DATABASE_URL" in data:
            return data

        if data.get("DB_DRIVER") == "sqlite":
            # Ensure the directory exists for SQLite
            db_path = data.get("DB_PATH", Path("db") / "health_assistant.db")
            if isinstance(db_path, str):
                db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            data["DATABASE_URL"] = f"sqlite:///{db_path}"
        elif all(
            k in data
            for k in ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
        ):
            # For other databases (PostgreSQL, MySQL, etc.)
            password = (
                data["DB_PASSWORD"].get_secret_value()
                if data["DB_PASSWORD"]
                else None
            )
            data["DATABASE_URL"] = str(
                PostgresDsn.build(
                    scheme="postgresql",
                    username=data["DB_USER"],
                    password=password,
                    host=data["DB_HOST"],
                    port=data["DB_PORT"],
                    path=f"/{data['DB_NAME'] or ''}",
                )
            )
        return data


# Create settings instance
settings = Settings()
