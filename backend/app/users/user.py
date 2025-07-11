from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.services.coin_stats import CoinStatsService
from app.users.models import WalletOperation

# Initialize services
capital_manager = CapitalManager(initial_capital=1000.0)
stats_service = CoinStatsService()
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
    coin = operation.coin.lower()  # Standardize to lowercase for internal use
    amount = operation.amount

    # Validate amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Perform deposit
    try:
        capital_manager.deposit(user_id, coin, amount)
        new_balance = capital_manager.get_user_investment(user_id, coin)
        return BalanceResponse(coin=coin.upper(), balance=new_balance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deposit failed: {str(e)}")


@auth_router.post("/balance/withdraw", response_model=BalanceResponse)
async def withdraw_balance(
    operation: BalanceOperation, current_user: Dict = Depends(get_current_user)
):
    """Withdraw an amount of a specific coin from the user's balance."""
    user_id = current_user["id"]
    coin = operation.coin.lower()
    amount = operation.amount

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        capital_manager.withdraw(user_id, coin, amount)
        new_balance = capital_manager.get_user_investment(user_id, coin)
        return BalanceResponse(coin=coin.upper(), balance=new_balance)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Withdrawal failed: {str(e)}")


@auth_router.get("/investment/{coin}")
async def get_investment_details(
    coin: str, current_user: dict = Depends(get_current_user)
):
    """Display comprehensive user investment details and coin performance for a given coin."""
    user_id = current_user["id"]
    coin = coin.lower()  # Ensure consistency with CapitalManager

    # Fetch current coin stats
    stats = stats_service.get_latest_stats(coin)
    if stats is None or "price" not in stats:
        raise HTTPException(
            status_code=404, detail="Coin not found or no price data available"
        )

    current_price = stats["price"]

    # Get enhanced user investment details
    details = capital_manager.get_user_investment_details(user_id, coin, current_price)

    # FIXED: Use the correct key "net_investment" instead of "investment"
    if details["net_investment"] == 0.0:
        return {"message": "No investment found for this coin"}

    # Get overall coin performance summary
    coin_summary = capital_manager.get_coin_performance_summary(coin, current_price)

    # Enhanced coin performance metrics
    coin_performance = {
        # Market data
        "current_price": stats.get("price", "N/A"),
        "price_change_24h": stats.get("price_change_24h_percent", "N/A"),
        "volume_24h": stats.get("volume_24h", "N/A"),
        "market_cap": stats.get("market_cap", "N/A"),
        # Global portfolio performance
        "total_deposits": coin_summary["total_deposits"],
        "total_withdrawals": coin_summary["total_withdrawals"],
        "net_deposits": coin_summary["net_deposits"],
        "current_capital": coin_summary["current_capital"],
        "position_quantity": coin_summary["position_quantity"],
        "position_value": coin_summary["position_value"],
        "total_portfolio_value": coin_summary["total_portfolio_value"],
        "total_realized_profits": coin_summary["realized_profits"],
        "total_unrealized_gains": coin_summary["unrealized_gains"],
        "total_gains": coin_summary["total_gains"],
        "overall_performance": coin_summary["performance_percentage"],
    }

    # FIXED: Structure the response using the correct keys from get_user_investment_details
    user_investment = {
        # Core Investment Information
        "total_deposits": details["total_deposits"],
        "total_withdrawals": details["total_withdrawals"],
        "net_investment": details["net_investment"],
        # Current Position & Performance
        "ownership_percentage": details["ownership_percentage"],
        "current_share_value": details["current_share_value"],
        # Gains/Loss Breakdown
        "realized_gains_share": details["realized_gains_share"],
        "unrealized_gains_share": details["unrealized_gains_share"],
        "total_gains": details["total_gains"],
        "overall_profit_loss": details["profit_loss"],
        "performance_percentage": details["performance_percentage"],
        # Portfolio Breakdown
        "portfolio_breakdown": {
            "cash_portion": details["portfolio_breakdown"]["cash_portion"],
            "position_portion": details["portfolio_breakdown"]["position_portion"],
            "total_value": details["portfolio_breakdown"]["total_portfolio_value"],
        },
        # Additional fields
        "fees_paid_share": details["fees_paid_share"],
        "fee_impact_percentage": details["fee_impact_percentage"],
        "has_active_investment": details["has_active_investment"],
    }

    # Return comprehensive investment data
    return {
        "user_investment": user_investment,
        "coin_performance": coin_performance,
        "coin": coin.upper(),
        "timestamp": datetime.now().isoformat(),
    }


@auth_router.post("/wallet/add")
async def add_wallet_address(
    operation: WalletOperation, current_user: dict = Depends(get_current_user)
):
    """
    Add or update a wallet address for a specific coin for the authenticated user.
    """
    user_id = current_user["id"]
    coin = operation.coin.upper()
    wallet_address = operation.wallet_address

    success = user_service.add_wallet(user_id, coin, wallet_address)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to add or update wallet address"
        )

    return {"message": f"Wallet address for {coin} added/updated successfully."}


@auth_router.get("/wallets/{coin}")
async def get_wallet_addresses(
    coin: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all wallet addresses for the authenticated user.
    """
    user_id = current_user["id"]
    wallet = user_service.get_wallet(user_id, coin)

    if not wallet:
        raise HTTPException(status_code=404, detail="No wallet found for this user")

    return {"wallet": wallet}


from fastapi import Query, Depends
from datetime import datetime, timedelta
from typing import List, Dict, Any


@auth_router.get("/profit_trend/{coin}")
async def get_global_profit_trend(
    coin: str,
    days: int = Query(..., gt=0),  # Require days > 0
    current_user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Retrieve global profit trend for a coin for the last N days.
    If no data is found, returns a list with one default record containing zero values.

    Args:
        coin: The coin symbol (e.g., 'btc', 'eth') or full name (e.g., 'bitcoin', 'ethereum')
        days: Number of days to look back (e.g., 30 for 1 month, 90 for 3 months)
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query the trend data
    trend_data = user_service.get_profit_trend(coin.lower(), start_date, end_date)

    # Check if no data was found
    if not trend_data:
        # Define a default record with zero values
        default_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "price": 0,
            "global": {
                "realized_profits": 0,
                "unrealized_gains": 0,
                "total_gains": 0,
                "performance_percentage": 0,
                "total_portfolio_value": 0,
                "current_capital": 0,
                "position_value": 0,
                "total_net_investments": 0,
            },
        }
        return [default_record]  # Return list with one default record

    # Return actual data if available
    return trend_data
