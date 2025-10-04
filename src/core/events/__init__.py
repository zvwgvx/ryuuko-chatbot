# src/core/events/__init__.py
"""
Event listener registration module.
Aggregates all event handlers and provides a single function to register them all.
"""
from discord.ext import commands
from .messages import setup_message_events

def register_all_events(bot: commands.Bot, dependencies: dict):
    """
    Registers all event listeners with the bot.

    Args:
        bot (commands.Bot): The Discord bot instance.
        dependencies (dict): A dictionary containing all required dependencies
                           (managers, stores, helper functions, etc.)
    """
    setup_message_events(bot, dependencies)

__all__ = ['register_all_events']