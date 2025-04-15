from .llm_handler import LLMHandler
from .data_handler import DataHandler
from .model_handler import ModelHandler
from .news_handler import NewsHandler
from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService
from services.coin_history import CoinHistory
from config import config

class CoinTrader:
    """Orchestrates the trading process for a specific coin."""
    def __init__(self, coin, override):
        self.coin = coin
        self.override = override
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

    def get_current_price(self):
        """Fetches the current price of the coin."""
        stats_file = (self.stats_service.fetch_and_save_coin_stats(self.coin) if self.override 
                      else self.stats_service.get_latest_stats(self.coin))
        return stats_file.get("price", 0)

    def generate_report(self, current_price, predicted_close, news_sentiment, news_text, recommendation):
        """Generates a trading report."""
        # Truncate news_text for the report to keep it concise
        news_text_truncated = " ".join(news_text.split()[:50]) + ("..." if len(news_text.split()) > 50 else "")
        report = f"""
        Daily Report for {self.coin.upper()}:
        - Current Price: ${current_price}
        - Predicted Close: ${predicted_close:.2f}
        - News Sentiment: {news_sentiment:.2f}
        - News Text: {news_text_truncated}
        - Recommendation: {recommendation}
        """
        return report

    def run(self):
        """Executes the trading process and returns the report."""
        df = self.data_handler.load_historical_data()
        df_features = self.data_handler.prepare_features(df)
        model, feature_cols = self.model_handler.train_model(df_features)
        predicted_close = self.model_handler.predict_close(model, df_features, feature_cols)
        current_price = self.get_current_price()
        news_sentiment, news_text = self.news_handler.process_news()
        recommendation = self.llm_handler.decide(self.coin, current_price, predicted_close, news_sentiment, news_text)
        return self.generate_report(current_price, predicted_close, news_sentiment, news_text, recommendation)