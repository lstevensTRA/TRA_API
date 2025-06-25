import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils import cookies
from app.utils.playwright_auth import logiqs_login_async

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", tags=["Auth"])
async def login(request: LoginRequest):
    logger.info("🔐 Received login request")
    logger.info(f"👤 Username: {request.username}")
    logger.info(f"🔑 Password: {'*' * len(request.password)} (length: {len(request.password)})")
    
    try:
        logger.info("🚀 Starting authentication process...")
        result = await logiqs_login_async(request.username, request.password)
        
        logger.info("✅ Authentication successful")
        logger.info(f"🍪 Cookie count: {result.get('cookieCount', 'unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Authentication failed: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.get("/auth/status", tags=["Auth"])
def status():
    has_cookies = cookies.cookies_exist()
    return {"authenticated": has_cookies}

@router.post("/auth/logout", tags=["Auth"])
def logout():
    cookies.delete_cookies()
    return {"success": True, "message": "Logged out."} 