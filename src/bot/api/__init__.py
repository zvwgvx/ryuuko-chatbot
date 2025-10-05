# src/bot/api/__init__.py
"""
API integration layer.
Contains clients for interacting with external AI services.
"""
from .client import (
    call_unified_api,
    build_api_request,
)

__all__ = [
    'call_unified_api',
    'build_api_request',
]