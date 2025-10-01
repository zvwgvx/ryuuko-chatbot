"""
Main entry point for running the application as a module.
Usage: python -m src
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.bot import Bot
from src.config import loader
from src.utils.logger import setup_logger, configure_discord_logging


def main():
    """Main application entry point."""
    try:
        # Setup logging FIRST - before any other imports that use logging
        logger = setup_logger(
            log_level="INFO",
            # Optional: log to file
            # log_file="logs/ryuuko.log"
        )

        # Configure Discord.py logging to be less verbose
        configure_discord_logging(level="WARNING")

        logger.info("Starting application...")

        # Initialize storage (MongoDB)
        loader.init_storage()
        logger.info("Storage initialized successfully")

        # Create config from loader
        config = {
            "discord_token": loader.DISCORD_TOKEN,
            "api_server": loader.API_SERVER,
            "api_key": loader.API_KEY,
            "mongodb_connection_string": loader.MONGODB_CONNECTION_STRING,
            "mongodb_database_name": loader.MONGODB_DATABASE_NAME,
            "webhook_url": loader.WEBHOOK_URL,
            "request_timeout": loader.REQUEST_TIMEOUT,
            "max_msg": loader.MAX_MSG,
            "memory_max_per_user": loader.MEMORY_MAX_PER_USER,
            "memory_max_tokens": loader.MEMORY_MAX_TOKENS,
        }
        logger.info("Configuration loaded successfully")

        # Initialize and run bot
        bot = Bot(config)
        logger.info("Bot initialized, starting...")
        bot.run()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()