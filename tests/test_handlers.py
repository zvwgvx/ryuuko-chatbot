#!/usr/bin/env python3
# coding: utf-8
"""
Test suite for handlers.py module
Tests bot functionality including attachment processing, user management,
message formatting, and command handling.
MongoDB is MANDATORY - no file mode tests.
"""

import pytest
import asyncio
import json
import discord
import base64
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import os
from datetime import datetime, timezone, timedelta

# Import the module under test
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bot import handlers


class TestUtilityFunctions:
    """Test utility helper functions"""

    def test_extract_user_id_from_str_valid_id(self):
        """Test extracting valid user ID from string"""
        # Test Discord mention format
        assert handlers._extract_user_id_from_str("<@123456789012345678>") == 123456789012345678
        assert functions._extract_user_id_from_str("<@!123456789012345678>") == 123456789012345678

        # Test plain number
        assert handlers._extract_user_id_from_str("123456789012345678") == 123456789012345678

        # Test number in text
        assert functions._extract_user_id_from_str("User ID: 123456789012345678") == 123456789012345678

    def test_vietnam_timestamp_format(self):
        """Test Vietnam timestamp formatting"""
        timestamp = functions.get_vietnam_timestamp()
        assert "Current time:" in timestamp
        assert "GMT+7" in timestamp
        assert len(timestamp) > 20  # Should be a reasonable length


class TestAttachmentProcessing:
    """Test attachment processing functionality"""

    @pytest.fixture
    def setup_mock_attachment(self):
        """Setup mock attachment for testing"""

        def _create_mock_attachment(filename, size, content_type, content=b"test content"):
            mock_attachment = Mock()
            mock_attachment.filename = filename
            mock_attachment.size = size
            mock_attachment.content_type = content_type
            mock_attachment.read = AsyncMock(return_value=content)
            return mock_attachment

        return _create_mock_attachment

    @pytest.mark.asyncio
    async def test_read_text_attachment_valid(self, setup_mock_attachment):
        """Test reading valid text attachment"""
        attachment = setup_mock_attachment("test.txt", 100, "text/plain", b"Hello world!")

        result = await handlers._read_text_attachment(attachment)

        assert result["filename"] == "test.txt"
        assert result["type"] == "text"
        assert result["text"] == "Hello world!"
        assert result["skipped"] == False
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_read_text_attachment_too_large(self, setup_mock_attachment):
        """Test reading text attachment that's too large"""
        large_size = handlers.FILE_MAX_BYTES + 1
        attachment = setup_mock_attachment("large.txt", large_size, "text/plain")

        result = await handlers._read_text_attachment(attachment)

        assert result["skipped"] == True
        assert "too large" in result["reason"]

    @pytest.mark.asyncio
    async def test_read_text_attachment_unsupported_type(self, setup_mock_attachment):
        """Test reading unsupported file type"""
        attachment = setup_mock_attachment("test.exe", 100, "application/exe")

        result = await functions._read_text_attachment(attachment)

        assert result["skipped"] == True
        assert "unsupported file type" in result["reason"]

    @pytest.mark.asyncio
    async def test_read_image_attachment_valid(self, setup_mock_attachment):
        """Test reading valid image attachment"""
        # Create a simple base64 image content
        image_content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
        attachment = setup_mock_attachment("test.png", len(image_content), "image/png", image_content)

        result = await handlers._read_image_attachment(attachment)

        assert result["filename"] == "test.png"
        assert result["type"] == "image"
        assert result["data"] is not None
        assert result["mime_type"] == "image/png"
        assert result["skipped"] == False

    @pytest.mark.asyncio
    async def test_read_image_attachment_too_large(self, setup_mock_attachment):
        """Test reading image that's too large"""
        large_size = functions.IMAGE_MAX_BYTES + 1
        attachment = setup_mock_attachment("large.jpg", large_size, "image/jpeg")

        result = await handlers._read_image_attachment(attachment)

        assert result["skipped"] == True
        assert "too large" in result["reason"]

    @pytest.mark.asyncio
    async def test_read_attachments_enhanced_mixed(self, setup_mock_attachment):
        """Test reading mixed attachments (text + images)"""
        attachments = [
            setup_mock_attachment("doc.txt", 100, "text/plain", b"Document content"),
            setup_mock_attachment("image.png", 1000, "image/png", b"fake_image_data"),
            setup_mock_attachment("code.py", 200, "text/x-python", b"print('hello')")
        ]

        result = await handlers._read_attachments_enhanced(attachments)

        assert len(result["text_files"]) == 2
        assert len(result["images"]) == 1
        assert "doc.txt" in result["text_summary"]
        assert "code.py" in result["text_summary"]


