# tests/events/test_messages.py
"""
Test suite for the message event handlers and AI request processing.
"""
import pytest
import discord
from discord.ext import commands
from unittest.mock import Mock, AsyncMock, MagicMock, patch, ANY

from bot.bot.events.messages import setup_message_events

# --- Fixtures ---

OWNER_ID = 99999
AUTHORIZED_USER_ID = 12345
UNAUTHORIZED_USER_ID = 54321

@pytest.fixture
def mock_bot():
    """Fixture for a mock bot that correctly handles listeners."""
    bot = MagicMock(spec=commands.Bot)
    bot.user = Mock(spec=discord.ClientUser, id=112233)

    bot.listeners = {}
    def listen_decorator(event_name):
        def decorator(func):
            bot.listeners[event_name] = func
            return func
        return decorator

    bot.listen = Mock(side_effect=listen_decorator)
    bot.get_context = AsyncMock()
    bot.is_owner = AsyncMock(side_effect=lambda user: user.id == OWNER_ID)
    return bot

@pytest.fixture
def mock_dependencies():
    """Fixture for the dictionary of mocked dependencies with accurate async/sync methods."""
    # Create a more specific mock for the request queue
    request_queue = Mock()
    request_queue.add_request = AsyncMock()  # This method is async
    request_queue.set_process_callback = Mock() # This method is sync

    return {
        'user_config_manager': Mock(),
        'request_queue': request_queue,
        'call_api': AsyncMock(),
        'memory_store': Mock(),
        'mongodb_store': Mock(),
        'authorized_users': {AUTHORIZED_USER_ID}
    }

@pytest.fixture
def mock_message():
    """Fixture for a mock Discord message."""
    message = AsyncMock(spec=discord.Message)
    message.author = Mock(spec=discord.Member, id=AUTHORIZED_USER_ID, bot=False)
    message.channel = AsyncMock(spec=discord.TextChannel)
    message.channel.send = AsyncMock()
    message.mentions = []
    message.content = ""
    message.attachments = []
    return message

# --- Test Suite ---

@pytest.mark.asyncio
class TestOnMessageListener:
    """Tests the logic of the on_message event listener."""

    async def test_ignores_bot_message(self, mock_bot, mock_dependencies, mock_message):
        mock_message.author.bot = True
        setup_message_events(mock_bot, mock_dependencies)
        on_message_callback = mock_bot.listeners['on_message']
        await on_message_callback(mock_message)
        mock_dependencies['request_queue'].add_request.assert_not_called()

    async def test_ignores_valid_command(self, mock_bot, mock_dependencies, mock_message):
        mock_bot.get_context.return_value.valid = True
        setup_message_events(mock_bot, mock_dependencies)
        on_message_callback = mock_bot.listeners['on_message']
        await on_message_callback(mock_message)
        mock_dependencies['request_queue'].add_request.assert_not_called()

    async def test_ignores_message_without_mention_or_dm(self, mock_bot, mock_dependencies, mock_message):
        mock_bot.get_context.return_value.valid = False
        mock_message.mentions = []
        setup_message_events(mock_bot, mock_dependencies)
        on_message_callback = mock_bot.listeners['on_message']
        await on_message_callback(mock_message)
        mock_dependencies['request_queue'].add_request.assert_not_called()

    async def test_rejects_unauthorized_user(self, mock_bot, mock_dependencies, mock_message):
        mock_bot.get_context.return_value.valid = False
        mock_message.author.id = UNAUTHORIZED_USER_ID
        mock_message.mentions = [mock_bot.user]
        setup_message_events(mock_bot, mock_dependencies)
        on_message_callback = mock_bot.listeners['on_message']
        await on_message_callback(mock_message)
        mock_dependencies['request_queue'].add_request.assert_not_called()
        mock_message.channel.send.assert_called_once_with("❌ Bạn không có quyền sử dụng bot này.")

    async def test_accepts_authorized_user_with_mention(self, mock_bot, mock_dependencies, mock_message):
        mock_bot.get_context.return_value.valid = False
        mock_message.mentions = [mock_bot.user]
        mock_message.content = f"<@!{mock_bot.user.id}> Hello bot"
        setup_message_events(mock_bot, mock_dependencies)
        on_message_callback = mock_bot.listeners['on_message']
        await on_message_callback(mock_message)
        mock_dependencies['request_queue'].add_request.assert_called_once_with(mock_message, "Hello bot")

@pytest.mark.asyncio
class TestProcessAIRequest:
    """Tests the core AI request processing logic."""

    @pytest.fixture
    def mock_request(self, mock_message):
        request = Mock()
        request.message = mock_message
        request.final_user_text = "This is a test prompt."
        return request

    @patch('bot.bot.events.messages.send_long_message_with_reference', new_callable=AsyncMock)
    @patch('bot.bot.events.messages._read_attachments_enhanced', new_callable=AsyncMock)
    async def test_successful_flow(self, mock_read_attachments, mock_send_long, mock_bot, mock_dependencies, mock_request):
        mock_read_attachments.return_value = {"text_summary": "", "has_images": False}
        ucm = mock_dependencies['user_config_manager']
        ucm.get_user_model.return_value = "test-model"
        ucm.get_user_system_message.return_value = {"role": "system", "content": "System prompt"}
        ucm.get_user_config.return_value = {"access_level": 2, "credit": 100}

        mongo = mock_dependencies['mongodb_store']
        mongo.get_model_info.return_value = {"access_level": 1, "credit_cost": 10}

        memory = mock_dependencies['memory_store']
        memory.get_user_messages.return_value = []

        api = mock_dependencies['call_api']
        api.call_unified_api.return_value = (True, "This is the AI response.")

        setup_message_events(mock_bot, mock_dependencies)
        process_callback = mock_dependencies['request_queue'].set_process_callback.call_args.args[0]

        await process_callback(mock_request)

        api.call_unified_api.assert_called_once()
        mock_send_long.assert_called_once_with(
            mock_request.message.channel,
            "This is the AI response.",
            mock_request.message
        )
        assert memory.add_message.call_count == 2
        mongo.deduct_user_credit.assert_called_once_with(AUTHORIZED_USER_ID, 10)

    @patch('bot.bot.events.messages._read_attachments_enhanced', new_callable=AsyncMock)
    async def test_insufficient_credits(self, mock_read_attachments, mock_bot, mock_dependencies, mock_request):
        mock_read_attachments.return_value = {"text_summary": "", "has_images": False}
        ucm = mock_dependencies['user_config_manager']
        ucm.get_user_model.return_value = "costly-model"
        ucm.get_user_config.return_value = {"access_level": 2, "credit": 5}

        mongo = mock_dependencies['mongodb_store']
        mongo.get_model_info.return_value = {"access_level": 1, "credit_cost": 10}

        api = mock_dependencies['call_api']

        setup_message_events(mock_bot, mock_dependencies)
        process_callback = mock_dependencies['request_queue'].set_process_callback.call_args.args[0]

        await process_callback(mock_request)

        api.call_unified_api.assert_not_called()
        mock_request.message.channel.send.assert_called_once()
        sent_message = mock_request.message.channel.send.call_args.args[0]
        assert "Không đủ credit" in sent_message