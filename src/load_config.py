# --------------------------------------------------
# load_config.py - Updated with PostgreSQL support - FIXED
# --------------------------------------------------
import json
import logging
from pathlib import Path
from typing import Any, Dict

# --------------------------------------------------------------------
# Logger
# --------------------------------------------------------------------
logger = logging.getLogger("config")
if not logger.handlers:
    hdlr = logging.StreamHandler()
    fmt = "%(asctime)s %(name)s %(levelname)s: %(message)s"
    hdlr.setFormatter(logging.Formatter(fmt))
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

# --------------------------------------------------------------------
# Path constants (still needed for config.json)
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
# Đọc config.json
# --------------------------------------------------------------------
env_data: Dict[str, Any] = _load_json_file(ENV_FILE)

# --------------------------------------------------------------------
# Environment variables
# --------------------------------------------------------------------
DISCORD_TOKEN = env_data.get("DISCORD_TOKEN")
OPENAI_API_KEY = env_data.get("OPENAI_API_KEY")
OPENAI_API_BASE = env_data.get("OPENAI_API_BASE")
OPENAI_MODEL = env_data.get("OPENAI_MODEL")

# Gemini API configuration
CLIENT_GEMINI_API_KEY = env_data.get("CLIENT_GEMINI_API_KEY")
OWNER_GEMINI_API_KEY = env_data.get("OWNER_GEMINI_API_KEY")  # Owner-specific key

# PostgreSQL configuration
POSTGRESQL_HOST = env_data.get("POSTGRESQL_HOST", "localhost")
POSTGRESQL_PORT = env_data.get("POSTGRESQL_PORT", "5432")
POSTGRESQL_DATABASE = env_data.get("POSTGRESQL_DATABASE", "polydevsdb")
POSTGRESQL_USER = env_data.get("POSTGRESQL_USER")
POSTGRESQL_PASSWORD = env_data.get("POSTGRESQL_PASSWORD")
USE_DATABASE = env_data.get("USE_DATABASE", True)  # Default to True for PostgreSQL

# Tham số toàn cục
REQUEST_TIMEOUT = _int_or_default(env_data.get("REQUEST_TIMEOUT"), 100, "REQUEST_TIMEOUT")
MAX_MSG = _int_or_default(env_data.get("MAX_MSG"), 1900, "MAX_MSG")
MEMORY_MAX_PER_USER = _int_or_default(env_data.get("MEMORY_MAX_PER_USER"), 10, "MEMORY_MAX_PER_USER")
MEMORY_MAX_TOKENS = _int_or_default(env_data.get("MEMORY_MAX_TOKENS"), 2500, "MEMORY_MAX_TOKENS")

# --------------------------------------------------------------------
# Mandatory checks
# --------------------------------------------------------------------
if DISCORD_TOKEN is None or OPENAI_API_KEY is None:
    raise RuntimeError(
        "Both DISCORD_TOKEN and OPENAI_API_KEY must be defined in config.json."
    )

# PostgreSQL validation
if USE_DATABASE:
    if not POSTGRESQL_USER or not POSTGRESQL_PASSWORD:
        raise RuntimeError(
            "USE_DATABASE is enabled but POSTGRESQL_USER or POSTGRESQL_PASSWORD is not provided in config.json."
        )

    # Validate PostgreSQL connection parameters
    if not POSTGRESQL_HOST or not POSTGRESQL_PORT or not POSTGRESQL_DATABASE:
        raise RuntimeError(
            "PostgreSQL connection parameters (HOST, PORT, DATABASE) must be properly configured."
        )

# Supported models (updated list)
SUPPORTED_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gpt-3.5-turbo",
    "gpt-5",
    "gpt-oss-20b",
    "gpt-oss-120b",
    "o3-mini",
    "gpt-4.1"
}

if OPENAI_MODEL and OPENAI_MODEL not in SUPPORTED_MODELS:
    logger.warning(f"MODEL {OPENAI_MODEL} not listed; should be monitored.")

# Gemini API validation (optional)
if CLIENT_GEMINI_API_KEY:
    logger.info("Gemini API key found - Gemini models will be available")
else:
    logger.warning("Gemini API key not found - Gemini models will not be available")

# Owner Gemini API validation
if OWNER_GEMINI_API_KEY:
    logger.info("Owner Gemini API key found - enhanced features available")

# --------------------------------------------------------------------
# Storage initialization status
# --------------------------------------------------------------------
_storage_initialized = False


def init_storage():
    """Initialize storage backend (PostgreSQL or file-based)"""
    global _storage_initialized

    if USE_DATABASE and not _storage_initialized:
        try:
            # Import here to avoid circular import
            from database import get_postgresql_store

            # PostgreSQL store initialization
            store = get_postgresql_store()
            if store:
                logger.info(
                    f"PostgreSQL storage initialized: {POSTGRESQL_DATABASE}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}")
                _storage_initialized = True
            else:
                raise RuntimeError("Failed to get PostgreSQL store instance")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL storage: {e}")
            raise RuntimeError(f"PostgreSQL initialization failed: {e}")
    elif not USE_DATABASE:
        logger.info("Using file-based storage (legacy mode)")
        logger.warning("File-based storage is deprecated. Consider enabling PostgreSQL.")


def get_storage_type() -> str:
    """Get current storage type"""
    return "postgresql" if USE_DATABASE else "file"


def is_database_enabled() -> bool:
    """Check if database storage is enabled"""
    return USE_DATABASE


def get_database_info() -> Dict[str, Any]:
    """Get database connection information"""
    if not USE_DATABASE:
        return {"type": "file", "enabled": False}

    return {
        "type": "postgresql",
        "enabled": True,
        "host": POSTGRESQL_HOST,
        "port": POSTGRESQL_PORT,
        "database": POSTGRESQL_DATABASE,
        "user": POSTGRESQL_USER
    }


# --------------------------------------------------------------------
# System prompt loader (DEPRECATED - kept for backward compatibility)
# --------------------------------------------------------------------
def load_system_prompt() -> Dict[str, str]:
    """
    DEPRECATED: System prompts are now managed per-user in database.
    This function is kept for backward compatibility but will return empty.
    """
    logger.warning("load_system_prompt() is deprecated. System prompts are now managed per-user in database.")
    return {"role": "system", "content": ""}


# --------------------------------------------------------------------
# Cleanup function
# --------------------------------------------------------------------
def cleanup_storage():
    """Clean up storage connections on shutdown"""
    if USE_DATABASE:
        try:
            from database import close_postgresql_store
            close_postgresql_store()
            logger.info("PostgreSQL connections closed")
        except Exception as e:
            logger.error(f"Error closing PostgreSQL connections: {e}")


# --------------------------------------------------------------------
# Export all configuration variables
# --------------------------------------------------------------------
__all__ = [
    # Discord & OpenAI
    "DISCORD_TOKEN",
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "OPENAI_MODEL",

    # Gemini
    "CLIENT_GEMINI_API_KEY",
    "OWNER_GEMINI_API_KEY",

    # PostgreSQL
    "POSTGRESQL_HOST",
    "POSTGRESQL_PORT",
    "POSTGRESQL_DATABASE",
    "POSTGRESQL_USER",
    "POSTGRESQL_PASSWORD",
    "USE_DATABASE",

    # Global parameters
    "REQUEST_TIMEOUT",
    "MAX_MSG",
    "MEMORY_MAX_PER_USER",
    "MEMORY_MAX_TOKENS",
    "SUPPORTED_MODELS",

    # Functions
    "init_storage",
    "get_storage_type",
    "is_database_enabled",
    "get_database_info",
    "cleanup_storage",
    "load_system_prompt"
]