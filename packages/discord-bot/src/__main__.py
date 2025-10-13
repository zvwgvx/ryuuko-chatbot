# /packages/discord-bot/src/__main__.py
import logging
import asyncio
import sys

# A simple logger setup for the client
def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

from .main import Bot

def main():
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting Ryuuko Discord Bot Client...")
    try:
        bot = Bot()
        asyncio.run(bot.run_client())
    except Exception as e:
        logger.critical(f"A fatal error occurred in the client: {e}", exc_info=True)

if __name__ == "__main__":
    main()
