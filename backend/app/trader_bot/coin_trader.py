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


class CoinTrader:
    def __init__(
        self,
        coin,
        override,
        capital_manager,
        activities_file_path="data/activities/coin_reports.json",
    ):
        self.coin = coin.lower()  # Ensure coin names are lowercase for consistency
        self.override = override
        self.capital_manager = capital_manager
        self.activities_file_path = activities_file_path
        self.ensure_directory_exists()
        self.history_service = CoinHistory()
        self.stats_service = CoinStatsService()
        self.news_service = NewsSentimentService()
        self.llm_handler = LLMHandler(
            base_url=config.chat_endpoint,
            model=config.chat_model,
            temperature=0.1,
            timeout=60,
        )
        self.data_handler = DataHandler(self.history_service, self.coin, self.override)
        self.model_handler = ModelHandler()
        self.news_handler = NewsHandler(
            self.news_service, self.coin, self.override, self.llm_handler
        )
        self.trading_fee = 0.001  # Assume 0.1% fee per trade
        self.stop_loss_percentage = 0.05  # 5% stop-loss
        self.trade_percentage = 0.2  # Use 20% of capital per trade
        self.min_capital_threshold = 10.0  # Use full capital if below $10
        self.stop_loss_price = None  # Track stop-loss price after a buy

    def withdraw(self, user_id):
        """Withdraw the user's share of the capital for this coin."""
        return self.capital_manager.withdraw(user_id, self.coin)

    def ensure_directory_exists(self):
        """Ensure the directory for the activities file exists."""
        directory = os.path.dirname(self.activities_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_activities(self):
        """Load existing activities from the JSON file."""
        if os.path.exists(self.activities_file_path):
            try:
                with open(self.activities_file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(
                    f"Error loading {self.activities_file_path}: {e}. Initializing empty state."
                )
                return {}
        else:
            return {}

    def get_report(self, coin):
        """Retrieve the latest report for the specified coin from the activities file."""
        if not os.path.exists(self.activities_file_path):
            return None
        try:
            with open(self.activities_file_path, "r") as f:
                data = json.load(f)
            coin = coin.lower()
            return data.get(coin, None)
        except (json.JSONDecodeError, IOError):
            return None

    def save_activities(self, data):
        """Save the activities data to the JSON file."""
        try:
            self.ensure_directory_exists()
            with open(self.activities_file_path, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Saved activities to {self.activities_file_path}")
        except IOError as e:
            print(f"Error saving to {self.activities_file_path}: {e}")

    def save_activity(self, report):
        """Save the latest report for the coin to the activities file."""
        data = self.load_activities()
        data[self.coin] = {"timestamp": datetime.now().isoformat(), "report": report}
        self.save_activities(data)

    def generate_report(
        self,
        stats,
        predicted_close,
        news_sentiment,
        news_text,
        recommendation=None,
        trade_details=None,
    ):
        """Generates a trading report with optional recommendation and trade details.
        Returns a tuple: (full_report, summary_report)
        """
        # Extract and format statistics, handling "N/A" cases
        price = stats.get("price", "N/A")
        price_str = f"${price:.2f}" if isinstance(price, float) else price

        price_change = stats.get("price_change_24h_percent", "N/A")
        price_change_str = (
            f"{price_change:.2f}%" if isinstance(price_change, float) else price_change
        )

        low_24h = stats.get("low_24h", "N/A")
        low_24h_str = f"${low_24h:.2f}" if isinstance(low_24h, float) else low_24h

        high_24h = stats.get("high_24h", "N/A")
        high_24h_str = f"${high_24h:.2f}" if isinstance(high_24h, float) else high_24h

        volume_24h = stats.get("volume_24h", "N/A")
        volume_24h_str = (
            f"${volume_24h:,.2f}" if isinstance(volume_24h, float) else volume_24h
        )

        market_cap = stats.get("market_cap", "N/A")
        market_cap_str = (
            f"${market_cap:,.2f}" if isinstance(market_cap, float) else market_cap
        )

        # Construct the full report
        report = f"""
        Report for {self.coin.upper()}:
        - Current Price: {price_str}
        - 24h Price Change: {price_change_str}
        - 24h Low: {low_24h_str}
        - 24h High: {high_24h_str}
        - 24h Volume: {volume_24h_str}
        - Market Cap: {market_cap_str}
        - Predicted Close: ${predicted_close:.2f}
        - News Sentiment: {news_sentiment:.2f}
        - News Text: {news_text}
        """
        if recommendation is not None:
            report += f"- Recommendation: {recommendation}\n"
        report += (
            f"- Current Capital: ${self.capital_manager.get_capital(self.coin):.2f}\n"
        )
        if trade_details is not None:
            report += f"Trade Details:\n{trade_details}\n"
        full_report = report.strip()

        # Construct the summary one-liner (no news text)
        summary = (
            f"{self.coin.upper()} | Price: {price_str} | 24h Change: {price_change_str} | "
            f"Predicted Close: ${predicted_close:.2f} | News Sentiment: {news_sentiment:.2f}"
        )
        if recommendation is not None:
            summary += f" | Recommendation: {recommendation}"
        summary += f" | Capital: ${self.capital_manager.get_capital(self.coin):.2f}"
        if trade_details is not None:
            summary += f" | {trade_details.splitlines()[0]}"
        summary_report = summary

        return full_report, summary_report

    def generate_potential_trade_details(self, stats, predicted_close):
        """Generates potential trade details for BUY and SELL scenarios."""
        current_price = stats["price"]
        position = self.capital_manager.get_position(self.coin)
        trade_details = ""

        # Potential BUY details if no position exists
        if position == 0.0:
            capital = self.capital_manager.get_capital(self.coin)
            trade_capital = capital * self.trade_percentage
            quantity = (trade_capital * (1 - self.trading_fee)) / current_price
            if quantity > 0:
                stop_loss_price = current_price * (1 - self.stop_loss_percentage)
                potential_sale_value = (
                    quantity * predicted_close * (1 - self.trading_fee)
                )
                potential_profit = potential_sale_value - trade_capital
                trade_details += (
                    f"Potential BUY:\n"
                    + f"- Quantity: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                    + f"- Using {self.trade_percentage*100:.0f}% of capital: ${trade_capital:.2f}\n"
                    + f"- Stop-Loss: ${stop_loss_price:.2f} (-{self.stop_loss_percentage*100:.1f}%)\n"
                    + f"- Potential Sale at ${predicted_close:.2f}: ${potential_sale_value:.2f}\n"
                    + f"- Potential Profit: ${potential_profit:.2f} ({(potential_profit/trade_capital)*100:.2f}%)\n"
                )
            else:
                trade_details += "Potential BUY: Insufficient capital to buy.\n"

        # Potential SELL details if position exists
        if position > 0.0:
            sale_value = position * current_price * (1 - self.trading_fee)
            trade_details += (
                f"Potential SELL:\n"
                + f"- Quantity: {position:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                + f"- Net Proceeds: ${sale_value:.2f}\n"
            )

        if not trade_details:
            trade_details = f"No trade possible.\n- Current Position: {position:.2f} {self.coin.upper()}"

        return trade_details.strip()

    def check_stop_loss(self, current_price):
        """Check if the current price triggers the stop-loss and simulate a sell."""
        position = self.capital_manager.get_position(self.coin)
        if position > 0 and self.stop_loss_price is not None:
            if current_price <= self.stop_loss_price:
                sale_value = position * current_price * (1 - self.trading_fee)
                if self.capital_manager.simulate_sell(
                    self.coin, position, current_price, self.trading_fee
                ):
                    self.stop_loss_price = None  # Reset stop-loss after selling
                    return f"Stop-loss triggered: Sold {position:.2f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}"
        return None

    def run(self):
        """Executes the trading process, simulates trades, updates capital, and returns the report."""
        # Fetch data for the specified coin
        df = self.data_handler.load_historical_data()
        df_features = self.data_handler.prepare_features(df)
        model, feature_cols = self.model_handler.train_model(df_features)
        predicted_close, uncertainty = self.model_handler.predict_close(
            model, df_features, feature_cols
        )

        # Fetch all current statistics
        stats = self.stats_service.fetch_coin_stats(self.coin)
        if stats is None or "price" not in stats or stats["price"] == "N/A":
            print(f"No valid price available for {self.coin}")
            return "No valid price available"
        current_price = stats["price"]

        news_sentiment, news_text = self.news_handler.process_news()

        # Check stop-loss before proceeding
        stop_loss_result = self.check_stop_loss(current_price)
        if stop_loss_result:
            trade_details = stop_loss_result
            recommendation = "SELL (Stop-Loss)"
        else:
            # Generate potential trade details for the LLM
            potential_trade_details = self.generate_potential_trade_details(
                stats, predicted_close
            )

            # Generate preliminary report
            prelim_report = self.generate_report(
                stats,
                predicted_close,
                news_sentiment,
                news_text,
                trade_details=potential_trade_details,
            )

            # Get recommendation from LLM
            recommendation = self.llm_handler.decide(prelim_report)

            # Simulate trading based on recommendation
            trade_details = ""
            position = self.capital_manager.get_position(self.coin)
            if recommendation == "BUY" and position == 0.0:
                capital = self.capital_manager.get_capital(self.coin)
                # Check if capital is below threshold
                if capital <= self.min_capital_threshold:
                    trade_capital = capital  # Use full capital
                    trade_percentage_used = 1.0
                else:
                    trade_capital = capital * self.trade_percentage  # Use default 20%
                    trade_percentage_used = self.trade_percentage
                quantity = (trade_capital * (1 - self.trading_fee)) / current_price
                if self.capital_manager.simulate_buy(
                    self.coin, quantity, current_price
                ):
                    self.stop_loss_price = current_price * (
                        1 - self.stop_loss_percentage
                    )
                    trade_details = (
                        f"Simulated BUY: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                        f"Using {trade_percentage_used*100:.0f}% of capital: ${trade_capital:.2f}\n"
                        f"Stop-Loss set at ${self.stop_loss_price:.2f}\n"
                        "Action: Manually buy on an exchange."
                    )
                    print(
                        f"Simulated BUY: {quantity:.2f} {self.coin.upper()} with {trade_percentage_used*100:.0f}% of capital"
                    )
                else:
                    trade_details = (
                        f"BUY failed: Insufficient capital.\n"
                        f"Current position: {position:.2f} {self.coin.upper()}\n"
                        "Action: No trade possible."
                    )
                    print(f"BUY failed: Insufficient capital.")
            elif recommendation == "SELL" and position > 0.0:
                if self.capital_manager.simulate_sell(
                    self.coin, position, current_price
                ):
                    sale_value = position * current_price * (1 - self.trading_fee)
                    self.stop_loss_price = None
                    trade_details = (
                        f"Simulated SELL: {position:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                        f"Net proceeds: ${sale_value:.2f}\n"
                        "Action: Manually sell on an exchange."
                    )
                    print(
                        f"Simulated SELL: {position:.2f} {self.coin.upper()} at ${current_price:.2f}"
                    )
                else:
                    trade_details = (
                        f"SELL failed: Insufficient position.\n"
                        f"Current position: {position:.2f} {self.coin.upper()}\n"
                        "Action: No trade possible."
                    )
                    print(f"SELL failed: Insufficient position.")
            else:
                trade_details = (
                    f"No trade executed (Recommendation: {recommendation}).\n"
                    f"Current position: {position:.2f} {self.coin.upper()}\n"
                    "Action: No manual trade required."
                )
                print(f"No trade executed: {recommendation}")

        # Generate and return the final report
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
        return final_report, summarized_report
