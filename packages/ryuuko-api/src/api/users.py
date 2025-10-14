from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from jose import JWTError, jwt

from .auth import OAUTH2_SCHEME, SECRET_KEY, ALGORITHM, TokenData
from ..database import db_store # Import the shared db_store instance

router = APIRouter()

# --- Pydantic Schemas ---

class LinkedAccount(BaseModel):
    platform: str
    platform_display_name: Optional[str] = None

class UserProfile(BaseModel):
    id: str
    username: str
    email: EmailStr
    linked_accounts: List[LinkedAccount] = []

# --- Dependency ---

async def get_current_user(token: str = Depends(OAUTH2_SCHEME)):
    """Decodes JWT token to get user ID, then fetches user from DB."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = db_store.get_dashboard_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

# --- Endpoint ---

@router.get("/me", response_model=UserProfile)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Fetches profile for the currently authenticated user."""
    user_id = str(current_user["_id"])
    linked_accounts = db_store.get_linked_accounts_for_user(user_id)
    
    # We need to manually construct the response model as the DB dictionary is not directly compatible
    user_profile = UserProfile(
        id=user_id,
        username=current_user["username"],
        email=current_user["email"],
        linked_accounts=[LinkedAccount(**acc) for acc in linked_accounts]
    )
    return user_profile
