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
            temperature=0.4,  # More dynamic decisions
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
        self.trading_fee = 0.001  # 0.1% fee per trade
        self.stop_loss_percentage = 0.015  # Tightened to 1.5% stop-loss
        self.trade_percentage = 0.6  # Use 60% of capital per trade
        self.min_capital_threshold = 10.0  # Use full capital if below $10
        self.stop_loss_price = None  # Track stop-loss price after a buy
        self.highest_price = None  # Track highest price for trailing stop
        self.last_trade_time = 0  # Track last trade time for cool-down
        self.last_sell_time = 0  # Track last sell time for periodic sells
        self.cool_down = 900  # 15-minute cool-down in seconds
        self.profit_target = 0.03  # 3% profit target
        self.sell_of_after_days = 3  # Sell after 3 days



    def withdraw(self, user_id):
        """Withdraw the user's share of the capital for this coin."""
        return self.capital_manager.withdraw(user_id, self.coin)

    def ensure_directory_exists(self):
        """Ensure the directory for the activities file exists."""
        directory = os.path.dirname(self.activities_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_activities(self):
        """Load existing activities from the JSON file, ensuring a dictionary is returned."""
        if os.path.exists(self.activities_file_path):
            try:
                with open(self.activities_file_path, "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    print(
                        f"Warning: {self.activities_file_path} does not contain a dictionary (found {type(data).__name__}). Initializing empty state."
                    )
                    return {}
                return data
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
        """Generates a trading report with optional recommendation and trade details."""
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

        report = f"""
        Report for {self.coin.upper()}:
        - Current Price: {price_str}
        - 24h Price Change: {price_change_str}
        - 24h Low: {low_24h_str}
        - 24h High: {high_24h_str}
        - 24h Volume: {volume_24h_str}
        - Market Cap: {market_cap_str}
        - Predicted Close: ${ predicted_close:.2f}
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
                    f"- Quantity: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                    f"- Using {self.trade_percentage*100:.0f}% of capital: ${trade_capital:.2f}\n"
                    f"- Stop-Loss: ${stop_loss_price:.2f} (-{self.stop_loss_percentage*100:.1f}%)\n"
                    f"- Potential Sale at ${predicted_close:.2f}: ${potential_sale_value:.2f}\n"
                    f"- Potential Profit: ${potential_profit:.2f} ({(potential_profit/trade_capital)*100:.2f}%)\n"
                )
            else:
                trade_details += "Potential BUY: Insufficient capital to buy.\n"

        if position > 0.0:
            sale_value = position * current_price * (1 - self.trading_fee)
            trade_details += (
                f"Potential SELL:\n"
                f"- Quantity: {position:.2f} {self.coin.upper()} at ${current_price:.2f}\n"
                f"- Net Proceeds: ${sale_value:.2f}\n"
            )

        if not trade_details:
            trade_details = f"No trade possible.\n- Current Position: {position:.2f} {self.coin.upper()}"

        return trade_details.strip()

    def calculate_position_size(self, capital, current_price, signal_strength):
        """Dynamic position sizing based on signal strength."""
        if signal_strength > 0.8:  # Strong signal
            return capital * 0.8
        elif signal_strength > 0.6:  # Medium signal
            return capital * 0.6
        else:  # Weak signal
            return capital * 0.4

    def tiered_sell_strategy(self, position, current_price, profit_margin):
        """Adjusted tiered selling to realize profits more frequently."""
        if profit_margin >= 0.05:  # 5% profit
            return position * 0.5  # Sell 50%
        elif profit_margin >= 0.03:  # 3% profit
            return position * 0.3  # Sell 30%
        elif profit_margin >= 0.01:  # 1% profit
            return position * 0.1  # Sell 10%
        else:
            return 0  # Hold

    def dynamic_stop_loss(self, current_price, avg_cost, volatility):
        """Adjust stop-loss based on market volatility using tightened base stop."""
        base_stop = self.stop_loss_percentage  # Use 1.5% from init
        if volatility > 0.1:  # High volatility
            return avg_cost * (1 - (base_stop * 1.5))  # 2.25% stop
        elif volatility < 0.05:  # Low volatility
            return avg_cost * (1 - (base_stop * 0.8))  # 1.2% stop
        else:
            return avg_cost * (1 - base_stop)  # 1.5% stop

    def calculate_signal_strength(self, news_sentiment, predicted_close, current_price):
        """Calculate signal strength based on news sentiment and predicted price movement."""
        price_signal = (predicted_close - current_price) / current_price
        if price_signal > 0.05 and news_sentiment > 0.5:
            return 0.9  # Strong signal
        elif price_signal > 0.02 or news_sentiment > 0.3:
            return 0.7  # Medium signal
        else:
            return 0.5  # Weak signal

    def calculate_market_volatility(self, df, periods=30):
        """Calculate market volatility based on recent price changes."""
        if len(df) < periods:
            return 0.05  # Default volatility
        recent_df = df.tail(periods)
        returns = recent_df["close"].pct_change().dropna()
        volatility = returns.std()
        return volatility

    def check_stop_loss(self, current_price):
        """Check if stop-loss or trailing stop-loss triggers and simulate a sell."""
        position = self.capital_manager.get_position(self.coin)
        if position <= 0 or (
            self.stop_loss_price is None and self.highest_price is None
        ):
            return None

        # Dynamic stop-loss
        df = self.data_handler.load_historical_data()
        volatility = self.calculate_market_volatility(df)
        avg_cost = (
            self.capital_manager.total_cost.get(self.coin, 0) / position
            if position > 0
            else 0
        )
        dynamic_stop_price = self.dynamic_stop_loss(current_price, avg_cost, volatility)

        if current_price <= dynamic_stop_price:
            sell_quantity = position * 0.5  # Sell 50% on stop-loss
            if self.capital_manager.simulate_sell(
                self.coin, sell_quantity, current_price
            ):
                sale_value = sell_quantity * current_price * (1 - self.trading_fee)
                self.last_sell_time = time.time()  # Update last sell time
                return f"Dynamic stop-loss: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}"

        # Trailing stop-loss
        if self.highest_price and current_price <= self.highest_price * (
            1 - self.stop_loss_percentage
        ):
            sell_quantity = position * 0.5  # Sell 50% on trailing stop
            if self.capital_manager.simulate_sell(
                self.coin, sell_quantity, current_price
            ):
                sale_value = sell_quantity * current_price * (1 - self.trading_fee)
                self.last_sell_time = time.time()  # Update last sell time
                return f"Trailing stop-loss triggered: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}"

        return None

    def run(self):
        """Executes the trading process with logic to realize profits more frequently."""
        self.capital_manager.load_state()

        df = self.data_handler.load_historical_data()
        df_features = self.data_handler.prepare_features(df)
        model, feature_cols = self.model_handler.train_model(df_features)
        predicted_close, uncertainty = self.model_handler.predict_close(
            model, df_features, feature_cols
        )

        stats = self.stats_service.fetch_coin_stats(self.coin)
        if (
            stats is None
            or not isinstance(stats, dict)
            or "price" not in stats
            or stats["price"] == "N/A"
        ):
            print(
                f"No valid price available for {self.coin} (stats type: {type(stats)})"
            )
            return "No valid price available", "No valid price available"

        current_price = stats["price"]
        news_sentiment, news_text = self.news_handler.process_news()

        capital = self.capital_manager.get_capital(self.coin)
        position = self.capital_manager.get_position(self.coin)
        quantity = 0.0  # Initialize quantity

        print(f"Capital for {self.coin}: {capital}")

        if position > 0:
            self.highest_price = max(self.highest_price or current_price, current_price)

        stop_loss_result = self.check_stop_loss(current_price)
        if stop_loss_result:
            trade_details = stop_loss_result
            recommendation = "SELL (Stop-Loss)"
        else:
            potential_trade_details = self.generate_potential_trade_details(
                stats, predicted_close
            )
            prelim_report = self.generate_report(
                stats,
                predicted_close,
                news_sentiment,
                news_text,
                trade_details=potential_trade_details,
            )
            recommendation = self.llm_handler.decide(prelim_report)

            if time.time() - self.last_trade_time < self.cool_down:
                print(f"Cool-down active for {self.coin}")
                trade_details = "Cool-down active, no trade executed."
            else:
                trade_details = ""
                signal_strength = self.calculate_signal_strength(
                    news_sentiment, predicted_close, current_price
                )

                if recommendation == "BUY" and capital > 0:
                    trade_capital = self.calculate_position_size(
                        capital, current_price, signal_strength
                    )
                    quantity = trade_capital / (current_price * (1 + self.trading_fee))
                    if self.capital_manager.simulate_buy(
                        self.coin, quantity, current_price
                    ):
                        self.stop_loss_price = current_price * (
                            1 - self.stop_loss_percentage
                        )
                        self.highest_price = current_price
                        trade_details = f"Simulated BUY: {quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nAction: Manually buy on an exchange."
                        print(trade_details)
                        self.last_trade_time = time.time()
                    else:
                        trade_details = "BUY failed: Insufficient capital after fee."

                elif recommendation == "SELL" and position > 0:
                    avg_cost = (
                        self.capital_manager.total_cost.get(self.coin, 0) / position
                        if position > 0
                        else 0
                    )
                    profit_margin = (
                        (current_price - avg_cost) / avg_cost if avg_cost > 0 else 0
                    )
                    sell_quantity = self.tiered_sell_strategy(
                        position, current_price, profit_margin
                    )
                    if sell_quantity > 0:
                        if self.capital_manager.simulate_sell(
                            self.coin, sell_quantity, current_price
                        ):
                            sale_value = (
                                sell_quantity * current_price * (1 - self.trading_fee)
                            )
                            trade_details = f"Tiered SELL: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}\nAction: Manually sell on an exchange."
                            print(trade_details)
                            self.last_trade_time = time.time()
                            self.last_sell_time = time.time()  # Update last sell time
                            quantity = sell_quantity
                        else:
                            trade_details = "SELL failed: Insufficient position."
                    else:
                        trade_details = f"HOLD: Profit margin {profit_margin:.2%} below tier thresholds."
                else:
                    trade_details = (
                        f"No trade executed (Recommendation: {recommendation})."
                    )

            # Periodic sell check if no sell occurred
            if (
                "SELL" not in recommendation
                and position > 0
                and time.time() - self.last_sell_time > self.sell_of_after_days * 24 * 3600
            ):
                sell_quantity = position * 0.1  # Sell 10% periodically
                if self.capital_manager.simulate_sell(
                    self.coin, sell_quantity, current_price
                ):
                    sale_value = sell_quantity * current_price * (1 - self.trading_fee)
                    trade_details += f"\nPeriodic SELL: Sold {sell_quantity:.6f} {self.coin.upper()} at ${current_price:.2f}\nNet proceeds: ${sale_value:.2f}"
                    self.last_sell_time = time.time()
                    self.last_trade_time = time.time()
                    recommendation = "SELL (Periodic)"
                    quantity = sell_quantity

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
            "capital": float(capital),
            "position": float(position),
        }
        self.capital_manager.trade_records.setdefault(
            self.coin, {"trades": [], "total_profit": 0.0}
        )
        self.capital_manager.trade_records[self.coin]["trades"].append(trade_entry)
        self.capital_manager.save_state()

        return final_report, summarized_report
