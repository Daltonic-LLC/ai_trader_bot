from services.crypto_data import CryptoDataService

if __name__ == "__main__":
    service = CryptoDataService()

    try:
        result = service.fetch_and_save_crypto_data("xrp", include_news=False)
    
        print("\nSummary of fetched data:")
        print(f"Coin: {result['coin'].upper()}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Current price: ${result['price']}")
        if "sentiment" in result:
            print(f"Sentiment score (0-1): {result['sentiment']:.2f}")
            sentiment_text = "Bullish" if result['sentiment'] > 0.6 else "Neutral" if result['sentiment'] >= 0.4 else "Bearish"
            print(f"Market sentiment: {sentiment_text}")
        print(f"Data saved to: {result.get('csv_file', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
