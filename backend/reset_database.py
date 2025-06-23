#!/usr/bin/env python3
"""
Database Reset Script
=====================
This script performs a complete database reset by:
1. Clearing all MongoDB collections (users, trading_state, investment_records)
2. Resetting the CapitalManager singleton state
3. Providing detailed logging and confirmation

WARNING: This is a destructive operation that will permanently delete all data!
"""

import logging
import sys
from datetime import datetime
from app.services.mongodb_service import MongoUserService
from app.services.capital_manager import CapitalManager

# Configure detailed logging
log_filename = f"data/database_reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename),
    ],
)


def confirm_reset():
    """Interactive confirmation for database reset. Returns True if user confirms."""
    print("\n" + "=" * 60)
    print("⚠️  DATABASE RESET WARNING ⚠️")
    print("=" * 60)
    print("This operation will PERMANENTLY DELETE ALL DATA including:")
    print("• All user accounts and profiles")
    print("• All trading history and records")
    print("• All investment data and balances")
    print("• All wallet addresses")
    print("• All capital manager state")
    print("=" * 60)
    confirmation = input("\nType 'RESET' to confirm deletion: ").strip()
    return confirmation.lower() == "reset"


def backup_reminder():
    """Remind user about backup before proceeding. Returns True if confirmed."""
    print("\n📋 BACKUP REMINDER:")
    print("Have you backed up your database if needed?")
    backup_confirm = (
        input("Type 'YES' if you have a backup or don't need one: ").strip().upper()
    )
    return backup_confirm == "YES"


def reset_database():
    """Perform the complete database reset operation. Returns True if successful."""
    try:
        logging.info("Starting database reset operation...")
        mongo_service = MongoUserService()
        logging.info("Clearing MongoDB collections...")
        success = mongo_service.clear_database(confirm=True)
        if not success:
            logging.error("Failed to clear MongoDB collections")
            return False
        logging.info("Successfully cleared MongoDB collections")

        # Reset CapitalManager state
        capital_service = CapitalManager()
        capital_service.reset_state()
        logging.info("CapitalManager state reset and saved to database")

        # Verify state
        logging.info("Verifying reset completion...")
        remaining_users = mongo_service.get_all_users()
        if len(remaining_users) == 0:
            logging.info("✅ MongoDB users collection is empty")
        else:
            logging.warning(f"⚠️ {len(remaining_users)} users still remain in database")

        post_reset_capital = capital_service.get_total_capital()
        post_reset_capitals = capital_service.get_all_capitals()
        if post_reset_capital == 0 and len(post_reset_capitals) == 0:
            logging.info("✅ Capital Manager capital is reset")
        else:
            logging.warning(
                f"⚠️ Capital Manager capital may not be fully reset. Total: ${post_reset_capital:.2f}, Capitals: {post_reset_capitals}"
            )

        if not capital_service.total_deposits and not capital_service.user_investments:
            logging.info("✅ Total deposits and user investments are reset")
        else:
            logging.warning(
                "⚠️ Total deposits or user investments may not be fully reset"
            )

        return True
    except Exception as e:
        logging.error(f"Error during database reset: {str(e)}")
        return False


def main():
    """Main execution function."""
    print("🔄 Database Reset Utility")
    print("=" * 30)
    if not backup_reminder():
        print("❌ Operation cancelled - backup not confirmed")
        return
    if not confirm_reset():
        print("❌ Operation cancelled - reset not confirmed")
        return
    print("\n🚀 Starting database reset...")
    success = reset_database()
    if success:
        print("\n✅ DATABASE RESET COMPLETED SUCCESSFULLY")
        print("All data has been permanently deleted.")
        logging.info("Database reset operation completed successfully")
    else:
        print("\n❌ DATABASE RESET FAILED")
        print("Check the logs for details about what went wrong.")
        logging.error("Database reset operation failed")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        logging.info("Database reset cancelled by user interrupt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logging.error(f"Unexpected error during database reset: {str(e)}")
        sys.exit(1)
