from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

from .dependencies import get_current_user, verify_bot_api_key
from ..database import db_store

router = APIRouter()

# --- Pydantic Schemas ---

class LinkedAccount(BaseModel):
    platform: str
    platform_user_id: str
    platform_display_name: Optional[str] = None
    platform_avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: datetime

class UserProfile(BaseModel):
    id: str
    username: str
    email: EmailStr
    credit: int
    access_level: int
    linked_accounts: List[LinkedAccount] = []

class UserConfigUpdate(BaseModel):
    model: Optional[str] = None
    system_prompt: Optional[str] = None

# --- Helper for model validation ---
def validate_model_access(user: dict, model_name: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_model = db_store.get_model_by_name(model_name)
    if not target_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model '{model_name}' does not exist.")

    user_level = user.get("access_level", 0)
    model_level = target_model.get("access_level", 0)

    if user_level < model_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your current plan does not grant access to the '{model_name}' model."
        )

# --- Endpoints ---

@router.get("/me", response_model=UserProfile, dependencies=[Depends(get_current_user)])
async def read_users_me(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    linked_accounts = db_store.get_linked_accounts_for_user(user_id)
    return UserProfile(
        id=user_id, username=current_user["username"], email=current_user["email"],
        credit=current_user.get("credit", 0), access_level=current_user.get("access_level", 0),
        linked_accounts=[LinkedAccount(**acc) for acc in linked_accounts]
    )

@router.put("/me/config", status_code=200)
async def update_user_config_dashboard(config_update: UserConfigUpdate, current_user: dict = Depends(get_current_user)):
    """(Dashboard) Updates the authenticated user's configuration."""
    if config_update.model:
        validate_model_access(current_user, config_update.model)
    
    user_id = str(current_user["_id"])
    success = db_store.update_user_config(user_id, model=config_update.model, system_prompt=config_update.system_prompt)
    if success: return {"message": "Configuration updated successfully."}
    return {"message": "Configuration was not modified."}


@router.get("/by-platform/{platform}/{platform_user_id}", response_model=UserProfile, dependencies=[Depends(verify_bot_api_key)])
async def get_user_by_platform_id(platform: str, platform_user_id: str):
    link = db_store.find_linked_account(platform, platform_user_id)
    if not link: raise HTTPException(status_code=404, detail="Linked account not found.")
    user = db_store.get_dashboard_user_by_id(str(link["user_id"]))
    if not user: raise HTTPException(status_code=404, detail="User associated with link not found.")
    linked_accounts = db_store.get_linked_accounts_for_user(str(user["_id"]))
    return UserProfile(
        id=str(user["_id"]), username=user["username"], email=user["email"],
        credit=user.get("credit", 0), access_level=user.get("access_level", 0),
        linked_accounts=[LinkedAccount(**acc) for acc in linked_accounts]
    )

@router.put("/by-platform/{platform}/{platform_user_id}/config", status_code=200, dependencies=[Depends(verify_bot_api_key)])
async def update_user_config_by_platform(platform: str, platform_user_id: str, config_update: UserConfigUpdate):
    """(Bot) Updates a user's configuration (e.g., preferred model)."""
    link = db_store.find_linked_account(platform, platform_user_id)
    if not link: raise HTTPException(status_code=404, detail="Linked account not found.")
    user = db_store.get_dashboard_user_by_id(str(link["user_id"]))

    if config_update.model:
        validate_model_access(user, config_update.model)

    success = db_store.update_user_config(str(user["_id"]), model=config_update.model, system_prompt=config_update.system_prompt)
    if success: return {"message": "Configuration updated successfully."}
    return {"message": "Configuration was not modified."}
