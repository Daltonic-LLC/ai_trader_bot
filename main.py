from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService

def main():
    coin = "xrp"
    # coin_service = CoinStatsService()
    news_service = NewsSentimentService()

    # Fetch and save coin stats
    # stats_result = coin_service.fetch_and_save_coin_stats(coin)
    # print("Coin Stats Summary:")
    # for key, value in stats_result.items():
    #     print(f"{key.replace('_', ' ').title()}: {value}")

    # Fetch and save news sentiment
    posts, sentiment = news_service.get_news_and_sentiment(coin)
    print(f"\nNews Sentiment for {coin}: {sentiment}")
    print(f"Number of posts: {len(posts)}")

if __name__ == "__main__":
    main()