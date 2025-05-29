from app.services.mongodb_service import MongoUserService  # Adjust import path
from app.services.capital_manager import CapitalManager       # Adjust import path

# Initialize MongoUserService
mongo_service = MongoUserService()

# Initialize CapitalManager for the scheduler
capital_manager = CapitalManager(
    initial_capital=1000.0,
    mongo_service=mongo_service
)

# Perform operations
# capital_manager.deposit("bitcoin", 500.0)
# capital_manager.simulate_buy("bitcoin", 0.01, 30000.0)
print(f"Bitcoin position: {capital_manager.get_position('bitcoin')}")
print(f"Bitcoin capital: {capital_manager.get_capital('bitcoin')}")