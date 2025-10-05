"""
Configuration package for the unified Ryuuko Chatbot application.
Provides access to bot settings, gateway settings, and user management.
"""

# Import the entire loader module. This is the recommended way to access config.
# Example: from src.config import loader; print(loader.DISCORD_TOKEN)
from . import loader

# Import user_config management separately as it contains a class and factory function.
from .user_config import (
    UserConfigManager,
    get_user_config_manager,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_MODEL,
    FALLBACK_SUPPORTED_MODELS
)

# Define what gets imported with 'from src.config import *'
# It's generally better to import the loader module directly.
__all__ = [
    'loader',
    'UserConfigManager',
    'get_user_config_manager',
    'DEFAULT_SYSTEM_PROMPT',
    'DEFAULT_MODEL',
    'FALLBACK_SUPPORTED_MODELS'
]