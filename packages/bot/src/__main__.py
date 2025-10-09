"""
Main entry point for running the application as a module.
Usage: python -m bot
"""
import sys
import logging
import asyncio
from pathlib import Path

# [SỬA LỖI] Sử dụng import tuyệt đối từ `bot`
from bot.main import Bot
from bot.config import loader
from bot.utils.logger import setup_logger, configure_discord_logging

def main():
    """Main application entry point."""
    setup_logger(log_level="INFO", log_to_file=True, log_dir="logs", log_filename="ryuuko.log")
    configure_discord_logging(level="WARNING")
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting application...")

        logger.info("Initializing storage...")
        loader.init_storage()
        logger.info("Storage initialized successfully.")

        bot = Bot()
        bot.setup_modules()

        asyncio.run(bot.run_bot())

    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.critical(f"A fatal error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()