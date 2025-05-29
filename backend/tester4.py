from app.services.mongodb_service import MongoUserService

mongo_service = MongoUserService()
success = mongo_service.clear_database(confirm=True)
if success:
    print("Database cleared successfully.")
else:
    print("Failed to clear database.")