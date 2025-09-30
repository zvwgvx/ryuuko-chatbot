#!/usr/bin/env python3
# coding: utf-8
"""
Test suite for functions.py module
Tests core functionality including attachment processing, user management,
message formatting, and command handling.
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import functions


class TestUtilityFunctions:
    """Test utility helper functions"""

    def test_extract_user_id_from_str_valid_id(self):
        """Test extracting valid user ID from string"""
        # Test Discord mention format
        assert functions._extract_user_id_from_str("<@123456789012345678>") == 123456789012345678
        assert functions._extract_user_id_from_str("<@!123456789012345678>") == 123456789012345678

        # Test plain number
        assert functions._extract_user_id_from_str("123456789012345678") == 123456789012345678

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

        result = await functions._read_text_attachment(attachment)

        assert result["filename"] == "test.txt"
        assert result["type"] == "text"
        assert result["text"] == "Hello world!"
        assert result["skipped"] == False
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_read_text_attachment_too_large(self, setup_mock_attachment):
        """Test reading text attachment that's too large"""
        large_size = functions.FILE_MAX_BYTES + 1
        attachment = setup_mock_attachment("large.txt", large_size, "text/plain")

        result = await functions._read_text_attachment(attachment)

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

        result = await functions._read_image_attachment(attachment)

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

        result = await functions._read_image_attachment(attachment)

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

        result = await functions._read_attachments_enhanced(attachments)

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
        result = functions.convert_latex_to_discord("\\frac{1}{2}")
        assert result == "1/2"

        result = functions.convert_latex_to_discord("\\frac{numerator}{denominator}")
        assert result == "(numerator)/(denominator)"

    def test_convert_latex_to_discord_protected_regions(self):
        """Test that code blocks are protected from LaTeX conversion"""
        text = "```python\n\\alpha = 5\n```\n\\alpha"
        result = functions.convert_latex_to_discord(text)

        # Code block should be unchanged, but outside LaTeX should be converted
        assert "\\alpha = 5" in result  # Inside code block
        assert result.endswith("α")  # Outside code block

    def test_split_message_smart_short(self):
        """Test splitting short messages"""
        short_text = "Hello world!"
        result = functions.split_message_smart(short_text, 2000)
        assert result == ["Hello world!"]


