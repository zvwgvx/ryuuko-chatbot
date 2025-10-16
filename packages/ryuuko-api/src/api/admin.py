from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .dependencies import verify_bot_api_key
from ..database import db_store

router = APIRouter()

# --- Pydantic Schemas ---

class CreditUpdateRequest(BaseModel):
    amount: int

class LevelUpdateRequest(BaseModel):
    level: int = Field(..., ge=0, le=3)

class AdminActionResponse(BaseModel):
    message: str
    user_id: str
    new_value: int

# --- Endpoints (now using dashboard user_id) ---

@router.post("/users/{user_id}/credits/add", response_model=AdminActionResponse, dependencies=[Depends(verify_bot_api_key)])
async def admin_add_credits(user_id: str, request: CreditUpdateRequest):
    """(Admin) Adds credits to a user specified by their dashboard user ID."""
    user = db_store.get_dashboard_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found.")
    
    success, new_balance = db_store.admin_add_user_credit(user_id, request.amount)
    
    if success:
        return {"message": "Credits added successfully", "user_id": user_id, "new_value": new_balance}
    raise HTTPException(status_code=500, detail="Failed to add credits.")

@router.post("/users/{user_id}/credits/set", response_model=AdminActionResponse, dependencies=[Depends(verify_bot_api_key)])
async def admin_set_credits(user_id: str, request: CreditUpdateRequest):
    """(Admin) Sets the credits for a user specified by their dashboard user ID."""
    user = db_store.get_dashboard_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found.")

    db_store.admin_set_user_credit(user_id, request.amount)
    return {"message": "Credits set successfully", "user_id": user_id, "new_value": request.amount}

@router.post("/users/{user_id}/level/set", response_model=AdminActionResponse, dependencies=[Depends(verify_bot_api_key)])
async def admin_set_level(user_id: str, request: LevelUpdateRequest):
    """(Admin) Sets the access level for a user specified by their dashboard user ID."""
    user = db_store.get_dashboard_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found.")

    db_store.admin_set_user_level(user_id, request.level)
    return {"message": "Access level set successfully", "user_id": user_id, "new_value": request.level}
