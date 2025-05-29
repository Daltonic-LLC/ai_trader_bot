from datetime import datetime
import logging
from app.services.mongodb_service import MongoUserService

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CapitalManager:
    """A singleton class to manage trading capital, positions, and trade records."""
    
    _instance = None

    def __new__(cls, initial_capital=1000.0):
        """Ensure only one instance of CapitalManager exists."""
        if cls._instance is None:
            cls._instance = super(CapitalManager, cls).__new__(cls)
            cls._instance.mongo_service = MongoUserService()
            cls._instance.initial_capital = initial_capital
            cls._instance.capital = {}
            cls._instance.positions = {}
            cls._instance.total_cost = {}
            cls._instance.trade_records = {}
            cls._instance.load_state()
        return cls._instance

    def load_state(self):
        """Load the trading state from MongoDB."""
        try:
            state = self.mongo_service.get_trading_state()
            self.capital = state.get('capital', {})
            self.positions = state.get('positions', {})
            self.total_cost = state.get('total_cost', {})
            self.trade_records = state.get('trade_records', {})
            logging.info("Loaded trading state from database.")
        except Exception as e:
            logging.error(f"Failed to load state from MongoDB: {e}")
            raise

    def save_state(self):
        """Save the trading state to MongoDB."""
        state = {
            'capital': self.capital,
            'positions': self.positions,
            'total_cost': self.total_cost,
            'trade_records': self.trade_records
        }
        try:
            self.mongo_service.set_trading_state(state)
            logging.info("Saved trading state to database.")
        except Exception as e:
            logging.error(f"Failed to save state to MongoDB: {e}")
            raise

    def deposit(self, coin, amount):
        """Add capital to a specific coin."""
        coin = coin.lower()
        self.capital[coin] = self.capital.get(coin, 0.0) + amount
        if coin not in self.trade_records:
            self.trade_records[coin] = {'trades': [], 'total_profit': 0.0}
        self.save_state()
        logging.info(f"Deposited ${amount:.2f} to {coin}. New capital: ${self.capital[coin]:.2f}")

    def withdraw(self, coin, amount):
        """Remove capital from a specific coin."""
        coin = coin.lower()
        if coin not in self.capital or self.capital[coin] < amount:
            logging.warning(f"Insufficient capital to withdraw from {coin}: Have ${self.capital.get(coin, 0.0):.2f}, need ${amount:.2f}")
            return False
        self.capital[coin] -= amount
        self.save_state()
        logging.info(f"Withdrew ${amount:.2f} from {coin}. New capital: ${self.capital[coin]:.2f}")
        return True

    def simulate_buy(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a buy trade."""
        coin = coin.lower()
        if coin not in self.capital:
            self.capital[coin] = self.initial_capital
            self.trade_records[coin] = {'trades': [], 'total_profit': 0.0}
        cost = quantity * price * (1 + trading_fee)
        if cost > self.capital[coin]:
            logging.warning(f"Insufficient capital for BUY {coin}: Need ${cost:.2f}, have ${self.capital[coin]:.2f}")
            return False
        self.capital[coin] -= cost
        self.positions[coin] = self.positions.get(coin, 0.0) + quantity
        self.total_cost[coin] = self.total_cost.get(coin, 0.0) + cost
        self.trade_records[coin]['trades'].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'buy',
            'quantity': quantity,
            'price': price,
            'cost': cost
        })
        self.save_state()
        logging.info(f"Simulated BUY of {quantity} {coin} at ${price:.2f}. Cost: ${cost:.2f}")
        return True

    def simulate_sell(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a sell trade."""
        coin = coin.lower()
        if coin not in self.positions or self.positions[coin] < quantity:
            logging.warning(f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}")
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
        self.trade_records[coin]['trades'].append({
            'timestamp': datetime.now().isoformat(),
            'type': 'sell',
            'quantity': quantity,
            'price': price,
            'proceeds': proceeds,
            'profit': profit
        })
        self.trade_records[coin]['total_profit'] += profit
        self.save_state()
        logging.info(f"Simulated SELL of {quantity} {coin} at ${price:.2f}. Proceeds: ${proceeds:.2f}, Profit: ${profit:.2f}")
        return True

    def get_position(self, coin):
        """Return the quantity held for a coin."""
        return self.positions.get(coin.lower(), 0.0)

    def get_capital(self, coin):
        """Return the current capital for a coin."""
        return self.capital.get(coin.lower(), 0.0)

    def get_total_capital(self):
        """Return the total capital across all coins."""
        return sum(self.capital.values())

    def get_portfolio_value(self, market_prices):
        """Calculate the current portfolio value based on market prices.
        
        Args:
            market_prices (dict): A dictionary of current market prices for each coin (e.g., {'btc': 50000.0, 'eth': 3000.0}).
        
        Returns:
            float: Total portfolio value (capital + position values).
        """
        total_value = self.get_total_capital()
        for coin, position in self.positions.items():
            price = market_prices.get(coin, 0.0)
            total_value += position * price
        return total_value