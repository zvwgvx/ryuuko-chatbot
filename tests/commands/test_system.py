# tests/commands/test_system.py
"""
Test suite for the system command module (model and credit management).
"""
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock

# Import the setup function to be tested
from src.bot.commands.system import setup_system_commands

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mock bot that captures command registration."""
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
    return bot

@pytest.fixture
def mock_mongodb_store():
    """Fixture for a mock MongoDB store."""
    store = Mock()
    store.add_supported_model.return_value = (True, "Model added.")
    store.remove_supported_model.return_value = (True, "Model removed.")
    store.edit_supported_model.return_value = (True, "Model edited.")
    store.add_user_credit.return_value = (True, 100)
    store.deduct_user_credit.return_value = (True, 50)
    store.set_user_credit.return_value = True
    store.set_user_level.return_value = True
    return store

@pytest.fixture
def mock_ctx():
    """Fixture for a mock command context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
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
    assert command_mock is not None, f"Command '{name}' not found."
    return command_mock.callback

# --- Test Suite ---

class TestSystemCommandSetup:
    def test_setup_registers_all_commands(self, mock_bot, mock_mongodb_store):
        """Verify that all system commands are registered."""
        setup_system_commands(mock_bot, mock_mongodb_store)
        assert mock_bot.command.call_count == 7
        assert mock_bot.add_command.call_count == 7
        assert hasattr(mock_bot, 'mongodb_store')

@pytest.mark.asyncio
class TestAddModelCommand:
    """Tests for the 'addmodel' command."""
    async def test_add_model_success(self, mock_bot, mock_ctx, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "addmodel")

        await callback(mock_ctx, "test-model", 10, 1)

        mock_mongodb_store.add_supported_model.assert_called_once_with("test-model", 10, 1)
        mock_ctx.send.assert_called_once_with("✅ Model added.")

    async def test_add_model_invalid_cost(self, mock_bot, mock_ctx, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "addmodel")

        await callback(mock_ctx, "test-model", -5, 1)

        mock_mongodb_store.add_supported_model.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ Credit cost must be non-negative.")

    async def test_add_model_no_mongo(self, mock_bot, mock_ctx):
        # Arrange: Setup with no MongoDB store
        setup_system_commands(mock_bot, None)
        callback = get_command_callback(mock_bot, "addmodel")

        # Act
        await callback(mock_ctx, "test-model", 10, 1)

        # Assert: The check should now directly send the message
        mock_ctx.send.assert_called_once_with("❌ This feature requires MongoDB to be configured.")


@pytest.mark.asyncio
class TestCreditCommands:
    """Tests for credit management commands (add, deduct, set)."""
    async def test_add_credit_success(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "addcredit")

        await callback(mock_ctx, mock_member, 50)

        mock_mongodb_store.add_user_credit.assert_called_once_with(12345, 50)
        mock_ctx.send.assert_called_once_with("✅ Added 50 credits to TestUser. New balance: 100")

    async def test_deduct_credit_invalid_amount(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "deductcredit")

        await callback(mock_ctx, mock_member, 0)

        mock_mongodb_store.deduct_user_credit.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ Amount must be positive.")

    async def test_set_credit_success(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "setcredit")

        await callback(mock_ctx, mock_member, 500)

        mock_mongodb_store.set_user_credit.assert_called_once_with(12345, 500)
        mock_ctx.send.assert_called_once_with("✅ Set TestUser's credit balance to 500.")

    async def test_set_credit_db_failure(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        mock_mongodb_store.set_user_credit.return_value = False
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "setcredit")

        await callback(mock_ctx, mock_member, 500)

        mock_mongodb_store.set_user_credit.assert_called_once_with(12345, 500)
        mock_ctx.send.assert_called_once_with("❌ Failed to set credits.")


@pytest.mark.asyncio
class TestSetLevelCommand:
    """Tests for the 'setlevel' command."""
    async def test_set_level_success(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "setlevel")

        await callback(mock_ctx, mock_member, 2)

        mock_mongodb_store.set_user_level.assert_called_once_with(12345, 2)
        mock_ctx.send.assert_called_once_with("✅ Set TestUser's access level to Ultimate (Level 2).")

    async def test_set_level_invalid_level(self, mock_bot, mock_ctx, mock_member, mock_mongodb_store):
        setup_system_commands(mock_bot, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "setlevel")

        await callback(mock_ctx, mock_member, 99)

        mock_mongodb_store.set_user_level.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ Level must be 0 (Basic), 1 (Advanced), or 2 (Ultimate).")