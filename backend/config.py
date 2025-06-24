from os import environ
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class EnvironmentConfig:
    """Configuration manager for environment-specific settings"""

    def __init__(self):
        # Initialize configurations
        self._initialize_config()

    def _initialize_config(self):
        """Initialize configuration based on environment"""
        self.config = {
            "binance_api_key": environ.get("BINANCE_API_KEY", ""),
            "binance_api_secret": environ.get("BINANCE_SECRET_KEY", ""),
            "chat_model": environ.get("CHAT_MODEL", "llama3.1:8b"),
            "chat_endpoint": environ.get(
                "CHAT_ENDPOINT", "http://ollama_service:11434"
            ),
            "environment": environ.get("ENVIRONMENT", "local").lower(),
            "mongodb_uri": environ.get("MONGODB_URI", ""),
            "mongodb_username": environ.get("MONGODB_USERNAME", ""),
            "mongodb_password": environ.get("MONGODB_PASSWORD", ""),
            "google_client_id": environ.get("GOOGLE_CLIENT_ID", ""),
            "jwt_secret_key": environ.get("SECRET_KEY", ""),
            "n8n_webhook_secret": environ.get("N8N_WEBHOOK_SECRET", ""),
            "n8n_webhook_url": environ.get("N8N_WEBHOOK_URL", ""),
            "coin_limit": environ.get("COIN_LIMIT", None),
            "port": environ.get("PORT", 8000),
        }

    @property
    def binance_api_key(self) -> str:
        return self.config["binance_api_key"]

    @property
    def binance_api_secret(self) -> str:
        return self.config["binance_api_secret"]

    @property
    def chat_endpoint(self) -> str:
        return self.config["chat_endpoint"]

    @property
    def chat_model(self) -> str:
        return self.config["chat_model"]

    @property
    def mongodb_uri(self) -> str:
        url = self.config["mongodb_uri"]
        if not url:
            raise ValueError("MONGODB_URI environment variable is not set")
        return url

    @property
    def mongodb_username(self) -> str:
        username = self.config["mongodb_username"]
        if not username:
            raise ValueError("MONGODB_USERNAME environment variable is not set")
        return username

    @property
    def mongodb_password(self) -> str:
        password = self.config["mongodb_password"]
        if not password:
            raise ValueError("MONGODB_PASSWORD environment variable is not set")
        return password

    @property
    def google_client_id(self) -> str:
        return self.config["google_client_id"]

    @property
    def jwt_secret_key(self) -> str:
        return self.config["jwt_secret_key"]

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @property
    def access_token_expire_minutes(self) -> int:
        return 720

    def get_all(self) -> Dict[str, str]:
        """Return all configuration values"""
        return self.config

    @property
    def n8n_webhook_secret(self) -> str:
        return self.config["n8n_webhook_secret"]

    @property
    def n8n_webhook_url(self) -> str:
        return self.config["n8n_webhook_url"]

    @property
    def coin_limit(self) -> int:
        return int(self.config["coin_limit"] or 15)

    @property
    def get_port(self) -> int:
        """Get the port for the FastAPI server"""
        return int(self.config["port"])

    def __str__(self) -> str:
        """String representation of current configuration"""
        return (
            f"Environment: {self.environment}\n"
            f"Chat Model: {self.chat_model}\n"
            f"Chat Endpoint: {self.chat_endpoint}\n"
            f"Vision Model: {self.vision_model}"
            f"Vision Endpoint: {self.vision_endpoint}\n"
        )


# Create a singleton instance
config = EnvironmentConfig()

# Export the instance and the class
__all__ = ["config", "EnvironmentConfig"]
