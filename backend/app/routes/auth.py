import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils import cookies
from app.utils.playwright_auth import logiqs_login_async
from app.utils.common import log_endpoint_call, log_success, log_error
from app.models.response_models import SuccessResponse, ErrorResponse

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", tags=["Auth"])
async def login(request: LoginRequest):
    """
    Authenticate user with Logiqs system.
    
    Args:
        request: LoginRequest containing username and password
        
    Returns:
        SuccessResponse: Authentication result with cookie information
    """
    log_endpoint_call("login", username=request.username)
    
    try:
        logger.info("🚀 Starting authentication process...")
        result = await logiqs_login_async(request.username, request.password)
        
        cookie_count = result.get('cookieCount', 'unknown')
        log_success("login", username=request.username, cookie_count=cookie_count)
        
        return SuccessResponse(
            message="Authentication successful",
            status="success",
            data=result
        )
        
    except Exception as e:
        log_error("login", e, username=request.username)
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.get("/status", tags=["Auth"], response_model=SuccessResponse)
def status():
    """
    Check authentication status.
    
    Returns:
        SuccessResponse: Current authentication status
    """
    log_endpoint_call("auth_status")
    
    has_cookies = cookies.cookies_exist()
    
    if has_cookies:
        log_success("auth_status", authenticated=True)
        return SuccessResponse(
            message="User is authenticated",
            status="success",
            data={"authenticated": True}
        )
    else:
        log_success("auth_status", authenticated=False)
        return SuccessResponse(
            message="User is not authenticated",
            status="success",
            data={"authenticated": False}
        )

@router.post("/logout", tags=["Auth"])
def logout():
    """
    Logout user by clearing authentication cookies.
    
    Returns:
        SuccessResponse: Logout confirmation
    """
    log_endpoint_call("logout")
    
    cookies.delete_cookies()
    
    log_success("logout")
    return SuccessResponse(
        message="Logged out successfully",
        status="success"
    ) 