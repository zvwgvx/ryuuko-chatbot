# /packages/ryuuko-api/src/main.py
import logging
from typing import Dict, Any, List, Optional, Set

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Import config first to ensure all environment variables are loaded and validated.
from . import config

# --- NEW: Import the shared db_store instance from the new database module ---
from .database import db_store

# --- NEW: Import API routers for dashboard functionality ---
from .api import auth as auth_router
from .api import users as users_router
from .api import link as link_router

# Import other local modules
from .providers import polydevs, aistudio, proxyvn

# --- App Initialization ---
app = FastAPI(
    title="Ryuuko API",
    description="Core API Service for the Ryuuko Chatbot ecosystem.",
    version="2.0.1"
)

# --- NEW: Include Dashboard API Routers ---
# These routers handle authentication, user management, and account linking for the new dashboard.
app.include_router(auth_router.router, prefix="/api/auth", tags=["Dashboard Auth"])
app.include_router(users_router.router, prefix="/api/users", tags=["Dashboard Users"])
app.include_router(link_router.router, prefix="/api/link", tags=["Account Linking"])


# Map provider names to their forwarding functions.
PROVIDER_MAP = {"polydevs": polydevs.forward, "aistudio": aistudio.forward, "proxyvn": proxyvn.forward}

# --- Authentication (for original bot functionality) ---
async def verify_api_key(x_api_key: str = Header(...)):
    """Dependency to verify the provided API key in the request header."""
    if x_api_key != config.CORE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

# --- Pydantic Models (for original bot functionality) ---
class ModelInfoResponse(BaseModel):
    model_name: str
    credit_cost: int
    access_level: int

class UserProfileResponse(BaseModel):
    model: str
    system_prompt: str
    credit: int
    access_level: int

class ChatCompletionRequest(BaseModel):
    user_id: int
    messages: List[Dict[str, Any]]
    model: Optional[str] = None

class UserConfigUpdateRequest(BaseModel):
    model: Optional[str] = None
    system_prompt: Optional[str] = None

class CreditUpdateRequest(BaseModel):
    amount: int

class LevelUpdateRequest(BaseModel):
    level: int = Field(..., ge=0, le=3)

class ModelCreateRequest(BaseModel):
    model_name: str
    credit_cost: int = Field(..., ge=0)
    access_level: int = Field(..., ge=0, le=3)

class AuthUserRequest(BaseModel):
    user_id: int

# --- API Endpoints (Original and New Root) ---
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Ryuuko API is running."}

# --- Existing API Endpoints for Bot ---

