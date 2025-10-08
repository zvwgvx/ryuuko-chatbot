# tests/commands/test_user.py
"""
Test suite for the user command module.
"""
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock, ANY

# The setup function to be tested is in `user.py`
from bot.commands.user import setup_user_commands

# --- Constants for Fixtures ---
OWNER_ID = 99999
AUTHORIZED_USER_ID = 12345
UNAUTHORIZED_USER_ID = 54321

# --- Fixtures ---

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

    bot.authorized_users = {AUTHORIZED_USER_ID, OWNER_ID}
    bot.is_owner = AsyncMock(side_effect=lambda user: user.id == OWNER_ID)
    return bot

@pytest.fixture
def mock_user_config_manager():
    """Fixture for a mock user config manager."""
    manager = Mock()
    manager.set_user_model.return_value = (True, "Model updated successfully.")
    manager.set_user_system_prompt.return_value = (True, "System prompt updated successfully.")
    manager.get_user_config.return_value = {"model": "test-gpt", "credit": 100, "access_level": 1}
    manager.get_user_system_prompt.return_value = "You are a helpful assistant."
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
    store.clear_user_messages = Mock()
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
def mock_ctx_authorized(mock_authorized_member):
    """Fixture for a mock command context of an authorized user."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = mock_authorized_member
    return ctx

@pytest.fixture
def mock_authorized_member():
    """Fixture for an authorized discord member."""
    member = Mock(spec=discord.Member)
    member.id = AUTHORIZED_USER_ID
    member.display_name = "TestUser"
    member.display_avatar = Mock(url="http://example.com/avatar.png")
    return member

@pytest.fixture
def mock_ctx_owner(mock_owner):
    """Fixture for a context where the author is the owner."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = mock_owner
    return ctx

@pytest.fixture
def mock_owner():
    """Fixture for a bot owner member."""
    owner = Mock(spec=discord.Member)
    owner.id = OWNER_ID
    owner.display_name = "BotOwner"
    owner.display_avatar = Mock(url="http://example.com/owner_avatar.png")
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
    async def test_set_model_success(self, mock_bot, mock_ctx_authorized, mock_user_config_manager, mock_call_api):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, mock_call_api, None, None)
        callback = get_command_callback(mock_bot, "model")

        await callback(mock_ctx_authorized, model="gpt-4")

        mock_user_config_manager.set_user_model.assert_called_once_with(AUTHORIZED_USER_ID, "gpt-4")
        mock_ctx_authorized.send.assert_called_once_with("✅ Model updated successfully.")

    async def test_set_model_unauthorized(self, mock_bot, mock_ctx_authorized, mock_user_config_manager, mock_call_api):
        mock_ctx_authorized.bot = mock_bot
        mock_bot.authorized_users = set() # Make user unauthorized
        setup_user_commands(mock_bot, mock_user_config_manager, mock_call_api, None, None)
        callback = get_command_callback(mock_bot, "model")

        await callback(mock_ctx_authorized, model="gpt-4")

        mock_user_config_manager.set_user_model.assert_not_called()
        mock_ctx_authorized.send.assert_called_once_with("❌ You are not authorized to use this command.")

@pytest.mark.asyncio
class TestProfileCommand:
    """Tests for the 'profile' command."""
    async def test_view_own_profile(self, mock_bot, mock_ctx_authorized, mock_user_config_manager):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None)
        callback = get_command_callback(mock_bot, "profile")

        await callback(mock_ctx_authorized, member=None)

        mock_user_config_manager.get_user_config.assert_called_once_with(AUTHORIZED_USER_ID)
        mock_ctx_authorized.send.assert_called_once_with(embed=ANY)
        sent_embed = mock_ctx_authorized.send.call_args.kwargs['embed']
        assert sent_embed.title == "Profile for TestUser"
        assert sent_embed.fields[0].value == "`test-gpt`"

@pytest.mark.asyncio
class TestModelsCommand:
    """Tests for the 'models' command."""
    async def test_show_models_with_mongodb(self, mock_bot, mock_ctx_authorized, mock_user_config_manager, mock_mongodb_store):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, mock_mongodb_store)
        callback = get_command_callback(mock_bot, "models")

        await callback(mock_ctx_authorized)

        mock_mongodb_store.list_all_models.assert_called_once()
        mock_ctx_authorized.send.assert_called_once_with(embed=ANY)
        embed = mock_ctx_authorized.send.call_args.kwargs['embed']
        assert "Ultimate (Lvl 2)" in embed.fields[0].name
        assert "`gpt-4`" in embed.fields[0].value
        assert "Advanced (Lvl 1)" in embed.fields[1].name
        assert "`gpt-3.5`" in embed.fields[1].value

    async def test_show_models_from_file(self, mock_bot, mock_ctx_authorized, mock_user_config_manager):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, mock_user_config_manager, None, None, None) # No mongo store
        callback = get_command_callback(mock_bot, "models")

        await callback(mock_ctx_authorized)

        mock_user_config_manager.get_supported_models.assert_called_once()
        mock_ctx_authorized.send.assert_called_once()
        sent_message = mock_ctx_authorized.send.call_args[0][0]
        assert "Supported AI Models (from config file):" in sent_message
        assert "`gpt-3.5`" in sent_message
        assert "`gpt-4`" in sent_message

@pytest.mark.asyncio
class TestClearMemoryCommand:
    """Tests for the 'clearmemory' command."""
    async def test_clear_own_memory_success(self, mock_bot, mock_ctx_authorized, mock_memory_store):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, None, None, mock_memory_store, None)
        callback = get_command_callback(mock_bot, "clearmemory")

        await callback(mock_ctx_authorized, member=None)

        mock_memory_store.clear_user_messages.assert_called_once_with(AUTHORIZED_USER_ID)
        mock_ctx_authorized.send.assert_called_once_with("✅ Cleared conversation memory for TestUser.")

    async def test_owner_clears_other_memory(self, mock_bot, mock_ctx_owner, mock_authorized_member, mock_memory_store):
        mock_ctx_owner.bot = mock_bot
        setup_user_commands(mock_bot, None, None, mock_memory_store, None)
        callback = get_command_callback(mock_bot, "clearmemory")

        await callback(mock_ctx_owner, member=mock_authorized_member)

        mock_memory_store.clear_user_messages.assert_called_once_with(mock_authorized_member.id)
        mock_ctx_owner.send.assert_called_once_with(f"✅ Cleared conversation memory for {mock_authorized_member.display_name}.")

    async def test_user_clears_other_memory_denied(self, mock_bot, mock_ctx_authorized, mock_owner, mock_memory_store):
        mock_ctx_authorized.bot = mock_bot
        setup_user_commands(mock_bot, None, None, mock_memory_store, None)
        callback = get_command_callback(mock_bot, "clearmemory")

        await callback(mock_ctx_authorized, member=mock_owner)

        mock_memory_store.clear_user_messages.assert_not_called()
        mock_ctx_authorized.send.assert_called_once_with("❌ You can only clear your own conversation memory.")