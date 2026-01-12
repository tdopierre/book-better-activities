import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class BookingConfig(BaseModel):
    """Configuration for a single booking job."""

    name: str = Field(description="Name of this booking job")
    username: str = Field(description="Better account username")
    password: str = Field(description="Better account password")
    venue: str = Field(description="Venue slug")
    activity: str = Field(description="Activity slug")
    min_slot_time: str = Field(description="Minimum slot time (HH:MM:SS)")
    max_slot_time: str | None = Field(
        default=None, description="Maximum slot time (HH:MM:SS)"
    )
    n_slots: int = Field(default=1, description="Number of consecutive slots to book")
    days_ahead: int = Field(default=4, description="Days ahead to book")
    schedule: str = Field(description="Cron expression for scheduling")


class AppConfig(BaseModel):
    """Application configuration."""

    bookings: list[BookingConfig] = Field(default_factory=list)


def substitute_env_vars(value: str) -> str:
    """Substitute <ENV_VAR> patterns with environment variable values."""
    pattern = r"<([A-Z_][A-Z0-9_]*)>"

    def replace(match: re.Match) -> str:
        env_var = match.group(1)
        env_value = os.environ.get(env_var)
        if env_value is None:
            raise ValueError(f"Environment variable {env_var} is not set")
        return env_value

    return re.sub(pattern, replace, value)


def process_config_values(obj):
    """Recursively process config values to substitute environment variables."""
    if isinstance(obj, dict):
        return {k: process_config_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_config_values(item) for item in obj]
    elif isinstance(obj, str):
        return substitute_env_vars(obj)
    return obj


def load_config(config_path: Path | str = "config.yaml") -> AppConfig:
    """Load configuration from YAML file with environment variable substitution."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    # Process environment variable substitution
    processed_config = process_config_values(raw_config)

    # Remove credentials key if present (it's only for YAML anchors)
    if "credentials" in processed_config:
        del processed_config["credentials"]

    return AppConfig(**processed_config)
