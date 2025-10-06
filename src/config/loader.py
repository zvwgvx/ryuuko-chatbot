# src/config/loader.py
"""
Handles loading and validation of all application configurations.

This module is responsible for:
- Loading environment variables from a .env file.
- Loading JSON configuration files for different parts of the application.
- Validating and providing access to configuration values.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Set

from dotenv import load_dotenv

logger = logging.getLogger("Config.Loader")

# --- Path Constants & Initial Setup ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
ENV_FILE_PATH = BASE_DIR / ".env"

# Load .env file from the project root if it exists.
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)
    logger.info(".env file loaded successfully from the project root.")
else:
    logger.warning(".env file not found at %s. Assuming environment variables are set externally.", ENV_FILE_PATH)

# --- Helper Functions ---
def _load_json_config(file_name: str) -> Dict[str, Any]:
    """Loads a JSON configuration file from the config directory."""
    config_path = CONFIG_DIR / file_name
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    try:
        return json.loads(config_path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Error decoding JSON from {config_path}: {exc}")
    except Exception as exc:
        raise RuntimeError(f"Error reading configuration file {config_path}: {exc}")

def _get_env_var(key: str, required: bool = True, default: Any = None) -> str:
    """Retrieves an environment variable, raising an error if it's required but not set."""
    value = os.getenv(key)
    if value is None and required:
        raise ValueError(f"CRITICAL: Required environment variable '{key}' is not set.")
    return value or default

def _int_or_default(val: Any, default: int, name: str) -> int:
    """Safely converts a value to an integer, falling back to a default."""
    try:
        return int(val)
    except (ValueError, TypeError, AttributeError):
        logger.warning("Configuration value '%s' is invalid. Using default value: %d", name, default)
        return default

# =================================================================
#  I. BOT CONFIGURATION
# =================================================================
logger.info("Loading bot configuration...")
_bot_config_data = _load_json_config("chatbot.json")

# Core bot settings from environment variables
DISCORD_TOKEN = _get_env_var("DISCORD_TOKEN")
MONGODB_CONNECTION_STRING = _get_env_var("MONGODB_CONNECTION_STRING")

# Settings from chatbot.json with defaults
MONGODB_DATABASE_NAME = _bot_config_data.get("MONGODB_DATABASE_NAME", "ryuukodb")
REQUEST_TIMEOUT = _int_or_default(_bot_config_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG_LENGTH = _int_or_default(_bot_config_data.get("MAX_MSG_LENGTH"), 1900, "MAX_MSG_LENGTH")
MEMORY_MAX_MESSAGES = _int_or_default(_bot_config_data.get("MEMORY_MAX_MESSAGES"), 100, "MEMORY_MAX_MESSAGES")
MEMORY_MAX_TOKENS = _int_or_default(_bot_config_data.get("MEMORY_MAX_TOKENS"), 10000, "MEMORY_MAX_TOKENS")

logger.info("Bot configuration loaded.")

# =================================================================
#  II. GATEWAY CONFIGURATION
# =================================================================
logger.info("Loading gateway configuration...")
_gateway_config_data = _load_json_config("gateway.json")

# Provider settings from gateway.json
ALLOWED_PROVIDERS: Set[str] = set(_gateway_config_data.get("ALLOWED_PROVIDERS", []))
PROVIDER_DEFAULT_MODEL: Dict[str, str] = dict(_gateway_config_data.get("PROVIDER_DEFAULT_MODEL", {}))
PROVIDER_ALLOWED_MODELS: Dict[str, Set[str]] = {
    k: set(v) for k, v in _gateway_config_data.get("PROVIDER_ALLOWED_MODELS", {}).items()
}

# Load API keys from environment variables based on mappings in gateway.json
_provider_env_names: Dict[str, str] = _gateway_config_data.get("PROVIDER_ENV_NAMES", {})
UPSTREAM_API_KEYS: Dict[str, str] = {}
for provider_name, env_var_name in _provider_env_names.items():
    api_key = os.getenv(env_var_name)
    if api_key:
        UPSTREAM_API_KEYS[provider_name] = api_key
    elif provider_name in ALLOWED_PROVIDERS:
        logger.warning(
            "API key for allowed provider '%s' (via environment variable '%s') is NOT set.",
            provider_name,
            env_var_name
        )

logger.info("Loaded %d upstream provider API keys.", len(UPSTREAM_API_KEYS))
logger.info("Gateway configuration loaded.")

# =================================================================
#  III. STORAGE INITIALIZATION
# =================================================================
def init_storage():
    """
    Initializes and verifies the MongoDB database connection.
    This function is called at startup to ensure the database is ready.
    """
    logger.info("Initializing MongoDB connection to database: %s", MONGODB_DATABASE_NAME)
    try:
        # Import only when needed to avoid circular dependency issues.
        import pymongo
        from src.storage.database import init_mongodb_store

        # Ping the server to verify the connection.
        with pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000) as client:
            client.admin.command('ping')

        # Initialize the global store instance.
        init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
        logger.info("MongoDB store initialized successfully.")
    except Exception as e:
        logger.critical("MongoDB initialization FAILED: %s", e)
        raise RuntimeError(f"MongoDB initialization FAILED: {e}") from e