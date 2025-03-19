from services.coin_news import CoinNewsService

if __name__ == "__main__":
    service = CoinNewsService()

    try:
        posts = service.get_news_and_sentiment(coin="xrp", num_posts=25)
        print(f"Gathered {len(posts)} posts.")
        sentiment = service.calculate_sentiment_from_last_file(coin="xrp")
        print(f"Sentiment score from last file: {sentiment:.2f}")
    except Exception as e:
        print(f"Error: {e}")
