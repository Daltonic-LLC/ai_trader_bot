from services.coin_news import CoinNewsService

if __name__ == "__main__":
    news = CoinNewsService()

    try:
        posts, sentiment = news.get_news_and_sentiment(coin="xrp", num_posts=20)
        print("\nNews Posts:")
        for post in posts:
            print(f"User: {post['username']}, Time: {post['time']}, Text: {''.join(post['text'])[:100]}...")
            print(f"Reactions: {post['reactions']}")
        print(f"Overall Sentiment Score: {sentiment:.2f}")
    except Exception as e:
        print(f"Error: {e}")
