# Remove the root health check endpoint
# (No code for @router.get("/") should remain) 

from fastapi import APIRouter
from ..models.response_models import SuccessResponse

router = APIRouter()

@router.get("/", tags=["Health"], response_model=SuccessResponse)
def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        SuccessResponse: API status and version information
    """
    return SuccessResponse(
        message="Backend API is running!",
        status="success",
        data={
            "version": "1.0.0",
            "status": "ok"
        }
    ) 