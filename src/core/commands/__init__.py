# src/core/commands/__init__.py
"""
Command registration module.
Aggregates all command groups and provides a single function to register them all.
"""
from discord.ext import commands
from .basic import setup_basic_commands
from .user import setup_user_commands
from .admin import setup_admin_commands
from .system import setup_system_commands


def register_all_commands(bot: commands.Bot, dependencies: dict):
    """
    Registers all command groups with the bot.

    Args:
        bot (commands.Bot): The Discord bot instance.
        dependencies (dict): A dictionary containing all required dependencies
                           (managers, stores, helper functions, etc.)
    """
    # Create auth helpers for admin commands
    auth_helpers = {
        'add': dependencies['add_authorized_user'],
        'remove': dependencies['remove_authorized_user'],
        'get_set': lambda: dependencies['authorized_users']
    }

    # Attach the authorized_users set to bot for easy access
    bot.authorized_users = dependencies['authorized_users']

    # Register each command group
    setup_basic_commands(bot)

    setup_user_commands(
        bot,
        dependencies['user_config_manager'],
        dependencies['call_api'],
        dependencies['memory_store'],
        dependencies.get('mongodb_store')
    )

    setup_admin_commands(
        bot,
        dependencies['memory_store'],
        auth_helpers
    )

    setup_system_commands(
        bot,
        dependencies.get('mongodb_store')
    )


__all__ = ['register_all_commands']