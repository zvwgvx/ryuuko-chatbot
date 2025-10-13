# /packages/discord-bot/src/__main__.py
import logging
import asyncio
import sys

# Import the new, advanced logger setup
from .utils.logger import setup_logger, configure_discord_logging
from .main import Bot

def main():
    """Entry point to configure and run the Discord Bot Client."""
    # Setup logging before anything else
    setup_logger()
    configure_discord_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Ryuuko Discord Bot Client...")
    try:
        bot = Bot()
        asyncio.run(bot.run_client())
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.critical(f"A fatal error occurred in the client: {e}", exc_info=True)

if __name__ == "__main__":
    main()
