# tests/commands/test_basic.py
"""
Test suite for the basic command module.
"""
import pytest
import discord
from unittest.mock import Mock, AsyncMock, MagicMock, patch, ANY

from discord.ext import commands

# Import the setup function to be tested
from src.bot.commands.basic import setup_basic_commands

@pytest.fixture
def mock_bot():
    """Fixture to create a mock bot that accurately captures command registration."""
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
    # Mock latency attribute for the ping command
    bot.latency = 0.123  # 123 ms
    return bot

@pytest.fixture
def mock_ctx():
    """Fixture for a mock command context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    # Mock the author object for the help command's owner check
    ctx.author = Mock(spec=discord.Member)
    return ctx

def get_command_callback(bot, name):
    """Helper to find a command's callback from the mock bot."""
    command_mock = next(
        call.args[0] for call in bot.add_command.call_args_list if call.args[0].name == name
    )
    return command_mock.callback

# --- Test Suite ---

class TestBasicCommandSetup:
    """Test the initial setup of basic commands."""
    def test_setup_registers_commands(self, mock_bot):
        """Verify that the setup function registers the ping and help commands."""
        setup_basic_commands(mock_bot)
        assert mock_bot.command.call_count == 2
        assert mock_bot.add_command.call_count == 2
        command_names = [cmd.name for cmd in [c.args[0] for c in mock_bot.add_command.call_args_list]]
        assert "ping" in command_names
        assert "help" in command_names

@pytest.mark.asyncio
class TestPingCommand:
    """Tests for the 'ping' command."""
    @patch('time.perf_counter')
    async def test_ping_calculates_latency(self, mock_perf_counter, mock_bot, mock_ctx):
        # Arrange: Set up the mock time and the mock message returned by ctx.send
        mock_perf_counter.side_effect = [1000.0, 1000.5] # 0.5s difference
        mock_message = AsyncMock()
        mock_message.edit = AsyncMock()
        mock_ctx.send.return_value = mock_message

        setup_basic_commands(mock_bot)
        ping_callback = get_command_callback(mock_bot, "ping")

        # Act
        await ping_callback(mock_ctx)

        # Assert
        mock_ctx.send.assert_called_once_with("Pinging...")

        expected_content = (
            f"Pong! 🏓\n"
            f"Response Time: `500ms`\n"
            f"WebSocket Latency: `123ms`"
        )
        mock_message.edit.assert_called_once_with(content=expected_content)

@pytest.mark.asyncio
class TestHelpCommand:
    """Tests for the 'help' command."""
    async def test_help_for_normal_user(self, mock_bot, mock_ctx):
        # Arrange: User is not an owner
        mock_bot.is_owner = AsyncMock(return_value=False)
        setup_basic_commands(mock_bot)
        help_callback = get_command_callback(mock_bot, "help")

        # Act
        await help_callback(mock_ctx)

        # Assert: Check that send was called with an embed
        mock_ctx.send.assert_called_once_with(embed=ANY)
        sent_embed = mock_ctx.send.call_args.kwargs['embed']

        assert isinstance(sent_embed, discord.Embed)
        # Normal user should only see one field for user commands
        assert len(sent_embed.fields) == 1
        assert sent_embed.fields[0].name == "👤 User Commands"

    async def test_help_for_owner_user(self, mock_bot, mock_ctx):
        # Arrange: User is an owner
        mock_bot.is_owner = AsyncMock(return_value=True)
        setup_basic_commands(mock_bot)
        help_callback = get_command_callback(mock_bot, "help")

        # Act
        await help_callback(mock_ctx)

        # Assert: Check that send was called with an embed containing all sections
        mock_ctx.send.assert_called_once_with(embed=ANY)
        sent_embed = mock_ctx.send.call_args.kwargs['embed']

        assert isinstance(sent_embed, discord.Embed)
        # Owner should see all four fields
        assert len(sent_embed.fields) == 4
        field_names = [field.name for field in sent_embed.fields]
        assert "👤 User Commands" in field_names
        assert "👑 Owner Commands" in field_names
        assert "🛠️ Model Management (Owner)" in field_names
        assert "💰 Credit & Access Management (Owner)" in field_names