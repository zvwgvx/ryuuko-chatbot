# src/utils/logger.py
"""
Centralized logging configuration for Ryuuko Chatbot.
"""

import logging
import sys
import os
import tarfile
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

# Global flag to track if logging has been configured
_logging_configured = False


class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Extended TimedRotatingFileHandler that compresses rotated log files.
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=30,
                 encoding='utf-8', delay=False, utc=False, atTime=None):
        super().__init__(filename, when, interval, backupCount,
                         encoding, delay, utc, atTime)
        self.compress_on_rotate = True

    def rotation_filename(self, default_name):
        """Modify the filename of a rotated log file to use date format."""
        dir_name = os.path.dirname(default_name)
        base_name = os.path.basename(default_name)

        if '.' in base_name:
            parts = base_name.split('.')
            if len(parts) >= 2:
                date_part = parts[-1]
                new_name = f"{parts[0]}_{date_part}.log"
                return os.path.join(dir_name, new_name)

        return default_name

    def doRollover(self):
        """Perform rollover and compress the rotated file."""
        super().doRollover()

        if self.compress_on_rotate:
            self._compress_rotated_files()

    def _compress_rotated_files(self):
        """Compress rotated log files into tar.gz format."""
        try:
            log_dir = Path(self.baseFilename).parent
            base_name = Path(self.baseFilename).stem

            rotated_files = list(log_dir.glob(f"{base_name}_*.log"))

            files_by_date = {}
            for log_file in rotated_files:
                try:
                    date_str = log_file.stem.split('_')[-1]
                    if date_str not in files_by_date:
                        files_by_date[date_str] = []
                    files_by_date[date_str].append(log_file)
                except (IndexError, ValueError):
                    continue

            for date_str, files in files_by_date.items():
                if files:
                    self._compress_files_to_tarball(files, date_str)

        except Exception as e:
            print(f"Warning: Failed to compress log files: {e}", file=sys.stderr)

    def _compress_files_to_tarball(self, files: list, date_str: str):
        """Compress multiple log files into a single tar.gz archive."""
        try:
            log_dir = Path(self.baseFilename).parent
            base_name = Path(self.baseFilename).stem

            archive_name = log_dir / f"{base_name}_{date_str}.tar.gz"

            if archive_name.exists():
                return

            with tarfile.open(archive_name, 'w:gz') as tar:
                for log_file in files:
                    tar.add(log_file, arcname=log_file.name)

            for log_file in files:
                try:
                    log_file.unlink()
                except Exception as e:
                    print(f"Warning: Failed to delete {log_file}: {e}", file=sys.stderr)

        except Exception as e:
            print(f"Warning: Failed to create tar.gz archive: {e}", file=sys.stderr)


def setup_logger(
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_dir: Optional[str] = None,
        log_filename: Optional[str] = None,
        log_format: Optional[str] = None,
        backup_count: int = 30
) -> logging.Logger:
    """
    Configure and return the root logger.
    """
    global _logging_configured

    if _logging_configured:
        return logging.getLogger()

    # Default formats
    console_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    file_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    if log_format:
        console_format = file_format = log_format

    # Get root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Set log level
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(console_format, datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler without colors
    if log_to_file:
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        else:
            log_dir = Path(log_dir)

        log_dir.mkdir(parents=True, exist_ok=True)

        if log_filename is None:
            log_filename = "ryuuko.log"

        log_file_path = log_dir / log_filename

        file_handler = CompressingTimedRotatingFileHandler(
            filename=str(log_file_path),
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8',
            utc=False
        )

        # File formatter without colors
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        root_logger.info("File logging enabled: %s", log_file_path)
        root_logger.info("Log rotation: daily, keeping %d days", backup_count)
        root_logger.info("Compressed archives will be created in: %s", log_dir)

    _logging_configured = True

    # Print startup banner
    print("\n" + "=" * 60)
    print("[SYSTEM] Ryuuko Chatbot - Logging initialized")
    print("=" * 60 + "\n")

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def configure_discord_logging(level: str = "WARNING"):
    """Configure logging for Discord.py library."""
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(getattr(logging, level.upper()))

    http_logger = logging.getLogger("discord.http")
    http_logger.setLevel(logging.WARNING)

    gateway_logger = logging.getLogger("discord.llm_services")
    gateway_logger.setLevel(logging.WARNING)


def cleanup_old_logs(log_dir: Optional[str] = None, days_to_keep: int = 30):
    """Clean up old compressed log files."""
    try:
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        else:
            log_dir = Path(log_dir)

        if not log_dir.exists():
            return

        now = datetime.now()

        for archive in log_dir.glob("*.tar.gz"):
            try:
                mtime = datetime.fromtimestamp(archive.stat().st_mtime)
                age_days = (now - mtime).days

                if age_days > days_to_keep:
                    archive.unlink()
                    logger = logging.getLogger("Logger")
                    logger.info("[DONE] Deleted old log archive: %s (age: %d days)", archive.name, age_days)

            except Exception as e:
                print(f"Warning: Failed to process {archive}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"Warning: Failed to cleanup old logs: {e}", file=sys.stderr)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True):
    """Helper function to log exceptions consistently."""
    logger.error(message, exc_info=exc_info)


class Loggers:
    """Common logger names used across the application."""
    MAIN = "Main"
    BOT = "Bot"
    CONFIG = "Config"
    DATABASE = "Database"
    API = "Call API"
    HANDLERS = "Handlers"
    STORAGE = "Storage"
    LOGGER = "Logger"