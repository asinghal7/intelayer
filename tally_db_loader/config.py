"""
Configuration management for Tally Database Loader.

Loads settings from environment variables with sensible defaults.
Reuses the existing Intelayer connection settings where applicable.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


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

