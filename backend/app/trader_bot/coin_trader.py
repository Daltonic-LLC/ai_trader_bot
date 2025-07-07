from app.trader_bot.llm_handler import LLMHandler
from app.trader_bot.data_handler import DataHandler
from app.trader_bot.model_handler import ModelHandler
from app.trader_bot.news_handler import NewsHandler
from app.services.coin_stats import CoinStatsService
from app.services.coin_news import NewsSentimentService
from app.services.coin_history import CoinHistory
from config import config
import os
import json
from datetime import datetime
import time


class CoinTrader:
    def __init__(
        self,
        coin,
        override,
        capital_manager,
        activities_file_path="data/activities/coin_reports.json",
        skip_history_download=False,
    ):
        self.coin = coin.lower()
        self.override = override
        self.capital_manager = capital_manager
        self.activities_file_path = activities_file_path
        self.skip_history_download = skip_history_download
        self.ensure_directory_exists()
        self.history_service = CoinHistory()
        self.stats_service = CoinStatsService()
        self.news_service = NewsSentimentService()
        self.llm_handler = LLMHandler(
            base_url=config.chat_endpoint,
            model=config.chat_model,
            temperature=0.4,
            timeout=60,
        )
        self.data_handler = DataHandler(
            self.history_service,
            self.coin,
            self.override,
            skip_download=self.skip_history_download,
        )
        self.model_handler = ModelHandler()
        self.news_handler = NewsHandler(
            self.news_service, self.coin, self.override, self.llm_handler
        )
        self.trading_fee = 0.001
        self.stop_loss_percentage = 0.015
        self.trade_percentage = 0.6
        self.min_capital_threshold = 10.0
        self.stop_loss_price = None
        self.highest_price = None
        self.last_trade_time = 0
        self.last_sell_time = 0
        self.cool_down = 900
        self.profit_target = 0.03
        self.sell_of_after_days = 3

    ### Utility Methods
    def withdraw(self, user_id):
        """Withdraw the user's share of the capital for this coin."""
        return self.capital_manager.withdraw(user_id, self.coin)

    def ensure_directory_exists(self):
        """Ensure the directory for activities file exists."""
        directory = os.path.dirname(self.activities_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_activities(self):
        """Load existing activities from the JSON file."""
        if os.path.exists(self.activities_file_path):
            try:
                with open(self.activities_file_path, "r") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading activities: {e}")
                return {}
        return {}

    def save_activities(self, data):
        """Save activities data to the JSON file."""
        try:
            self.ensure_directory_exists()
            with open(self.activities_file_path, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving activities: {e}")

    def save_activity(self, report):
        """Save the latest report for the coin."""
        data = self.load_activities()
        data[self.coin] = {"timestamp": datetime.now().isoformat(), "report": report}
        self.save_activities(data)

    def get_report(self, coin):
        """Retrieve the latest report for a coin."""
        data = self.load_activities()
        return data.get(coin.lower(), None)

    ### Data and Prediction Methods
    def load_and_prepare_data(self):
        """Load historical data and prepare features."""
        df = self.data_handler.load_historical_data()
        return self.data_handler.prepare_features(df)

    def train_and_predict(self, df_features):
        """Train the model and predict the close price."""
        model, feature_cols = self.model_handler.train_model(df_features)
        return self.model_handler.predict_close(model, df_features, feature_cols)

    def fetch_coin_stats(self):
        """Fetch current stats for the coin."""
        return self.stats_service.fetch_coin_stats(self.coin)

    def process_news(self):
        """Process news sentiment and text."""
        return self.news_handler.process_news()

    ### Trading Strategy Methods
    def calculate_signal_strength(self, news_sentiment, predicted_close, current_price):
        """Calculate signal strength based on news and price movement."""
        price_signal = (predicted_close - current_price) / current_price
        if price_signal > 0.05 and news_sentiment > 0.5:
            return 0.9
        elif price_signal > 0.02 or news_sentiment > 0.3:
            return 0.7
        return 0.5

    def calculate_position_size(self, capital, current_price, signal_strength):
        """Determine trade capital based on signal strength."""
        if signal_strength > 0.8:
            return capital * 0.8
        elif signal_strength > 0.6:
            return capital * 0.6
        return capital * 0.4

    def tiered_sell_strategy(self, position, current_price, profit_margin):
        """Decide sell quantity based on profit margin."""
        if profit_margin >= 0.05:
            return position * 0.5
        elif profit_margin >= 0.03:
            return position * 0.3
        elif profit_margin >= 0.01:
            return position * 0.1
        return 0

    def calculate_market_volatility(self, df, periods=30):
        """Calculate volatility from recent price changes."""
        if len(df) < periods:
            return 0.05
        recent_df = df.tail(periods)
        returns = recent_df["close"].pct_change().dropna()
        return returns.std()

    def dynamic_stop_loss(self, current_price, avg_cost, volatility):
        """Adjust stop-loss based on volatility."""
        base_stop = self.stop_loss_percentage
        if volatility > 0.1:
            return avg_cost * (1 - (base_stop * 1.5))
        elif volatility < 0.05:
            return avg_cost * (1 - (base_stop * 0.8))
        return avg_cost * (1 - base_stop)

    def check_stop_loss(self, current_price):
        """Check if stop-loss triggers and simulate a sell."""
        position = self.capital_manager.get_position(self.coin)
        if position <= 0 or (
            self.stop_loss_price is None and self.highest_price is None
        ):
            return None

        df = self.data_handler.load_historical_data()
        volatility = self.calculate_market_volatility(df)
        avg_cost = (
            self.capital_manager.total_cost.get(self.coin, 0) / position
            if position > 0
            else 0
        )
        dynamic_stop_price = self.dynamic_stop_loss(current_price, avg_cost, volatility)

        if current_price <= dynamic_stop_price or (
            self.highest_price
            and current_price <= self.highest_price * (1 - self.stop_loss_percentage)
        ):
            sell_quantity = position * 0.5
            if self.capital_manager.simulate_sell(
                self.coin, sell_quantity, current_price
            ):
                sale_value = sell_quantity * current_price * (1 - self.trading_fee)
                self.last_sell_time = time.time()
                self.last_trade_time = time.time()
                return f"Stop-loss triggered: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}"
        return None

    def generate_potential_trade_details(self, stats, predicted_close):
        """Generate details for potential trades."""
        current_price = stats["price"]
        position = self.capital_manager.get_position(self.coin)
        trade_details = ""

        if position == 0.0:
            capital = self.capital_manager.get_capital(self.coin)
            trade_capital = capital * self.trade_percentage
            quantity = trade_capital / current_price * (1 - self.trading_fee)
            if quantity > 0:
                stop_loss_price = current_price * (1 - self.stop_loss_percentage)
                potential_sale_value = (
                    quantity * predicted_close * (1 - self.trading_fee)
                )
                potential_profit = potential_sale_value - trade_capital
                trade_details += (
                    f"Potential BUY:\n"
                    f"- Quantity: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                    f"- Capital Used: ${trade_capital:.2f}\n"
                    f"- Stop-Loss: ${stop_loss_price:.2f}\n"
                    f"- Potential Profit: ${potential_profit:.2f}"
                )
            else:
                trade_details += "Potential BUY: Insufficient capital."
        elif position > 0.0:
            sale_value = position * current_price * (1 - self.trading_fee)
            trade_details += (
                f"Potential SELL:\n"
                f"- Quantity: {position:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                f"- Net Proceeds: ${sale_value:.2f}"
            )
        else:
            trade_details = "No trade possible."
        return trade_details.strip()

    ### Trade Execution Methods
    def execute_buy(self, capital, current_price, signal_strength):
        """Execute a buy trade."""
        trade_capital = self.calculate_position_size(
            capital, current_price, signal_strength
        )
        quantity = trade_capital / (current_price * (1 + self.trading_fee))
        if self.capital_manager.simulate_buy(self.coin, quantity, current_price):
            self.stop_loss_price = current_price * (1 - self.stop_loss_percentage)
            self.highest_price = current_price
            self.last_trade_time = time.time()
            return (
                f"Simulated BUY: {quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nAction: Manually buy on an exchange.",
                quantity,
            )
        return "BUY failed: Insufficient capital.", 0.0

    def execute_sell(self, position, current_price, profit_margin):
        """Execute a sell trade."""
        sell_quantity = self.tiered_sell_strategy(
            position, current_price, profit_margin
        )
        if sell_quantity > 0 and self.capital_manager.simulate_sell(
            self.coin, sell_quantity, current_price
        ):
            sale_value = sell_quantity * current_price * (1 - self.trading_fee)
            self.last_trade_time = time.time()
            self.last_sell_time = time.time()
            return (
                f"Tiered SELL: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}",
                sell_quantity,
            )
        return f"HOLD: Profit margin {profit_margin:.2%} below threshold.", 0.0

    def periodic_sell(self, position, current_price):
        """Perform a periodic sell if time threshold is met."""
        if (
            position > 0
            and time.time() - self.last_sell_time > self.sell_of_after_days * 24 * 3600
        ):
            sell_quantity = position * 0.1
            if self.capital_manager.simulate_sell(
                self.coin, sell_quantity, current_price
            ):
                sale_value = sell_quantity * current_price * (1 - self.trading_fee)
                self.last_sell_time = time.time()
                self.last_trade_time = time.time()
                return (
                    f"\nPeriodic SELL: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}",
                    sell_quantity,
                )
        return "", 0.0

    def execute_trade(
        self, recommendation, current_price, predicted_close, news_sentiment
    ):
        """Execute trade based on recommendation."""
        capital = self.capital_manager.get_capital(self.coin)
        position = self.capital_manager.get_position(self.coin)

        if time.time() - self.last_trade_time < self.cool_down:
            return "Cool-down active, no trade executed.", 0.0

        signal_strength = self.calculate_signal_strength(
            news_sentiment, predicted_close, current_price
        )
        if recommendation == "BUY" and capital > 0:
            trade_details, quantity = self.execute_buy(
                capital, current_price, signal_strength
            )
        elif recommendation == "SELL" and position > 0:
            avg_cost = (
                self.capital_manager.total_cost.get(self.coin, 0) / position
                if position > 0
                else 0
            )
            profit_margin = (current_price - avg_cost) / avg_cost if avg_cost > 0 else 0
            trade_details, quantity = self.execute_sell(
                position, current_price, profit_margin
            )
        else:
            trade_details, quantity = (
                f"No trade executed (Recommendation: {recommendation}).",
                0.0,
            )

        periodic_details, periodic_quantity = self.periodic_sell(
            position, current_price
        )
        trade_details += periodic_details
        quantity += periodic_quantity

        return trade_details, quantity

    ### Report Generation
    def generate_report(
        self,
        stats,
        predicted_close,
        news_sentiment,
        news_text,
        recommendation=None,
        trade_details=None,
    ):
        """Generate a detailed trading report."""
        price = stats.get("price", "N/A")
        price_str = f"${price:.2f}" if isinstance(price, float) else price
        report = f"""
        Report for {self.coin.upper()}:
        - Current Price: {price_str}
        - Predicted Close: ${predicted_close:.2f}
        - News Sentiment: {news_sentiment:.2f}
        - News Text: {news_text}
        - Capital: ${self.capital_manager.get_capital(self.coin):.2f}
        """
        if recommendation:
            report += f"- Recommendation: {recommendation}\n"
        if trade_details:
            report += f"Trade Details:\n{trade_details}\n"
        full_report = report.strip()

        summary = f"{self.coin.upper()} | Price: {price_str} | Predicted: ${predicted_close:.2f}"
        if recommendation:
            summary += f" | {recommendation}"
        summary_report = summary

        return full_report, summary_report

    ### Main Execution
    def run(self):
        """Execute the trading process."""
        self.capital_manager.load_state()

        df_features = self.load_and_prepare_data()
        predicted_close, uncertainty = self.train_and_predict(df_features)

        stats = self.fetch_coin_stats()
        if not stats or "price" not in stats or stats["price"] == "N/A":
            print(f"No valid price available for {self.coin}")
            return "No valid price available", "No valid price available"

        current_price = stats["price"]
        news_sentiment, news_text = self.process_news()

        position = self.capital_manager.get_position(self.coin)
        if position > 0:
            self.highest_price = max(self.highest_price or current_price, current_price)

        stop_loss_result = self.check_stop_loss(current_price)
        if stop_loss_result:
            trade_details, quantity = stop_loss_result, 0.0  # Quantity not tracked here
            recommendation = "SELL (Stop-Loss)"
        else:
            potential_trade_details = self.generate_potential_trade_details(
                stats, predicted_close
            )
            prelim_report, _ = self.generate_report(
                stats,
                predicted_close,
                news_sentiment,
                news_text,
                trade_details=potential_trade_details,
            )
            recommendation = self.llm_handler.decide(prelim_report)
            trade_details, quantity = self.execute_trade(
                recommendation, current_price, predicted_close, news_sentiment
            )

        news_text_truncated = " ".join(news_text.split()[:50]) + (
            "..." if len(news_text.split()) > 50 else ""
        )
        final_report, summarized_report = self.generate_report(
            stats,
            predicted_close,
            news_sentiment,
            news_text_truncated,
            recommendation,
            trade_details,
        )
        self.save_activity(final_report)

        trade_entry = {
            "coin": self.coin.upper(),
            "recommendation": recommendation,
            "quantity": float(quantity),
            "price": float(current_price),
            "timestamp": datetime.now().isoformat(),
            "details": trade_details,
            "capital": float(self.capital_manager.get_capital(self.coin)),
            "position": float(self.capital_manager.get_position(self.coin)),
        }
        self.capital_manager.trade_records.setdefault(
            self.coin, {"trades": [], "total_profit": 0.0}
        )
        self.capital_manager.trade_records[self.coin]["trades"].append(trade_entry)
        self.capital_manager.save_state()

        return final_report, summarized_report
