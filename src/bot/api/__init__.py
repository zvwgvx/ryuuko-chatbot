# src/bot/api/__init__.py
"""
API integration layer.
Contains clients for interacting with external AI services.
"""
from .client import (
    UnifiedAPIClient,
    call_unified_api,
    is_thinking_model,
    build_api_request,
)

__all__ = [
    'UnifiedAPIClient',
    'call_unified_api',
    'is_thinking_model',
    'build_api_request',
]