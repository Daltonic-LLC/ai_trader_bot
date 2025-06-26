from app.services.capital_manager import CapitalManager  # Adjust import path

# Initialize CapitalManager for the scheduler
capital_manager = CapitalManager(initial_capital=1000.0)

# Perform operations
capital_manager.deposit("67ustubutywq", "bitcoin", 25000.0)
# # capital_manager.simulate_buy("bitcoin", 0.01, 30000.0)
# print(f"Bitcoin position: {capital_manager.get_position('btc')}")
print(f"Bitcoin capital: {capital_manager.get_capital('btc')}")
