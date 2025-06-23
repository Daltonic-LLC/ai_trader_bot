#!/usr/bin/env python3
"""
Database Reset Script
=====================
This script performs a complete database reset by:
1. Clearing all MongoDB collections (users, trading_state, investment_records)
2. Properly resetting the CapitalManager singleton state
3. Providing detailed logging and confirmation

WARNING: This is a destructive operation that will permanently delete all data!
"""

import logging
import sys
from datetime import datetime
from app.services.mongodb_service import MongoUserService
from app.services.capital_manager import CapitalManager

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"data/database_reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)


def confirm_reset():
    """
    Interactive confirmation for database reset.
    Returns True if user confirms, False otherwise.
    """
    print("\n" + "=" * 60)
    print("⚠️  DATABASE RESET WARNING ⚠️")
    print("=" * 60)
    print("This operation will PERMANENTLY DELETE ALL DATA including:")
    print("• All user accounts and profiles")
    print("• All trading history and records")
    print("• All investment data and balances")
    print("• All wallet addresses")
    print("• All capital manager state")
    print("• All ownership percentages and user investments")
    print("=" * 60)

    confirmation = input("\nType 'RESET' to confirm deletion: ").strip()
    return confirmation == "RESET".lower() or confirmation == "RESET".upper()


def backup_reminder():
    """Remind user about backup before proceeding."""
    print("\n📋 BACKUP REMINDER:")
    print("Have you backed up your database if needed?")
    backup_confirm = (
        input("Type 'YES' if you have a backup or don't need one: ").strip().upper()
    )
    return backup_confirm == "YES".lower() or backup_confirm == "YES".upper()


def reset_database():
    """
    Perform the complete database reset operation.
    Returns True if successful, False otherwise.
    """
    try:
        logging.info("Starting database reset operation...")

        # Initialize services
        logging.info("Initializing MongoDB service...")
        mongo_service = MongoUserService()

        # Get initial state for logging BEFORE creating CapitalManager
        try:
            all_users = mongo_service.get_all_users()
            user_count = len(all_users)
            logging.info(f"Found {user_count} users in database")
        except Exception as e:
            logging.warning(f"Could not count users: {e}")
            user_count = "unknown"

        # Force reset the singleton first (in case it exists)
        logging.info("Resetting CapitalManager singleton...")
        CapitalManager.force_reset_singleton()

        # Now initialize Capital Manager (this will create a fresh instance)
        logging.info("Initializing Capital Manager...")
        capital_service = CapitalManager()

        try:
            total_capital = capital_service.get_total_capital()
            all_capitals = capital_service.get_all_capitals()
            logging.info(f"Total capital across all coins: ${total_capital:.2f}")
            logging.info(f"Capital breakdown: {all_capitals}")

            # Log user investments if they exist
            if (
                hasattr(capital_service, "user_investments")
                and capital_service.user_investments
            ):
                logging.info(f"User investments: {capital_service.user_investments}")
            if (
                hasattr(capital_service, "total_deposits")
                and capital_service.total_deposits
            ):
                logging.info(f"Total deposits: {capital_service.total_deposits}")
        except Exception as e:
            logging.warning(f"Could not get capital information: {e}")

        # Step 1: Reset Capital Manager state first
        logging.info("Resetting Capital Manager state...")
        capital_service.reset_state()
        capital_service.load_state()
        logging.info("Successfully reset Capital Manager state")

        # Step 2: Clear MongoDB collections
        logging.info("Clearing MongoDB collections...")
        success = mongo_service.clear_database(confirm=True)

        if not success:
            logging.error("Failed to clear MongoDB collections")
            return False

        logging.info("Successfully cleared MongoDB collections")

        # Step 3: Force another singleton reset to ensure clean state
        logging.info("Performing final singleton reset...")
        CapitalManager.force_reset_singleton()

        # Step 4: Create a fresh instance to verify reset
        logging.info("Creating fresh CapitalManager instance for verification...")
        fresh_capital_service = CapitalManager()

        # Verify reset
        logging.info("Verifying reset completion...")

        # Check MongoDB is cleared
        remaining_users = mongo_service.get_all_users()
        if len(remaining_users) == 0:
            logging.info("✅ MongoDB users collection is empty")
        else:
            logging.warning(f"⚠️ {len(remaining_users)} users still remain in database")

        # Check Capital Manager is reset
        post_reset_capital = fresh_capital_service.get_total_capital()
        post_reset_capitals = fresh_capital_service.get_all_capitals()

        # Check all the important data structures
        verification_results = {
            "capital": len(fresh_capital_service.capital),
            "positions": len(fresh_capital_service.positions),
            "user_investments": len(fresh_capital_service.user_investments),
            "user_withdrawals": len(fresh_capital_service.user_withdrawals),
            "total_deposits": len(fresh_capital_service.total_deposits),
            "total_withdrawals": len(fresh_capital_service.total_withdrawals),
            "realized_profits": len(fresh_capital_service.realized_profits),
            "trade_records": len(fresh_capital_service.trade_records),
        }

        all_structures_empty = all(
            count == 0 for count in verification_results.values()
        )

        if (
            post_reset_capital == 0
            and len(post_reset_capitals) == 0
            and all_structures_empty
        ):
            logging.info("✅ Capital Manager state is completely reset")
            logging.info("✅ All data structures are empty:")
            for structure, count in verification_results.items():
                logging.info(f"   - {structure}: {count} items")
        else:
            logging.warning("⚠️ Capital Manager may not be fully reset:")
            logging.warning(f"   - Total capital: ${post_reset_capital:.2f}")
            logging.warning(f"   - Capitals: {post_reset_capitals}")
            for structure, count in verification_results.items():
                if count > 0:
                    logging.warning(f"   - {structure}: {count} items (should be 0)")

        return True

    except Exception as e:
        logging.error(f"Error during database reset: {str(e)}")
        import traceback

        logging.error(f"Full traceback: {traceback.format_exc()}")
        return False


def main():
    """Main execution function."""
    print("🔄 Database Reset Utility")
    print("=" * 30)

    # Safety confirmations
    if not backup_reminder():
        print("❌ Operation cancelled - backup not confirmed")
        return

    if not confirm_reset():
        print("❌ Operation cancelled - reset not confirmed")
        return

    print("\n🚀 Starting database reset...")

    # Perform reset
    success = reset_database()

    if success:
        print("\n✅ DATABASE RESET COMPLETED SUCCESSFULLY")
        print("All data has been permanently deleted.")
        print("All user ownership percentages have been reset.")
        print("The next deposit will create 100% ownership for that user.")
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
