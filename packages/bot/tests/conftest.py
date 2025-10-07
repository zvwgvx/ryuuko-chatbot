# tests/conftest.py
# !/usr/bin/env python3
# coding: utf-8
"""
Pytest configuration and fixtures for the test suite
"""

import pytest
import sys
import os
from pathlib import Path
import shutil


# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_discord_objects():
    """Create commonly used Discord mock objects"""
    from unittest.mock import Mock, AsyncMock

    mock_user = Mock()
    mock_user.id = 123456789012345678
    mock_user.name = "testuser"
    mock_user.bot = False

    mock_channel = Mock()
    mock_channel.send = AsyncMock()

    mock_message = Mock()
    mock_message.author = mock_user
    mock_message.channel = mock_channel
    mock_message.content = "Test message"
    mock_message.attachments = []
    mock_message.mentions = []

    return {
        'user': mock_user,
        'channel': mock_channel,
        'message': mock_message
    }


def pytest_sessionfinish(session):
    """
    Hook được gọi sau khi toàn bộ phiên test kết thúc.
    Tự động dọn dẹp các file cache của Python (__pycache__, .pyc).
    """
    print("\n\n--- Cleaning up Python cache files ---")

    # Lấy đường dẫn thư mục gốc của dự án từ session của pytest
    root_dir = Path(session.config.rootdir)

    # Tìm và xóa tất cả các thư mục __pycache__
    pycache_dirs = list(root_dir.rglob("__pycache__"))
    if pycache_dirs:
        print(f"Found {len(pycache_dirs)} __pycache__ directories to remove.")
        for path in pycache_dirs:
            try:
                shutil.rmtree(path)
            except OSError as e:
                print(f"  - Error removing directory {path}: {e}")

    # Tìm và xóa tất cả các file .pyc
    pyc_files = list(root_dir.rglob("*.pyc"))
    if pyc_files:
        print(f"Found {len(pyc_files)} .pyc files to remove.")
        for path in pyc_files:
            try:
                os.remove(path)
            except OSError as e:
                print(f"  - Error removing file {path}: {e}")

    print("--- Cache cleanup complete ---")