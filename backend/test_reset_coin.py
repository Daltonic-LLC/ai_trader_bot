from app.services.mongodb_service import MongoUserService
import logging
import os

# Configure logging to both console and file
log_dir = "./data"
log_file = os.path.join(log_dir, "reset.log")

# Ensure the ./data directory exists
os.makedirs(log_dir, exist_ok=True)

# Set up logging with both console and file handlers
logger = logging.getLogger("CoinReset")
logger.setLevel(logging.INFO)

# File handler for reset.log
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

def main():
    """Execute the coin reset operation for a specific coin and log to ./data/reset.log."""
    # Prompt for coin name
    coin = input("Enter the coin to reset (e.g., bitcoin): ").strip().lower()
    if not coin:
        logger.warning("No coin specified. Operation cancelled.")
        print("❌ No coin specified. Operation cancelled.")
        return

    # Confirmation
    confirm = input(f"Type 'RESET' to reset all records for {coin}: ").strip()
    if confirm.lower() != "reset":
        logger.warning(f"Operation cancelled for coin {coin}: Confirmation not provided.")
        print("❌ Operation cancelled")
        return

    try:
        # Initialize MongoUserService
        logger.info(f"Initializing MongoUserService for coin reset: {coin}")
        mongo_service = MongoUserService()
        
        # Execute coin reset
        logger.info(f"Attempting to reset all records for coin: {coin}")
        if mongo_service.reset_coin_records(coin):
            logger.info(f"Successfully reset all records for coin: {coin}")
            print(f"✅ Successfully reset all records for {coin}")
        else:
            logger.error(f"Failed to reset records for coin: {coin}. Check MongoDB logs for details.")
            print(f"❌ Failed to reset records for {coin}. Check logs for details.")
        
        logger.info(f"Coin reset operation completed for {coin}")
        print("✅ Operation completed")
    except Exception as e:
        logger.error(f"Error during coin reset for {coin}: {str(e)}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()