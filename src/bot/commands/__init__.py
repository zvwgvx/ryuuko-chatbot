# src/bot/commands/__init__.py
"""
Command registration module.
Aggregates all command groups and provides a single function to register them all.
"""
import logging
from discord.ext import commands

# Import setup functions from each command module
from .basic import setup_basic_commands
from .user import setup_user_commands
from .admin import setup_admin_commands
from .system import setup_system_commands

logger = logging.getLogger("Bot.Commands")


def register_all_commands(bot: commands.Bot, dependencies: dict):
    """
    Registers all command groups with the bot.

    Args:
        bot (commands.Bot): The Discord bot instance.
        dependencies (dict): A dictionary containing all required dependencies
                           (managers, stores, helper functions, etc.)
    """
    logger.info("[INIT] Registering all command groups...")

    auth_helpers = dependencies['auth_helpers']

    # Attach the authorized_users set to the bot for easy access in other parts of the code
    bot.authorized_users = dependencies['authorized_users']

    # --- Register each command group with its required dependencies ---

    # Basic commands have no external dependencies
    setup_basic_commands(bot)

    # User commands require several managers and the API client
    setup_user_commands(
        bot,
        dependencies['user_config_manager'],
        dependencies['call_api'],
        dependencies['memory_store'],
        dependencies.get('mongodb_store')  # .get() is safer in case it's optional
    )

    # Admin commands require the memory store and the auth helpers dictionary
    setup_admin_commands(
        bot,
        dependencies['memory_store'],
        auth_helpers  # Pass the `auth_helpers` dictionary directly
    )

    # System commands require the MongoDB store
    setup_system_commands(
        bot,
        dependencies.get('mongodb_store')
    )

    logger.info("[OK] All command groups have been registered.")


__all__ = ['register_all_commands']

