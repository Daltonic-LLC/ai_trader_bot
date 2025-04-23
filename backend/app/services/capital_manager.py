import json
import os
from datetime import datetime

class CapitalManager:
    def __init__(self, coin, initial_capital=1000.0, file_path="data/activities/trade_history.json"):
        """
        Initialize the CapitalManager with capital for a single coin, updating records based on trades.

        :param coin: The coin symbol (e.g., 'bnb') to initialize with capital if not already set.
        :param initial_capital: The initial capital for the coin if not already in state (default: 1000.0).
        :param file_path: Path to the JSON file for saving state.
        """
        self.capital = {}  # {coin: current_capital}
        self.positions = {}  # {coin: quantity}
        self.total_cost = {}  # {coin: total_cost_basis}
        self.trade_records = {}  # {coin: {timestamp, quantity, price, total_profit}}
        self.file_path = file_path
        self.coin = coin.lower()
        self.initial_capital = initial_capital
        self.ensure_directory_exists()
        self.load_state()

    def ensure_directory_exists(self):
        """Create the directory for the file_path if it doesn’t exist."""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

    def load_state(self):
        """Load capital, positions, cost basis, and trade records from the file."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    loaded_capital = data.get('capital', {})
                    if isinstance(loaded_capital, float):
                        print(f"Warning: Legacy capital format detected. Converting.")
                        self.capital[self.coin] = loaded_capital
                        self.trade_records[self.coin] = {
                            'timestamp': datetime.now().isoformat(),
                            'quantity': 0.0,
                            'price': 0.0,
                            'total_profit': 0.0
                        }
                    else:
                        self.capital.update(loaded_capital)
                    self.positions = data.get('positions', {})
                    self.total_cost = data.get('total_cost', {})
                    self.trade_records = data.get('trade_records', data.get('trade_history', {}))
                    # Convert legacy trade_history list to trade_records if needed
                    if isinstance(self.trade_records, list):
                        self.trade_records = {}
                        for trade in data.get('trade_history', []):
                            coin = trade['coin']
                            self.trade_records[coin] = {
                                'timestamp': trade['timestamp'],
                                'quantity': trade['quantity'],
                                'price': trade['price'],
                                'total_profit': trade.get('profit', 0.0)
                            }
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading {self.file_path}: {e}. Initializing empty state.")
                self.capital = {}
                self.positions = {}
                self.total_cost = {}
                self.trade_records = {}
        else:
            print(f"No file at {self.file_path}. Initializing empty state.")
            self.capital = {}
            self.positions = {}
            self.total_cost = {}
            self.trade_records = {}
        # Do not automatically initialize the coin here
        # Let deposit() or simulate_buy() handle coin initialization
        self.save_state()

    def save_state(self):
        """Save the current state to the file."""
        state = {
            'capital': self.capital,
            'positions': self.positions,
            'total_cost': self.total_cost,
            'trade_records': self.trade_records
        }
        try:
            self.ensure_directory_exists()
            with open(self.file_path, 'w') as f:
                json.dump(state, f, indent=4)
            print(f"Saved state to {self.file_path}")
        except IOError as e:
            print(f"Error saving to {self.file_path}: {e}")

    def simulate_buy(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a buy trade, updating the coin's record."""
        coin = coin.lower()
        if coin not in self.capital:
            # Initialize the coin with zero capital if not present
            self.capital[coin] = 0.0
            self.trade_records[coin] = {
                'timestamp': datetime.now().isoformat(),
                'quantity': 0.0,
                'price': 0.0,
                'total_profit': 0.0
            }
        cost = quantity * price * (1 + trading_fee)
        if cost > self.capital[coin]:
            print(f"Insufficient capital for BUY {coin}: Need ${cost:.2f}, have ${self.capital[coin]:.2f}")
            return False
        self.capital[coin] -= cost
        self.positions[coin] = self.positions.get(coin, 0.0) + quantity
        self.total_cost[coin] = self.total_cost.get(coin, 0.0) + cost
        # Update trade record
        self.trade_records[coin] = {
            'timestamp': datetime.now().isoformat(),
            'quantity': self.positions.get(coin, 0.0),
            'price': price,
            'total_profit': self.trade_records.get(coin, {}).get('total_profit', 0.0)
        }
        self.save_state()
        return True

    def simulate_sell(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a sell trade, updating the coin's record with profit."""
        coin = coin.lower()
        if coin not in self.positions or self.positions[coin] < quantity:
            print(f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}")
            return False
        original_quantity = self.positions[coin]
        average_cost = self.total_cost.get(coin, 0.0) / original_quantity if original_quantity > 0 else 0
        proceeds = quantity * price * (1 - trading_fee)
        profit = (price * (1 - trading_fee) - average_cost) * quantity
        # Update state
        self.capital[coin] += proceeds
        self.positions[coin] -= quantity
        if self.positions[coin] <= 0:
            del self.positions[coin]
            self.total_cost[coin] = 0
        else:
            cost_removed = (quantity / original_quantity) * self.total_cost[coin]
            self.total_cost[coin] -= cost_removed
        # Update trade record
        current_profit = self.trade_records.get(coin, {}).get('total_profit', 0.0)
        self.trade_records[coin] = {
            'timestamp': datetime.now().isoformat(),
            'quantity': self.positions.get(coin, 0.0),
            'price': price,
            'total_profit': current_profit + profit
        }
        self.save_state()
        return True

    def deposit(self, coin, amount):
        """Add capital to a specific coin’s account."""
        coin = coin.lower()
        self.capital[coin] = self.capital.get(coin, 0.0) + amount
        if coin not in self.trade_records:
            self.trade_records[coin] = {
                'timestamp': datetime.now().isoformat(),
                'quantity': self.positions.get(coin, 0.0),
                'price': 0.0,
                'total_profit': 0.0
            }
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

    def get_available_coins(self):
        """
        Retrieve a list of unique coins available in capital, positions, or trade records.

        :return: A sorted list of unique coin names.
        """
        available_coins = set()
        available_coins.update(self.capital.keys())
        available_coins.update(self.positions.keys())
        available_coins.update(self.trade_records.keys())
        return sorted(list(available_coins))