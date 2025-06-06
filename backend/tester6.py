from app.services.capital_manager import CapitalManager
from app.users.user import capital_manager

# Debug script to test the API response data
def debug_api_response(capital_manager, coin="bitcoin", current_price=50000):
    """Debug what the API endpoint actually returns"""
    
    print("=== API RESPONSE DEBUG ===")
    
    # Test get_coin_performance_summary
    print("1. Testing get_coin_performance_summary():")
    coin_summary = capital_manager.get_coin_performance_summary(coin, current_price)
    print("Coin Summary:")
    for key, value in coin_summary.items():
        if isinstance(value, float):
            print(f"  {key}: ${value:.2f}")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Test individual user details (simulate both users)
    user_ids = ["6842c7f4f895fa1e5267a548", "6842c810f895fa1e5267a549"]
    
    print("2. Testing get_user_investment_details() for each user:")
    for i, user_id in enumerate(user_ids, 1):
        print(f"\nUser {i} ({user_id}):")
        details = capital_manager.get_user_investment_details(user_id, coin, current_price)
        
        key_metrics = [
            "original_investment", "total_deposits", "net_investment", 
            "ownership_percentage", "current_share", "total_gains"
        ]
        
        for key in key_metrics:
            if key in details:
                if key == "ownership_percentage":
                    print(f"  {key}: {details[key]:.2f}%")
                else:
                    print(f"  {key}: ${details[key]:.2f}")
    
    print("\n3. Raw CapitalManager state:")
    print(f"  total_deposits[{coin}]: ${capital_manager.total_deposits.get(coin, 0):.2f}")
    print(f"  capital[{coin}]: ${capital_manager.capital.get(coin, 0):.2f}")
    print(f"  user_investments[{coin}]: {capital_manager.user_investments.get(coin, {})}")
    
    print("\n4. Simulating full API response structure:")
    
    # Simulate the coin_performance part of API response
    coin_performance = {
        "current_price": current_price,
        "total_portfolio_value": coin_summary["total_portfolio_value"],
        "total_realized_profits": coin_summary["realized_profits"],
        "total_unrealized_gains": coin_summary["unrealized_gains"],
        "overall_performance": coin_summary["performance_percentage"],
    }
    
    print("coin_performance section:")
    for key, value in coin_performance.items():
        if key == "current_price":
            print(f"  {key}: ${value:.2f}")
        elif isinstance(value, float):
            print(f"  {key}: ${value:.2f}")
        else:
            print(f"  {key}: {value}")

# Usage:
# debug_api_response(capital_manager, "bitcoin", 50000)

# Usage example:
capital_manager = CapitalManager()
debug_api_response(capital_manager, "bitcoin", 50000)