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
                    base_uri = base_uri[len("mongodb://"):]
                mongo_uri = f"mongodb://{escaped_username}:{escaped_password}@{base_uri}"
                if "?authSource=" not in mongo_uri:
                    mongo_uri += "?authSource=admin"
            else:
                # Use the base URI as-is (no credentials)
                mongo_uri = base_uri
                if "?authSource=" not in mongo_uri and "mongodb://" in mongo_uri:
                    mongo_uri += "?authSource=admin"

            # Log connection attempt (mask password)
            logging.info(f"Connecting to MongoDB at {mongo_uri.replace(password, '****') if password else mongo_uri}")

            # Connect to MongoDB
            self.client = MongoClient(mongo_uri)
            self.db = self.client.user_management
            self.users = self.db.users

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