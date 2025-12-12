"""
Configuration management for Tally Database Loader.

Loads settings from environment variables with sensible defaults.
Reuses the existing Intelayer connection settings where applicable.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def _parse_books_from_date() -> Optional[date]:
    """Parse TALLY_BOOKS_FROM environment variable to date."""
    env_val = os.getenv("TALLY_BOOKS_FROM")
    if not env_val:
        return None
    try:
        # Support formats: YYYY-MM-DD or YYYYMMDD
        env_val = env_val.strip()
        if "-" in env_val:
            return date.fromisoformat(env_val)
        elif len(env_val) == 8:
            return date(int(env_val[:4]), int(env_val[4:6]), int(env_val[6:8]))
    except (ValueError, TypeError):
        pass
    return None


@dataclass
class TallyLoaderConfig:
    """Configuration settings for Tally Database Loader."""

    # Tally connection settings (reuse existing Intelayer settings)
    tally_url: str = field(
        default_factory=lambda: os.getenv("TALLY_URL", "http://192.168.1.50:9000")
    )
    tally_company: str = field(
        default_factory=lambda: os.getenv("TALLY_COMPANY", "Your Company")
    )

    # Database settings (separate schema for tally_db_loader)
    db_url: str = field(
        default_factory=lambda: os.getenv(
            "DB_URL", "postgresql://inteluser:change_me@localhost:5432/intelayer"
        )
    )
    db_schema: str = field(default_factory=lambda: os.getenv("TALLY_LOADER_SCHEMA", "tally_db"))

    # Sync settings
    batch_size: int = field(default_factory=lambda: int(os.getenv("TALLY_BATCH_SIZE", "1000")))
    request_timeout: int = field(
        default_factory=lambda: int(os.getenv("TALLY_REQUEST_TIMEOUT", "300"))
    )
    retry_attempts: int = field(
        default_factory=lambda: int(os.getenv("TALLY_RETRY_ATTEMPTS", "3"))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv("TALLY_RETRY_DELAY", "1.0"))
    )
    
    # Books from date - the date from which Tally books start
    # Set via TALLY_BOOKS_FROM env var (format: YYYY-MM-DD or YYYYMMDD)
    # This is used as the default start date for full sync transactions
    # Example: TALLY_BOOKS_FROM=2023-04-01
    books_from: Optional[date] = field(default_factory=_parse_books_from_date)

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Optional[str] = field(
        default_factory=lambda: os.getenv("TALLY_LOADER_LOG_FILE")
    )

    # Incremental sync settings
    enable_incremental: bool = field(
        default_factory=lambda: os.getenv("TALLY_INCREMENTAL", "true").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "TallyLoaderConfig":
        """Create config from environment variables."""
        return cls()

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        if not self.tally_url:
            errors.append("TALLY_URL is required")
        if not self.tally_company:
            errors.append("TALLY_COMPANY is required")
        if not self.db_url:
            errors.append("DB_URL is required")
        return errors


# Default configuration instance
default_config = TallyLoaderConfig.from_env()

