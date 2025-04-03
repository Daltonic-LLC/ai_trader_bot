class NewsHandler:
    """Handles news fetching, sentiment analysis, and summarization."""
    def __init__(self, news_service, coin, override, llm_handler):
        self.news_service = news_service
        self.coin = coin
        self.override = override
        self.llm_handler = llm_handler

    def process_news(self):
        """Fetches news, calculates sentiment, and summarizes it."""
        news_posts, news_sentiment = (self.news_service.fetch_news_and_sentiment(self.coin) if self.override 
                                      else self.news_service.get_saved_news_and_sentiment(self.coin))
        news_text = " ".join(post.get("text", [""])[0] for post in news_posts)
        news_summary = self.llm_handler.summarize(news_text)
        return news_sentiment, news_summary