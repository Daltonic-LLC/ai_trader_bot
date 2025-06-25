from fastapi import APIRouter

welcome_router = APIRouter()


@welcome_router.post("/")
async def welcome_message():
    return {
        "status": "Success",
        "message": "Welcome to the Starter API! This is a simple FastAPI application to get you started.",
    }