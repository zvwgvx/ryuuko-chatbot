# packages/api/src/config/loader.py
"""
Handles loading and validation of API configurations.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger("API.Config.Loader")

# --- Path Constants & Initial Setup ---
# The package root is 3 levels up from this file's location
# (packages/api/src/config/loader.py -> ... -> packages/api)
PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = PACKAGE_ROOT / ".env"

# Load .env file from the package root if it exists.
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)
    logger.info(".env file loaded successfully from: %s", ENV_FILE_PATH)
else:
    logger.warning(".env file not found at %s. Assuming environment variables are set externally.", ENV_FILE_PATH)

import json

# --- Helper Functions ---
def _load_json_config(file_name: str) -> dict:
    """Loads a JSON configuration file from the shared config directory."""
    # The API and Bot share a common root structure, so we find the root config dir
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    config_path = project_root / "packages" / "bot" / "config" / file_name
    if not config_path.exists():
        logger.warning(f"Shared configuration file not found at {config_path}. Using defaults.")
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8") or "{}")
    except Exception as exc:
        logger.error(f"Error reading shared config file {config_path}: {exc}")
        return {}

def _get_env_var(key: str, required: bool = True, default: any = None) -> str:
    """Retrieves an environment variable, raising an error if it's required but not set."""
    value = os.getenv(key)
    if value is None and required:
        raise ValueError(f"CRITICAL: Required environment variable '{key}' is not set.")
    return value or default

# =================================================================
#  API CONFIGURATION
# =================================================================
logger.info("Loading API configuration...")

# Load shared settings from the bot's config file for consistency
_shared_config = _load_json_config("chatbot.json")

# Core API settings from environment variables, with shared config as fallback
API_PORT = int(_get_env_var("API_PORT", default=8000))
MONGODB_CONNECTION_STRING = _get_env_var("MONGODB_CONNECTION_STRING")
MONGODB_DATABASE_NAME = _get_env_var(
    "MONGODB_DATABASE_NAME",
    required=False,
    default=_shared_config.get("MONGODB_DATABASE_NAME", "ryuukodb")
)
ACCESS_TOKEN_EXPIRE_MINUTES = int(_get_env_var("ACCESS_TOKEN_EXPIRE_MINUTES", default=30))
SECRET_KEY = _get_env_var("SECRET_KEY")
ALGORITHM = _get_env_var("ALGORITHM", required=False, default="HS256")

logger.info("API configuration loaded. Using database: %s", MONGODB_DATABASE_NAME)