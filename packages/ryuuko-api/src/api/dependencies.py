# /packages/ryuuko-api/src/api/dependencies.py
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional

from .. import config
from ..database import db_store

# --- Schemas & Constants ---

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = "HS256"

class TokenData(BaseModel):
    user_id: Optional[str] = None

# --- Dependency Functions ---

async def get_current_user(token: str = Depends(OAUTH2_SCHEME)) -> dict:
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

async def verify_bot_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the API key used by internal bots."""
    if x_api_key != config.BOT_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bot API Key")

async def verify_core_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the CORE_API_KEY for admin actions."""
    if x_api_key != config.CORE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Core API Key")
