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

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test"""
    # This ensures tests don't interfere with each other
    from src.core import handlers

    # Reset module-level variables
    handlers._bot = None
    functions._call_api = None
    functions._config = None
    functions._user_config_manager = None
    functions._request_queue = None
    handlers._authorized_users = set()
    functions._use_mongodb_auth = False
    functions._mongodb_store = None
    functions._memory_store = None

    yield

    # Cleanup after test if needed
    pass


@pytest.fixture
def mock_discord_objects():
    """Create commonly used Discord mock objects"""
    from unittest.mock import Mock

    mock_user = Mock()
    mock_user.id = 123456789012345678
    mock_user.name = "zvwgvx"
    mock_user.bot = False

    mock_channel = Mock()
    mock_channel.send = Mock()

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