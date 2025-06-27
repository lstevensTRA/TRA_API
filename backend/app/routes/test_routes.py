from fastapi import APIRouter

router = APIRouter(tags=["Test"])

@router.get("/hello")
async def hello():
    return {"message": "Hello from test routes!"} 