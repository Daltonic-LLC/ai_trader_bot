from typing import Optional, Dict, List
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import logging
from config import config
from urllib.parse import quote_plus
from app.users.models import SocialProvider, UserRole


class MongoUserService:
    def __init__(self):
        """Initialize MongoDB connection and set up collections."""
        try:
            # Get base URI and credentials from config
            base_uri = config.mongodb_uri
            username = config.mongodb_username
            password = config.mongodb_password

            # Construct the MongoDB URI
            if username and password:
                # Escape username and password to handle special characters
                escaped_username = quote_plus(username)
                escaped_password = quote_plus(password)
                # Ensure the URI includes credentials and authSource
                if base_uri.startswith("mongodb://"):
                    base_uri = base_uri[len("mongodb://") :]
                mongo_uri = (
                    f"mongodb://{escaped_username}:{escaped_password}@{base_uri}"
                )
                if "?authSource=" not in mongo_uri:
                    mongo_uri += "?authSource=admin"
            else:
                # Use the base URI as-is (no credentials)
                mongo_uri = base_uri
                if "?authSource=" not in mongo_uri and "mongodb://" in mongo_uri:
                    mongo_uri += "?authSource=admin"

            # Log connection attempt (mask password)
            logging.info(
                f"Connecting to MongoDB at {mongo_uri.replace(password, '****') if password else mongo_uri}"
            )

            # Connect to MongoDB
            self.client = MongoClient(mongo_uri)
            self.db = self.client.user_management
            self.users = self.db.users
            self.trading_state = self.db.trading_state

            # Create indexes
            self.users.create_index("email", unique=True)
            self.users.create_index([("social_id", 1), ("provider", 1)], unique=True)

            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def create_user(
        self,
        email: str,
        social_id: str,
        provider: SocialProvider,
        name: str,
        profile_picture: Optional[str] = None,
    ) -> Dict:
        """Create a new user with social login details."""
        try:
            user = {
                "email": email,
                "social_id": social_id,
                "provider": provider.value,
                "name": name,
                "discord": "",
                "telegram": "",
                "whatsapp": "",
                "profile_picture": profile_picture,
                "role": UserRole.USER.value,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
            }

            result = self.users.insert_one(user)
            user["_id"] = result.inserted_id
            return user
        except Exception as e:
            logging.error(f"Failed to create user: {str(e)}")
            raise

    def get_all_users(self) -> List[Dict]:
        """Retrieve all users."""
        try:
            return list(self.users.find())
        except Exception as e:
            logging.error(f"Failed to get all users: {str(e)}")
            return []

    def get_user_by_social_id(
        self, social_id: str, provider: SocialProvider
    ) -> Optional[Dict]:
        """Retrieve user by social ID and provider."""
        return self.users.find_one({"social_id": social_id, "provider": provider.value})

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Retrieve user by email."""
        return self.users.find_one({"email": email})

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Retrieve user by MongoDB ID."""
        try:
            return self.users.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            logging.error(f"Failed to get user by ID: {str(e)}")
            return None

    def update_user_role(self, user_id: str, role: UserRole) -> bool:
        """Update user's role (admin/user)."""
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"role": role.value, "updated_at": datetime.utcnow()}},
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Failed to update user role: {str(e)}")
            return False

    def social_login(self, social_id: str, provider: SocialProvider) -> Optional[Dict]:
        """Handle social login and update last login timestamp."""
        try:
            result = self.users.find_one_and_update(
                {"social_id": social_id, "provider": provider.value},
                {"$set": {"last_login": datetime.utcnow()}},
                return_document=True,
            )
            return result
        except Exception as e:
            logging.error(f"Failed to process social login: {str(e)}")
            return None

    def list_users(self, skip: int = 0, limit: int = 50) -> List[Dict]:
        """Retrieve a paginated list of users."""
        try:
            return list(self.users.find().skip(skip).limit(limit))
        except Exception as e:
            logging.error(f"Failed to list users: {str(e)}")
            return []

    def list_admins(self) -> List[Dict]:
        """Retrieve all admin users."""
        try:
            return list(self.users.find({"role": UserRole.ADMIN.value}))
        except Exception as e:
            logging.error(f"Failed to list admins: {str(e)}")
            return []

    def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID."""
        try:
            result = self.users.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Failed to delete user: {str(e)}")
            return False

    def __del__(self):
        """Clean up MongoDB connection."""
        try:
            self.client.close()
        except:
            pass

    # Add to MongoUserService class in app/users/mongodb_service.py

    def deposit_balance(self, user_id: str, coin: str, amount: float) -> bool:
        """Increase the user's balance for a specific coin."""
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {f"balances.{coin}": amount},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )
            # $inc creates the balances field and coin entry if they don't exist
            if result.modified_count == 0:
                logging.warning(
                    f"No user found or balance unchanged for user_id: {user_id}, coin: {coin}"
                )
            return result.modified_count > 0
        except Exception as e:
            logging.error(
                f"Failed to deposit balance for user_id: {user_id}, coin: {coin}: {str(e)}"
            )
            raise

    def withdraw_balance(self, user_id: str, coin: str, amount: float) -> bool:
        """Decrease the user's balance for a specific coin if sufficient funds exist."""
        try:
            result = self.users.update_one(
                {
                    "_id": ObjectId(user_id),
                    f"balances.{coin}": {"$gte": amount},  # Ensure sufficient balance
                },
                {
                    "$inc": {f"balances.{coin}": -amount},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )
            if result.matched_count == 0:
                logging.warning(
                    f"Insufficient balance or user not found for user_id: {user_id}, coin: {coin}"
                )
            return result.matched_count > 0 and result.modified_count > 0
        except Exception as e:
            logging.error(
                f"Failed to withdraw balance for user_id: {user_id}, coin: {coin}: {str(e)}"
            )
            raise

    def get_trading_state(self) -> Dict:
        """Retrieve the scheduler's trading state from the database."""
        state = self.trading_state.find_one({"_id": "scheduler_state"})
        if state:
            return {
                "user_investments": state.get("user_investments", {}),
                "total_deposits": state.get("total_deposits", {}),
                "capital": state.get("capital", {}),
                "positions": state.get("positions", {}),
                "total_cost": state.get("total_cost", {}),
                "trade_records": state.get("trade_records", {}),
            }
        # Return empty state if no document exists
        return {
            "user_investments": {},
            "total_deposits": {},
            "capital": {},
            "positions": {},
            "total_cost": {},
            "trade_records": {},
        }

    def set_trading_state(self, state: Dict) -> bool:
        """Save or update the scheduler's trading state in the database."""
        try:
            result = self.trading_state.update_one(
                {"_id": "scheduler_state"},  # Fixed ID for the scheduler's state
                {"$set": state},
                upsert=True,  # Create the document if it doesn’t exist
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logging.error(f"Failed to set trading state: {str(e)}")
            return False

    def add_wallet(self, user_id: str, coin: str, wallet_address: str) -> bool:
        """
        Add or update a wallet address for a specific coin for the user.

        Args:
            user_id (str): The user's MongoDB ID.
            coin (str): The coin symbol (e.g., 'BTC', 'ETH').
            wallet_address (str): The wallet address to associate.

        Returns:
            bool: True if the wallet was added/updated, False otherwise.
        """
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        f"wallets.{coin}": wallet_address,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(
                f"Failed to add wallet for user_id: {user_id}, coin: {coin}: {str(e)}"
            )
            return False

    def get_wallet(self, user_id: str, coin: str) -> Optional[str]:
        """
        Retrieve the wallet address for a specific coin for the user.

        Args:
            user_id (str): The user's MongoDB ID.
            coin (str): The coin symbol (e.g., 'BTC', 'ETH').

        Returns:
            Optional[str]: The wallet address if found, None otherwise.
        """
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)}, {"wallets": 1})
            if user and "wallets" in user and coin in user["wallets"]:
                return user["wallets"][coin]
            return None
        except Exception as e:
            logging.error(
                f"Failed to get wallet for user_id: {user_id}, coin: {coin}: {str(e)}"
            )
            return None

    def clear_database(self, confirm: bool = False) -> bool:
        """
        Clear all records from the database, including users, trading_state, and investment_records.
        This is a destructive operation and should be used with caution.

        Args:
            confirm (bool): Confirmation flag to proceed with deletion. Defaults to False.

        Returns:
            bool: True if deletion was successful, False otherwise.

        Note:
            Ensure the application is stopped or in a safe state before calling this method to avoid conflicts.
        """
        if not confirm:
            logging.warning("Clear database operation requires confirmation")
            return False

        try:
            # Delete all documents from the users collection
            result_users = self.users.delete_many({})
            logging.info(
                f"Deleted {result_users.deleted_count} documents from users collection"
            )

            # Delete all documents from the trading_state collection
            result_trading = self.trading_state.delete_many({})
            logging.info(
                f"Deleted {result_trading.deleted_count} documents from trading_state collection"
            )

            # Delete all documents from the investment_records collection
            result_investments = self.db.investment_records.delete_many({})
            logging.info(
                f"Deleted {result_investments.deleted_count} documents from investment_records collection"
            )

            return True
        except Exception as e:
            logging.error(f"Failed to clear database: {str(e)}")
            return False

    def insert_profit_snapshot(self, snapshot: Dict) -> bool:
        """Insert a profit snapshot into the database."""
        try:
            result = self.db.profit_snapshots.insert_one(snapshot)
            return result.inserted_id is not None
        except Exception as e:
            logging.error(f"Failed to insert profit snapshot: {str(e)}")
            return False

    def get_profit_trend(
        self,
        coin: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict]:
        """Retrieve profit trend data for a coin within a date range."""
        query = {
            "coin": coin.lower(),
            "timestamp": {"$gte": start_date, "$lte": end_date},
        }
        projection = {"_id": 0, "timestamp": 1, "price": 1, "global": 1}

        print(f"Querying profit trend with: {query} and projection: {projection}")

        try:
            snapshots = list(
                self.db.profit_snapshots.find(query, projection).sort("timestamp", 1)
            )
            return snapshots
        except Exception as e:
            logging.error(f"Failed to retrieve profit trend: {str(e)}")
            return []


    def reset_coin_records(self, coin: str) -> bool:
        """Reset all records related to a specific coin, including user balances, trading state, and profit snapshots."""
        try:
            coin = coin.lower()
            
            # Reset user balances for the coin
            result_users = self.users.update_many({}, {"$unset": {f"balances.{coin}": ""}})
            logging.info(f"Removed balance for coin {coin} from {result_users.modified_count} user records")
            
            # Reset trading state for the coin
            unset_fields = {
                f"user_investments.{coin}": "",
                f"total_deposits.{coin}": "",
                f"capital.{coin}": "",
                f"positions.{coin}": "",
                f"total_cost.{coin}": "",
                f"trade_records.{coin}": "",
                f"user_withdrawals.{coin}": "",
                f"total_withdrawals.{coin}": "",
                f"realized_profits.{coin}": "",
            }
            result_trading = self.trading_state.update_one(
                {"_id": "scheduler_state"}, {"$unset": unset_fields}
            )
            logging.info(f"Reset trading state for coin {coin}")
            
            # Reset profit snapshots for the coin
            result_snapshots = self.db.profit_snapshots.delete_many({"coin": coin})
            logging.info(f"Deleted {result_snapshots.deleted_count} profit snapshots for coin {coin}")
            
            return True
        except Exception as e:
            logging.error(f"Failed to reset coin records for {coin}: {str(e)}")
            return False