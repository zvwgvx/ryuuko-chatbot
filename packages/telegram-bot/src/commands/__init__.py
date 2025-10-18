# /packages/telegram-bot/src/commands/__init__.py
import logging
from telegram.ext import Application

from .basic import setup_basic_commands
from .user import setup_user_commands
# UPDATED: Import the admin command setup function
from .admin import setup_admin_commands

logger = logging.getLogger(__name__)

def setup_commands(application: Application) -> None:
    """Registers all command handlers for the bot."""
    
    # A dictionary for any dependencies commands might need, e.g., a database client.
    # For now, it's empty.
    dependencies = {}

    setup_basic_commands(application, dependencies)
    setup_user_commands(application, dependencies)
    # UPDATED: Call the admin command setup function
    setup_admin_commands(application, dependencies)

    logger.info("All command modules have been set up.")
