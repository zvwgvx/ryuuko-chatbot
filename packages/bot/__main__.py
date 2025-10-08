"""
Main entry point for running the application as a module.
Usage: python -m src
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path if not already present
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot.bot.main import Bot
from bot.config import loader  # Import the unified loader
from bot.utils.logger import setup_logger, configure_discord_logging


def main():
    """Main application entry point."""
    try:
        # 1. Setup logging FIRST
        # This returns the root logger which we can use
        root_logger = setup_logger(
            log_level="INFO",
            log_to_file=True,
            log_dir="logs",
            log_filename="ryuuko.log"
        )

        configure_discord_logging(level="WARNING")

        root_logger.info("Starting application...")

        # 2. Initialize storage (this is a mandatory step from the loader)
        root_logger.info("Initializing storage...")
        loader.init_storage()
        root_logger.info("Storage initialized successfully.")

        # 3. Log initial status (using a simpler method)
        root_logger.info("=" * 50)
        root_logger.info(f"Ryuuko Chatbot Initializing...")
        root_logger.info(f"Storage Type: MongoDB")
        root_logger.info(f"Database Name: {loader.MONGODB_DATABASE_NAME}")
        root_logger.info(f"AI Gateway Mode: Integrated (Direct Call)")
        root_logger.info("=" * 50)

        # 4. Initialize and run the bot
        # The bot can now import from 'src.config.loader' directly,
        # so we don't need to pass a large config dictionary.
        # We only need to pass the token.
        if not loader.DISCORD_TOKEN:
            root_logger.critical("DISCORD_TOKEN is not configured. Exiting.")
            sys.exit(1)

        bot = Bot()
        root_logger.info("Bot instance created. Starting bot...")
        bot.run(loader.DISCORD_TOKEN)

    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown signal received. Exiting gracefully.")
        sys.exit(0)
    except Exception as e:
        # Use the root logger to log the final fatal error
        logging.getLogger(__name__).critical(f"A fatal error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
