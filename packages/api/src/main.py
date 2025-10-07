import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Generator

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from pymongo.database import Database

# --- Configuration ---
MONGO_URI = os.getenv("MONGODB_CONNECTION_STRING", "")
MONGO_DB_NAME = "ryuuko_db"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a_very_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- Lifespan Manager for DB Connection ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, connect to the database
    app.state.mongo_client = MongoClient(MONGO_URI)
    app.state.db = app.state.mongo_client[MONGO_DB_NAME]
    print("Database connection established.")
    yield
    # On shutdown, close the connection
    app.state.mongo_client.close()
    print("Database connection closed.")

# --- FastAPI App ---
app = FastAPI(title="Ryuuko API", lifespan=lifespan)

# --- Dependency to get DB session ---
def get_db(request: Request) -> Database:
    return request.app.state.db

# --- Security ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Pydantic Models ---
class UserBase(BaseModel):
    email: EmailStr
    display_name: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    ryuuko_user_id: str
    password_hash: str
    created_at: datetime
    linked_accounts: dict = {}
    link_codes: list = []

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    ryuuko_user_id: Optional[str] = None

class UserConfig(BaseModel):
    model: str
    system_prompt: str

class LinkPlatformRequest(BaseModel):
    code: str
    platform: str
    platform_user_id: str

# --- Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire_time = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire_time, "sub": data["sub"]})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Dependency for getting current user ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        ryuuko_user_id: Optional[str] = payload.get("sub")
        if ryuuko_user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.users.find_one({"ryuuko_user_id": ryuuko_user_id})
    if user is None:
        raise credentials_exception
    return user

# --- API Endpoints ---
@app.post("/auth/register", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Database = Depends(get_db)):
    if db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = UserInDB(
        ryuuko_user_id=f"user_{uuid.uuid4().hex}",
        email=user.email,
        display_name=user.display_name,
        password_hash=get_password_hash(user.password),
        created_at=datetime.utcnow(),
    )
    db.users.insert_one(new_user.dict())
    return UserBase(**new_user.dict())

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    user_doc = db.users.find_one({"email": form_data.username})
    if not user_doc or not verify_password(form_data.password, user_doc["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(
        data={"sub": user_doc["ryuuko_user_id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserBase)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return UserBase(**current_user)

@app.post("/users/me/generate-link-code", status_code=status.HTTP_201_CREATED)
async def generate_link_code(current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    code = "".join(uuid.uuid4().hex[:6].upper())
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.users.update_one(
        {"ryuuko_user_id": current_user["ryuuko_user_id"]},
        {"$push": {"link_codes": {"code": code, "created_at": datetime.utcnow(), "expires_at": expires_at}}}
    )
    return {"code": code, "expires_at": expires_at}

@app.post("/link-platform", status_code=status.HTTP_200_OK)
async def link_platform(request: LinkPlatformRequest, db: Database = Depends(get_db)):
    user_doc = db.users.find_one({
        "link_codes": {"$elemMatch": {"code": request.code, "expires_at": {"$gt": datetime.utcnow()}}}
    })
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired link code.")

    db.users.update_one(
        {"ryuuko_user_id": user_doc["ryuuko_user_id"]},
        {"$set": {f"linked_accounts.{request.platform}": {"user_id": request.platform_user_id, "linked_at": datetime.utcnow()}},
         "$pull": {"link_codes": {"code": request.code}}}
    )
    return {"message": "Account linked successfully."}

@app.get("/users/me/config", response_model=UserConfig)
async def get_user_config(current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    config = db.user_configs.find_one({"ryuuko_user_id": current_user["ryuuko_user_id"]})
    if config:
        return UserConfig(**config)
    return UserConfig(model="ryuuko-r1-vnm-pro", system_prompt="Tên của bạn là Ryuuko (nữ), nói tiếng việt")

@app.put("/users/me/config", response_model=UserConfig)
async def update_user_config(config: UserConfig, current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    update_data = config.dict()
    update_data["updated_at"] = datetime.utcnow()
    db.user_configs.update_one(
        {"ryuuko_user_id": current_user["ryuuko_user_id"]},
        {"$set": update_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    return config