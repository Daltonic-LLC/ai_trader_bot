from fastapi import APIRouter, Query
from app.services.coin_extractor import TopCoinsExtractor
from app.services.capital_manager import CapitalManager
from app.services.coin_scheduler import CoinScheduler
from app.trader_bot.coin_trader import CoinTrader
import logging

coin_router = APIRouter()


@coin_router.get("/top_coins")
async def list_top_coin(
    limit: int = Query(default=10, ge=1, description="Number of top coins to return")
):
    try:
        # Initialize the TopCoinsExtractor
        extractor = TopCoinsExtractor()

        # Load the most recent top coins data
        top_coins = extractor.load_most_recent_data()

        # Check if data is available
        if top_coins is None:
            logging.warning("No top coins data found for history extraction")
            print("No top coins data found. Run top coins extraction first.")
            return {
                "status": "Error",
                "message": "No top coins data found. Please run top coins extraction first.",
                "data": [],
            }

        # Apply the limit to the top_coins list
        limited_coins = top_coins[:limit] if top_coins else []

        # Return the limited top coins data in the response
        return {
            "status": "Success",
            "message": f"Retrieved {len(limited_coins)} top coins successfully.",
            "data": limited_coins,
        }
    except Exception as e:
        logging.error(f"Error retrieving top coins: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve top coins: {str(e)}",
            "data": [],
        }


@coin_router.get("/available")
async def list_available_coins():
    try:
        capital_manager = CapitalManager(initial_capital=0.0)
        available_coins = capital_manager.get_available_coins()

        if not available_coins:
            logging.warning("No available coins found in CapitalManager.")
            return {
                "status": "Error",
                "message": "No available coins found in CapitalManager.",
                "data": [],
            }
        return {
            "status": "Success",
            "message": f"Retrieved {len(available_coins)} available coins from CapitalManager.",
            "data": available_coins,
        }
    except Exception as e:
        logging.error(f"Error retrieving available coins from CapitalManager: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve available coins from CapitalManager: {str(e)}",
            "data": [],
        }


@coin_router.get("/report/{coin}")
async def get_coin_report(coin: str):
    try:
        capital_manager = CapitalManager()
        trader = CoinTrader(coin=coin, override=True, capital_manager=capital_manager)
        report_data = trader.get_report(coin)

        if report_data is None:
            logging.warning(f"No report found for coin {coin.upper()}")
            return {
                "status": "Error",
                "message": f"No report found for {coin.upper()}. Run the CoinTrader script for this coin.",
                "data": {},
            }
        return {
            "status": "Success",
            "message": f"Retrieved trade report for {coin.upper()}",
            "data": {
                "coin": coin.upper(),
                "timestamp": report_data["timestamp"],
                "report": report_data["report"],
            },
        }
    except Exception as e:
        logging.error(f"Error retrieving report for {coin.upper()}: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve report for {coin.upper()}: {str(e)}",
            "data": {},
        }


@coin_router.get("/execution_log")
async def get_execution_log():
    """Retrieve the last execution details using the CoinScheduler."""
    try:
        scheduler = CoinScheduler()
        execution_log = scheduler.load_execution_log()

        if not execution_log:
            logging.warning("Execution log is empty or not found.")
            return {
                "status": "Error",
                "message": "Execution log is empty or not found.",
                "data": {},
            }

        return {
            "status": "Success",
            "message": "Retrieved execution log successfully.",
            "data": execution_log,
        }
    except Exception as e:
        logging.error(f"Error retrieving execution log: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve execution log: {str(e)}",
            "data": {},
        }

@coin_router.get("/capitals")
def get_capitals():
    """Retrieve the current capital allocations for all coins."""
    capital_manager = CapitalManager()  # Singleton instance
    capital_manager.load_state()  # Ensure the latest state is loaded from the database
    capitals = capital_manager.get_all_capitals()
    return capitals