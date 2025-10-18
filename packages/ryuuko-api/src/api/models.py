# /packages/ryuuko-api/src/api/models.py
from fastapi import APIRouter
from typing import List

from ..database import db_store

router = APIRouter()

# CORRECTED: Make this endpoint public as the data is not sensitive.
# This resolves authentication issues for both the bot and the dashboard.
@router.get("")
async def get_supported_models() -> List[dict]:
    """Returns a list of all supported AI models available in the system."""
    models = db_store.get_all_models()
    return models
