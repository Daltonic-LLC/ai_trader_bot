from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import logging
from threading import Lock
from app.services.mongodb_service import MongoUserService
from app.services.coin_stats import CoinStatsService
from typing import Optional

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CapitalManager:
    """A singleton class to manage trading capital, positions, and user investments for multiple coins.
    Uses Decimal for precise financial calculations and MongoDB for state persistence.
    """

    _instance = None
    _lock = Lock()  # Thread safety lock

    # Fee constants
    TRADING_FEE = 0.0005  # 0.05% fee for buy/sell trades
    WITHDRAWAL_FEE = 0.0005  # 0.05% fee for withdrawals

    def __new__(cls, initial_capital=1000.0):
        """Ensure singleton pattern: only one instance exists."""
        if cls._instance is None:
            cls._instance = super(CapitalManager, cls).__new__(cls)
            cls._instance._initialize(initial_capital)
        return cls._instance

    def _initialize(self, initial_capital):
        """Set up initial state and load from MongoDB."""
        self.mongo_service = MongoUserService()
        self.initial_capital = initial_capital
        self.capital = {}  # {coin: current_cash}
        self.positions = {}  # {coin: quantity_held}
        self.total_cost = {}  # {coin: total_investment_cost}
        self.trade_records = {}  # {coin: {'trades': [], 'total_profit': float}}
        self.user_investments = {}  # {coin: {user_id: total_deposits}}
        self.user_withdrawals = {}  # {coin: {user_id: total_withdrawn}}
        self.total_deposits = {}  # {coin: sum_of_deposits}
        self.total_withdrawals = {}  # {coin: sum_of_withdrawals}
        self.realized_profits = {}  # {coin: total_realized_profit}
        self.load_state()

    # --- State Management Methods ---

    def load_state(self):
        """Load trading state from MongoDB or reset if loading fails."""
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
            self.realized_profits = state.get("realized_profits", {})
            logging.info("Loaded trading state from database.")
        except Exception as e:
            logging.error(f"Failed to load state from MongoDB: {e}")
            self._reset_internal_state()

    def save_state(self):
        """Save current trading state to MongoDB."""
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

    def reset_state(self):
        """Reset all state variables and save to MongoDB."""
        with self._lock:
            self._reset_internal_state()
            self.save_state()
            logging.info("CapitalManager state has been completely reset")

    def _reset_internal_state(self):
        """Helper method to reset all state dictionaries."""
        self.capital = {}
        self.positions = {}
        self.total_cost = {}
        self.trade_records = {}
        self.user_investments = {}
        self.user_withdrawals = {}
        self.total_deposits = {}
        self.total_withdrawals = {}
        self.realized_profits = {}

    # --- User Investment Methods ---

    def deposit(self, user_id, coin, amount):
        """Add user capital to a specific coin."""
        with self._lock:
            coin = coin.lower()
            self._ensure_coin_initialized(coin)
            # Update user investments
            self.user_investments[coin][user_id] = (
                self.user_investments[coin].get(user_id, 0.0) + amount
            )
            self.total_deposits[coin] = self.total_deposits.get(coin, 0.0) + amount
            self.capital[coin] = self.capital.get(coin, 0.0) + amount
            self.save_state()
            logging.info(f"User {user_id} deposited ${amount:.2f} to {coin}.")

    def withdraw(self, user_id, coin, amount):
        """Withdraw user capital from a coin with a 0.05% fee."""
        with self._lock:
            coin = coin.lower()
            if not self._user_has_investment(user_id, coin):
                raise ValueError(f"No investment found for user {user_id} in {coin}")

            # Validate withdrawal amount
            max_withdrawal = self.calculate_withdrawal(user_id, coin)
            if amount > max_withdrawal:
                raise ValueError(
                    f"Insufficient withdrawable amount: Requested ${amount:.2f}, Available ${max_withdrawal:.2f}"
                )
            if amount > self.capital.get(coin, 0.0):
                raise ValueError(
                    f"Insufficient capital: Requested ${amount:.2f}, Available ${self.capital[coin]:.2f}"
                )

            # Calculate fee and net amount
            amount_d = Decimal(str(amount))
            fee = amount_d * Decimal(str(self.WITHDRAWAL_FEE))
            fee = fee.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            net_withdrawal = amount_d - fee

            # Update state
            self.capital[coin] = float(Decimal(str(self.capital[coin])) - amount_d)
            self._update_user_withdrawals(user_id, coin, float(amount_d))
            self.save_state()

            logging.info(
                f"User {user_id} withdrew ${amount:.2f} from {coin} (Fee: ${float(fee):.2f}, Net: ${float(net_withdrawal):.2f})"
            )
            return {
                "gross_amount": float(amount_d),
                "fee": float(fee),
                "fee_percentage": self.WITHDRAWAL_FEE * 100,
                "net_amount": float(net_withdrawal),
            }

    def calculate_withdrawal(self, user_id, coin):
        """Calculate max withdrawal based on ownership percentage."""
        ownership_pct = self.get_user_ownership_percentage(user_id, coin)
        if ownership_pct <= 0:
            return 0.0
        total_value = self.capital.get(coin, 0.0) + (
            self.positions.get(coin, 0.0) * self.get_current_price(coin) or 0
        )
        return (ownership_pct / 100) * total_value

    def get_user_ownership_percentage(self, user_id, coin):
        """Calculate user's ownership percentage based on net investments."""
        coin = coin.lower()
        net_investment = self.get_user_investment(user_id, coin)
        if net_investment <= 0:
            return 0.0
        total_net = self.get_total_net_investments(coin)
        return (net_investment / total_net * 100) if total_net > 0 else 0.0

    def get_total_net_investments(self, coin):
        """Calculate total net investments for a coin."""
        coin = coin.lower()
        total = 0.0
        for user_id in self.user_investments.get(coin, {}):
            net = self.get_user_investment(user_id, coin)
            if net > 0:
                total += net
        return total

    def get_user_investment(self, user_id, coin):
        """Get user's net investment (deposits - withdrawals)."""
        coin = coin.lower()
        deposits = self.user_investments.get(coin, {}).get(user_id, 0.0)
        withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        return deposits - withdrawals

    # --- Trade Simulation Methods ---

    def simulate_buy(self, coin, quantity, price):
        """Simulate a buy trade with a 0.05% fee."""
        with self._lock:
            coin = coin.lower()
            self._ensure_coin_initialized(coin)
            qty_d = Decimal(str(quantity))
            price_d = Decimal(str(price))
            base_cost = qty_d * price_d
            fee = base_cost * Decimal(str(self.TRADING_FEE))
            total_cost = base_cost + fee

            if total_cost > Decimal(str(self.capital[coin])):
                logging.warning(
                    f"Insufficient capital for BUY {coin}: Need ${float(total_cost):.2f}"
                )
                return False

            self.capital[coin] = float(Decimal(str(self.capital[coin])) - total_cost)
            self.positions[coin] = float(
                Decimal(str(self.positions.get(coin, 0.0))) + qty_d
            )
            self.total_cost[coin] = float(
                Decimal(str(self.total_cost.get(coin, 0.0))) + total_cost
            )
            self._record_trade(coin, "buy", qty_d, price_d, base_cost, fee, total_cost)
            self.save_state()

            logging.info(
                f"BUY {float(qty_d)} {coin} at ${float(price_d):.2f}, Total: ${float(total_cost):.2f}"
            )
            return True

    def simulate_sell(self, coin, quantity, price):
        """Simulate a sell trade with a 0.05% fee."""
        with self._lock:
            coin = coin.lower()
            if self.positions.get(coin, 0.0) < quantity:
                logging.warning(f"Insufficient position for SELL {coin}")
                return False

            qty_d = Decimal(str(quantity))
            price_d = Decimal(str(price))
            base_proceeds = qty_d * price_d
            fee = base_proceeds * Decimal(str(self.TRADING_FEE))
            net_proceeds = base_proceeds - fee

            avg_cost = Decimal(str(self.total_cost[coin])) / Decimal(
                str(self.positions[coin])
            )
            profit = net_proceeds - (avg_cost * qty_d)

            self.capital[coin] = float(Decimal(str(self.capital[coin])) + net_proceeds)
            self.positions[coin] = float(Decimal(str(self.positions[coin])) - qty_d)
            self.total_cost[coin] = float(
                Decimal(str(self.total_cost[coin])) - (avg_cost * qty_d)
            )
            self.realized_profits[coin] = float(
                Decimal(str(self.realized_profits.get(coin, 0.0))) + profit
            )
            self._record_trade(
                coin, "sell", qty_d, price_d, base_proceeds, fee, net_proceeds, profit
            )

            if self.positions[coin] <= 0:
                del self.positions[coin]
                self.total_cost[coin] = 0.0

            self.save_state()
            logging.info(
                f"SELL {float(qty_d)} {coin} at ${float(price_d):.2f}, Profit: ${float(profit):.2f}"
            )
            return True

    # --- Information Retrieval Methods ---

    def get_position(self, coin):
        """Get quantity held for a coin."""
        return self.positions.get(coin.lower(), 0.0)

    def get_capital(self, coin):
        """Get current capital for a coin."""
        return self.capital.get(coin.lower(), 0.0)

    def get_total_capital(self):
        """Get total capital across all coins."""
        return sum(self.capital.values())

    def get_all_capitals(self):
        """Get capital for all coins, rounded to 2 decimals."""
        return {coin: round(capital, 2) for coin, capital in self.capital.items()}

    def get_coin_performance_summary(self, coin, current_price):
        """Get performance metrics for a coin."""
        coin = coin.lower()
        position_value = self.positions.get(coin, 0.0) * current_price
        total_value = self.capital.get(coin, 0.0) + position_value
        realized = self.realized_profits.get(coin, 0.0)
        net_investments = self.get_total_net_investments(coin)
        unrealized = total_value - (net_investments + realized)
        total_gains = realized + unrealized
        perf_pct = (total_gains / net_investments * 100) if net_investments > 0 else 0.0
        # Calculate net_deposits
        net_deposits = self.total_deposits.get(coin, 0.0) - self.total_withdrawals.get(
            coin, 0.0
        )

        return {
            "coin": coin.upper(),  # Restored from old version
            "total_deposits": self.total_deposits.get(coin, 0.0),
            "total_withdrawals": self.total_withdrawals.get(coin, 0.0),
            "net_deposits": net_deposits,  # Restored to fix KeyError
            "net_investments": net_investments,  # Equivalent to total_net_investments
            "current_capital": self.capital.get(coin, 0.0),
            "position_quantity": self.positions.get(
                coin, 0.0
            ),  # Restored from old version
            "position_value": position_value,
            "total_portfolio_value": total_value,  # Added alias for consistency
            "total_value": total_value,  # Keep new version's key
            "realized_profits": realized,
            "unrealized_gains": unrealized,
            "total_gains": total_gains,
            "performance_percentage": perf_pct,
        }

    def get_user_investment_details(self, user_id, coin, current_price):
        """Get detailed investment info for a user."""
        coin = coin.lower()
        if not self._user_has_investment(user_id, coin):
            return {
                "investment": 0.0,
                "ownership_percentage": 0.0,
                "current_share": 0.0,
            }

        net_investment = self.get_user_investment(user_id, coin)
        ownership_pct = self.get_user_ownership_percentage(user_id, coin)
        perf_summary = self.get_coin_performance_summary(coin, current_price)
        current_share = (ownership_pct / 100) * perf_summary["total_value"]
        realized_gains = (ownership_pct / 100) * perf_summary["realized_profits"]
        unrealized_gains = (ownership_pct / 100) * perf_summary["unrealized_gains"]
        total_gains = realized_gains + unrealized_gains
        perf_pct = (total_gains / net_investment * 100) if net_investment > 0 else 0.0

        return {
            "investment": net_investment,
            "ownership_percentage": ownership_pct,
            "current_share": current_share,
            "realized_gains": realized_gains,
            "unrealized_gains": unrealized_gains,
            "total_gains": total_gains,
            "performance_percentage": perf_pct,
        }

    # --- Utility Methods ---

    def get_current_price(self, coin: str) -> Optional[float]:
        """Fetch current price from CoinStatsService."""
        stats = CoinStatsService().get_latest_stats(coin)
        return stats.get("price") if stats else None

    def save_profit_snapshot(self):
        """Save a snapshot of profit metrics for all coins."""
        with self._lock:
            for coin in self.capital:
                price = self.get_current_price(coin)
                if price is None:
                    logging.warning(f"Could not fetch price for {coin}")
                    continue
                metrics = self.get_coin_performance_summary(coin, price)
                snapshot = {
                    "timestamp": datetime.utcnow(),
                    "coin": coin,
                    "price": price,
                    "metrics": metrics,
                }
                self.mongo_service.insert_profit_snapshot(snapshot)
                logging.info(f"Saved profit snapshot for {coin}")

    # --- Helper Methods ---

    def _ensure_coin_initialized(self, coin):
        """Initialize coin-related dictionaries if not present."""
        if coin not in self.capital:
            self.capital[coin] = 0.0
            self.positions[coin] = 0.0
            self.total_cost[coin] = 0.0
            self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
            self.realized_profits[coin] = 0.0
            self.user_investments[coin] = {}
            self.user_withdrawals[coin] = {}

    def _user_has_investment(self, user_id, coin):
        """Check if user has an investment in the coin."""
        return coin in self.user_investments and user_id in self.user_investments[coin]

    def _update_user_withdrawals(self, user_id, coin, amount):
        """Update withdrawal records for a user."""
        self.user_withdrawals[coin][user_id] = (
            self.user_withdrawals[coin].get(user_id, 0.0) + amount
        )
        self.total_withdrawals[coin] = self.total_withdrawals.get(coin, 0.0) + amount

    def _record_trade(
        self, coin, trade_type, qty, price, base, fee, total, profit=None
    ):
        """Record a trade in trade_records."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": trade_type,
            "quantity": float(qty),
            "price": float(price),
            "base": float(base),
            "fee": float(fee),
            "total": float(total),
        }
        if profit is not None:
            record["profit"] = float(profit)
        self.trade_records[coin]["trades"].append(record)
        if profit:
            self.trade_records[coin]["total_profit"] += float(profit)
