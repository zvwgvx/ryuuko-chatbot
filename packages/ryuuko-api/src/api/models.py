# /packages/ryuuko-api/src/api/models.py
from fastapi import APIRouter, Depends
from typing import List

from .dependencies import get_current_user
from ..database import db_store

router = APIRouter()

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_supported_models() -> List[dict]:
    """Returns a list of all supported AI models available in the system."""
    models = db_store.get_all_models()
    return models
