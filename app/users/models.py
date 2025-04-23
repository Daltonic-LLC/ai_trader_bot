from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Pydantic models for request/response
class GoogleTokenRequest(BaseModel):
    token: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")  # Convert MongoDB `_id` to id
    name: str
    email: str
    profile_picture: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None
    token: Optional[Token] = None  # Ensure token is included

    class Config:
        populate_by_name = True
        from_attributes = True


class UserRole(Enum):
    USER = "user"
    ADMIN = "admin"


class SocialProvider(Enum):
    GOOGLE = "google"
