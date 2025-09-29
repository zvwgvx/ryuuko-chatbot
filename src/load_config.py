# --------------------------------------------------
# load_config.py - Unified API only
# --------------------------------------------------
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed. Install with: pip install python-dotenv")

from database import init_mongodb_store, get_mongodb_store

# --------------------------------------------------------------------
# Logger
# --------------------------------------------------------------------
logger = logging.getLogger("Config")

if not logger.handlers:
    hdlr = logging.StreamHandler()
    fmt = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    hdlr.setFormatter(logging.Formatter(fmt))
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

# --------------------------------------------------------------------
# Path constants
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / "config.json"

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _load_json_file(path: Path) -> Dict[str, Any]:
    """Return an empty dict if file missing; raise warning if JSON bad."""
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return {}
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON format in {path}:\n{exc}")
        return {}
    except Exception as exc:
        logger.exception(f"Error reading {path}: {exc}")
        return {}


def _get_env_or_config(env_key: str, config_data: Dict[str, Any], config_key: str = None) -> str:
    """Get value from .env first, then fallback to config.json"""
    if config_key is None:
        config_key = env_key

    # Try to get from environment variables (.env file)
    env_value = os.getenv(env_key)
    if env_value:
        return env_value

    # Fallback to config.json
    config_value = config_data.get(config_key)
    if config_value:
        logger.info(f"{env_key} loaded from config.json (consider moving to .env)")
        return config_value

    return None


def _int_or_default(val: Any, default: int, name: str) -> int:
    if val is None:
        logger.warning(f"{name} not defined in config; using default {default}")
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.error(f"{name} must be an integer; using {default}")
        return default


# --------------------------------------------------------------------
# Load config.json for non-sensitive data
# --------------------------------------------------------------------
env_data: Dict[str, Any] = _load_json_file(ENV_FILE)

# --------------------------------------------------------------------
# Environment variables (read from .env first, fallback to config.json)
# --------------------------------------------------------------------
DISCORD_TOKEN = _get_env_or_config("DISCORD_TOKEN", env_data)
MONGODB_CONNECTION_STRING = _get_env_or_config("MONGODB_CONNECTION_STRING", env_data)

# Unified API configuration (the only API we use now)
API_SERVER = _get_env_or_config("API_SERVER", env_data)
API_KEY = _get_env_or_config("API_KEY", env_data)

# --------------------------------------------------------------------
# Non-sensitive configuration (read from config.json)
# --------------------------------------------------------------------
MONGODB_DATABASE_NAME = env_data.get("MONGODB_DATABASE_NAME", "discord_openai_proxy")
USE_MONGODB = env_data.get("USE_MONGODB", False)
WEBHOOK_URL = env_data.get("WEBHOOK_URL", "")

# Global parameters
REQUEST_TIMEOUT = _int_or_default(env_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG = _int_or_default(env_data.get("MAX_MSG"), 1900, "MAX_MSG")
MEMORY_MAX_PER_USER = _int_or_default(env_data.get("MEMORY_MAX_PER_USER"), 10, "MEMORY_MAX_PER_USER")
MEMORY_MAX_TOKENS = _int_or_default(env_data.get("MEMORY_MAX_TOKENS"), 2500, "MEMORY_MAX_TOKENS")

# --------------------------------------------------------------------
# Mandatory checks
# --------------------------------------------------------------------
if DISCORD_TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN must be defined in .env file or config.json.")

if API_SERVER is None or API_KEY is None:
    raise RuntimeError("Both API_SERVER and API_KEY must be defined in .env file or config.json.")

# MongoDB validation
if USE_MONGODB and not MONGODB_CONNECTION_STRING:
    raise RuntimeError(
        "USE_MONGODB is enabled but MONGODB_CONNECTION_STRING is not provided in .env file or config.json."
    )

logger.info(f"Unified API Server configured: {API_SERVER}")
logger.info("All models will use the unified API endpoint")

# --------------------------------------------------------------------
# Initialize MongoDB if enabled
# --------------------------------------------------------------------
_mongodb_initialized = False


def init_storage():
    """Initialize storage backend (MongoDB or file-based)"""
    global _mongodb_initialized

    if USE_MONGODB and not _mongodb_initialized:
        try:
            init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
            logger.info(f"MongoDB initialized: {MONGODB_DATABASE_NAME}")
            _mongodb_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            raise RuntimeError(f"MongoDB initialization failed: {e}")
    elif not USE_MONGODB:
        logger.info("Using file-based storage (legacy mode)")


def get_storage_type() -> str:
    """Get current storage type"""
    return "mongodb" if USE_MONGODB else "file"


# --------------------------------------------------------------------
# System prompt loader (DEPRECATED - kept for backward compatibility)
# --------------------------------------------------------------------
def load_system_prompt() -> Dict[str, str]:
    """
    DEPRECATED: System prompts are now managed per-user.
    This function is kept for backward compatibility but will return empty.
    """
    logger.warning("load_system_prompt() is deprecated. System prompts are now managed per-user.")
    return {"role": "system", "content": ""}