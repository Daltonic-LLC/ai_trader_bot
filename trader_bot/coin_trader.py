from .llm_handler import LLMHandler
from .data_handler import DataHandler
from .model_handler import ModelHandler
from .news_handler import NewsHandler
from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService
from services.coin_records import FileDownloadService

class CoinTrader:
    """Orchestrates the trading process for a specific coin."""
    def __init__(self, coin, override):
        self.coin = coin
        self.override = override
        self.file_service = FileDownloadService()
        self.stats_service = CoinStatsService()
        self.news_service = NewsSentimentService()
        self.llm_handler = LLMHandler(
            base_url="https://11434-daltonic-aitraderbot-f9rpnbt00si.ws-eu118.gitpod.io",
            model="phi4-mini:3.8b",
            temperature=0.1,
            timeout=60
        )
        self.data_handler = DataHandler(self.file_service, self.coin, self.override)
        self.model_handler = ModelHandler()
        self.news_handler = NewsHandler(self.news_service, self.coin, self.override, self.llm_handler)

    def get_current_price(self):
        """Fetches the current price of the coin."""
        stats_file = (self.stats_service.fetch_and_save_coin_stats(self.coin) if self.override 
                      else self.stats_service.get_latest_stats(self.coin))
        return stats_file.get("price", 0)

    def generate_report(self, current_price, predicted_close, news_sentiment, news_summary, recommendation):
        """Generates a trading report."""
        report = f"""
        Daily Report for {self.coin.upper()}:
        - Current Price: ${current_price}
        - Predicted Close: ${predicted_close:.2f}
        - News Sentiment: {news_sentiment:.2f}
        - News Summary: {news_summary}
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
        news_sentiment, news_summary = self.news_handler.process_news()
        recommendation = self.llm_handler.decide(self.coin, current_price, predicted_close, news_sentiment, news_summary)
        return self.generate_report(current_price, predicted_close, news_sentiment, news_summary, recommendation)