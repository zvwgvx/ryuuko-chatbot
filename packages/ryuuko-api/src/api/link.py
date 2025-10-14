from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional

from .users import get_current_user
from ..database import db_store # Import the shared db_store instance
from .. import config

router = APIRouter()

# --- Dependency for Bot-only endpoints ---

async def verify_bot_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the API key used by internal bots."""
    if x_api_key != config.BOT_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bot API Key")

# --- Pydantic Schemas ---

class LinkCodeResponse(BaseModel):
    link_code: str
    expires_in_seconds: int

class VerifyRequest(BaseModel):
    code: str
    platform: str
    platform_user_id: str
    platform_display_name: str

# --- Endpoints ---

@router.post("/generate-code", response_model=LinkCodeResponse)
async def generate_link_code(current_user: dict = Depends(get_current_user)):
    """Generates a temporary link code for the authenticated user."""
    user_id = str(current_user["_id"])
    code = db_store.create_link_code(user_id)
    return {"link_code": code, "expires_in_seconds": 300} # TTL is set in MongoDB index

@router.post("/verify", dependencies=[Depends(verify_bot_api_key)])
async def verify_link_code(request: VerifyRequest):
    """Verifies a link code and creates the account link. Called by the bot."""
    # 1. Validate the code
    user_id = db_store.validate_link_code(request.code)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link code")

    # 2. Check if the platform account is already linked to someone else
    existing_link = db_store.find_linked_account(request.platform, request.platform_user_id)
    if existing_link and str(existing_link["user_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This platform account is already linked to another user.")

    # 3. Create the link
    success, message = db_store.create_linked_account(
        user_id=user_id,
        platform=request.platform,
        platform_user_id=request.platform_user_id,
        platform_display_name=request.platform_display_name
    )

    if not success:
        # This might happen in a rare race condition or if the DB fails
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    return {"message": message}
