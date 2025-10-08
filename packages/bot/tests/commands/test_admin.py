# tests/commands/test_admin.py
"""
Test suite for the admin command module.
"""
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock, ANY

# Import the setup function to be tested
from bot.bot.commands.admin import setup_admin_commands

@pytest.fixture
def mock_bot():
    """
    Fixture to create a mock bot that accurately captures command registration.
    """
    bot = MagicMock(spec=commands.Bot)
    bot.add_command = Mock()

    def command_decorator(**kwargs):
        def decorator(func):
            cmd = Mock(spec=commands.Command, callback=func, **kwargs)
            cmd.name = kwargs.get('name', func.__name__)
            cmd.checks = [lambda ctx: True]
            bot.add_command(cmd)
            return cmd
        return decorator

    bot.command = Mock(side_effect=command_decorator)
    bot.is_owner = AsyncMock(return_value=True)
    return bot

@pytest.fixture
def mock_auth_helpers():
    """Fixture to create mock authentication helper functions."""
    return {
        'get_set': Mock(return_value=set()),
        'add': Mock(return_value=True),
        'remove': Mock(return_value=True),
    }

@pytest.fixture
def mock_memory_store():
    """Fixture for a mock memory store."""
    store = Mock()
    store.get_user_messages = Mock(return_value=[])
    return store

@pytest.fixture
def mock_ctx():
    """Fixture for a mock command context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = Mock(spec=discord.Member)
    ctx.author.id = 98765
    ctx.author.display_name = "TestOwner"
    return ctx

@pytest.fixture
def mock_member():
    """Fixture for a mock discord member."""
    member = Mock(spec=discord.Member)
    member.id = 12345
    member.display_name = "TestUser"
    return member

def get_command_callback(bot, name):
    """Helper to find a command's callback from the mock bot."""
    command_mock = next(
        (call.args[0] for call in bot.add_command.call_args_list if call.args[0].name == name),
        None
    )
    assert command_mock is not None, f"Command '{name}' not found"
    return command_mock.callback

# --- Test Suite ---

class TestAdminCommandSetup:
    """Test the initial setup of admin commands."""
    def test_setup_registers_commands(self, mock_bot, mock_memory_store, mock_auth_helpers):
        """Verify that the setup function registers commands on the bot."""
        setup_admin_commands(mock_bot, mock_memory_store, mock_auth_helpers)
        assert mock_bot.command.call_count == 4
        assert mock_bot.add_command.call_count == 4
        assert hasattr(mock_bot, 'memory_store')
        assert hasattr(mock_bot, 'auth_helpers')

@pytest.mark.asyncio
class TestAuthCommand:
    """Tests for the 'auth' command."""
    async def test_auth_new_user_success(self, mock_bot, mock_ctx, mock_member, mock_auth_helpers):
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        auth_callback = get_command_callback(mock_bot, "auth")
        await auth_callback(mock_ctx, member=mock_member)
        mock_auth_helpers['add'].assert_called_once_with(12345)
        mock_ctx.send.assert_called_once_with("✅ Added TestUser to the authorized user list.")

    async def test_auth_user_already_authorized(self, mock_bot, mock_ctx, mock_member, mock_auth_helpers):
        mock_auth_helpers['get_set'].return_value = {12345}
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        auth_callback = get_command_callback(mock_bot, "auth")
        await auth_callback(mock_ctx, member=mock_member)
        mock_auth_helpers['add'].assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ User TestUser is already authorized.")

    async def test_auth_add_fails(self, mock_bot, mock_ctx, mock_member, mock_auth_helpers):
        mock_auth_helpers['add'].return_value = False
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        auth_callback = get_command_callback(mock_bot, "auth")
        await auth_callback(mock_ctx, member=mock_member)
        mock_ctx.send.assert_called_once_with("❌ An error occurred while trying to authorize TestUser.")

