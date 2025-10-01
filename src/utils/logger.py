"""
Centralized logging configuration for Ryuuko Chatbot.

This module provides a unified logging setup with file rotation and
automatic compression of old log files.
"""

import logging
import sys
import gzip
import shutil
import tarfile
from typing import Optional
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import os


# Global flag to track if logging has been configured
_logging_configured = False


class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Extended TimedRotatingFileHandler that compresses rotated log files.

    This handler automatically compresses old log files into tar.gz format
    when they are rotated (daily rotation).
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=30,
                 encoding='utf-8', delay=False, utc=False, atTime=None):
        """
        Initialize the handler with compression support.

        Args:
            filename: Base filename for log files
            when: When to rotate ('midnight' for daily)
            interval: Rotation interval (1 for daily)
            backupCount: Number of backup files to keep
            encoding: File encoding
            delay: Delay file opening
            utc: Use UTC time
            atTime: Specific time for rotation
        """
        super().__init__(filename, when, interval, backupCount,
                        encoding, delay, utc, atTime)
        self.compress_on_rotate = True

    def rotation_filename(self, default_name):
        """
        Modify the filename of a rotated log file to use date format.

        Args:
            default_name: Default rotated filename

        Returns:
            Modified filename with date stamp
        """
        # Get directory and base filename
        dir_name = os.path.dirname(default_name)
        base_name = os.path.basename(default_name)

        # Extract timestamp from the rotated filename
        # Format: ryuuko.log.YYYY-MM-DD -> ryuuko_YYYY-MM-DD.log
        if '.' in base_name:
            parts = base_name.split('.')
            if len(parts) >= 2:
                # Get the date part (last part before extension)
                date_part = parts[-1]
                # Create new format: ryuuko_YYYY-MM-DD.log
                new_name = f"{parts[0]}_{date_part}.log"
                return os.path.join(dir_name, new_name)

        return default_name

    def doRollover(self):
        """
        Perform rollover and compress the rotated file.
        """
        # Perform standard rollover
        super().doRollover()

        # Find and compress the rotated file
        if self.compress_on_rotate:
            self._compress_rotated_files()

    def _compress_rotated_files(self):
        """
        Compress rotated log files into tar.gz format.

        This method finds all .log files (except current one) and compresses
        them by date into tar.gz archives.
        """
        try:
            log_dir = Path(self.baseFilename).parent
            base_name = Path(self.baseFilename).stem

            # Find all rotated log files (name pattern: base_YYYY-MM-DD.log)
            rotated_files = list(log_dir.glob(f"{base_name}_*.log"))

            # Group files by date and compress
            files_by_date = {}
            for log_file in rotated_files:
                # Extract date from filename: ryuuko_YYYY-MM-DD.log
                try:
                    date_str = log_file.stem.split('_')[-1]  # Get YYYY-MM-DD
                    if date_str not in files_by_date:
                        files_by_date[date_str] = []
                    files_by_date[date_str].append(log_file)
                except (IndexError, ValueError):
                    continue

            # Compress each date group
            for date_str, files in files_by_date.items():
                if files:
                    self._compress_files_to_tarball(files, date_str)

        except Exception as e:
            # Don't crash the application if compression fails
            print(f"Warning: Failed to compress log files: {e}", file=sys.stderr)

    def _compress_files_to_tarball(self, files: list, date_str: str):
        """
        Compress multiple log files into a single tar.gz archive.

        Args:
            files: List of log file paths to compress
            date_str: Date string for the archive name (YYYY-MM-DD)
        """
        try:
            log_dir = Path(self.baseFilename).parent
            base_name = Path(self.baseFilename).stem

            # Create tar.gz filename
            archive_name = log_dir / f"{base_name}_{date_str}.tar.gz"

            # Skip if archive already exists
            if archive_name.exists():
                return

            # Create tar.gz archive
            with tarfile.open(archive_name, 'w:gz') as tar:
                for log_file in files:
                    # Add file to archive with just the filename (no path)
                    tar.add(log_file, arcname=log_file.name)

            # Remove original files after successful compression
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
    Configure and return the root logger with consistent settings.

    This function should be called once at application startup to ensure
    all modules use the same logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file (default: True)
        log_dir: Directory for log files (default: project_root/logs)
        log_filename: Base name for log files (default: ryuuko.log)
        log_format: Optional custom log format
        backup_count: Number of daily backup files to keep (default: 30 days)

    Returns:
        Configured root logger
    """
    global _logging_configured

    # Only configure once
    if _logging_configured:
        return logging.getLogger()

    # Default format if not provided
    if log_format is None:
        log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    # Get root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Set log level
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation and compression
    if log_to_file:
        # Determine log directory
        if log_dir is None:
            # Default to project_root/logs
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        else:
            log_dir = Path(log_dir)

        # Create log directory if needed
        log_dir.mkdir(parents=True, exist_ok=True)

        # Determine log filename
        if log_filename is None:
            log_filename = "ryuuko.log"

        log_file_path = log_dir / log_filename

        # Create rotating file handler with compression
        file_handler = CompressingTimedRotatingFileHandler(
            filename=str(log_file_path),
            when='midnight',      # Rotate at midnight
            interval=1,           # Every 1 day
            backupCount=backup_count,  # Keep N days of logs
            encoding='utf-8',
            utc=False             # Use local time
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"File logging enabled: {log_file_path}")
        root_logger.info(f"Log rotation: daily, keeping {backup_count} days")
        root_logger.info(f"Compressed archives will be created in: {log_dir}")

    # Mark as configured
    _logging_configured = True

    # Log initial message
    root_logger.info("=" * 60)
    root_logger.info(f"Ryuuko Chatbot - Logging initialized at {log_level} level")
    root_logger.info("=" * 60)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    This is a convenience wrapper around logging.getLogger() to ensure
    consistent usage across the application.

    Args:
        name: Logger name (typically module name or functional area)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def configure_discord_logging(level: str = "WARNING"):
    """
    Configure logging for Discord.py library.

    Discord.py can be quite verbose, so this function allows setting
    a different log level specifically for discord modules.

    Args:
        level: Log level for discord modules (default: WARNING)
    """
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(getattr(logging, level.upper()))

    # Also configure discord.http separately as it can be very verbose
    http_logger = logging.getLogger("discord.http")
    http_logger.setLevel(logging.WARNING)

    # Configure discord.gateway
    gateway_logger = logging.getLogger("discord.gateway")
    gateway_logger.setLevel(logging.WARNING)


def cleanup_old_logs(log_dir: Optional[str] = None, days_to_keep: int = 30):
    """
    Clean up old compressed log files.

    This function removes tar.gz log archives older than the specified
    number of days.

    Args:
        log_dir: Directory containing log files (default: project_root/logs)
        days_to_keep: Number of days to keep archives (default: 30)
    """
    try:
        # Determine log directory
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        else:
            log_dir = Path(log_dir)

        if not log_dir.exists():
            return

        # Current timestamp
        now = datetime.now()

        # Find all tar.gz files
        for archive in log_dir.glob("*.tar.gz"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(archive.stat().st_mtime)
                age_days = (now - mtime).days

                # Delete if older than threshold
                if age_days > days_to_keep:
                    archive.unlink()
                    logger = logging.getLogger("Logger")
                    logger.info(f"Deleted old log archive: {archive.name} (age: {age_days} days)")

            except Exception as e:
                print(f"Warning: Failed to process {archive}: {e}", file=sys.stderr)

    except Exception as e:
        print(f"Warning: Failed to cleanup old logs: {e}", file=sys.stderr)


def log_exception(logger: logging.Logger, message: str, exc_info: bool = True):
    """
    Helper function to log exceptions consistently.

    Args:
        logger: Logger instance to use
        message: Error message
        exc_info: Whether to include exception traceback
    """
    logger.error(message, exc_info=exc_info)


# Optional: Create module-specific loggers as constants for easy import
class Loggers:
    """Common logger names used across the application."""
    MAIN = "Main"
    BOT = "Bot"
    CONFIG = "Config"
    DATABASE = "Database"
    API = "Call API"
    FUNCTIONS = "Functions"
    STORAGE = "Storage"
    LOGGER = "Logger"