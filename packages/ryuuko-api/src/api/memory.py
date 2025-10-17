# /packages/ryuuko-api/src/api/memory.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from .dependencies import get_current_user, verify_bot_api_key
from ..database import db_store

router = APIRouter()

# --- Dashboard Endpoint ---
@router.get("/dashboard", response_model=List[Dict[str, Any]], dependencies=[Depends(get_current_user)])
async def get_memory_dashboard(current_user: dict = Depends(get_current_user)):
    """(Dashboard) Fetches the entire conversation memory for the authenticated user."""
    user_id = str(current_user["_id"])
    memory = db_store.get_user_memory(user_id)
    return memory

@router.delete("/dashboard", status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_user)])
async def clear_memory_dashboard(current_user: dict = Depends(get_current_user)):
    """(Dashboard) Clears the entire conversation memory for the authenticated user."""
    user_id = str(current_user["_id"])
    success = db_store.clear_user_memory(user_id)
    if success:
        return {"message": "Your conversation memory has been cleared."}
    return {"message": "No conversation memory was found to clear."}

# --- Bot Endpoints ---
@router.get("/{platform}/{platform_user_id}", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_bot_api_key)])
async def get_memory_bot(platform: str, platform_user_id: str):
    """(Bot) Fetches the conversation memory for a user on a specific platform."""
    link = db_store.find_linked_account(platform, platform_user_id)
    if not link:
        raise HTTPException(status_code=404, detail="Account not linked.")
    
    user_id = str(link["user_id"])
    memory = db_store.get_user_memory(user_id)
    return memory

@router.delete("/{platform}/{platform_user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(verify_bot_api_key)])
async def clear_memory_bot(platform: str, platform_user_id: str):
    """(Bot) Clears the conversation memory for a user on a specific platform."""
    link = db_store.find_linked_account(platform, platform_user_id)
    if not link:
        raise HTTPException(status_code=404, detail="Account not linked.")

    user_id = str(link["user_id"])
    success = db_store.clear_user_memory(user_id)
    if success:
        return {"message": "Your conversation memory has been cleared."}
    return {"message": "No conversation memory was found to clear."}
