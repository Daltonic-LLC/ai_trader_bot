from datetime import datetime
from app.services.mongodb_service import MongoUserService  # Import MongoUserService

class CapitalManager:
    def __init__(self, initial_capital=1000.0):
        """
        Initialize CapitalManager for scheduler operations.

        :param initial_capital: Initial capital for coins if not in state (default: 1000.0).
        """
        self.mongo_service = MongoUserService()  # Initialize MongoUserService internally
        self.initial_capital = initial_capital
        self.capital = {}
        self.positions = {}
        self.total_cost = {}
        self.trade_records = {}
        self.load_state()  # Load state directly since mongo_service is always present

    def load_state(self):
        """Load the trading state from MongoDB."""
        state = self.mongo_service.get_trading_state()
        self.capital = state.get('capital', {})
        self.positions = state.get('positions', {})
        self.total_cost = state.get('total_cost', {})
        self.trade_records = state.get('trade_records', {})

    def save_state(self):
        """Save the trading state to MongoDB."""
        state = {
            'capital': self.capital,
            'positions': self.positions,
            'total_cost': self.total_cost,
            'trade_records': self.trade_records
        }
        self.mongo_service.set_trading_state(state)

    def deposit(self, coin, amount):
        """Add capital to a specific coin."""
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
        """Remove capital from a specific coin."""
        coin = coin.lower()
        if coin not in self.capital or self.capital[coin] < amount:
            print(f"Insufficient capital to withdraw from {coin}: Have ${self.capital.get(coin, 0.0):.2f}, need ${amount:.2f}")
            return False
        self.capital[coin] -= amount
        self.save_state()
        print(f"Withdrew ${amount:.2f} from {coin}. New capital: ${self.capital[coin]:.2f}")
        return True

    def simulate_buy(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a buy trade."""
        coin = coin.lower()
        if coin not in self.capital:
            self.capital[coin] = self.initial_capital
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
        self.trade_records[coin] = {
            'timestamp': datetime.now().isoformat(),
            'quantity': self.positions.get(coin, 0.0),
            'price': price,
            'total_profit': self.trade_records.get(coin, {}).get('total_profit', 0.0)
        }
        self.save_state()
        return True

    def simulate_sell(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a sell trade."""
        coin = coin.lower()
        if coin not in self.positions or self.positions[coin] < quantity:
            print(f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}")
            return False
        original_quantity = self.positions[coin]
        average_cost = self.total_cost.get(coin, 0.0) / original_quantity if original_quantity > 0 else 0
        proceeds = quantity * price * (1 - trading_fee)
        profit = (price * (1 - trading_fee) - average_cost) * quantity
        self.capital[coin] = self.capital.get(coin, 0.0) + proceeds
        self.positions[coin] -= quantity
        if self.positions[coin] <= 0:
            del self.positions[coin]
            self.total_cost[coin] = 0
        else:
            cost_removed = (quantity / original_quantity) * self.total_cost[coin]
            self.total_cost[coin] -= cost_removed
        current_profit = self.trade_records.get(coin, {}).get('total_profit', 0.0)
        self.trade_records[coin] = {
            'timestamp': datetime.now().isoformat(),
            'quantity': self.positions.get(coin, 0.0),
            'price': price,
            'total_profit': current_profit + profit
        }
        self.save_state()
        return True

    def get_position(self, coin):
        """Return the quantity held for a coin."""
        return self.positions.get(coin.lower(), 0.0)

    def get_capital(self, coin):
        """Return the current capital for a coin."""
        return self.capital.get(coin.lower(), 0.0)