@pytest.mark.asyncio
class TestDeauthCommand:
    """Tests for the 'deauth' command."""
    async def test_deauth_user_success(self, mock_bot, mock_ctx, mock_member, mock_auth_helpers):
        mock_auth_helpers['get_set'].return_value = {12345}
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        deauth_callback = get_command_callback(mock_bot, "deauth")
        await deauth_callback(mock_ctx, member=mock_member)
        mock_auth_helpers['remove'].assert_called_once_with(12345)
        mock_ctx.send.assert_called_once_with("✅ Removed TestUser from the authorized user list.")

    async def test_deauth_user_not_authorized(self, mock_bot, mock_ctx, mock_member, mock_auth_helpers):
        mock_auth_helpers['get_set'].return_value = {999}
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        deauth_callback = get_command_callback(mock_bot, "deauth")
        await deauth_callback(mock_ctx, member=mock_member)
        mock_auth_helpers['remove'].assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ User TestUser is not on the authorized list.")

@pytest.mark.asyncio
class TestShowAuthsCommand:
    """Tests for the 'auths' command."""
    async def test_show_auths_empty_list(self, mock_bot, mock_ctx, mock_auth_helpers):
        mock_auth_helpers['get_set'].return_value = set()
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        show_auth_callback = get_command_callback(mock_bot, "auths")
        await show_auth_callback(mock_ctx)
        mock_ctx.send.assert_called_once_with("The authorized users list is currently empty.")

    async def test_show_auths_short_list(self, mock_bot, mock_ctx, mock_auth_helpers):
        users = {1, 2, 3}
        mock_auth_helpers['get_set'].return_value = users
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        show_auth_callback = get_command_callback(mock_bot, "auths")
        await show_auth_callback(mock_ctx)
        expected_output = "**Authorized User IDs:**\n```\n1\n2\n3\n```"
        mock_ctx.send.assert_called_once_with(expected_output)

    async def test_show_auths_long_list(self, mock_bot, mock_ctx, mock_auth_helpers):
        # Generate a large set of users to exceed the Discord message limit.
        # 300 users with IDs up to 20 digits plus newline should be > 1900 chars.
        users = {10000000000000000000 + i for i in range(300)}
        mock_auth_helpers['get_set'].return_value = users
        setup_admin_commands(mock_bot, None, mock_auth_helpers)
        show_auth_callback = get_command_callback(mock_bot, "auths")
        await show_auth_callback(mock_ctx)
        mock_ctx.send.assert_called_once_with(
            "The list of authorized users is too long to display, sending it as a file.",
            file=ANY
        )

@pytest.mark.asyncio
class TestMemoryCommand:
    """Tests for the 'memory' command."""
    async def test_memory_for_author_success(self, mock_bot, mock_ctx, mock_memory_store, mock_auth_helpers):
        mock_memory_store.get_user_messages.return_value = [{'role': 'user', 'content': 'Hello there'}]
        setup_admin_commands(mock_bot, mock_memory_store, mock_auth_helpers)
        memory_callback = get_command_callback(mock_bot, "memory")
        await memory_callback(mock_ctx, member=None)
        mock_memory_store.get_user_messages.assert_called_once_with(mock_ctx.author.id)
        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]
        assert "Conversation Memory for TestOwner" in sent_message
        assert "**User**: Hello there" in sent_message

    async def test_memory_for_other_member(self, mock_bot, mock_ctx, mock_member, mock_memory_store, mock_auth_helpers):
        mock_memory_store.get_user_messages.return_value = [{'role': 'assistant', 'content': 'General Kenobi'}]
        setup_admin_commands(mock_bot, mock_memory_store, mock_auth_helpers)
        memory_callback = get_command_callback(mock_bot, "memory")
        await memory_callback(mock_ctx, member=mock_member)
        mock_memory_store.get_user_messages.assert_called_once_with(mock_member.id)
        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]
        assert "Conversation Memory for TestUser" in sent_message
        assert "**Assistant**: General Kenobi" in sent_message

    async def test_memory_not_found(self, mock_bot, mock_ctx, mock_member, mock_memory_store, mock_auth_helpers):
        mock_memory_store.get_user_messages.return_value = []
        setup_admin_commands(mock_bot, mock_memory_store, mock_auth_helpers)
        memory_callback = get_command_callback(mock_bot, "memory")
        await memory_callback(mock_ctx, member=mock_member)
        mock_ctx.send.assert_called_once_with("No conversation memory found for TestUser.")