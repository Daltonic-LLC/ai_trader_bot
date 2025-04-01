import pandas as pd
from services.coin_stats import CoinStatsService
from services.coin_news import NewsSentimentService
from services.coin_records import FileDownloadService


def summarize_with_llm(text):
    # Placeholder for LLM summarization
    # Replace with actual Ollama LLM call, e.g., llm.summarize(text)
    return "Summary: " + text[:100] + "..."  # Dummy summary


def main(coin="xrp", override=False):
    file_service = FileDownloadService()
    stats_service = CoinStatsService()
    news_service = NewsSentimentService()
    
    if override:
        historical_file = file_service.download_file(coin)
    else:
        historical_file = file_service.get_latest_file(coin)

    df = pd.read_csv(historical_file, sep=';')
    df["SMA50"] = df["close"].rolling(window=50).mean()
    sma50 = df["SMA50"].iloc[-1] if not df["SMA50"].isna().all() else 0

    # # # Real-time stats
    if override:
        stats_file = stats_service.fetch_and_save_coin_stats(coin)
    else:
        stats_file = stats_service.get_latest_stats(coin)
        
    current_price = stats_file.get("price", 0)

    # # # News sentiment
    if override:
        news_posts, news_sentiment = news_service.fetch_news_and_sentiment(coin)
    else:
        news_posts, news_sentiment = news_service.get_saved_news_and_sentiment(coin)
    
    news_text = " ".join(post.get("text", [""])[0] for post in news_posts)


    # # 3. LLM Analysis
    news_summary = summarize_with_llm(news_text)

    

    # 4. Decision Logic
    if current_price > sma50 and news_sentiment > 0:
        recommendation = "Buy"
    elif current_price < sma50 or news_sentiment < 0:
        recommendation = "Sell"
    else:
        recommendation = "Hold"
    

    # 5. Generate Report
    report = f"""
    Daily Report for {coin.upper()}:
    - Current Price: ${current_price}
    - 50-day SMA: ${sma50:.2f}
    - News Sentiment: {news_sentiment:.2f}
    - News Summary: {news_summary}
    - Recommendation: {recommendation}
    """
    print(report)


if __name__ == "__main__":
    main("xrp", override=True)