class TestMessageFormatting:
    """Test message formatting functions"""

    def test_convert_latex_to_discord_basic(self):
        """Test basic LaTeX to Discord conversion"""
        test_cases = [
            ("\\alpha + \\beta", "α + β"),
            ("\\pi \\times 2", "π × 2"),
            ("x \\leq y \\geq z", "x ≤ y ≥ z"),
            ("\\infty \\neq 0", "∞ ≠ 0"),
        ]

        for latex, expected in test_cases:
            result = functions.convert_latex_to_discord(latex)
            assert result == expected

    def test_convert_latex_to_discord_fractions(self):
        """Test fraction conversion"""
        result = handlers.convert_latex_to_discord("\\frac{1}{2}")
        assert result == "1/2"

        result = handlers.convert_latex_to_discord("\\frac{numerator}{denominator}")
        assert result == "(numerator)/(denominator)"

    def test_convert_latex_to_discord_protected_regions(self):
        """Test that code blocks are protected from LaTeX conversion"""
        text = "```python\n\\alpha = 5\n```\n\\alpha"
        result = handlers.convert_latex_to_discord(text)

        # Code block should be unchanged, but outside LaTeX should be converted
        assert "\\alpha = 5" in result  # Inside code block
        assert result.endswith("α")  # Outside code block

    def test_split_message_smart_short(self):
        """Test splitting short messages"""
        short_text = "Hello world!"
        result = handlers.split_message_smart(short_text, 2000)
        assert result == ["Hello world!"]

    def test_split_message_smart_empty(self):
        """Test splitting empty messages"""
        result = functions.split_message_smart("", 2000)
        assert result == ["[Empty response]"]


class TestUserManagementMongoDB:
    """Test user management functionality with MongoDB ONLY"""

    @pytest.fixture
    def setup_mongodb_mock(self):
        """Setup MongoDB mock"""
        # Reset global state
        handlers._authorized_users = set()
        handlers._use_mongodb_auth = True
        functions._mongodb_store = Mock()
        functions._config = Mock()
        handlers._config.USE_MONGODB = True

        yield functions._mongodb_store

        # Cleanup
        handlers._use_mongodb_auth = False
        handlers._mongodb_store = None

    def test_load_authorized_users_mongodb(self, setup_mongodb_mock):
        """Test loading authorized users from MongoDB"""
        mock_store = setup_mongodb_mock
        mock_store.get_authorized_users.return_value = {123, 456, 789}

        result = handlers.load_authorized_users()

        assert result == {123, 456, 789}
        mock_store.get_authorized_users.assert_called_once()

    def test_add_authorized_user_mongodb_success(self, setup_mongodb_mock):
        """Test adding authorized user via MongoDB"""
        mock_store = setup_mongodb_mock
        mock_store.add_authorized_user.return_value = True
        handlers._authorized_users = set()

        result = functions.add_authorized_user(123)

        assert result == True
        assert 123 in handlers._authorized_users
        mock_store.add_authorized_user.assert_called_once_with(123)

    def test_add_authorized_user_mongodb_failure(self, setup_mongodb_mock):
        """Test adding authorized user via MongoDB failure"""
        mock_store = setup_mongodb_mock
        mock_store.add_authorized_user.return_value = False
        handlers._authorized_users = set()

        result = handlers.add_authorized_user(123)

        assert result == False
        assert 123 not in functions._authorized_users

    def test_remove_authorized_user_mongodb_success(self, setup_mongodb_mock):
        """Test removing authorized user via MongoDB"""
        mock_store = setup_mongodb_mock
        mock_store.remove_authorized_user.return_value = True
        handlers._authorized_users = {123, 456}

        result = handlers.remove_authorized_user(123)

        assert result == True
        assert 123 not in handlers._authorized_users
        mock_store.remove_authorized_user.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_is_authorized_user_owner(self):
        """Test authorization check for bot owner"""
        functions._bot = Mock()
        handlers._bot.is_owner = AsyncMock(return_value=True)
        functions._authorized_users = set()

        mock_user = Mock()
        mock_user.id = 123456789

        result = await handlers.is_authorized_user(mock_user)
        assert result == True

    @pytest.mark.asyncio
    async def test_is_authorized_user_in_list(self):
        """Test authorization check for user in authorized list"""
        handlers._bot = Mock()
        handlers._bot.is_owner = AsyncMock(return_value=False)
        functions._authorized_users = {123456789}

        mock_user = Mock()
        mock_user.id = 123456789

        result = await functions.is_authorized_user(mock_user)
        assert result == True

    @pytest.mark.asyncio
    async def test_is_authorized_user_not_authorized(self):
        """Test authorization check for unauthorized user"""
        handlers._bot = Mock()
        handlers._bot.is_owner = AsyncMock(return_value=False)
        handlers._authorized_users = set()

        mock_user = Mock()
        mock_user.id = 123456789

        result = await handlers.is_authorized_user(mock_user)
        assert result == False


