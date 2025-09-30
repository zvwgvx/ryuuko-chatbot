"""
Configuration package for Ryuuko Chatbot
Provides unified access to configuration and user management
"""

# Import individual items
from .loader import (
    DISCORD_TOKEN,
    API_SERVER,
    API_KEY,
    USE_MONGODB,
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE_NAME,
    REQUEST_TIMEOUT,
    MAX_MSG,
    MEMORY_MAX_PER_USER,
    MEMORY_MAX_TOKENS,
    WEBHOOK_URL,
    init_storage,
    get_storage_type,
    load_system_prompt,
)

from .user_config import (
    UserConfigManager,
    get_user_config_manager,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    FALLBACK_SUPPORTED_MODELS,
    SUPPORTED_MODELS,
    get_supported_models,
)

# ⭐ BACKWARD COMPATIBILITY:
# Import the entire loader module as 'loader' for legacy code
from . import loader

# Create alias for old import style
# This allows: import src.config as load_config
# Or: from src.config import loader as load_config
load_config = loader  # This creates the module object needed for functions.setup()

__all__ = [
    # Individual exports
    'DISCORD_TOKEN', 'API_SERVER', 'API_KEY', 'USE_MONGODB',
    'MONGODB_CONNECTION_STRING', 'MONGODB_DATABASE_NAME',
    'REQUEST_TIMEOUT', 'MAX_MSG', 'MEMORY_MAX_PER_USER', 'MEMORY_MAX_TOKENS',
    'WEBHOOK_URL', 'init_storage', 'get_storage_type', 'load_system_prompt',
    'UserConfigManager', 'get_user_config_manager', 'DEFAULT_SYSTEM_PROMPT',
    'DEFAULT_MODEL', 'FALLBACK_SUPPORTED_MODELS', 'SUPPORTED_MODELS',
    'get_supported_models',

    # Module objects for backward compatibility
    'loader',
    'load_config',
]