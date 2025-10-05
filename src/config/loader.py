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
    """Hàm trợ giúp để tải một file JSON từ thư mục /config."""
    config_path = CONFIG_DIR / file_name
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    try:
        content = config_path.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON format in {config_path}: {exc}")
    except Exception as exc:
        raise RuntimeError(f"Error reading {config_path}: {exc}")


def _get_env_var(key: str, required: bool = True, default: Any = None) -> str:
    """Lấy biến môi trường. Báo lỗi nếu biến bắt buộc bị thiếu."""
    value = os.getenv(key)
    if value is None:
        if required:
            raise ValueError(f"CRITICAL: Required environment variable '{key}' is not set in .env file.")
        return default
    return value


def _int_or_default(val: Any, default: int, name: str) -> int:
    """Chuyển đổi giá trị sang int một cách an toàn."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.warning(f"Config value '{name}' is not a valid integer. Using default: {default}")
        return default


# ====================================================================
# I. LOAD BOT CONFIGURATION
# ====================================================================
logger.info("Loading bot configuration...")
_bot_config_data = _load_json_config("chatbot.json")

# --- Bot Secrets (from .env) ---
DISCORD_TOKEN = _get_env_var("DISCORD_TOKEN")
MONGODB_CONNECTION_STRING = _get_env_var("MONGODB_CONNECTION_STRING")

# --- Bot Settings (from chatbot.json) ---
USE_MONGODB = _bot_config_data.get("USE_MONGODB", True)
if not USE_MONGODB:
    raise RuntimeError("MongoDB is MANDATORY. Set USE_MONGODB=true in chatbot.json")

MONGODB_DATABASE_NAME = _bot_config_data.get("MONGODB_DATABASE_NAME", "ryuukodb")
WEBHOOK_URL = _bot_config_data.get("WEBHOOK_URL", "")

REQUEST_TIMEOUT = _int_or_default(_bot_config_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG_LENGTH = _int_or_default(_bot_config_data.get("MAX_MSG_LENGTH"), 1900, "MAX_MSG_LENGTH")
MEMORY_MAX_MESSAGES = _int_or_default(_bot_config_data.get("MEMORY_MAX_MESSAGES"), 100, "MEMORY_MAX_MESSAGES")
MEMORY_MAX_TOKENS = _int_or_default(_bot_config_data.get("MEMORY_MAX_TOKENS"), 10000, "MEMORY_MAX_TOKENS")

logger.info("Bot configuration loaded successfully.")

# ====================================================================
# II. LOAD GATEWAY CONFIGURATION
# ====================================================================
logger.info("Loading gateway configuration...")
_gateway_config_data = _load_json_config("gateway.json")

# --- Gateway Settings (from gateway.json) ---
ALLOWED_PROVIDERS: Set[str] = set(_gateway_config_data.get("ALLOWED_PROVIDERS", []))
_provider_env_names: Dict[str, str] = dict(_gateway_config_data.get("PROVIDER_ENV_NAMES", {}))
PROVIDER_DEFAULT_MODEL: Dict[str, str] = dict(_gateway_config_data.get("PROVIDER_DEFAULT_MODEL", {}))

_pam_raw = _gateway_config_data.get("PROVIDER_ALLOWED_MODELS", {})
PROVIDER_ALLOWED_MODELS: Dict[str, Set[str]] = {k: set(v) for k, v in _pam_raw.items()}

# --- Gateway Secrets (from .env) ---
# 1. Bot's API Key to communicate with Gateway (if ever needed for an external API)
# This key was previously named API_KEY in the old loader.py
BOT_API_KEY = _get_env_var("BOT_API_KEY", required=False)  # Key for bot to identify itself

# 2. Provider API Keys (e.g., OPENAI_API_KEY)
PROVIDER_API_KEYS: Dict[str, str] = {}
for provider, env_name in _provider_env_names.items():
    api_key = os.getenv(env_name)
    if api_key:
        PROVIDER_API_KEYS[provider] = api_key
    else:
        logger.warning(f"API key for provider '{provider}' (env var '{env_name}') is not set.")

logger.info("Gateway configuration loaded successfully.")

# ====================================================================
# III. STORAGE INITIALIZATION (Moved from old bot loader)
# ====================================================================
_mongodb_initialized = False


def init_storage():
    """Initialize MongoDB storage. This is a mandatory step."""
    global _mongodb_initialized
    if _mongodb_initialized:
        return

    logger.info("Initializing MongoDB connection to database: %s", MONGODB_DATABASE_NAME)
    try:
        # Import here to avoid circular dependency and ensure deps are checked
        import pymongo
        from src.storage.database import init_mongodb_store

        # Test connection
        with pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000) as client:
            client.admin.command('ping')

        # Initialize the store
        init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
        _mongodb_initialized = True
        logger.info("MongoDB store initialized successfully.")
    except ImportError as e:
        raise RuntimeError(f"CRITICAL: MongoDB dependencies missing: {e}. Run 'pip install pymongo'.")
    except pymongo.errors.ServerSelectionTimeoutError:
        raise RuntimeError(
            f"Cannot connect to MongoDB. Is it running and accessible at the provided connection string?")
    except Exception as e:
        raise RuntimeError(f"MongoDB initialization FAILED: {e}")