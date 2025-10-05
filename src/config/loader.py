# src/config/loader.py
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

if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)
    logger.info(".env file loaded from project root.")
else:
    logger.warning(".env file not found. Environment variables should be set manually.")

# --- Helper Functions ---
def _load_json_config(file_name: str) -> Dict[str, Any]:
    config_path = CONFIG_DIR / file_name
    if not config_path.exists(): raise FileNotFoundError(f"Config file not found: {config_path}")
    try: return json.loads(config_path.read_text(encoding="utf-8") or "{}")
    except Exception as exc: raise RuntimeError(f"Error reading {config_path}: {exc}")

def _get_env_var(key: str, required: bool = True, default: Any = None) -> str:
    value = os.getenv(key)
    if value is None and required: raise ValueError(f"CRITICAL: Required env var '{key}' is not set.")
    return value or default

def _int_or_default(val: Any, default: int, name: str) -> int:
    try: return int(val)
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Config value '{name}' is not valid. Using default: {default}")
        return default

# =================== I. BOT CONFIGURATION ===================
logger.info("Loading bot configuration...")
_bot_config_data = _load_json_config("chatbot.json")
DISCORD_TOKEN = _get_env_var("DISCORD_TOKEN")
MONGODB_CONNECTION_STRING = _get_env_var("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = _bot_config_data.get("MONGODB_DATABASE_NAME", "ryuukodb")
REQUEST_TIMEOUT = _int_or_default(_bot_config_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG_LENGTH = _int_or_default(_bot_config_data.get("MAX_MSG_LENGTH"), 1900, "MAX_MSG_LENGTH")
MEMORY_MAX_MESSAGES = _int_or_default(_bot_config_data.get("MEMORY_MAX_MESSAGES"), 100, "MEMORY_MAX_MESSAGES")
MEMORY_MAX_TOKENS = _int_or_default(_bot_config_data.get("MEMORY_MAX_TOKENS"), 10000, "MEMORY_MAX_TOKENS")

logger.info("Bot configuration loaded successfully.")

# =================== II. GATEWAY CONFIGURATION ===================
logger.info("Loading gateway configuration...")
_gateway_config_data = _load_json_config("gateway.json")
ALLOWED_PROVIDERS: Set[str] = set(_gateway_config_data.get("ALLOWED_PROVIDERS", []))
PROVIDER_DEFAULT_MODEL: Dict[str, str] = dict(_gateway_config_data.get("PROVIDER_DEFAULT_MODEL", {}))
PROVIDER_ALLOWED_MODELS: Dict[str, Set[str]] = {k: set(v) for k, v in _gateway_config_data.get("PROVIDER_ALLOWED_MODELS", {}).items()}

_provider_env_names: Dict[str, str] = _gateway_config_data.get("PROVIDER_ENV_NAMES", {})
UPSTREAM_API_KEYS: Dict[str, str] = {}
for provider_name, env_var_name in _provider_env_names.items():
    api_key = os.getenv(env_var_name)
    if api_key:
        UPSTREAM_API_KEYS[provider_name] = api_key
    elif provider_name in ALLOWED_PROVIDERS:
        logger.warning(f"API key for allowed provider '{provider_name}' (env var '{env_var_name}') is NOT set.")

logger.info(f"Loaded {len(UPSTREAM_API_KEYS)} upstream provider API keys.")
logger.info("Gateway configuration loaded successfully.")

# =================== III. STORAGE INITIALIZATION ===================
def init_storage():
    logger.info("Initializing MongoDB connection to database: %s", MONGODB_DATABASE_NAME)
    try:
        import pymongo
        from src.storage.database import init_mongodb_store
        with pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000) as client:
            client.admin.command('ping')
        init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
        logger.info("MongoDB store initialized successfully.")
    except Exception as e:
        raise RuntimeError(f"MongoDB initialization FAILED: {e}")
