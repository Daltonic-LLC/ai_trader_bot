from fastapi import FastAPI
from app.welcome.starter import welcome_router
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
app.include_router(welcome_router, prefix="/welcome", tags=["Welcome"])