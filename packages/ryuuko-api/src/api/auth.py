import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, date
from typing import Optional

from .. import config
from ..database import db_store

# --- Configuration & Setup ---

logger = logging.getLogger("RyuukoAPI.Auth")

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()

# --- Security Helper Functions ---

def _truncate_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    return password_bytes[:72].decode('utf-8', 'ignore') if len(password_bytes) > 72 else password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return PWD_CONTEXT.verify(_truncate_password(plain_password), hashed_password)

def get_password_hash(password: str) -> str:
    return PWD_CONTEXT.hash(_truncate_password(password))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Pydantic Schemas ---

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    dob: date
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str

class RegisterResponse(BaseModel):
    message: str
    user_id: str
    token: Token

# --- Endpoints ---

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Handles new user registration and immediately returns an access token."""
    if db_store.get_dashboard_user_by_username(user.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    user_id = db_store.create_dashboard_user(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        dob=datetime.combine(user.dob, datetime.min.time())
    )
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email may already be registered")

    access_token = create_access_token(data={"user_id": user_id})
    
    return {
        "message": "User created successfully",
        "user_id": user_id,
        "token": {"access_token": access_token, "token_type": "bearer"}
    }

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Handles user login and issues a JWT token, with self-healing for the owner account."""
    # --- Self-Healing Owner Account (driven by .env variables) ---
    if form_data.username == config.OWNER_USERNAME:
        owner_password_hash = get_password_hash(config.OWNER_PASSWORD)
        db_store.create_or_update_owner_user(
            username=config.OWNER_USERNAME,
            email=config.OWNER_EMAIL,
            hashed_password=owner_password_hash,
            first_name=config.OWNER_FIRST_NAME,
            last_name=config.OWNER_LAST_NAME
        )

    # --- Standard Authentication ---
    user = db_store.get_dashboard_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    
    access_token = create_access_token(data={"user_id": str(user["_id"])})
    
    return {"access_token": access_token, "token_type": "bearer"}
