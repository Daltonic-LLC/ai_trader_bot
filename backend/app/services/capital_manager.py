from datetime import datetime
import logging
from app.services.mongodb_service import MongoUserService

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class CapitalManager:
    """A singleton class to manage trading capital, positions, and trade records."""

    _instance = None

    def __new__(cls, initial_capital=1000.0):
        """Ensure only one instance of CapitalManager exists."""
        if cls._instance is None:
            cls._instance = super(CapitalManager, cls).__new__(cls)
            cls._instance.mongo_service = MongoUserService()
            cls._instance.initial_capital = initial_capital
            cls._instance.capital = {}  # Current capital per coin
            cls._instance.positions = {}  # Quantity held per coin
            cls._instance.total_cost = {}  # Total cost of positions per coin
            cls._instance.trade_records = {}  # Trade history per coin
            cls._instance.user_investments = {}  # {coin: {user_id: total_deposit}}
            cls._instance.user_withdrawals = {}  # {coin: {user_id: total_withdrawn}}
            cls._instance.total_deposits = {}  # {coin: total_deposits}
            cls._instance.total_withdrawals = {}  # {coin: total_withdrawals}
            cls._instance.load_state()
        return cls._instance

    def load_state(self):
        """Load the trading state from MongoDB."""
        try:
            state = self.mongo_service.get_trading_state()
            self.capital = state.get("capital", {})
            self.positions = state.get("positions", {})
            self.total_cost = state.get("total_cost", {})
            self.trade_records = state.get("trade_records", {})
            self.user_investments = state.get("user_investments", {})
            self.user_withdrawals = state.get("user_withdrawals", {})
            self.total_deposits = state.get("total_deposits", {})
            self.total_withdrawals = state.get("total_withdrawals", {})
            logging.info("Loaded trading state from database.")
        except Exception as e:
            logging.error(f"Failed to load state from MongoDB: {e}")
            raise

    def save_state(self):
        """Save the trading state to MongoDB."""
        state = {
            "capital": self.capital,
            "positions": self.positions,
            "total_cost": self.total_cost,
            "trade_records": self.trade_records,
            "user_investments": self.user_investments,
            "user_withdrawals": self.user_withdrawals,
            "total_deposits": self.total_deposits,
            "total_withdrawals": self.total_withdrawals,
        }
        try:
            self.mongo_service.set_trading_state(state)
            logging.info("Saved trading state to database.")
        except Exception as e:
            logging.error(f"Failed to save state to MongoDB: {e}")
            raise

    def deposit(self, user_id, coin, amount):
        """Add capital to a specific coin for a user."""
        coin = coin.lower()
        # Initialize coin-specific dictionaries if not present
        if coin not in self.user_investments:
            self.user_investments[coin] = {}
        if coin not in self.user_withdrawals:
            self.user_withdrawals[coin] = {}
        
        # Update user's total deposit for the coin
        self.user_investments[coin][user_id] = (
            self.user_investments[coin].get(user_id, 0.0) + amount
        )
        # Update total deposits for the coin
        self.total_deposits[coin] = self.total_deposits.get(coin, 0.0) + amount
        # Update current capital
        self.capital[coin] = self.capital.get(coin, 0.0) + amount
        
        if coin not in self.trade_records:
            self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
        
        self.save_state()
        logging.info(
            f"User {user_id} deposited ${amount:.2f} to {coin}. Total deposits: ${self.total_deposits[coin]:.2f}, Current capital: ${self.capital[coin]:.2f}"
        )

    def withdraw(self, user_id, coin, amount, withdrawal_fee=0.001):
        """Withdraw capital from a specific coin for a user with 0.1% withdrawal fee."""
        coin = coin.lower()

        if (
            coin not in self.user_investments
            or user_id not in self.user_investments[coin]
        ):
            raise ValueError(f"No investment found for user {user_id} in {coin}")
        
        # Calculate available withdrawal amount based on ownership
        withdrawal_amount = self.calculate_withdrawal(user_id, coin)
        
        if amount > withdrawal_amount:
            raise ValueError(
                f"Insufficient withdrawable amount for {coin}: Requested ${amount:.2f}, Available ${withdrawal_amount:.2f}"
            )
        
        available_capital = self.capital.get(coin, 0.0)
        if amount > available_capital:
            raise ValueError(
                f"Insufficient capital for {coin}: Requested ${amount:.2f}, Available ${available_capital:.2f}"
            )
        
        # Calculate withdrawal fee
        fee = amount * withdrawal_fee
        net_withdrawal = amount - fee
        
        # Initialize withdrawal tracking if not present
        if coin not in self.user_withdrawals:
            self.user_withdrawals[coin] = {}
        
        # Record the withdrawal (but don't change user_investments)
        self.user_withdrawals[coin][user_id] = (
            self.user_withdrawals[coin].get(user_id, 0.0) + amount
        )
        self.total_withdrawals[coin] = self.total_withdrawals.get(coin, 0.0) + amount
        
        # Reduce available capital (full amount including fee stays in system)
        self.capital[coin] -= amount
        
        self.save_state()
        
        logging.info(
            f"User {user_id} withdrew ${amount:.2f} from {coin} (Fee: ${fee:.2f}, Net: ${net_withdrawal:.2f}). Remaining capital: ${self.capital[coin]:.2f}"
        )
        
        return {
            "gross_amount": amount,
            "fee": fee,
            "net_amount": net_withdrawal
        }

    def calculate_withdrawal(self, user_id, coin):
        """Calculate the withdrawal amount based on user's ownership percentage."""
        coin = coin.lower()
        if (
            coin not in self.user_investments
            or user_id not in self.user_investments[coin]
        ):
            logging.warning(f"No investment found for user {user_id} in {coin}")
            return 0.0
        
        user_total_deposits = self.user_investments[coin][user_id]
        total_deposits = self.total_deposits.get(coin, 0.0)
        
        if total_deposits == 0:
            logging.warning(f"No total deposits recorded for {coin}")
            return 0.0
        
        # Calculate ownership based on original deposits
        ownership_percentage = user_total_deposits / total_deposits
        
        # Calculate total current value (capital + positions)
        position_value = self.positions.get(coin, 0.0) * 1.0  # You'll need current price here
        total_current_value = self.capital.get(coin, 0.0) + position_value
        
        # User's share of current value
        user_current_value = ownership_percentage * total_current_value
        
        # Subtract what they've already withdrawn
        user_total_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        available_for_withdrawal = max(0, user_current_value - user_total_withdrawals)
        
        return available_for_withdrawal

    def get_user_investment_details(self, user_id, coin, current_price):
        """Retrieve investment details for a user and a specific coin."""
        coin = coin.lower()

        # Check if the user has investments in this coin
        if (
            coin not in self.user_investments
            or user_id not in self.user_investments[coin]
        ):
            return {
                "investment": 0.0,
                "ownership_percentage": 0.0,
                "current_share": 0.0,
                "profit_loss": 0.0,
            }

        # Get user's total investment amount (original deposits)
        user_investment = self.user_investments[coin][user_id]
        user_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        total_deposits = self.total_deposits.get(coin, 0.0)

        # Handle edge case where total deposits are zero
        if total_deposits == 0:
            return {
                "investment": user_investment,
                "ownership_percentage": 0.0,
                "current_share": 0.0,
                "profit_loss": 0.0,
            }

        # Calculate ownership percentage based on original deposits
        ownership_percentage = (user_investment / total_deposits) * 100

        # Calculate total value including positions
        position_value = self.positions.get(coin, 0.0) * current_price
        total_value = self.capital.get(coin, 0.0) + position_value

        # Calculate user's current share
        current_share = (ownership_percentage / 100) * total_value
        
        # Calculate net investment (what user should currently own)
        net_investment = user_investment - user_withdrawals
        
        # Calculate profit/loss: current_share vs what they should have (net_investment)
        # If no trading occurred, current_share should equal net_investment
        profit_loss = current_share - net_investment

        return {
            "investment": net_investment,  # Current remaining investment (what user should see)
            "original_investment": user_investment,  # For internal tracking
            "total_deposits": user_investment,  # Total ever deposited
            "total_withdrawals": user_withdrawals,  # Total ever withdrawn
            "net_investment": net_investment,  # Current remaining investment
            "ownership_percentage": ownership_percentage,
            "current_share": current_share,
            "profit_loss": profit_loss,
        }

    def get_user_investment(self, user_id, coin):
        """Get the user's net investment (total deposits - withdrawals) for a specific coin."""
        coin = coin.lower()
        total_deposits = self.user_investments.get(coin, {}).get(user_id, 0.0)
        total_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        return total_deposits - total_withdrawals

    def simulate_buy(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a buy trade with 0.1% trading fee."""
        coin = coin.lower()
        if coin not in self.capital:
            self.capital[coin] = 0.0
            self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
        
        cost = quantity * price * (1 + trading_fee)
        if cost > self.capital[coin]:
            logging.warning(
                f"Insufficient capital for BUY {coin}: Need ${cost:.2f}, have ${self.capital[coin]:.2f}"
            )
            return False
        
        self.capital[coin] -= cost
        self.positions[coin] = self.positions.get(coin, 0.0) + quantity
        self.total_cost[coin] = self.total_cost.get(coin, 0.0) + cost
        
        fee_amount = quantity * price * trading_fee
        
        self.trade_records[coin]["trades"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "buy",
                "quantity": quantity,
                "price": price,
                "cost": cost,
                "fee": fee_amount,
                "fee_percentage": trading_fee * 100
            }
        )
        self.save_state()
        logging.info(
            f"Simulated BUY of {quantity} {coin} at ${price:.2f}. Cost: ${cost:.2f} (Fee: ${fee_amount:.2f})"
        )
        return True

    def simulate_sell(self, coin, quantity, price, trading_fee=0.001):
        """Simulate a sell trade with 0.1% trading fee."""
        coin = coin.lower()
        if coin not in self.positions or self.positions[coin] < quantity:
            logging.warning(
                f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}"
            )
            return False
        
        original_quantity = self.positions[coin]
        average_cost = (
            self.total_cost.get(coin, 0.0) / original_quantity
            if original_quantity > 0
            else 0
        )
        
        proceeds = quantity * price * (1 - trading_fee)
        fee_amount = quantity * price * trading_fee
        profit = (price * (1 - trading_fee) - average_cost) * quantity
        
        self.capital[coin] = self.capital.get(coin, 0.0) + proceeds
        self.positions[coin] -= quantity
        
        if self.positions[coin] <= 0:
            del self.positions[coin]
            self.total_cost[coin] = 0
        else:
            cost_removed = (quantity / original_quantity) * self.total_cost[coin]
            self.total_cost[coin] -= cost_removed
        
        self.trade_records[coin]["trades"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "sell",
                "quantity": quantity,
                "price": price,
                "proceeds": proceeds,
                "profit": profit,
                "fee": fee_amount,
                "fee_percentage": trading_fee * 100
            }
        )
        self.trade_records[coin]["total_profit"] += profit
        self.save_state()
        logging.info(
            f"Simulated SELL of {quantity} {coin} at ${price:.2f}. Proceeds: ${proceeds:.2f}, Profit: ${profit:.2f} (Fee: ${fee_amount:.2f})"
        )
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

    def get_coin_summary(self, coin):
        """Get a summary of all investments and current state for a coin."""
        coin = coin.lower()
        
        total_deposits = self.total_deposits.get(coin, 0.0)
        total_withdrawals = self.total_withdrawals.get(coin, 0.0)
        current_capital = self.capital.get(coin, 0.0)
        current_positions = self.positions.get(coin, 0.0)
        
        # Calculate sum of all user investments to verify consistency
        calculated_total_deposits = 0.0
        user_details = {}
        if coin in self.user_investments:
            for user_id, investment in self.user_investments[coin].items():
                withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
                user_details[user_id] = {
                    "total_deposits": investment,
                    "total_withdrawals": withdrawals,
                    "net_investment": investment - withdrawals
                }
                calculated_total_deposits += investment
        
        # Check for data inconsistencies
        deposits_match = abs(total_deposits - calculated_total_deposits) < 0.01
        
        return {
            "coin": coin.upper(),
            "recorded_total_deposits": total_deposits,
            "calculated_total_deposits": calculated_total_deposits,
            "deposits_consistent": deposits_match,
            "total_withdrawals": total_withdrawals,
            "current_capital": current_capital,
            "current_positions": current_positions,
            "total_current_value": current_capital,  # + position_value when you have current price
            "user_details": user_details,
            "number_of_users": len(user_details),
            "data_integrity_issues": not deposits_match
        }

    def debug_all_coins(self):
        """Debug all coins to find inconsistencies."""
        all_coins = set(list(self.capital.keys()) + list(self.total_deposits.keys()) + list(self.user_investments.keys()))
        
        debug_info = {}
        for coin in all_coins:
            debug_info[coin] = self.get_coin_summary(coin)
        
        return debug_info

    def reset_coin_data(self, coin):
        """Reset all data for a specific coin - USE WITH CAUTION!"""
        coin = coin.lower()
        
        # Remove all traces of this coin
        self.capital.pop(coin, None)
        self.positions.pop(coin, None)
        self.total_cost.pop(coin, None)
        self.trade_records.pop(coin, None)
        self.user_investments.pop(coin, None)
        self.user_withdrawals.pop(coin, None)
        self.total_deposits.pop(coin, None)
        self.total_withdrawals.pop(coin, None)
        
        self.save_state()
        logging.info(f"Reset all data for {coin.upper()}")

    def fix_total_deposits_consistency(self):
        """Fix total_deposits to match sum of user investments."""
        for coin, users in self.user_investments.items():
            calculated_total = sum(users.values())
            current_total = self.total_deposits.get(coin, 0.0)
            
            if abs(calculated_total - current_total) > 0.01:
                logging.warning(f"Fixing {coin}: total_deposits was {current_total}, should be {calculated_total}")
                self.total_deposits[coin] = calculated_total
        
        self.save_state()

    def get_portfolio_value(self, market_prices):
        """Calculate the current portfolio value based on market prices."""
        total_value = self.get_total_capital()
        for coin, position in self.positions.items():
            price = market_prices.get(coin, 0.0)
            total_value += position * price
        return total_value
    
    def reset_state(self):
        """Reset the entire state."""
        self.capital = {}
        self.positions = {}
        self.total_cost = {}
        self.trade_records = {}
        self.user_investments = {}
        self.user_withdrawals = {}
        self.total_deposits = {}
        self.total_withdrawals = {}
        self.save_state()