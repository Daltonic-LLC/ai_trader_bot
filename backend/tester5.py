from app.services.capital_manager import CapitalManager

def load_test_funds(user_id, coins_amounts, reset=False):
    """
    Load test funds for a user across specified coins into the CapitalManager.

    :param user_id: The ID of the user depositing the funds.
    :param coins_amounts: A dictionary with coin names as keys and amounts as values.
    :param reset: If True, reset the CapitalManager state before loading funds.
    """
    # Get the singleton instance of CapitalManager
    cm = CapitalManager()

    # Optionally reset the state for a clean slate
    if reset:
        cm.reset_state()
        print("CapitalManager state reset.")

    # Deposit the specified amount for each coin
    for coin, amount in coins_amounts.items():
        cm.deposit(user_id, coin, amount)
        print(f"Deposited {amount} to {coin} for user {user_id}.")

    # Summary of loaded funds
    print(f"Loaded test funds for user {user_id}: {coins_amounts}")

# Example usage
if __name__ == "__main__":
    user_id = "test_user"
    coins_amounts = {
        "bitcoin": 1000.0,
        "ethereum": 500.0,
        "solana": 200.0,
        "bnb": 300.0,
        "xrp": 450.0,
        "sui": 650.0,
    }
    load_test_funds(user_id, coins_amounts, reset=True)