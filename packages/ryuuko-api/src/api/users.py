from fastapi import APIRouter, Depends, HTTPException
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
    # FIX: Make created_at optional to handle legacy documents.
    created_at: Optional[datetime] = None
    # Add updated_at, which should always be present.
    updated_at: datetime

class UserProfile(BaseModel):
    id: str
    username: str
    email: EmailStr
    credit: int
    access_level: int
    linked_accounts: List[LinkedAccount] = []

# --- Endpoints ---

@router.get("/me", response_model=UserProfile)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Fetches profile for the currently authenticated user."""
    user_id = str(current_user["_id"])
    linked_accounts = db_store.get_linked_accounts_for_user(user_id)
    
    return UserProfile(
        id=user_id,
        username=current_user["username"],
        email=current_user["email"],
        credit=current_user.get("credit", 0),
        access_level=current_user.get("access_level", 0),
        linked_accounts=[LinkedAccount(**acc) for acc in linked_accounts]
    )

@router.get("/by-platform/{platform}/{platform_user_id}", response_model=UserProfile, dependencies=[Depends(verify_bot_api_key)])
async def get_user_by_platform_id(platform: str, platform_user_id: str):
    """(For Bots) Finds a dashboard user via their linked platform account."""
    link = db_store.find_linked_account(platform, platform_user_id)
    if not link:
        raise HTTPException(status_code=404, detail="Linked account not found.")

    user_id = str(link["user_id"])
    user = db_store.get_dashboard_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User associated with link not found.")

    linked_accounts = db_store.get_linked_accounts_for_user(user_id)

    return UserProfile(
        id=user_id,
        username=user["username"],
        email=user["email"],
        credit=user.get("credit", 0),
        access_level=user.get("access_level", 0),
        linked_accounts=[LinkedAccount(**acc) for acc in linked_accounts]
    )
