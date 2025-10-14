from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

from .. import config
from ..database import db_store # Import the shared db_store instance

# --- Security & Token Configuration ---

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

SECRET_KEY = config.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Security Helper Functions ---

def _truncate_password(password: str) -> str:
    """Encodes, truncates to 72 bytes, and decodes back to a string."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        return password_bytes[:72].decode('utf-8', 'ignore')
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against a hash, truncating for bcrypt compatibility."""
    password_to_verify = _truncate_password(plain_password)
    return PWD_CONTEXT.verify(password_to_verify, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password, truncating it to 72 bytes for bcrypt compatibility."""
    password_to_hash = _truncate_password(password)
    return PWD_CONTEXT.hash(password_to_hash)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Pydantic Schemas ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

# --- Router ---

router = APIRouter()

# --- Endpoints ---

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Handles new user registration."""
    hashed_password = get_password_hash(user.password)
    user_id = db_store.create_dashboard_user(user.username, user.email, hashed_password)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )
    return {"message": "User created successfully", "user_id": user_id}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Handles user login and issues a JWT token. This uses the standard OAuth2 form data.
    The client should post to this endpoint with 'username' and 'password' in the form body.
    """
    user = db_store.get_dashboard_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