class TestSetupFunction:
    """Test the setup function with MongoDB MANDATORY"""

    @patch('src.storage.database.get_mongodb_store')
    @patch('src.config.get_user_config_manager')
    @patch('src.utils.get_request_queue')
    @patch('src.storage.MemoryStore')
    def test_setup_mongodb_success(self, mock_ms, mock_rq, mock_ucm, mock_get_store):
        """Test successful setup with MongoDB"""
        mock_bot = Mock()
        mock_call_api = Mock()
        mock_config = Mock()

        # Mock config for MongoDB
        mock_config.USE_MONGODB = True
        mock_config.init_storage = Mock()

        # Mock successful MongoDB store
        mock_store = Mock()
        mock_store.get_authorized_users.return_value = {123, 456}
        mock_get_store.return_value = mock_store

        # Mock managers
        mock_ucm.return_value = Mock()
        mock_rq_instance = Mock()
        mock_rq.return_value = mock_rq_instance
        mock_ms.return_value = Mock()

        # Run setup
        handlers.setup(mock_bot, mock_call_api, mock_config)

        # Verify setup calls
        mock_config.init_storage.assert_called_once()
        mock_get_store.assert_called_once()
        mock_ucm.assert_called_once()
        mock_rq.assert_called_once()
        mock_rq_instance.set_bot.assert_called_once_with(mock_bot)

        # Verify MongoDB store is set
        assert functions._mongodb_store == mock_store
        assert functions._use_mongodb_auth == True

    @patch('src.storage.database.get_mongodb_store')
    def test_setup_mongodb_failure_no_fallback(self, mock_get_store):
        """Test setup fails when MongoDB is not available - NO FALLBACK"""
        mock_bot = Mock()
        mock_call_api = Mock()
        mock_config = Mock()

        # Mock config for MongoDB
        mock_config.USE_MONGODB = True
        mock_config.init_storage = Mock()

        # Mock MongoDB failure
        mock_get_store.side_effect = RuntimeError("MongoDB not available")

        # Setup should handle the error but MongoDB will be None
        functions.setup(mock_bot, mock_call_api, mock_config)

        # Verify MongoDB is not set due to failure
        assert functions._mongodb_store is None
        assert functions._use_mongodb_auth == False  # Falls back to False on error


class TestProcessAIRequest:
    """Test AI request processing"""

    @pytest.mark.asyncio
    async def test_process_ai_request_no_user_config_manager(self):
        """Test handling when user config manager is not available"""
        mock_request = Mock()
        mock_message = Mock()
        mock_channel = Mock()
        mock_message.channel = mock_channel
        mock_request.message = mock_message
        mock_request.final_user_text = "test"
        mock_message.author.id = 123

        # Set user config manager to None
        handlers._user_config_manager = None

        await handlers.process_ai_request(mock_request)

        # Should send error message
        mock_channel.send.assert_called_once()
        args = mock_channel.send.call_args[1]
        assert "Bot configuration not ready" in args['content']


class TestErrorHandling:
    """Test error handling in various scenarios"""

    @pytest.mark.asyncio
    async def test_read_attachment_network_error(self):
        """Test handling network errors when reading attachments"""
        mock_attachment = Mock()
        mock_attachment.filename = "test.txt"
        mock_attachment.size = 100
        mock_attachment.content_type = "text/plain"
        mock_attachment.read = AsyncMock(side_effect=Exception("Network error"))

        result = await handlers._read_text_attachment(mock_attachment)

        assert result["skipped"] == True
        assert "read error" in result["reason"]


class TestOnMessage:
    """Test on_message event handler"""

    @pytest.mark.asyncio
    async def test_on_message_no_user_config_manager(self):
        """Test on_message when user config manager is not available"""
        mock_message = Mock()
        mock_message.author.bot = False
        mock_message.content = "test"

        # Mock bot context
        mock_bot = Mock()
        mock_ctx = Mock()
        mock_ctx.valid = False
        mock_bot.get_context = AsyncMock(return_value=mock_ctx)
        functions._bot = mock_bot

        # Set user config manager to None
        handlers._user_config_manager = None

        # Should return early without error
        await handlers.on_message(mock_message)

        # No further processing should happen
        assert mock_message.channel.send.call_count == 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])