from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging
from threading import Lock
from app.services.mongodb_service import MongoUserService

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CapitalManager:
    """A singleton class to manage trading capital, positions, and trade records."""

    _instance = None
    _lock = Lock()  # Lock for thread safety

    # Fee constants - Optimized to 0.05%
    TRADING_FEE = 0.0005  # 0.05% trading fee for buy/sell orders
    WITHDRAWAL_FEE = 0.0005  # 0.05% withdrawal fee

    def __new__(cls, initial_capital=1000.0):
        """Ensure only one instance of CapitalManager exists."""
        if cls._instance is None:
            cls._instance = super(CapitalManager, cls).__new__(cls)
            cls._instance._initialize(initial_capital)
        return cls._instance

    def _initialize(self, initial_capital):
        """Initialize the CapitalManager instance."""
        self.mongo_service = MongoUserService()
        self.initial_capital = initial_capital
        self._reset_all_data()
        self.load_state()

    def _reset_all_data(self):
        """Reset all data structures to empty state."""
        self.capital = {}  # Current capital per coin
        self.positions = {}  # Quantity held per coin
        self.total_cost = {}  # Total cost of positions per coin
        self.trade_records = {}  # Trade history per coin
        self.user_investments = {}  # {coin: {user_id: total_deposit}}
        self.user_withdrawals = {}  # {coin: {user_id: total_withdrawn}}
        self.total_deposits = {}  # {coin: total_deposits}
        self.total_withdrawals = {}  # {coin: total_withdrawals}
        self.realized_profits = {}  # {coin: total_realized_profit}

    def load_state(self):
        """Load the trading state from MongoDB."""
        try:
            state = self.mongo_service.get_trading_state()
            if state:  # Only load if state exists and is not empty
                self.capital = state.get("capital", {})
                self.positions = state.get("positions", {})
                self.total_cost = state.get("total_cost", {})
                self.trade_records = state.get("trade_records", {})
                self.user_investments = state.get("user_investments", {})
                self.user_withdrawals = state.get("user_withdrawals", {})
                self.total_deposits = state.get("total_deposits", {})
                self.total_withdrawals = state.get("total_withdrawals", {})
                self.realized_profits = state.get("realized_profits", {})
                logging.info("Loaded trading state from database.")
            else:
                logging.info("No existing state found in database. Using fresh state.")
                self._reset_all_data()
        except Exception as e:
            logging.error(f"Failed to load state from MongoDB: {e}")
            logging.info("Initializing with fresh state due to load failure.")
            self._reset_all_data()

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
            "realized_profits": self.realized_profits,
        }
        try:
            self.mongo_service.set_trading_state(state)
            logging.info("Saved trading state to database.")
        except Exception as e:
            logging.error(f"Failed to save state to MongoDB: {e}")

    def deposit(self, user_id, coin, amount):
        """Add capital to a specific coin for a user."""
        with self._lock:
            coin = coin.lower()

            # Initialize coin data if it doesn't exist
            if coin not in self.user_investments:
                self.user_investments[coin] = {}
            if coin not in self.user_withdrawals:
                self.user_withdrawals[coin] = {}
            if coin not in self.trade_records:
                self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
            if coin not in self.realized_profits:
                self.realized_profits[coin] = 0.0

            # Update user investment
            self.user_investments[coin][user_id] = (
                self.user_investments[coin].get(user_id, 0.0) + amount
            )

            # Update totals
            self.total_deposits[coin] = self.total_deposits.get(coin, 0.0) + amount
            self.capital[coin] = self.capital.get(coin, 0.0) + amount

            self.save_state()

            # Log ownership percentage for verification
            ownership_pct = self.get_user_ownership_percentage(user_id, coin)
            logging.info(
                f"User {user_id} deposited ${amount:.2f} to {coin}. "
                f"Total deposits: ${self.total_deposits[coin]:.2f}, "
                f"Current capital: ${self.capital[coin]:.2f}, "
                f"User ownership: {ownership_pct:.2f}%"
            )

    def get_user_ownership_percentage(self, user_id, coin):
        """Calculate user's ownership percentage for a coin."""
        coin = coin.lower()
        if (
            coin not in self.user_investments
            or user_id not in self.user_investments[coin]
        ):
            return 0.0

        user_investment = self.user_investments[coin][user_id]
        total_deposits = self.total_deposits.get(coin, 0.0)

        if total_deposits == 0:
            return 0.0

        return (user_investment / total_deposits) * 100

    def withdraw(self, user_id, coin, amount):
        """Withdraw capital from a specific coin for a user with 0.05% withdrawal fee."""
        with self._lock:
            coin = coin.lower()

            if (
                coin not in self.user_investments
                or user_id not in self.user_investments[coin]
            ):
                raise ValueError(f"No investment found for user {user_id} in {coin}")

            withdrawal_amount = self.calculate_withdrawal(user_id, coin)
            if amount > withdrawal_amount:
                raise ValueError(
                    f"Insufficient withdrawable amount for {coin}: "
                    f"Requested ${amount:.2f}, Available ${withdrawal_amount:.2f}"
                )

            available_capital = self.capital.get(coin, 0.0)
            if amount > available_capital:
                raise ValueError(
                    f"Insufficient capital for {coin}: "
                    f"Requested ${amount:.2f}, Available ${available_capital:.2f}"
                )

            amount = Decimal(str(amount))
            fee_rate = Decimal(str(self.WITHDRAWAL_FEE))
            fee = (amount * fee_rate).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            net_withdrawal = (amount - fee).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )

            # Update capital
            capital_decimal = Decimal(str(self.capital.get(coin, 0.0)))
            capital_decimal -= amount
            self.capital[coin] = float(capital_decimal)

            # Update user withdrawals
            if coin not in self.user_withdrawals:
                self.user_withdrawals[coin] = {}
            self.user_withdrawals[coin][user_id] = self.user_withdrawals[coin].get(
                user_id, 0.0
            ) + float(amount)
            self.total_withdrawals[coin] = self.total_withdrawals.get(
                coin, 0.0
            ) + float(amount)

            self.save_state()

            # Log ownership percentage after withdrawal
            ownership_pct = self.get_user_ownership_percentage(user_id, coin)
            logging.info(
                f"User {user_id} withdrew ${float(amount):.2f} from {coin} "
                f"(Fee: ${float(fee):.2f} [0.05%], Net: ${float(net_withdrawal):.2f}). "
                f"Remaining capital: ${self.capital[coin]:.2f}, "
                f"User ownership: {ownership_pct:.2f}%"
            )

            return {
                "gross_amount": float(amount),
                "fee": float(fee),
                "fee_percentage": float(self.WITHDRAWAL_FEE * 100),
                "net_amount": float(net_withdrawal),
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

        ownership_percentage = user_total_deposits / total_deposits
        current_capital = self.capital.get(coin, 0.0)
        available_for_withdrawal = ownership_percentage * current_capital
        return available_for_withdrawal

    def reset_state(self):
        """Reset the entire state and clear from database."""
        with self._lock:
            logging.info("Resetting CapitalManager state...")

            # Reset all instance variables
            self._reset_all_data()

            # Clear the database state
            try:
                self.mongo_service.clear_trading_state()
                logging.info("Cleared trading state from database")
            except Exception as e:
                logging.error(f"Failed to clear trading state from database: {e}")

            # Save the empty state to database to ensure it's persisted
            self.save_state()

            logging.info("CapitalManager state has been completely reset")

    @classmethod
    def force_reset_singleton(cls):
        """Force reset the singleton instance. Use with caution!"""
        with cls._lock:
            if cls._instance is not None:
                logging.info("Forcing singleton reset...")
                # Reset the instance data before clearing the reference
                if hasattr(cls._instance, "_reset_all_data"):
                    cls._instance._reset_all_data()
                cls._instance = None
                logging.info("Singleton instance reset complete")

    def get_investment_summary(self):
        """Get a summary of all investments across all coins and users."""
        summary = {}
        for coin in self.user_investments:
            coin_data = {
                "total_deposits": self.total_deposits.get(coin, 0.0),
                "total_withdrawals": self.total_withdrawals.get(coin, 0.0),
                "current_capital": self.capital.get(coin, 0.0),
                "users": {},
            }

            for user_id in self.user_investments[coin]:
                user_deposits = self.user_investments[coin][user_id]
                user_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
                ownership_pct = self.get_user_ownership_percentage(user_id, coin)

                coin_data["users"][user_id] = {
                    "deposits": user_deposits,
                    "withdrawals": user_withdrawals,
                    "net_investment": user_deposits - user_withdrawals,
                    "ownership_percentage": ownership_pct,
                }

            summary[coin] = coin_data

        return summary

    def verify_ownership_totals(self):
        """Verify that ownership percentages add up to 100% for each coin."""
        verification_results = {}

        for coin in self.user_investments:
            total_ownership = 0.0
            for user_id in self.user_investments[coin]:
                ownership_pct = self.get_user_ownership_percentage(user_id, coin)
                total_ownership += ownership_pct

            verification_results[coin] = {
                "total_ownership_percentage": total_ownership,
                "is_valid": abs(total_ownership - 100.0)
                < 0.01,  # Allow for rounding errors
            }

        return verification_results

    # ... [Rest of the existing methods remain the same] ...

    def get_position(self, coin):
        """Return the quantity held for a coin."""
        return self.positions.get(coin.lower(), 0.0)

    def get_capital(self, coin):
        """Return the current capital for a coin."""
        return self.capital.get(coin.lower(), 0.0)

    def get_total_capital(self):
        """Return the total capital across all coins."""
        return sum(self.capital.values())

    def get_all_capitals(self):
        """Return the current capital for all coins, formatted to 2 decimal places."""
        return {coin: round(capital, 2) for coin, capital in self.capital.items()}
