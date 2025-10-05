# tests/commands/test_user.py
"""
Test suite for the user command module.
"""
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock

# The setup function to be tested is in `user.py`
from src.bot.commands.user import setup_user_commands

# --- Fixtures ---

OWNER_ID = 99999
AUTHORIZED_USER_ID = 12345

@pytest.fixture
def mock_bot():
    """Fixture for a mock bot that captures command registration and user auth."""
    bot = MagicMock(spec=commands.Bot)
    bot.add_command = Mock()

    def command_decorator(**kwargs):
        def decorator(func):
            cmd = Mock(spec=commands.Command, callback=func, **kwargs)
            cmd.name = kwargs.get('name', func.__name__)
            bot.add_command(cmd)
            return cmd
        return decorator
    bot.command = Mock(side_effect=command_decorator)

    bot.authorized_users = {AUTHORIZED_USER_ID}
    # A more specific mock for is_owner check
    bot.is_owner = AsyncMock(side_effect=lambda user: user.id == OWNER_ID)

    return bot

@pytest.fixture
def mock_user_config_manager():
    """Fixture for a mock user config manager."""
    manager = Mock()
    manager.set_user_model.return_value = (True, "Model updated.")
    manager.set_user_system_prompt.return_value = (True, "Prompt updated.")
    manager.get_user_config.return_value = {"model": "test-gpt", "credit": 100, "access_level": 1}
    manager.get_user_system_message.return_value = "You are a helpful assistant."
    manager.get_supported_models.return_value = {"gpt-3.5", "gpt-4"}
    return manager

@pytest.fixture
def mock_call_api():
    """Fixture for a mock API client."""
    api = Mock()
    api.is_model_available.return_value = (True, None)
    return api

@pytest.fixture
def mock_memory_store():
    """Fixture for a mock memory store."""
    store = Mock()
    store.clear_user = Mock()
    return store

@pytest.fixture
def mock_mongodb_store():
    """Fixture for a mock MongoDB store."""
    store = Mock()
    store.list_all_models.return_value = [
        {"model_name": "gpt-4", "credit_cost": 20, "access_level": 2},
        {"model_name": "gpt-3.5", "credit_cost": 5, "access_level": 1},
    ]
    return store

@pytest.fixture
def mock_ctx(mock_member):
    """Fixture for a mock command context of an authorized user."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = mock_member
    ctx.bot = None
    return ctx

@pytest.fixture
def mock_member():
    """Fixture for an authorized discord member."""
    member = Mock(spec=discord.Member)
    member.id = AUTHORIZED_USER_ID
    member.display_name = "TestUser"
    return member

@pytest.fixture
def mock_owner_ctx(mock_owner):
    """Fixture for a context where the author is the owner."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = mock_owner
    ctx.bot = None
    return ctx

@pytest.fixture
def mock_owner():
    """Fixture for a bot owner member."""
    owner = Mock(spec=discord.Member)
    owner.id = OWNER_ID
    owner.display_name = "BotOwner"
    return owner

def get_command_callback(bot, name):
    """Helper to find a command's callback from the mock bot."""
    command_mock = next(
        (call.args[0] for call in bot.add_command.call_args_list if call.args[0].name == name),
        None
    )
    assert command_mock is not None, f"Command '{name}' not found."
    return command_mock.callback

# --- Test Suite ---

@pytest.mark.asyncio
class TestSetModelCommand:
    """Tests for the 'model' command."""
    async def test_set_model_success(self, mock_bot, mock_ctx, mock_user_config_manager, mock_call_api):
        mock_ctx.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, mock_call_api, None, None)
        callback = get_command_callback(mock_bot, "model")

        await callback(mock_ctx, model="gpt-4")

        mock_user_config_manager.set_user_model.assert_called_once_with(AUTHORIZED_USER_ID, "gpt-4")
        mock_ctx.send.assert_called_once_with("✅ Model updated.")

    async def test_set_model_unavailable(self, mock_bot, mock_ctx, mock_user_config_manager, mock_call_api):
        mock_ctx.bot = mock_bot
        mock_call_api.is_model_available.return_value = (False, "Model not found.")
        setup_user_commands(mock_bot, mock_user_config_manager, mock_call_api, None, None)
        callback = get_command_callback(mock_bot, "model")

        await callback(mock_ctx, model="unknown-model")

        mock_user_config_manager.set_user_model.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ Model not found.")

    async def test_set_model_unauthorized(self, mock_bot, mock_ctx, mock_user_config_manager, mock_call_api):
        mock_ctx.bot = mock_bot
        mock_bot.authorized_users = set() # Make user unauthorized
        setup_user_commands(mock_bot, mock_user_config_manager, mock_call_api, None, None)
        callback = get_command_callback(mock_bot, "model")

        await callback(mock_ctx, model="gpt-4")

        mock_user_config_manager.set_user_model.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ You are not authorized to use this command.")

@pytest.mark.asyncio
class TestProfileCommand:
    """Tests for the 'profile' command."""
    async def test_view_own_profile(self, mock_bot, mock_ctx, mock_user_config_manager):
        mock_ctx.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None)
        callback = get_command_callback(mock_bot, "profile")

        await callback(mock_ctx, member=None)

        mock_user_config_manager.get_user_config.assert_called_once_with(AUTHORIZED_USER_ID)
        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]
        assert "Profile for TestUser" in sent_message
        assert "Current Model**: `test-gpt`" in sent_message
        assert "Credit Balance**: 100" in sent_message
        assert "Access Level**: Advanced" in sent_message

    async def test_owner_views_other_profile(self, mock_bot, mock_owner_ctx, mock_member, mock_user_config_manager):
        mock_owner_ctx.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None)
        callback = get_command_callback(mock_bot, "profile")

        await callback(mock_owner_ctx, member=mock_member)

        mock_user_config_manager.get_user_config.assert_called_once_with(mock_member.id)
        mock_owner_ctx.send.assert_called_once() # Corrected assertion

    async def test_user_views_other_profile_denied(self, mock_bot, mock_ctx, mock_user_config_manager):
        mock_ctx.bot = mock_bot
        other_user = Mock(spec=discord.Member, id=67890)
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None)
        callback = get_command_callback(mock_bot, "profile")

        await callback(mock_ctx, member=other_user)

        mock_user_config_manager.get_user_config.assert_not_called()
        mock_ctx.send.assert_called_once_with("❌ You can only view your own profile.")

@pytest.mark.asyncio
class TestModelsCommand:
    """Tests for the 'models' command."""
    async def test_show_models_with_mongodb(self, mock_bot, mock_ctx, mock_user_config_manager, mock_mongodb_store):
        mock_ctx.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "models")

        await callback(mock_ctx)

        mock_mongodb_store.list_all_models.assert_called_once()
        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]
        assert "**Ultimate Models:**" in sent_message
        assert "`gpt-4` - 20 credits" in sent_message
        assert "**Advanced Models:**" in sent_message
        assert "`gpt-3.5` - 5 credits" in sent_message

    async def test_show_models_from_file(self, mock_bot, mock_ctx, mock_user_config_manager):
        mock_ctx.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None) # No mongo store
        callback = get_command_callback(mock_bot, "models")

        await callback(mock_ctx)

        mock_user_config_manager.get_supported_models.assert_called_once()
        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]
        assert "Supported AI Models (from file):" in sent_message
        assert "`gpt-3.5`" in sent_message
        assert "`gpt-4`" in sent_message