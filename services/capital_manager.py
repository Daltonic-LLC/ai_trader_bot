import json
import os
from datetime import datetime

class CapitalManager:
    def __init__(self, coin, initial_capital=1000.0, file_path="data/activities/trade_history.json"):
        """
        Initialize the CapitalManager with capital for a single coin, preserving existing state.

        :param coin: The coin symbol (e.g., 'bnb') to initialize with capital if not already set.
        :param initial_capital: The initial capital for the coin if not already in state (default: 1000.0).
        :param file_path: Path to the JSON file for saving state.
        """
        self.capital = {}  # Dictionary: {coin: current_capital}
        self.positions = {}  # Dictionary: {coin: quantity}
        self.trade_history = []  # List of trade records
        self.file_path = file_path
        self.coin = coin.lower()  # Store the specified coin
        self.initial_capital = initial_capital  # Store the initial capital
        self.ensure_directory_exists()
        self.load_state()

    def ensure_directory_exists(self):
        """Create the directory for the file_path if it doesn’t exist."""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

    def load_state(self):
        """Load capital, positions, and trade history from the file, initializing new coin if needed."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    loaded_capital = data.get('capital', {})
                    if isinstance(loaded_capital, float):
                        # Handle legacy format: assign float to the specified coin
                        print(f"Warning: Legacy capital format (float) found in {self.file_path}. Converting to new format.")
                        self.capital[self.coin] = loaded_capital
                    else:
                        # Use loaded capital dictionary
                        self.capital.update(loaded_capital)
                    self.positions = data.get('positions', {})
                    self.trade_history = data.get('trade_history', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading {self.file_path}: {e}. Initializing with specified coin.")
                self.capital[self.coin] = self.initial_capital
        else:
            print(f"No file found at {self.file_path}. Initializing with specified coin.")
            self.capital[self.coin] = self.initial_capital

        # Initialize capital for the specified coin if not already set
        if self.coin not in self.capital:
            self.capital[self.coin] = self.initial_capital

        self.save_state()

    def save_state(self):
        """Save the current state to the file."""
        state = {
            'capital': self.capital,
            'positions': self.positions,
            'trade_history': self.trade_history
        }
        try:
            self.ensure_directory_exists()
            with open(self.file_path, 'w') as f:
                json.dump(state, f, indent=4)
            print(f"Saved state to {self.file_path}")
        except IOError as e:
            print(f"Error saving to {self.file_path}: {e}")

    def simulate_buy(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a buy trade using the capital allocated to the specified coin."""
        coin = coin.lower()
        if coin not in self.capital:
            print(f"No capital allocated for {coin}. Please deposit funds first.")
            return False
        cost = quantity * price * (1 + trading_fee)
        if cost > self.capital[coin]:
            print(f"Insufficient capital for BUY {coin}: Need ${cost:.2f}, have ${self.capital[coin]:.2f}")
            return False
        self.capital[coin] -= cost
        self.positions[coin] = self.positions.get(coin, 0.0) + quantity
        trade = {
            'timestamp': datetime.now().isoformat(),
            'coin': coin,
            'action': 'BUY',
            'quantity': quantity,
            'price': price,
            'capital_before': self.capital[coin] + cost,
            'capital_after': self.capital[coin],
            'profit': 0.0
        }
        self.trade_history.append(trade)
        self.save_state()
        return True

    def simulate_sell(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a sell trade, adding proceeds to the coin’s capital."""
        coin = coin.lower()
        if coin not in self.positions or self.positions[coin] < quantity:
            print(f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}")
            return False
        proceeds = quantity * price * (1 - trading_fee)
        self.capital[coin] += proceeds
        self.positions[coin] -= quantity
        if self.positions[coin] <= 0.0:
            del self.positions[coin]
        trade = {
            'timestamp': datetime.now().isoformat(),
            'coin': coin,
            'action': 'SELL',
            'quantity': quantity,
            'price': price,
            'capital_before': self.capital[coin] - proceeds,
            'capital_after': self.capital[coin],
            'profit': proceeds  # Simplified; actual profit depends on buy price
        }
        self.trade_history.append(trade)
        self.save_state()
        return True

    def deposit(self, coin, amount):
        """Add capital to a specific coin’s account."""
        coin = coin.lower()
        if coin not in self.capital:
            self.capital[coin] = amount
        else:
            self.capital[coin] += amount
        self.save_state()
        print(f"Deposited ${amount:.2f} to {coin}. New capital: ${self.capital[coin]:.2f}")

    def withdraw(self, coin, amount):
        """Remove capital from a specific coin’s account."""
        coin = coin.lower()
        if coin not in self.capital or self.capital[coin] < amount:
            print(f"Insufficient capital to withdraw from {coin}: Have ${self.capital.get(coin, 0.0):.2f}, need ${amount:.2f}")
            return False
        self.capital[coin] -= amount
        self.save_state()
        print(f"Withdrew ${amount:.2f} from {coin}. New capital: ${self.capital[coin]:.2f}")
        return True

    def get_position(self, coin):
        """Return the quantity held for a specific coin."""
        return self.positions.get(coin.lower(), 0.0)

    def get_capital(self, coin):
        """Return the current capital for a specific coin."""
        return self.capital.get(coin.lower(), 0.0)