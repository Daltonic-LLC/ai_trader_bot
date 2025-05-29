from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from typing import Optional, Dict
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime, timedelta
from jose import jwt, JWTError
from config import config
from typing import List

from app.services.capital_manager import CapitalManager
from app.services.mongodb_service import MongoUserService, UserRole, SocialProvider
from app.users.models import (
    GoogleTokenRequest,
    Token,
    UserResponse,
    BalanceOperation,
    BalanceResponse,
)

# Initialize services
user_service = MongoUserService()
auth_router = APIRouter()

# OAuth2 configuration
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, config.jwt_secret_key, algorithm=config.jwt_algorithm
    )

    return Token(
        access_token=encoded_jwt,
        token_type="bearer",
        expires_in=int((expire - datetime.utcnow()).total_seconds()),
    )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decode the JWT token to get user information"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, config.jwt_secret_key, algorithms=[config.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        user = user_service.get_user_by_id(user_id)
        if not user:
            raise credentials_exception

        user["id"] = str(user.pop("_id", ""))
        return user
    except JWTError:
        raise credentials_exception


async def verify_google_token(token: str) -> Dict:
    """Verify Google OAuth token and return user information"""
    try:

        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), config.google_client_id
        )

        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            print("Invalid issuer:", idinfo["iss"])  # Debug Log
            raise ValueError("Invalid issuer")

        return {
            "social_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo["name"],
            "profile_picture": idinfo.get("picture"),
        }
    except Exception as e:
        print("Google Token Verification Failed:", str(e))  # Debug Log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
        )


@auth_router.post("/login", response_model=UserResponse)
async def google_login(token_request: GoogleTokenRequest):
    try:
        # Verify Google token and get user info
        user_info = await verify_google_token(token_request.token)
        print("Google token verified.")

        # Check if user exists
        user = user_service.get_user_by_social_id(
            user_info["social_id"], SocialProvider.GOOGLE
        )

        if not user:
            # Create new user
            print("User not found, creating a new user...")
            user = user_service.create_user(
                email=user_info["email"],
                social_id=user_info["social_id"],
                provider=SocialProvider.GOOGLE,
                name=user_info["name"],
                profile_picture=user_info.get("profile_picture"),
            )
        else:
            # Update last login
            print("Updating last login for existing user...")
            user = user_service.social_login(
                user_info["social_id"], SocialProvider.GOOGLE
            )

        print("Final user data before token creation:", user)

        # Convert `_id` to `id`
        user["id"] = str(user.pop("_id", ""))

        # Create access token
        token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=timedelta(minutes=config.access_token_expire_minutes),
        )

        print("Generated access token:", token.access_token)

        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            profile_picture=user.get("profile_picture"),
            role=user["role"],
            created_at=user.get("created_at"),
            token=token,
        )

    except HTTPException as http_err:
        print("HTTPException occurred:", http_err.detail)
        raise
    except Exception as e:
        print("Unexpected Exception:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@auth_router.get("/token/verify")
async def verify_token(current_user: Dict = Depends(get_current_user)):
    """Verify if the current token is valid"""
    return {"valid": True, "user_id": str(current_user["_id"])}


@auth_router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's details, including role"""

    # Convert ObjectId to string for JSON serialization
    # current_user["id"] = str(current_user.pop("_id", ""))  # Rename `_id` to `id`

    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        profile_picture=current_user.get("profile_picture"),
        role=current_user["role"],  # Ensuring role is included
        created_at=current_user.get("created_at"),
        balances=current_user.get("balances", {}),  # Include balances if available
    )


@auth_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str, role: UserRole, current_user: Dict = Depends(get_current_user)
):
    """Allow only the super admin to assign or remove admin roles"""
    # Define your super admin email (or ID)
    SUPER_ADMIN_EMAIL = config.admin_email

    # Ensure only the super admin can modify roles
    if current_user["email"] != SUPER_ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the super admin can modify roles",
        )

    # Prevent changing the super admin's own role
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if target_user["email"] == SUPER_ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin role cannot be changed",
        )

    # Update role
    success = user_service.update_user_role(user_id, role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role update failed",
        )

    return {"message": "Role updated successfully"}


@auth_router.get("/users", response_model=List[UserResponse])
async def list_all_users(current_user: Dict = Depends(get_current_user)):
    """Retrieve a list of all users (Super Admin only)"""

    # Ensure only the super admin can access this route
    if current_user["email"] != config.admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the super admin can list all users",
        )

    # Fetch all users
    users = user_service.get_all_users()

    # Convert ObjectId to string and include role
    user_list = []
    for user in users:
        user["id"] = str(user.pop("_id", ""))
        role = (
            "super" if user["email"] == config.admin_email else user.get("role", "User")
        )

        user_list.append(
            UserResponse(
                id=user["id"],
                email=user["email"],
                name=user["name"],
                profile_picture=user.get("profile_picture"),
                role=role,
                created_at=user.get("created_at"),
            )
        )

    return user_list


@auth_router.post("/balance/deposit", response_model=BalanceResponse)
async def deposit_balance(
    operation: BalanceOperation, current_user: Dict = Depends(get_current_user)
):
    """Deposit an amount of a specific coin into the user's balance and update global trading capital."""
    user_id = current_user["id"]
    coin = (
        operation.coin.upper()
    )  # Standardize coin symbols to uppercase for user balance
    amount = operation.amount

    # Validate amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Perform deposit
    try:
        # Step 1: Deposit to user's balance
        success = user_service.deposit_balance(user_id, coin, amount)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        # Step 2: Deposit to global trading capital
        capital_manager = CapitalManager()
        capital_manager.deposit(coin.lower(), amount)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deposit failed: {str(e)}")

    # Fetch updated balance
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_balance = user.get("balances", {}).get(coin, 0.0)

    return BalanceResponse(coin=coin, balance=new_balance)


@auth_router.post("/balance/withdraw", response_model=BalanceResponse)
async def withdraw_balance(
    operation: BalanceOperation, current_user: Dict = Depends(get_current_user)
):
    """Withdraw an amount of a specific coin from the user's balance."""
    user_id = current_user["id"]
    coin = operation.coin.upper()
    amount = operation.amount

    # Validate amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Perform withdrawal
    try:
        success = user_service.withdraw_balance(user_id, coin, amount)
        if not success:
            raise HTTPException(
                status_code=400, detail="Insufficient balance or user not found"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")

    # Fetch updated balance
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_balance = user.get("balances", {}).get(coin, 0.0)

    return BalanceResponse(coin=coin, balance=new_balance)