@app.post("/api/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    user_id = request.user_id
    user_config = db_store.get_user_config(user_id)
    model_to_use = request.model or user_config.get("model", "ryuuko-r1-vnm-mini")
    
    provider_name = "polydevs"
    if model_to_use.startswith("gemini-"): provider_name = "aistudio"
    elif model_to_use.startswith("gpt-"): provider_name = "proxyvn"
    
    forward_fn = PROVIDER_MAP.get(provider_name)
    if not forward_fn: 
        raise HTTPException(status_code=400, detail=f"Provider for model '{model_to_use}' not found.")
        
    history = db_store.get_user_messages(user_id)
    provider_payload = {
        "model": model_to_use, 
        "messages": history + request.messages, 
        "config": {}, 
        "system_instruction": [user_config.get("system_prompt")]
    }
    
    api_key_map = {
        "polydevs": config.POLYDEVS_API_KEY, 
        "aistudio": config.GEMINI_API_KEY, 
        "proxyvn": config.PROXYVN_API_KEY
    }
    provider_api_key = api_key_map.get(provider_name)
    
    if not provider_api_key: 
        raise HTTPException(status_code=500, detail=f"API key for '{provider_name}' is not configured.")
        
    try:
        streaming_response = await forward_fn(http_request, provider_payload, provider_api_key)
        response_content_bytes = b"".join([chunk async for chunk in streaming_response.body_iterator])
        final_response_text = response_content_bytes.decode('utf-8').strip()
        
        db_store.add_message(user_id, request.messages[-1])
        db_store.add_message(user_id, {"role": "assistant", "content": final_response_text})
        
        async def final_streamer(): 
            yield final_response_text.encode('utf-8')
            
        return StreamingResponse(final_streamer(), media_type="text/plain; charset=utf-8")
    except Exception as e:
        logging.getLogger("RyuukoAPI.API").exception(f"Error during provider call: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.get("/api/v1/models", response_model=List[ModelInfoResponse], dependencies=[Depends(verify_api_key)])
async def list_available_models():
    return db_store.list_all_models()

@app.get("/api/v1/users/{user_id}", response_model=UserProfileResponse, dependencies=[Depends(verify_api_key)])
async def get_user_profile(user_id: int):
    return db_store.get_user_config(user_id)

@app.get("/api/v1/users/{user_id}/memory", dependencies=[Depends(verify_api_key)])
async def get_user_memory(user_id: int) -> List[Dict[str, Any]]:
    return db_store.get_user_messages(user_id)

@app.put("/api/v1/users/{user_id}/config", dependencies=[Depends(verify_api_key)])
async def update_user_config(user_id: int, config_update: UserConfigUpdateRequest):
    success = db_store.set_user_config(user_id, model=config_update.model, system_prompt=config_update.system_prompt)
    if success: return {"message": f"Configuration updated for user {user_id}"}
    raise HTTPException(status_code=500, detail="Failed to update configuration.")

@app.delete("/api/v1/users/{user_id}/memory", dependencies=[Depends(verify_api_key)])
async def clear_user_memory(user_id: int):
    success = db_store.clear_user_memory(user_id)
    if success: return {"message": f"Memory cleared for user {user_id}"}
    raise HTTPException(status_code=500, detail="Failed to clear memory.")

@app.post("/api/v1/admin/models", dependencies=[Depends(verify_api_key)])
async def add_model(model_data: ModelCreateRequest):
    success, message = db_store.add_supported_model(model_data.model_name, model_data.credit_cost, model_data.access_level)
    if success: return {"message": message}
    raise HTTPException(status_code=400, detail=message)

@app.delete("/api/v1/admin/models/{model_name}", dependencies=[Depends(verify_api_key)])
async def remove_model(model_name: str):
    success, message = db_store.remove_supported_model(model_name)
    if success: return {"message": message}
    raise HTTPException(status_code=400, detail=message)

@app.put("/api/v1/admin/users/{user_id}/credits/add", dependencies=[Depends(verify_api_key)])
async def add_user_credits(user_id: int, credit_update: CreditUpdateRequest):
    success, new_balance = db_store.add_user_credit(user_id, credit_update.amount)
    if success: return {"new_balance": new_balance}
    raise HTTPException(status_code=500, detail="Failed to add credits.")

@app.put("/api/v1/admin/users/{user_id}/credits/deduct", dependencies=[Depends(verify_api_key)])
async def deduct_user_credits(user_id: int, credit_update: CreditUpdateRequest):
    success, new_balance = db_store.deduct_user_credit(user_id, credit_update.amount)
    if success: return {"new_balance": new_balance}
    raise HTTPException(status_code=400, detail=f"Failed to deduct credits. Insufficient balance? Current: {new_balance}")

@app.put("/api/v1/admin/users/{user_id}/credits/set", dependencies=[Depends(verify_api_key)])
async def set_user_credits(user_id: int, credit_update: CreditUpdateRequest):
    success = db_store.set_user_credit(user_id, credit_update.amount)
    if success: return {"message": f"Credits set to {credit_update.amount}"}
    raise HTTPException(status_code=500, detail="Failed to set credits.")

@app.put("/api/v1/admin/users/{user_id}/level", dependencies=[Depends(verify_api_key)])
async def set_user_level(user_id: int, level_update: LevelUpdateRequest):
    success = db_store.set_user_level(user_id, level_update.level)
    if success: return {"message": f"Access level set to {level_update.level}"}
    raise HTTPException(status_code=500, detail="Failed to set access level.")

@app.get("/api/v1/admin/auth/users", dependencies=[Depends(verify_api_key)])
async def get_authorized_users() -> Set[int]:
    return db_store.get_authorized_users()

@app.post("/api/v1/admin/auth/users", dependencies=[Depends(verify_api_key)])
async def add_authorized_user(auth_request: AuthUserRequest):
    success = db_store.add_authorized_user(auth_request.user_id)
    if success: return {"message": f"User {auth_request.user_id} authorized."}
    raise HTTPException(status_code=500, detail="Failed to authorize user.")

@app.delete("/api/v1/admin/auth/users/{user_id}", dependencies=[Depends(verify_api_key)])
async def remove_authorized_user(user_id: int):
    success = db_store.remove_authorized_user(user_id)
    if success: return {"message": f"User {user_id} de-authorized."}
    raise HTTPException(status_code=500, detail="Failed to de-authorize user.")
