# packages/bot/src/api/__init__.py
"""
API integration layer.
Contains clients for interacting with llm_services AI services.
"""
from .client import (
    call_unified_api,
    build_api_request,
    is_model_available
)

__all__ = [
    'call_unified_api',
    'build_api_request',
    'is_model_available',
]