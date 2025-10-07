"""
Core package for Ryuuko Chatbot.

This package contains the main bot logic, command handlers, event listeners,
and service layers for the application.
"""

# Import the main Bot class from main.py
from .main import Bot

# Import the registration functions
from .commands import register_all_commands
from .events import register_all_events

# Import the authentication service
from .services import auth

__all__ = [
    'Bot',
    'register_all_commands',
    'register_all_events',
    'auth',
]