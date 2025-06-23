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
        self.capital = {}  # Current capital per coin
        self.positions = {}  # Quantity held per coin
        self.total_cost = {}  # Total cost of positions per coin
        self.trade_records = {}  # Trade history per coin
        self.user_investments = {}  # {coin: {user_id: total_deposit}}
        self.user_withdrawals = {}  # {coin: {user_id: total_withdrawn}}
        self.total_deposits = {}  # {coin: total_deposits}
        self.total_withdrawals = {}  # {coin: total_withdrawals}
        self.realized_profits = {}  # {coin: total_realized_profit}
        self.load_state()

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
            self.realized_profits = state.get("realized_profits", {})
            logging.info("Loaded trading state from database.")
        except Exception as e:
            logging.error(f"Failed to load state from MongoDB: {e}")
            self.capital = {}
            self.positions = {}
            self.total_cost = {}
            self.trade_records = {}
            self.user_investments = {}
            self.user_withdrawals = {}
            self.total_deposits = {}
            self.total_withdrawals = {}
            self.realized_profits = {}

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
            if coin not in self.user_investments:
                self.user_investments[coin] = {}
            if coin not in self.user_withdrawals:
                self.user_withdrawals[coin] = {}

            self.user_investments[coin][user_id] = (
                self.user_investments[coin].get(user_id, 0.0) + amount
            )
            self.total_deposits[coin] = self.total_deposits.get(coin, 0.0) + amount
            self.capital[coin] = self.capital.get(coin, 0.0) + amount

            if coin not in self.trade_records:
                self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
            if coin not in self.realized_profits:
                self.realized_profits[coin] = 0.0

            self.save_state()
            logging.info(
                f"User {user_id} deposited ${amount:.2f} to {coin}. Total deposits: ${self.total_deposits[coin]:.2f}, Current capital: ${self.capital[coin]:.2f}"
            )

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
                    f"Insufficient withdrawable amount for {coin}: Requested ${amount:.2f}, Available ${withdrawal_amount:.2f}"
                )

            available_capital = self.capital.get(coin, 0.0)
            if amount > available_capital:
                raise ValueError(
                    f"Insufficient capital for {coin}: Requested ${amount:.2f}, Available ${available_capital:.2f}"
                )

            amount = Decimal(str(amount))
            fee_rate = Decimal(str(self.WITHDRAWAL_FEE))  # 0.0005
            fee = (amount * fee_rate).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            net_withdrawal = (amount - fee).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )

            capital_decimal = Decimal(str(self.capital.get(coin, 0.0)))
            capital_decimal -= amount
            self.capital[coin] = float(capital_decimal)

            if coin not in self.user_withdrawals:
                self.user_withdrawals[coin] = {}
            self.user_withdrawals[coin][user_id] = self.user_withdrawals[coin].get(
                user_id, 0.0
            ) + float(amount)
            self.total_withdrawals[coin] = self.total_withdrawals.get(
                coin, 0.0
            ) + float(amount)

            self.save_state()

            logging.info(
                f"User {user_id} withdrew ${float(amount):.2f} from {coin} "
                f"(Fee: ${float(fee):.2f} [0.05%], Net: ${float(net_withdrawal):.2f}). "
                f"Remaining capital: ${self.capital[coin]:.2f}"
            )

            return {
                "gross_amount": float(amount),
                "fee": float(fee),
                "fee_percentage": float(self.WITHDRAWAL_FEE * 100),
                "net_amount": float(net_withdrawal),
            }

    def calculate_withdrawal(self, user_id, coin):
        """Calculate the withdrawal amount based on user's ownership percentage of current total value."""
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

    def get_user_investment_details(self, user_id, coin, current_price):
        """Retrieve comprehensive investment details for a user and a specific coin."""
        coin = coin.lower()

        if (
            coin not in self.user_investments
            or user_id not in self.user_investments[coin]
        ):
            return {
                "investment": 0.0,
                "ownership_percentage": 0.0,
                "current_share": 0.0,
                "profit_loss": 0.0,
                "realized_gains": 0.0,
                "unrealized_gains": 0.0,
                "total_gains": 0.0,
                "performance_percentage": 0.0,
            }

        user_investment = self.user_investments[coin][user_id]
        user_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        total_deposits = self.total_deposits.get(coin, 0.0)

        if total_deposits == 0:
            return {
                "investment": user_investment,
                "original_investment": user_investment,
                "total_deposits": user_investment,
                "total_withdrawals": user_withdrawals,
                "net_investment": user_investment - user_withdrawals,
                "ownership_percentage": 0.0,
                "current_share": 0.0,
                "profit_loss": 0.0,
                "realized_gains": 0.0,
                "unrealized_gains": 0.0,
                "total_gains": 0.0,
                "performance_percentage": 0.0,
            }

        ownership_percentage = (user_investment / total_deposits) * 100
        position_value = self.positions.get(coin, 0.0) * current_price
        total_portfolio_value = self.capital.get(coin, 0.0) + position_value
        current_share = (ownership_percentage / 100) * total_portfolio_value
        net_investment = user_investment - user_withdrawals
        total_realized_profit = self.realized_profits.get(coin, 0.0)
        user_realized_gains = (ownership_percentage / 100) * total_realized_profit
        expected_value_without_unrealized = total_deposits + total_realized_profit
        total_unrealized_gains = (
            total_portfolio_value - expected_value_without_unrealized
        )
        user_unrealized_gains = (ownership_percentage / 100) * total_unrealized_gains
        total_user_gains = user_realized_gains + user_unrealized_gains
        performance_percentage = (
            (total_user_gains / net_investment * 100) if net_investment > 0 else 0.0
        )
        profit_loss = current_share - net_investment

        return {
            "investment": net_investment,
            "original_investment": user_investment,
            "total_deposits": user_investment,
            "total_withdrawals": user_withdrawals,
            "net_investment": net_investment,
            "ownership_percentage": ownership_percentage,
            "current_share": current_share,
            "profit_loss": profit_loss,
            "realized_gains": user_realized_gains,
            "unrealized_gains": user_unrealized_gains,
            "total_gains": total_user_gains,
            "performance_percentage": performance_percentage,
            "portfolio_breakdown": {
                "cash_portion": (ownership_percentage / 100)
                * self.capital.get(coin, 0.0),
                "position_portion": (ownership_percentage / 100) * position_value,
                "total_portfolio_value": total_portfolio_value,
            },
        }

    def get_user_investment(self, user_id, coin):
        """Get the user's net investment (total deposits - withdrawals) for a specific coin."""
        coin = coin.lower()
        total_deposits = self.user_investments.get(coin, {}).get(user_id, 0.0)
        total_withdrawals = self.user_withdrawals.get(coin, {}).get(user_id, 0.0)
        return total_deposits - total_withdrawals

    def simulate_buy(self, coin, quantity, price):
        """Simulate a buy trade with 0.05% trading fee."""
        with self._lock:
            coin = coin.lower()
            if coin not in self.capital:
                self.capital[coin] = 0.0
                self.trade_records[coin] = {"trades": [], "total_profit": 0.0}
                self.realized_profits[coin] = 0.0

            quantity = Decimal(str(quantity))
            price = Decimal(str(price))
            base_cost = quantity * price
            fee_amount = (base_cost * Decimal(str(self.TRADING_FEE))).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )
            total_cost = base_cost + fee_amount

            capital_decimal = Decimal(str(self.capital.get(coin, 0.0)))
            if total_cost > capital_decimal:
                logging.warning(
                    f"Insufficient capital for BUY {coin}: Need ${float(total_cost):.2f}, have ${float(capital_decimal):.2f}"
                )
                return False

            capital_decimal -= total_cost
            self.capital[coin] = float(capital_decimal)

            positions_decimal = Decimal(str(self.positions.get(coin, 0.0)))
            positions_decimal += quantity
            self.positions[coin] = float(positions_decimal)

            total_cost_decimal = Decimal(str(self.total_cost.get(coin, 0.0)))
            total_cost_decimal += total_cost
            self.total_cost[coin] = float(total_cost_decimal)

            self.trade_records[coin]["trades"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "buy",
                    "quantity": float(quantity),
                    "price": float(price),
                    "base_cost": float(base_cost),
                    "fee": float(fee_amount),
                    "fee_percentage": float(self.TRADING_FEE * 100),
                    "total_cost": float(total_cost),
                }
            )
            self.save_state()

            logging.info(
                f"Simulated BUY of {float(quantity)} {coin} at ${float(price):.2f}. "
                f"Total cost: ${float(total_cost):.2f} (Base: ${float(base_cost):.2f}, Fee: ${float(fee_amount):.2f} [0.05%])"
            )
            return True

    def simulate_sell(self, coin, quantity, price):
        """Simulate a sell trade with 0.05% trading fee."""
        with self._lock:
            coin = coin.lower()
            if coin not in self.positions or self.positions[coin] < quantity:
                logging.warning(
                    f"Insufficient position for SELL {coin}: Have {self.positions.get(coin, 0.0)}, need {quantity}"
                )
                return False

            quantity = Decimal(str(quantity))
            price = Decimal(str(price))
            base_proceeds = quantity * price
            fee_amount = (base_proceeds * Decimal(str(self.TRADING_FEE))).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )
            net_proceeds = base_proceeds - fee_amount

            original_quantity = Decimal(str(self.positions[coin]))
            average_cost = (
                Decimal(str(self.total_cost[coin])) / original_quantity
                if original_quantity > 0
                else Decimal("0")
            )
            trade_profit = net_proceeds - (average_cost * quantity)

            capital_decimal = Decimal(str(self.capital.get(coin, 0.0)))
            capital_decimal += net_proceeds
            self.capital[coin] = float(capital_decimal)

            positions_decimal = Decimal(str(self.positions[coin]))
            positions_decimal -= quantity
            if positions_decimal <= 0:
                del self.positions[coin]
                self.total_cost[coin] = 0.0
            else:
                self.positions[coin] = float(positions_decimal)
                cost_removed = (quantity / original_quantity) * Decimal(
                    str(self.total_cost[coin])
                )
                self.total_cost[coin] = float(
                    Decimal(str(self.total_cost[coin])) - cost_removed
                )

            self.realized_profits[coin] = self.realized_profits.get(coin, 0.0) + float(
                trade_profit
            )

            self.trade_records[coin]["trades"].append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "type": "sell",
                    "quantity": float(quantity),
                    "price": float(price),
                    "base_proceeds": float(base_proceeds),
                    "fee": float(fee_amount),
                    "fee_percentage": float(self.TRADING_FEE * 100),
                    "net_proceeds": float(net_proceeds),
                    "profit": float(trade_profit),
                }
            )
            self.trade_records[coin]["total_profit"] += float(trade_profit)
            self.save_state()

            logging.info(
                f"Simulated SELL of {float(quantity)} {coin} at ${float(price):.2f}. "
                f"Net proceeds: ${float(net_proceeds):.2f} (Base: ${float(base_proceeds):.2f}, Fee: ${float(fee_amount):.2f} [0.05%]), Profit: ${float(trade_profit):.2f}"
            )
            return True

    def reset_state(self):
        """Reset the entire state and clear from database."""
        with self._lock:
            # Reset all instance variables
            self.capital = {}
            self.positions = {}
            self.total_cost = {}
            self.trade_records = {}
            self.user_investments = {}
            self.user_withdrawals = {}
            self.total_deposits = {}
            self.total_withdrawals = {}
            self.realized_profits = {}

            # Save the empty state to database
            self.save_state()

            logging.info("CapitalManager state has been completely reset")

    @classmethod
    def force_reset_singleton(cls):
        """Force reset the singleton instance. Use with caution!"""
        with cls._lock:
            if cls._instance is not None:
                logging.info("Forcing singleton reset...")
                cls._instance = None
                logging.info("Singleton instance reset complete")

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

    def get_coin_performance_summary(self, coin, current_price):
        """Get overall performance summary for a specific coin."""
        coin = coin.lower()

        total_deposits = self.total_deposits.get(coin, 0.0)
        total_withdrawals = self.total_withdrawals.get(coin, 0.0)
        current_capital = self.capital.get(coin, 0.0)
        position_quantity = self.positions.get(coin, 0.0)
        position_value = position_quantity * current_price
        total_portfolio_value = current_capital + position_value
        realized_profits = self.realized_profits.get(coin, 0.0)

        expected_value_without_unrealized = total_deposits + realized_profits
        unrealized_gains = total_portfolio_value - expected_value_without_unrealized

        net_deposits = total_deposits - total_withdrawals

        total_gains = realized_profits + unrealized_gains
        performance_percentage = (
            (total_gains / total_deposits * 100) if total_deposits > 0 else 0.0
        )

        return {
            "coin": coin.upper(),
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "net_deposits": net_deposits,
            "current_capital": current_capital,
            "position_quantity": position_quantity,
            "position_value": position_value,
            "total_portfolio_value": total_portfolio_value,
            "realized_profits": realized_profits,
            "unrealized_gains": unrealized_gains,
            "total_gains": total_gains,
            "performance_percentage": performance_percentage,
        }

    def get_detailed_performance(self, coin, current_price):
        """Get detailed performance metrics including fee impact for a specific coin."""
        coin = coin.lower()

        # Get basic performance metrics
        basic_perf = self.get_coin_performance_summary(coin, current_price)

        # Get trade records for the coin
        trades = self.trade_records.get(coin, {}).get("trades", [])

        # Calculate total number of trades
        total_trades = len(trades)

        # Calculate total fees paid from all trades
        total_fees_paid = sum(trade.get("fee", 0.0) for trade in trades)

        # Return basic performance plus additional metrics
        return {
            **basic_perf,
            "total_trades": total_trades,
            "total_fees_paid": total_fees_paid,
        }
