# Remove the root health check endpoint
# (No code for @router.get("/") should remain) 

from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "message": "Backend API is running!",
        "version": "1.0.0"
    } 