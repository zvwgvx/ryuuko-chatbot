# /packages/ryuuko-api/src/main.py
import logging
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .database import db_store
from .api import auth as auth_router
from .api import users as users_router
from .api import link as link_router
from .api import admin as admin_router
from .api import models as models_router
from .api import memory as memory_router # NEW: Import the memory router
from .api.dependencies import get_current_user, verify_bot_api_key
from .providers import polydevs, aistudio, proxyvn

# --- App Initialization ---
app = FastAPI(
    title="Ryuuko API",
    description="Core API Service for the Ryuuko Chatbot ecosystem.",
    version="3.5.0" # Version bump for memory endpoint
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(auth_router.router, prefix="/api/auth", tags=["Dashboard Auth"])
app.include_router(users_router.router, prefix="/api/users", tags=["Dashboard Users"])
app.include_router(link_router.router, prefix="/api/link", tags=["Account Linking"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["Dashboard Admin"])
app.include_router(models_router.router, prefix="/api/models", tags=["Models"])
app.include_router(memory_router.router, prefix="/api/memory", tags=["Dashboard Memory"]) # NEW: Include the memory router

# --- Provider Mapping ---
PROVIDER_MAP = {"polydevs": polydevs.forward, "aistudio": aistudio.forward, "proxyvn": proxyvn.forward}
API_KEY_MAP = {
    "polydevs": config.POLYDEVS_API_KEY, 
    "aistudio": config.GEMINI_API_KEY, 
    "proxyvn": config.PROXYVN_API_KEY
}

# --- Unified Chat Schemas ---
class UnifiedChatRequest(BaseModel):
    platform: str
    platform_user_id: str
    messages: List[Dict[str, Any]]
    model: Optional[str] = None

# --- Root Endpoint ---
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Ryuuko API is running."}

# --- UNIFIED CHAT ENDPOINT ---
@app.post("/api/chat/completions", dependencies=[Depends(verify_bot_api_key)])
async def unified_chat_completions(request: UnifiedChatRequest, http_request: Request):
    link = db_store.find_linked_account(request.platform, request.platform_user_id)
    if not link:
        raise HTTPException(status_code=403, detail="Account not linked. Please link your account on the dashboard first.")
    
    user_id = str(link["user_id"])
    user = db_store.get_dashboard_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Linked user not found in the database.")

    model_to_use = request.model or user.get("model") or "ryuuko-r1-vnm-mini"
    
    provider_name = "polydevs"
    if model_to_use.startswith("gemini-"): provider_name = "aistudio"
    elif model_to_use.startswith("gpt-"): provider_name = "proxyvn"

    forward_fn = PROVIDER_MAP.get(provider_name)
    provider_api_key = API_KEY_MAP.get(provider_name)

    if not forward_fn or not provider_api_key:
        raise HTTPException(status_code=501, detail=f"Provider or API key for model '{model_to_use}' is not configured.")

    history = db_store.get_user_memory(user_id)
    system_prompt = user.get("system_prompt")
    
    provider_payload = {
        "model": model_to_use,
        "messages": history + request.messages,
        "config": {},
        "system_instruction": [system_prompt] if system_prompt else []
    }

    try:
        streaming_response = await forward_fn(http_request, provider_payload, provider_api_key)
        response_content_bytes = b"".join([chunk async for chunk in streaming_response.body_iterator])
        final_response_text = response_content_bytes.decode('utf-8').strip()
        
        db_store.add_message_to_memory(user_id, request.messages[-1])
        db_store.add_message_to_memory(user_id, {"role": "assistant", "content": final_response_text})
        
        async def final_streamer():
            yield final_response_text.encode('utf-8')
            
        return StreamingResponse(final_streamer(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        logging.getLogger("RyuukoAPI.API").exception(f"Error during provider call: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred while contacting the AI provider: {e}")

# --- USER CONFIG ENDPOINTS ---
class UserConfigUpdate(BaseModel):
    model: Optional[str] = None
    system_prompt: Optional[str] = None

@app.put("/api/users/config", status_code=200)
async def update_user_config(config_update: UserConfigUpdate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    success = db_store.update_user_config(user_id, model=config_update.model, system_prompt=config_update.system_prompt)
    if success:
        return {"message": "Configuration updated successfully."}
    return {"message": "Configuration was not modified."}
