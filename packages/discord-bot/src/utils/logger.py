# /packages/discord-bot/src/utils/logger.py
import logging
import os
import gzip
import shutil
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

def gz_namer(name):
    return name + ".gz"

def gz_rotator(source, dest):
    with open(source, 'rb') as f_in:
        with gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

def setup_logger(log_dir="logs/client", log_filename="client.log"):
    """Configures the root logger for the Discord Bot Client."""
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Setup file handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        log_path / log_filename,
        when='midnight',
        backupCount=30, # Keep 30 days of logs
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.rotator = gz_rotator
    file_handler.namer = gz_namer
    root_logger.addHandler(file_handler)

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    logging.info("File logging enabled for Discord Bot Client.")

def configure_discord_logging():
    """Sets the logging level for discord.py specific loggers."""
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
