# src/bot/api/__init__.py
"""
API integration layer.
Contains clients for interacting with llm_services AI services.
"""
from .client import (
    call_unified_api,
    build_api_request,
    is_model_available  # <<< THÊM DÒNG NÀY
)

__all__ = [
    'call_unified_api',
    'build_api_request',
    'is_model_available', # <<< VÀ THÊM VÀO ĐÂY
]