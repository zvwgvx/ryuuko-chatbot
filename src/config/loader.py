# --------------------------------------------------
# loader.py - Unified API with MANDATORY MongoDB
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

# MANDATORY MongoDB import - NO FALLBACK
try:
    import pymongo
    from src.storage.database import init_mongodb_store
except ImportError as e:
    raise RuntimeError(f"❌ CRITICAL: MongoDB dependencies missing - {e}. Install pymongo: pip install pymongo")  # Keep emoji for user error

# --------------------------------------------------------------------
# Logger
# --------------------------------------------------------------------
logger = logging.getLogger("Config")

# --------------------------------------------------------------------
# Path constants
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / "config.json"


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _load_json_file(path: Path) -> Dict[str, Any]:
    """Load JSON configuration file"""
    if not path.exists():
        raise RuntimeError(f"❌ Configuration file not found: {path}")  # Keep emoji for user error
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"❌ Invalid JSON format in {path}: {exc}")  # Keep emoji for user error
    except Exception as exc:
        raise RuntimeError(f"❌ Error reading {path}: {exc}")  # Keep emoji for user error


def _get_env_or_config(env_key: str, config_data: Dict[str, Any], config_key: str = None) -> str:
    """Get value from .env first, then fallback to config.json"""
    if config_key is None:
        config_key = env_key

    # Try environment variables first
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
# Load config.json
# --------------------------------------------------------------------
env_data: Dict[str, Any] = _load_json_file(ENV_FILE)

# --------------------------------------------------------------------
# MANDATORY MongoDB Check
# --------------------------------------------------------------------
USE_MONGODB = env_data.get("USE_MONGODB", True)
if not USE_MONGODB:
    raise RuntimeError("❌ MongoDB is MANDATORY. Set USE_MONGODB=true in config.json")  # Keep emoji for user error

# --------------------------------------------------------------------
# Environment variables
# --------------------------------------------------------------------
DISCORD_TOKEN = _get_env_or_config("DISCORD_TOKEN", env_data)
MONGODB_CONNECTION_STRING = _get_env_or_config("MONGODB_CONNECTION_STRING", env_data)

# API configuration
API_SERVER = _get_env_or_config("API_SERVER", env_data)
API_KEY = _get_env_or_config("API_KEY", env_data)

# --------------------------------------------------------------------
# Configuration values
# --------------------------------------------------------------------
MONGODB_DATABASE_NAME = env_data.get("MONGODB_DATABASE_NAME", "polydevsdb")
MONGO_DB_NAME = MONGODB_DATABASE_NAME  # Alias for compatibility
WEBHOOK_URL = env_data.get("WEBHOOK_URL", "")

# Global parameters
REQUEST_TIMEOUT = _int_or_default(env_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG = _int_or_default(env_data.get("MAX_MSG"), 1900, "MAX_MSG")
MEMORY_MAX_PER_USER = _int_or_default(env_data.get("MEMORY_MAX_PER_USER"), 100, "MEMORY_MAX_PER_USER")
MEMORY_MAX_TOKENS = _int_or_default(env_data.get("MEMORY_MAX_TOKENS"), 10000, "MEMORY_MAX_TOKENS")

# --------------------------------------------------------------------
# CRITICAL Mandatory checks
# --------------------------------------------------------------------
if DISCORD_TOKEN is None:
    raise RuntimeError("❌ DISCORD_TOKEN must be defined in .env file or config.json")  # Keep emoji for user error

if API_SERVER is None or API_KEY is None:
    raise RuntimeError("❌ Both API_SERVER and API_KEY must be defined in .env file or config.json")  # Keep emoji for user error

if MONGODB_CONNECTION_STRING is None:
    raise RuntimeError("❌ MONGODB_CONNECTION_STRING is MANDATORY. Define it in .env file or config.json")  # Keep emoji for user error

logger.info("[OK] Unified API Server configured: %s", API_SERVER)  # Changed: log only
logger.info("[OK] MongoDB mode is MANDATORY - no fallback")  # Changed: log only

# --------------------------------------------------------------------
# MongoDB initialization
# --------------------------------------------------------------------
_mongodb_initialized = False


def init_storage():
    """Initialize MongoDB storage - MANDATORY, NO FALLBACK"""
    global _mongodb_initialized

    if _mongodb_initialized:
        logger.info("MongoDB already initialized")
        return

    logger.info("[SYNC] Initializing MongoDB connection to: %s", MONGODB_DATABASE_NAME)  # Changed: log only

    try:
        # Test MongoDB connection first
        test_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000)
        test_client.admin.command('ping')
        test_client.close()
        logger.info("[OK] MongoDB connection test successful")  # Changed: log only

        # Initialize MongoDB store
        init_mongodb_store(MONGODB_CONNECTION_STRING, MONGODB_DATABASE_NAME)
        logger.info("[OK] MongoDB store initialized: %s", MONGODB_DATABASE_NAME)  # Changed: log only
        _mongodb_initialized = True

    except pymongo.errors.ServerSelectionTimeoutError:
        raise RuntimeError(f"❌ Cannot connect to MongoDB at {MONGODB_CONNECTION_STRING}. Is MongoDB running?")  # Keep emoji for user error
    except Exception as e:
        raise RuntimeError(f"❌ MongoDB initialization FAILED: {e}")  # Keep emoji for user error


def get_storage_type() -> str:
    """Get current storage type - ALWAYS MongoDB"""
    return "mongodb"


# --------------------------------------------------------------------
# Deprecated function
# --------------------------------------------------------------------
def load_system_prompt() -> Dict[str, str]:
    """DEPRECATED: System prompts are now managed per-user"""
    logger.warning("load_system_prompt() is deprecated. System prompts are now managed per-user.")
    return {"role": "system", "content": ""}

# NO AUTHORIZED_STORE for file fallback - MongoDB ONLY