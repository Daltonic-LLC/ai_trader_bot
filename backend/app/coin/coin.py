from fastapi import APIRouter, Query
from app.services.coin_extractor import TopCoinsExtractor
from app.services.capital_manager import CapitalManager
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
                "data": []
            }
        
        # Apply the limit to the top_coins list
        limited_coins = top_coins[:limit] if top_coins else []
        
        # Return the limited top coins data in the response
        return {
            "status": "Success",
            "message": f"Retrieved {len(limited_coins)} top coins successfully.",
            "data": limited_coins
        }
    except Exception as e:
        logging.error(f"Error retrieving top coins: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve top coins: {str(e)}",
            "data": []
        }
        
@coin_router.get("/available")
async def list_available_coins():
    try:
        capital_manager = CapitalManager(coin="shared", initial_capital=0.0)
        available_coins = capital_manager.get_available_coins()
        
        if not available_coins:
            logging.warning("No available coins found in CapitalManager.")
            return {
                "status": "Error",
                "message": "No available coins found in CapitalManager.",
                "data": []
            }
        return {
            "status": "Success",
            "message": f"Retrieved {len(available_coins)} available coins from CapitalManager.",
            "data": available_coins
        }
    except Exception as e:
        logging.error(f"Error retrieving available coins from CapitalManager: {str(e)}")
        return {
            "status": "Error",
            "message": f"Failed to retrieve available coins from CapitalManager: {str(e)}",
            "data": []
        }