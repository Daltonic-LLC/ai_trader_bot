from fastapi import FastAPI
from app.users.user import auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to your frontend URL
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],  # Explicitly allow OPTIONS
    allow_headers=["Authorization", "Content-Type"],  # Allow Authorization header
)


# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
