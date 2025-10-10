# packages/bot/src/config/loader.py
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Set

from dotenv import load_dotenv

logger = logging.getLogger("Config.Loader")

# Assume the script is run from the project root (e.g., /Users/zvwgvx/PycharmProjects/ryuuko)
PROJECT_ROOT = Path.cwd()
BOT_PACKAGE_DIR = PROJECT_ROOT / "packages" / "bot"
CONFIG_DIR = BOT_PACKAGE_DIR / "config"
ENV_FILE_PATH = BOT_PACKAGE_DIR / ".env"

if ENV_FILE_PATH.exists():
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    logger.info("Shared .env file loaded successfully from: %s", ENV_FILE_PATH)
else:
    # Fallback for when CWD is not the project root
    bot_src_root = Path(__file__).resolve().parents[1]
    alt_env_path = bot_src_root.parent / ".env"
    if alt_env_path.exists():
        load_dotenv(dotenv_path=alt_env_path, override=True)
        logger.info("Shared .env file loaded successfully from fallback path: %s", alt_env_path)
        CONFIG_DIR = bot_src_root.parent / "config"
    else:
        logger.warning(
            "Bot package .env file not found at %s or %s. Assuming environment variables are set externally.",
            ENV_FILE_PATH,
            alt_env_path
        )


def _load_json_config(file_name: str) -> Dict[str, Any]:
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
    value = os.getenv(key)
    if value is None and required:
        raise ValueError(f"CRITICAL: Required environment variable '{key}' is not set.")
    return value or default


def _int_or_default(val: Any, default: int, name: str) -> int:
    try:
        return int(val)
    except (ValueError, TypeError, AttributeError):
        logger.warning("Configuration value '%s' is invalid. Using default value: %d", name, default)
        return default


logger.info("Loading configurations from config.json...")
_config_data = _load_json_config("config.json")
_bot_config_data = _config_data.get("bot_settings", {})
_gateway_config_data = _config_data.get("gateway_settings", {})

DISCORD_TOKEN = _get_env_var("DISCORD_TOKEN")
MONGODB_CONNECTION_STRING = _get_env_var("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = _bot_config_data.get("MONGODB_DATABASE_NAME", "ryuukodb")
REQUEST_TIMEOUT = _int_or_default(_bot_config_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG_LENGTH = _int_or_default(_bot_config_data.get("MAX_MSG_LENGTH"), 1900, "MAX_MSG_LENGTH")
MEMORY_MAX_MESSAGES = _int_or_default(_bot_config_data.get("MEMORY_MAX_MESSAGES"), 100, "MEMORY_MAX_MESSAGES")
MEMORY_MAX_TOKENS = _int_or_default(_bot_config_data.get("MEMORY_MAX_TOKENS"), 10000, "MEMORY_MAX_TOKENS")
logger.info("Bot configuration loaded.")

ALLOWED_PROVIDERS: Set[str] = set(_gateway_config_data.get("ALLOWED_PROVIDERS", []))
PROVIDER_DEFAULT_MODEL: Dict[str, str] = dict(_gateway_config_data.get("PROVIDER_DEFAULT_MODEL", {}))
PROVIDER_ALLOWED_MODELS: Dict[str, Set[str]] = {
    k: set(v) for k, v in _gateway_config_data.get("PROVIDER_ALLOWED_MODELS", {}).items()
}
_provider_env_names: Dict[str, str] = _gateway_config_data.get("PROVIDER_ENV_NAMES", {})
UPSTREAM_API_KEYS: Dict[str, str] = {}
for provider_name, env_var_name in _provider_env_names.items():
    api_key = os.getenv(env_var_name)
    if api_key:
        UPSTREAM_API_KEYS[provider_name] = api_key
    elif provider_name in ALLOWED_PROVIDERS:
        logger.warning("API key for provider '%s' (env var '%s') is NOT set.", provider_name, env_var_name)
logger.info("Loaded %d upstream provider API keys.", len(UPSTREAM_API_KEYS))
logger.info("Gateway configuration loaded.")


def init_storage():
    logger.info("Initializing MongoDB connection to database: %s", MONGODB_DATABASE_NAME)
    try:
        import pymongo
        from bot.storage.database import init_mongodb_store

        with pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000) as client:
            client.admin.command('ping')
        init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
        logger.info("MongoDB store initialized successfully.")
    except Exception as e:
        logger.critical("MongoDB initialization FAILED: %s", e)
        raise RuntimeError(f"MongoDB initialization FAILED: {e}") from e
