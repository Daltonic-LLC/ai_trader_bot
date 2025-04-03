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
            "redit_client_id": environ.get("REDDIT_CLIENT_ID", ""),
            "redit_client_secret": environ.get("REDDIT_CLIENT_SECRET", ""),
            "redit_user_agent": environ.get("REDDIT_USER_AGENT", ""),
            "chat_model": environ.get("CHAT_MODEL", "llama3.1:8b"),
            "chat_endpoint": environ.get(
                "CHAT_ENDPOINT", "http://ollama_service:11434"
            ),
            "environment": environ.get("ENVIRONMENT", "local").lower(),
        }

    @property
    def redit_client_id(self) -> str:
        return self.config["redit_client_id"]

    @property
    def redit_client_secret(self) -> str:
        return self.config["redit_client_secret"]

    @property
    def redit_user_agent(self) -> str:
        return self.config["redit_user_agent"]

    @property
    def chat_endpoint(self) -> str:
        return self.config["chat_endpoint"]

    @property
    def chat_model(self) -> str:
        return self.config["chat_model"]

    def get_all(self) -> Dict[str, str]:
        """Return all configuration values"""
        return self.config

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
