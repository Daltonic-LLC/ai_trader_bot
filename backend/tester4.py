from app.services.mongodb_service import MongoUserService
from app.services.capital_manager import CapitalManager

mongo_service = MongoUserService()
capital_service = CapitalManager()
success = mongo_service.clear_database(confirm=True)
capital_service.reset_state()

if success:
    debug_info = capital_service.debug_all_coins()
    print(debug_info)
    print("Database cleared successfully.")
else:
    print("Failed to clear database.")
