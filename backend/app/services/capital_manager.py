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

            max_withdrawal = self.calculate_withdrawal(user_id, coin)
            if amount > max_withdrawal:
                raise ValueError(
                    f"Insufficient withdrawable amount: Requested ${amount:.2f}, Available ${max_withdrawal:.2f}"
                )
            if amount > self.capital.get(coin, 0.0):
                raise ValueError(
                    f"Insufficient capital: Requested ${amount:.2f}, Available ${self.capital[coin]:.2f}"
                )

            amount_d = Decimal(str(amount))
            fee = amount_d * Decimal(str(self.WITHDRAWAL_FEE))
            fee = fee.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            net_withdrawal = amount_d - fee

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

        # Get current price with proper error handling
        current_price = self.get_current_price(coin)
        if current_price is None:
            logging.warning(
                f"Could not fetch current price for {coin}, using position value as 0"
            )
            current_price = 0.0

        position_value = self.positions.get(coin, 0.0) * current_price
        total_value = self.capital.get(coin, 0.0) + position_value

        max_withdrawal = (ownership_pct / 100) * total_value
        logging.debug(
            f"Withdrawal calculation for {user_id} in {coin}: ownership={ownership_pct:.2f}%, total_value=${total_value:.2f}, max_withdrawal=${max_withdrawal:.2f}"
        )

        return max_withdrawal

    def get_user_ownership_percentage(self, user_id, coin):
        """Calculate user's ownership percentage based on net investments."""
        coin = coin.lower()
        net_investment = self.get_user_investment(user_id, coin)
        if net_investment <= 0:
            return 0.0

        total_net = self.get_total_net_investments(coin)
        if total_net <= 0:
            logging.warning(
                f"Total net investments for {coin} is {total_net}, cannot calculate ownership percentage"
            )
            return 0.0

        ownership_pct = (net_investment / total_net) * 100
        logging.debug(
            f"User {user_id} ownership in {coin}: {ownership_pct:.2f}% (${net_investment:.2f} / ${total_net:.2f})"
        )

        return ownership_pct

    def get_total_net_investments(self, coin):
        """Calculate total net investments for a coin (including all users, even those with negative balances)."""
        coin = coin.lower()
        total_positive = 0.0
        total_negative = 0.0

        for user_id in self.user_investments.get(coin, {}):
            net = self.get_user_investment(user_id, coin)
            if net > 0:
                total_positive += net
            else:
                total_negative += abs(net)  # Track negative investments separately

        # Only return positive net investments for ownership calculations
        # but log if there are negative balances for transparency
        if total_negative > 0:
            logging.info(
                f"Coin {coin} has ${total_negative:.2f} in negative net investments from withdrawals"
            )

        return total_positive

    def get_user_investment(self, user_id, coin):
        """Get user's net investment (deposits - withdrawals)."""
        coin = coin.lower()
        deposits = self.user_investments.get(coin, {}).get(user_id, 0.0)
        withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        net_investment = deposits - withdrawals

        logging.debug(
            f"User {user_id} in {coin}: deposits=${deposits:.2f}, withdrawals=${withdrawals:.2f}, net=${net_investment:.2f}"
        )

        return net_investment

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
                    f"Insufficient capital for BUY {coin}: Need ${float(total_cost):.2f}, Available ${self.capital[coin]:.2f}"
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
                f"BUY {float(qty_d)} {coin} at ${float(price_d):.2f}, Fee: ${float(fee):.2f}, Total: ${float(total_cost):.2f}"
            )
            return True

    def simulate_sell(self, coin, quantity, price):
        """Simulate a sell trade with a 0.05% fee."""
        with self._lock:
            coin = coin.lower()
            if self.positions.get(coin, 0.0) < quantity:
                logging.warning(
                    f"Insufficient position for SELL {coin}: Need {quantity}, Available {self.positions.get(coin, 0.0)}"
                )
                return False

            qty_d = Decimal(str(quantity))
            price_d = Decimal(str(price))
            base_proceeds = qty_d * price_d
            fee = base_proceeds * Decimal(str(self.TRADING_FEE))
            net_proceeds = base_proceeds - fee

            # Calculate average cost per unit
            if self.positions[coin] > 0:
                avg_cost = Decimal(str(self.total_cost[coin])) / Decimal(
                    str(self.positions[coin])
                )
            else:
                avg_cost = Decimal("0")
                logging.warning(
                    f"No position found for {coin} but trying to sell - using avg_cost=0"
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

            # Clean up zero positions
            if self.positions[coin] <= 0:
                self.positions[coin] = 0.0
                self.total_cost[coin] = 0.0

            self.save_state()
            logging.info(
                f"SELL {float(qty_d)} {coin} at ${float(price_d):.2f}, Fee: ${float(fee):.2f}, Net: ${float(net_proceeds):.2f}, Profit: ${float(profit):.2f}"
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

    def get_total_fees_paid(self, coin):
        """Calculate total fees paid for a coin from trade records."""
        coin = coin.lower()
        trades = self.trade_records.get(coin, {}).get("trades", [])
        total_fees = sum(trade.get("fee", 0.0) for trade in trades)
        return total_fees

    def get_coin_performance_summary(self, coin, current_price=None):
        """Get performance metrics for a coin with improved calculations."""
        coin = coin.lower()

        # Get current price with proper error handling
        if current_price is None:
            current_price = self.get_current_price(coin)
            if current_price is None:
                logging.warning(f"Could not fetch current price for {coin}, using 0.0")
                current_price = 0.0

        # Basic values
        cash = self.capital.get(coin, 0.0)
        position_qty = self.positions.get(coin, 0.0)
        position_value = position_qty * current_price
        total_portfolio_value = cash + position_value

        # Investment tracking
        total_deposits = self.total_deposits.get(coin, 0.0)
        total_withdrawals = self.total_withdrawals.get(coin, 0.0)
        net_deposits = total_deposits - total_withdrawals
        net_investments = self.get_total_net_investments(coin)

        # Profit calculations
        realized_profits = self.realized_profits.get(coin, 0.0)
        total_fees_paid = self.get_total_fees_paid(coin)

        # Unrealized gains: current portfolio value minus what we put in (net investments) minus what we've already realized
        # This accounts for the fact that realized profits are already "extracted" value
        unrealized_gains = total_portfolio_value - net_investments - realized_profits

        # Total gains
        total_gains = realized_profits + unrealized_gains

        # Performance percentage (avoid division by zero)
        if net_investments > 0:
            performance_percentage = (total_gains / net_investments) * 100
        else:
            performance_percentage = 0.0
            if total_gains != 0:
                logging.warning(
                    f"Coin {coin} has {total_gains:.2f} in gains but 0 net investments - performance calculation may be misleading"
                )

        # Validate calculations
        self._validate_coin_calculations(
            coin,
            {
                "cash": cash,
                "position_value": position_value,
                "total_portfolio_value": total_portfolio_value,
                "net_investments": net_investments,
                "realized_profits": realized_profits,
                "unrealized_gains": unrealized_gains,
                "total_gains": total_gains,
                "total_fees_paid": total_fees_paid,
            },
        )

        return {
            "coin": coin.upper(),
            "current_price": current_price,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net_deposits": net_deposits,
            "net_investments": net_investments,
            "current_capital": cash,
            "position_quantity": position_qty,
            "position_value": position_value,
            "total_portfolio_value": total_portfolio_value,
            "realized_profits": realized_profits,
            "unrealized_gains": unrealized_gains,
            "total_gains": total_gains,
            "performance_percentage": performance_percentage,
            "total_fees_paid": total_fees_paid,
            "fee_impact_percentage": (
                (total_fees_paid / net_investments * 100)
                if net_investments > 0
                else 0.0
            ),
        }

    def get_user_investment_details(self, user_id, coin, current_price=None):
        """Get detailed investment info for a user with improved calculations."""
        coin = coin.lower()

        if not self._user_has_investment(user_id, coin):
            return {
                "user_id": user_id,
                "coin": coin.upper(),
                "total_deposits": 0.0,
                "total_withdrawals": 0.0,
                "net_investment": 0.0,
                "ownership_percentage": 0.0,
                "current_share_value": 0.0,
                "profit_loss": 0.0,
                "realized_gains_share": 0.0,
                "unrealized_gains_share": 0.0,
                "total_gains": 0.0,
                "performance_percentage": 0.0,
                "fees_paid_share": 0.0,
                "portfolio_breakdown": {
                    "cash_portion": 0.0,
                    "position_portion": 0.0,
                    "total_portfolio_value": 0.0,
                },
                "has_active_investment": False,
            }

        # Get current price
        if current_price is None:
            current_price = self.get_current_price(coin)
            if current_price is None:
                logging.warning(f"Could not fetch current price for {coin}, using 0.0")
                current_price = 0.0

        # User's investment details
        total_deposits = self.user_investments[coin].get(user_id, 0.0)
        total_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        net_investment = total_deposits - total_withdrawals

        # Ownership percentage
        ownership_pct = self.get_user_ownership_percentage(user_id, coin)

        # Get coin performance summary
        coin_summary = self.get_coin_performance_summary(coin, current_price)

        # Calculate user's share of everything
        total_portfolio_value = coin_summary["total_portfolio_value"]
        current_share_value = (ownership_pct / 100) * total_portfolio_value

        # User's share of gains/losses
        realized_gains_share = (ownership_pct / 100) * coin_summary["realized_profits"]
        unrealized_gains_share = (ownership_pct / 100) * coin_summary[
            "unrealized_gains"
        ]
        total_gains = realized_gains_share + unrealized_gains_share

        # User's share of fees paid
        fees_paid_share = (ownership_pct / 100) * coin_summary["total_fees_paid"]

        # Profit/loss calculation
        profit_loss = current_share_value - net_investment

        # Performance percentage for this user
        if net_investment > 0:
            performance_percentage = (total_gains / net_investment) * 100
        else:
            performance_percentage = 0.0
            if total_gains != 0:
                logging.warning(
                    f"User {user_id} in {coin} has {total_gains:.2f} in gains but {net_investment:.2f} net investment"
                )

        # Portfolio breakdown
        cash_portion = (ownership_pct / 100) * coin_summary["current_capital"]
        position_portion = (ownership_pct / 100) * coin_summary["position_value"]

        return {
            "user_id": user_id,
            "coin": coin.upper(),
            "current_price": current_price,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net_investment": net_investment,
            "ownership_percentage": ownership_pct,
            "current_share_value": current_share_value,
            "profit_loss": profit_loss,
            "realized_gains_share": realized_gains_share,
            "unrealized_gains_share": unrealized_gains_share,
            "total_gains": total_gains,
            "performance_percentage": performance_percentage,
            "fees_paid_share": fees_paid_share,
            "fee_impact_percentage": (
                (fees_paid_share / net_investment * 100) if net_investment > 0 else 0.0
            ),
            "portfolio_breakdown": {
                "cash_portion": cash_portion,
                "position_portion": position_portion,
                "total_portfolio_value": total_portfolio_value,
            },
            "has_active_investment": net_investment > 0,
        }

    # --- Utility Methods ---

    def get_current_price(self, coin: str) -> Optional[float]:
        """Fetch current price from CoinStatsService with proper error handling."""
        try:
            stats = CoinStatsService().get_latest_stats(coin)
            price = stats.get("price") if stats else None

            if price is None:
                logging.warning(f"No price data available for {coin}")
                return None

            if not isinstance(price, (int, float)) or price < 0:
                logging.warning(f"Invalid price data for {coin}: {price}")
                return None

            return float(price)

        except Exception as e:
            logging.error(f"Error fetching price for {coin}: {e}")
            return None

    def save_profit_snapshot(self):
        """Save a comprehensive snapshot of profit metrics for all coins."""
        with self._lock:
            snapshot_time = datetime.utcnow()

            for coin in self.capital:
                try:
                    current_price = self.get_current_price(coin)
                    if current_price is None:
                        logging.warning(
                            f"Skipping snapshot for {coin} - no price available"
                        )
                        continue

                    metrics = self.get_coin_performance_summary(coin, current_price)

                    # Additional metrics
                    trades = self.trade_records.get(coin, {}).get("trades", [])
                    total_trades = len(trades)

                    snapshot = {
                        "timestamp": snapshot_time,
                        "coin": coin,
                        "price": current_price,
                        "global": {
                            "total_deposits": metrics["total_deposits"],
                            "total_withdrawals": metrics["total_withdrawals"],
                            "net_deposits": metrics["net_deposits"],
                            "total_net_investments": metrics["net_investments"],
                            "current_capital": metrics["current_capital"],
                            "position_quantity": metrics["position_quantity"],
                            "position_value": metrics["position_value"],
                            "total_portfolio_value": metrics["total_portfolio_value"],
                            "realized_profits": metrics["realized_profits"],
                            "unrealized_gains": metrics["unrealized_gains"],
                            "total_gains": metrics["total_gains"],
                            "performance_percentage": metrics["performance_percentage"],
                            "total_trades": total_trades,
                            "total_fees_paid": metrics["total_fees_paid"],
                            "fee_impact_percentage": metrics["fee_impact_percentage"],
                        },
                    }

                    self.mongo_service.insert_profit_snapshot(snapshot)
                    logging.info(f"Saved comprehensive profit snapshot for {coin}")

                except Exception as e:
                    logging.error(f"Error saving snapshot for {coin}: {e}")

    def _validate_coin_calculations(self, coin, metrics):
        """Validate internal consistency of calculations."""
        try:
            # Check for obvious inconsistencies
            if metrics["total_portfolio_value"] < 0:
                logging.error(
                    f"Negative portfolio value for {coin}: {metrics['total_portfolio_value']}"
                )

            if metrics["cash"] < 0:
                logging.warning(f"Negative cash balance for {coin}: {metrics['cash']}")

            if metrics["position_value"] < 0:
                logging.warning(
                    f"Negative position value for {coin}: {metrics['position_value']}"
                )

            # Log significant discrepancies
            expected_total = metrics["cash"] + metrics["position_value"]
            if abs(expected_total - metrics["total_portfolio_value"]) > 0.01:
                logging.warning(
                    f"Portfolio value mismatch for {coin}: expected {expected_total}, got {metrics['total_portfolio_value']}"
                )

        except Exception as e:
            logging.error(f"Error validating calculations for {coin}: {e}")

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
            self.total_deposits[coin] = 0.0
            self.total_withdrawals[coin] = 0.0

    def _user_has_investment(self, user_id, coin):
        """Check if user has an investment in the coin."""
        return coin in self.user_investments and user_id in self.user_investments[coin]

    def _update_user_withdrawals(self, user_id, coin, amount):
        """Update withdrawal records for a user."""
        if coin not in self.user_withdrawals:
            self.user_withdrawals[coin] = {}

        self.user_withdrawals[coin][user_id] = (
            self.user_withdrawals[coin].get(user_id, 0.0) + amount
        )
        self.total_withdrawals[coin] = self.total_withdrawals.get(coin, 0.0) + amount

    def _record_trade(
        self, coin, trade_type, qty, price, base, fee, total, profit=None
    ):
        """Record a trade with detailed attributes."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "type": trade_type,
            "quantity": float(qty),
            "price": float(price),
            "fee": float(fee),
            "fee_percentage": self.TRADING_FEE * 100,
        }

        if trade_type == "buy":
            record.update(
                {
                    "base_cost": float(base),
                    "total_cost": float(total),
                }
            )
        elif trade_type == "sell":
            record.update(
                {
                    "base_proceeds": float(base),
                    "net_proceeds": float(total),
                    "profit": float(profit) if profit is not None else 0.0,
                }
            )

        self.trade_records[coin]["trades"].append(record)

        if profit is not None:
            self.trade_records[coin]["total_profit"] += float(profit)