class TestUserManagement:
    """Test user management functionality"""

    @pytest.fixture
    def setup_storage(self):
        """Setup temporary storage for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "authorized.json"

            # Mock config
            functions._config = Mock()
            functions._config.AUTHORIZED_STORE = temp_path

            # Reset global state
            functions._authorized_users = set()
            functions._use_mongodb_auth = False
            functions._mongodb_store = None

            yield temp_path

    def test_load_authorized_from_path_empty(self, setup_storage):
        """Test loading from non-existent file"""
        temp_path = setup_storage
        result = functions.load_authorized_from_path(temp_path)
        assert result == set()

    def test_load_save_authorized_users(self, setup_storage):
        """Test saving and loading authorized users"""
        temp_path = setup_storage
        test_users = {123456789, 987654321}

        # Save users
        functions.save_authorized_to_path(temp_path, test_users)

        # Load users
        loaded_users = functions.load_authorized_from_path(temp_path)
        assert loaded_users == test_users

    def test_add_authorized_user_file_mode(self, setup_storage):
        """Test adding authorized user in file mode"""
        temp_path = setup_storage

        result = functions.add_authorized_user(123456789)
        assert result == True
        assert 123456789 in functions._authorized_users

        # Verify it was saved to file
        loaded = functions.load_authorized_from_path(temp_path)
        assert 123456789 in loaded

    def test_remove_authorized_user_file_mode(self, setup_storage):
        """Test removing authorized user in file mode"""
        temp_path = setup_storage

        # Add user first
        functions.add_authorized_user(123456789)
        assert 123456789 in functions._authorized_users

        # Remove user
        result = functions.remove_authorized_user(123456789)
        assert result == True
        assert 123456789 not in functions._authorized_users

    @pytest.mark.asyncio
    async def test_is_authorized_user_owner(self):
        """Test authorization check for bot owner"""
        functions._bot = Mock()
        functions._bot.is_owner = AsyncMock(return_value=True)
        functions._authorized_users = set()

        mock_user = Mock()
        mock_user.id = 123456789

        result = await functions.is_authorized_user(mock_user)
        assert result == True

    @pytest.mark.asyncio
    async def test_is_authorized_user_in_list(self):
        """Test authorization check for user in authorized list"""
        functions._bot = Mock()
        functions._bot.is_owner = AsyncMock(return_value=False)
        functions._authorized_users = {123456789}

        mock_user = Mock()
        mock_user.id = 123456789

        result = await functions.is_authorized_user(mock_user)
        assert result == True

    @pytest.mark.asyncio
    async def test_is_authorized_user_not_authorized(self):
        """Test authorization check for unauthorized user"""
        functions._bot = Mock()
        functions._bot.is_owner = AsyncMock(return_value=False)
        functions._authorized_users = set()

        mock_user = Mock()
        mock_user.id = 123456789

        result = await functions.is_authorized_user(mock_user)
        assert result == False


class TestMongoDBIntegration:
    """Test MongoDB integration functionality"""

    @pytest.fixture
    def setup_mongodb_mock(self):
        """Setup MongoDB mock"""
        functions._use_mongodb_auth = True
        functions._mongodb_store = Mock()
        return functions._mongodb_store

    def test_load_authorized_users_mongodb(self, setup_mongodb_mock):
        """Test loading authorized users from MongoDB"""
        mock_store = setup_mongodb_mock
        mock_store.get_authorized_users.return_value = {123, 456, 789}

        result = functions.load_authorized_users()
        assert result == {123, 456, 789}
        mock_store.get_authorized_users.assert_called_once()

    def test_add_authorized_user_mongodb_success(self, setup_mongodb_mock):
        """Test adding authorized user via MongoDB"""
        mock_store = setup_mongodb_mock
        mock_store.add_authorized_user.return_value = True
        functions._authorized_users = set()

        result = functions.add_authorized_user(123)
        assert result == True
        assert 123 in functions._authorized_users
        mock_store.add_authorized_user.assert_called_once_with(123)

    def test_add_authorized_user_mongodb_failure(self, setup_mongodb_mock):
        """Test adding authorized user via MongoDB failure"""
        mock_store = setup_mongodb_mock
        mock_store.add_authorized_user.return_value = False
        functions._authorized_users = set()

        result = functions.add_authorized_user(123)
        assert result == False
        assert 123 not in functions._authorized_users


class TestSetupFunction:
    """Test the setup function"""

    def test_setup_basic(self):
        """Test basic setup functionality"""
        mock_bot = Mock()
        mock_call_api = Mock()
        mock_config = Mock()

        # Mock required attributes
        mock_config.USE_MONGODB = False
        mock_config.init_storage = Mock()

        # Mock managers
        with patch('functions.get_user_config_manager') as mock_ucm, \
                patch('functions.get_request_queue') as mock_rq, \
                patch('functions.MemoryStore') as mock_ms:
            mock_ucm.return_value = Mock()
            mock_rq.return_value = Mock()
            mock_ms.return_value = Mock()

            # Should not raise an exception
            functions.setup(mock_bot, mock_call_api, mock_config)

            # Verify setup calls
            mock_config.init_storage.assert_called_once()
            mock_ucm.assert_called_once()
            mock_rq.assert_called_once()


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

        result = await functions._read_text_attachment(mock_attachment)

        assert result["skipped"] == True
        assert "read error" in result["reason"]

    def test_save_authorized_users_io_error(self):
        """Test handling IO errors when saving authorized users"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a read-only directory to cause write error
            temp_path = Path(temp_dir) / "readonly" / "authorized.json"
            temp_path.parent.mkdir()
            temp_path.parent.chmod(0o444)  # Read-only

            # Should not raise exception, just log error
            functions.save_authorized_to_path(temp_path, {123})


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])