import pandas as pd
from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService
from services.coin_records import FileDownloadService
from services.reddit_news import RedditSentimentService


def summarize_with_llm(text):
    # Placeholder for LLM summarization
    # Replace with actual Ollama LLM call, e.g., llm.summarize(text)
    return "Summary: " + text[:100] + "..."  # Dummy summary


def main(coin="xrp"):
    file_service = FileDownloadService()
    stats_service = CoinStatsService()
    news_service = NewsSentimentService()
    reddit_service = RedditSentimentService()

    historical_file = file_service.get_latest_file(coin)
    df = pd.read_csv(historical_file, sep=';')
    df["SMA50"] = df["close"].rolling(window=50).mean()
    sma50 = df["SMA50"].iloc[-1] if not df["SMA50"].isna().all() else 0
    print(sma50)

    # # Real-time stats
    # stats_file = stats_service.fetch_and_save_coin_stats(coin)
    stats_file = stats_service.fetch_and_save_coin_stats(coin)
    current_price = stats_file.get("price", 0)
    print(current_price)

    # # News sentiment
    news_posts, news_sentiment = news_service.get_news_and_sentiment(coin)
    news_text = " ".join(post.get("text", [""])[0] for post in news_posts)
    print(news_text)

    # # Reddit sentiment
    # reddit_sentiment = reddit_service.analyze_sentiment(coin)
    # # Modify RedditSentimentService to return posts if needed
    # reddit_posts = []  # Placeholder; extend service to return post data
    # reddit_text = "Sample Reddit text"  # Replace with actual post text

    # # 2. Process Data
    # average_sentiment = (
    #     (news_sentiment + reddit_sentiment) / 2 if news_posts else news_sentiment
    # )

    # # 3. LLM Analysis
    # news_summary = summarize_with_llm(news_text)
    # reddit_summary = summarize_with_llm(reddit_text)

    # # 4. Decision Logic
    # if current_price > sma50 and average_sentiment > 0:
    #     recommendation = "Buy or Hold"
    # elif current_price < sma50 or average_sentiment < 0:
    #     recommendation = "Sell"
    # else:
    #     recommendation = "Hold"

    # # 5. Generate Report
    # report = f"""
    # Daily Report for {coin.upper()}:
    # - Current Price: ${current_price}
    # - 50-day SMA: ${sma50:.2f}
    # - News Sentiment: {news_sentiment:.2f}
    # - Reddit Sentiment: {reddit_sentiment:.2f}
    # - Average Sentiment: {average_sentiment:.2f}
    # - News Summary: {news_summary}
    # - Reddit Summary: {reddit_summary}
    # - Recommendation: {recommendation}
    # """
    # print(report)
    # # Optionally save to a file
    # with open(f"{coin}_daily_report.txt", "w") as f:
    #     f.write(report)


if __name__ == "__main__":
    main("tron")
