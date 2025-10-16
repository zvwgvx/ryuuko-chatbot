from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from .dependencies import get_current_user, verify_bot_api_key
from ..database import db_store

router = APIRouter()

# --- Pydantic Schemas ---

class LinkCodeResponse(BaseModel):
    link_code: str
    expires_in_seconds: int

class SubmitCodeRequest(BaseModel):
    code: str
    platform: str
    platform_user_id: str
    platform_display_name: str

class UnlinkRequest(BaseModel):
    platform: str
    platform_user_id: str

# --- Endpoints ---

@router.post("/generate-code", response_model=LinkCodeResponse)
async def generate_link_code(current_user: dict = Depends(get_current_user)):
    """(Dashboard) Generates a temporary link code for the authenticated user."""
    user_id = str(current_user["_id"])
    code = db_store.create_link_code(user_id)
    return {"link_code": code, "expires_in_seconds": 300}

@router.post("/submit-code", dependencies=[Depends(verify_bot_api_key)])
async def submit_link_code(request: SubmitCodeRequest):
    """(Bot) Verifies a link code and creates the account link."""
    user_id = db_store.validate_link_code(request.code)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link code.")

    existing_link = db_store.find_linked_account(request.platform, request.platform_user_id)
    if existing_link and str(existing_link["user_id"]) != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This platform account is already linked to another user.")

    success, message = db_store.create_linked_account(
        user_id=user_id,
        platform=request.platform,
        platform_user_id=request.platform_user_id,
        platform_display_name=request.platform_display_name
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    return {"message": message}

@router.post("/unlink", status_code=200, dependencies=[Depends(verify_bot_api_key)])
async def unlink_account(request: UnlinkRequest):
    """(Bot) Deletes a linked account record."""
    deleted = db_store.delete_linked_account(request.platform, request.platform_user_id)
    if not deleted:
        # We don't raise an error to make the operation idempotent.
        # If the link doesn't exist, the desired state is already achieved.
        return {"message": "This account was not linked."}
    
    return {"message": "Your account has been successfully unlinked."}
