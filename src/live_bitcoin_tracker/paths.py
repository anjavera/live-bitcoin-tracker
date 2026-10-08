"""Per-user directories for cache and config, following each platform's conventions."""

from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir

APP_NAME = "live-bitcoin-tracker"


def cache_dir() -> Path:
    """Linux ~/.cache/bitcoin-tracker-tui, macOS ~/Library/Caches/bitcoin-tracker-tui, Windows %LOCALAPPDATA%\\bitcoin-tracker-tui\\Cache."""
    return Path(user_cache_dir(APP_NAME))


def config_dir() -> Path:
    """Linux ~/.config/bitcoin-tracker-tui, macOS ~/Library/Application Support/bitcoin-tracker-tui, Windows %APPDATA%\\bitcoin-tracker-tui."""
    return Path(user_config_dir(APP_NAME, roaming=True))


def env_file() -> Path:
    """Where optional API keys can live so they work from any folder."""
    return config_dir() / ".env"
