"""
Core package for Ryuuko Chatbot
Contains main bot logic, API clients, and bot functions
"""

# Import from call_api.py
from .call_api import (
    UnifiedAPIClient,
    call_api,
    is_model_available,
    is_thinking_model,
    build_api_request,
)

# Import from functions.py
from .functions import (
    # Main setup function
    setup,

    # User authorization functions
    is_authorized_user,
    add_authorized_user,
    remove_authorized_user,
    load_authorized_users,

    # Utility functions
    should_respond_default,
    get_vietnam_timestamp,

    # Message formatting
    convert_latex_to_discord,
    split_message_smart,
    send_long_message_with_reference,

    # AI processing
    process_ai_request,
)

# Note: bot.py is the main entry point, doesn't export functions
# from .bot import ... (nothing to export)

__all__ = [
    # API client
    'UnifiedAPIClient',
    'call_api',
    'is_model_available',
    'is_thinking_model',
    'build_api_request',

    # Bot functions
    'setup',
    'is_authorized_user',
    'add_authorized_user',
    'remove_authorized_user',
    'load_authorized_users',
    'should_respond_default',
    'get_vietnam_timestamp',
    'convert_latex_to_discord',
    'split_message_smart',
    'send_long_message_with_reference',
    'process_ai_request',
]