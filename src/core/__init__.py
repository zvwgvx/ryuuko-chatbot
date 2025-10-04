"""
Core package for Ryuuko Chatbot.

This package contains the main bot logic, command handlers, event listeners,
and service layers for the application.
"""

# Import the main Bot class from bot.py
from .bot import Bot

# Import API client - GIỮ NGUYÊN VỊ TRÍ CŨ
from .call_api import UnifiedAPIClient

# Import the registration functions
from .commands import register_all_commands
from .events import register_all_events

# Import the authentication service
from .services import auth_service

__all__ = [
    'Bot',
    'UnifiedAPIClient',
    'register_all_commands',
    'register_all_events',
    'auth_service',
]