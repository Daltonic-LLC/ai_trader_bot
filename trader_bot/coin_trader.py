from .llm_handler import LLMHandler
from .data_handler import DataHandler
from .model_handler import ModelHandler
from .news_handler import NewsHandler
from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService
from services.coin_history import CoinHistory
from config import config

class CoinTrader:
    def __init__(self, coin, override, capital_manager):
        self.coin = coin.lower()  # Normalize to lowercase
        self.override = override
        self.capital_manager = capital_manager  # Instance of CapitalManager
        self.history_service = CoinHistory()
        self.stats_service = CoinStatsService()
        self.news_service = NewsSentimentService()
        self.llm_handler = LLMHandler(
            base_url=config.chat_endpoint,
            model=config.chat_model,
            temperature=0.1,
            timeout=60
        )
        self.data_handler = DataHandler(self.history_service, self.coin, self.override)
        self.model_handler = ModelHandler()
        self.news_handler = NewsHandler(self.news_service, self.coin, self.override, self.llm_handler)
        self.trading_fee = 0.001  # Assume 0.1% fee per trade
        self.stop_loss_percentage = 0.05  # 5% stop-loss

    def get_current_price(self):
        """Fetches the current price of the coin."""
        stats_file = (self.stats_service.fetch_and_save_coin_stats(self.coin) if self.override 
                      else self.stats_service.get_latest_stats(self.coin))
        return stats_file.get("price", 0)

    def generate_report(self, current_price, predicted_close, news_sentiment, news_text, recommendation, trade_details):
        """Generates a trading report with trade details."""
        news_text_truncated = " ".join(news_text.split()[:50]) + ("..." if len(news_text.split()) > 50 else "")
        report = f"""
        Daily Report for {self.coin.upper()}:
        - Current Price: ${current_price:.2f}
        - Predicted Close: ${predicted_close:.2f}
        - News Sentiment: {news_sentiment:.2f}
        - News Text: {news_text_truncated}
        - Recommendation: {recommendation}
        - Current Capital: ${self.capital_manager.get_capital(self.coin):.2f}
        Trade Details:
        {trade_details}
        """
        return report

    def run(self):
        """Executes the trading process, simulates trades, updates capital, and returns the report."""
        # Fetch data for the specified coin
        df = self.data_handler.load_historical_data()
        df_features = self.data_handler.prepare_features(df)
        model, feature_cols = self.model_handler.train_model(df_features)
        # Get prediction with uncertainty
        predicted_close, uncertainty = self.model_handler.predict_close(model, df_features, feature_cols)
        current_price = self.get_current_price()
        news_sentiment, news_text = self.news_handler.process_news()

        # Use LLMHandler's decide method with full news text
        recommendation = self.llm_handler.decide(self.coin, current_price, predicted_close, news_sentiment, news_text)

        # Simulate trading based on recommendation
        trade_details = ""
        position = self.capital_manager.get_position(self.coin)
        if recommendation == "BUY" and position == 0.0:
            # Simulate buying with available capital for this coin
            capital = self.capital_manager.get_capital(self.coin)
            quantity = (capital * (1 - self.trading_fee)) / current_price
            if self.capital_manager.simulate_buy(self.coin, quantity, current_price, self.trading_fee):
                stop_loss_price = current_price * (1 - self.stop_loss_percentage)
                potential_sale_value = quantity * predicted_close * (1 - self.trading_fee)
                potential_profit = potential_sale_value - capital
                trade_details = f"Simulated BUY: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}\n" + \
                                f"Stop-Loss set at ${stop_loss_price:.2f} (-{self.stop_loss_percentage*100:.1f}%)\n" + \
                                f"Potential sale at ${predicted_close:.2f} yields ${potential_sale_value:.2f}\n" + \
                                f"Potential profit: ${potential_profit:.2f} ({(potential_profit/capital)*100:.2f}%)\n" + \
                                f"Action: Manually buy {quantity:.2f} {self.coin.upper()} on an exchange."
                print(f"Simulated BUY: {quantity:.2f} {self.coin.upper()} at ${current_price:.2f}")
            else:
                trade_details = f"BUY failed: Insufficient capital.\nCurrent position: {position:.2f} {self.coin.upper()}\nAction: No trade possible."
                print(f"BUY failed: Insufficient capital.")
        elif recommendation == "SELL" and position > 0.0:
            # Simulate selling current position
            if self.capital_manager.simulate_sell(self.coin, position, current_price, self.trading_fee):
                sale_value = position * current_price * (1 - self.trading_fee)
                trade_details = f"Simulated SELL: {position:.2f} {self.coin.upper()} at ${current_price:.2f}\n" + \
                                f"Net proceeds: ${sale_value:.2f}\n" + \
                                f"Action: Manually sell {position:.2f} {self.coin.upper()} on an exchange."
                print(f"Simulated SELL: {position:.2f} {self.coin.upper()} at ${current_price:.2f}")
            else:
                trade_details = f"SELL failed: Insufficient position.\nCurrent position: {position:.2f} {self.coin.upper()}\nAction: No trade possible."
                print(f"SELL failed: Insufficient position.")
        else:
            # HOLD or no position
            trade_details = f"No trade executed (Recommendation: {recommendation}).\n" + \
                           f"Current position: {position:.2f} {self.coin.upper()}\n" + \
                           "Action: No manual trade required."
            print(f"No trade executed: {recommendation}")

        # Generate and return the report
        return self.generate_report(current_price, predicted_close, news_sentiment, news_text, recommendation, trade_details)