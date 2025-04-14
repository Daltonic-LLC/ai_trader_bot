from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import time
from datetime import datetime
from services.coin_extractor import TopCoinsExtractor
from services.coin_history import CoinHistory
from services.coin_news import NewsSentimentService
from services.coin_stats import CoinStatsService
from services.file_manager import DataCleaner

# Set up logging to monitor execution
logging.basicConfig(
    filename='scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def daily_top_coin_list():
    """Executes the TopCoinsExtractor to extract top coins and save them to a JSON file."""
    logging.info("Starting daily top coins extraction")
    try:
        # Create an instance of TopCoinsExtractor
        extractor = TopCoinsExtractor()
        
        # Extract top coins
        top_coins = extractor.extract_top_coins()
        
        # Save the data to a JSON file
        saved_file = extractor.save_to_json(top_coins)
        
        # Log and print the result
        message = f"Saved top coins to: {saved_file}"
        logging.info(message)
        print(message)
    except Exception as e:
        # Log any errors that occur
        logging.error(f"Error during top coins extraction: {e}")
        print(f"Error: {e}")

def daily_coin_history():
    """Loads the most recent top coins and runs CoinHistory on each slug."""
    logging.info("Starting daily coin history extraction")
    try:
        # Initialize TopCoinsExtractor to load saved data
        extractor = TopCoinsExtractor()
        
        # Load the most recent top coins data
        coins_data = extractor.load_most_recent_data()
        
        if coins_data is None:
            logging.warning("No top coins data found for history extraction")
            print("No top coins data found. Run top coins extraction first.")
            return
        
        # Initialize CoinHistory
        history_extractor = CoinHistory()
        
        # Process each coin's slug
        for coin in coins_data:
            slug = coin.get('slug')
            if not slug or slug == "N/A":
                logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                continue
            
            logging.info(f"Extracting history for {coin['name']} ({slug})")
            try:
                # Download historical data
                file_path = history_extractor.download_history(
                    coin=slug
                )
                message = f"{coin['name'].upper()} historical data downloaded to: {file_path}"
                logging.info(message)
                print(message)
            except Exception as e:
                logging.error(f"Error extracting history for {slug}: {e}")
                print(f"Error extracting history for {slug}: {e}")
        
        logging.info("Completed coin history extraction")
    except Exception as e:
        logging.error(f"Error during coin history job: {e}")
        print(f"Error in coin history job: {e}")

def daily_news_sentiment():
    """Loads the most recent top coins and fetches news sentiment for each slug."""
    logging.info("Starting daily news sentiment extraction")
    try:
        # Initialize TopCoinsExtractor to load saved data
        extractor = TopCoinsExtractor()
        
        # Load the most recent top coins data
        coins_data = extractor.load_most_recent_data()
        
        if coins_data is None:
            logging.warning("No top coins data found for news sentiment extraction")
            print("No top coins data found. Run top coins extraction first.")
            return
        
        # Initialize NewsSentimentService
        sentiment_service = NewsSentimentService()
        
        # Process each coin's slug
        for coin in coins_data:
            slug = coin.get('slug')
            if not slug or slug == "N/A":
                logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                continue
            
            logging.info(f"Fetching news sentiment for {coin['name']} ({slug})")
            try:
                # Fetch news and sentiment
                posts, sentiment = sentiment_service.fetch_news_and_sentiment(slug)
                message = f"Gathered {len(posts)} posts for {coin['name'].upper()} with average sentiment {sentiment:.2f}"
                logging.info(message)
                print(message)
            except Exception as e:
                logging.error(f"Error processing news sentiment for {slug}: {e}")
                print(f"Error processing news sentiment for {slug}: {e}")
        
        logging.info("Completed news sentiment extraction")
    except Exception as e:
        logging.error(f"Error during news sentiment job: {e}")
        print(f"Error in news sentiment job: {e}")

def daily_coin_prices():
    """Loads the most recent top coins and fetches latest prices every 20 minutes."""
    logging.info("Starting coin prices update")
    try:
        # Initialize TopCoinsExtractor to load saved data
        extractor = TopCoinsExtractor()
        
        # Load the most recent top coins data
        coins_data = extractor.load_most_recent_data()
        
        if coins_data is None:
            logging.warning("No top coins data found for price updates")
            print("No top coins data found. Run top coins extraction first.")
            return
        
        # Initialize CoinStatsService
        stats_service = CoinStatsService()
        
        # Process each coin's slug
        for coin in coins_data:
            slug = coin.get('slug')
            if not slug or slug == "N/A":
                logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                continue
            
            logging.info(f"Fetching stats for {coin['name']} ({slug})")
            try:
                result = stats_service.fetch_and_save_coin_stats(slug)
                if "error" not in result:
                    message = f"Updated {coin['name'].upper()} price: ${result.get('price', 'N/A')} saved to {result.get('csv_file', 'N/A')}"
                    logging.info(message)
                    print(message)
                else:
                    logging.warning(f"Failed to fetch stats for {slug}: {result['error']}")
                    print(f"Failed to fetch stats for {slug}: {result['error']}")
            except Exception as e:
                logging.error(f"Error fetching stats for {slug}: {e}")
                print(f"Error fetching stats for {slug}: {e}")
        
        logging.info("Completed coin prices update")
    except Exception as e:
        logging.error(f"Error during coin prices job: {e}")
        print(f"Error in coin prices job: {e}")

# Define the data cleaner job
def daily_data_cleaner():
    """Runs the DataCleaner to clean up duplicate files in the data directory."""
    logging.info("Starting daily data cleanup")
    try:
        cleaner = DataCleaner()
        cleaner.clean_timestamped_files()
        logging.info("Completed daily data cleanup")
    except Exception as e:
        logging.error(f"Error during data cleanup: {e}")

if __name__ == "__main__":
    # Initialize the background scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule the top coins extraction daily at midnight (00:00)
    top_coins_trigger = IntervalTrigger(hours=12)
    scheduler.add_job(daily_top_coin_list, top_coins_trigger)
    
    # Schedule the coin history extraction daily at 00:20
    history_trigger = CronTrigger(hour=0, minute=20)
    scheduler.add_job(daily_coin_history, history_trigger)
    
    # Schedule the coin prices update every 4 hours
    sentiment_trigger = IntervalTrigger(hours=4)
    scheduler.add_job(daily_news_sentiment, sentiment_trigger)
    
    # Schedule the coin prices update every 1 hour
    prices_trigger = IntervalTrigger(hours=1)
    scheduler.add_job(daily_coin_prices, prices_trigger)
    
    # Schedule the data cleanup daily at 1:00 AM
    cleanup_trigger = CronTrigger(hour=1, minute=0)
    scheduler.add_job(daily_data_cleaner, cleanup_trigger)
    
    # Start the scheduler
    scheduler.start()
    logging.info("Scheduler started, watching and executing various coin jobs")
    print("Scheduler started, watching and executing various coin jobs. Press Ctrl+C to stop.")
    
    try:
        # Keep the script running
        while True:
            time.sleep(60)  # Sleep for 60 seconds to reduce CPU usage
    except (KeyboardInterrupt, SystemExit):
        # Gracefully shut down on interruption
        scheduler.shutdown()
        logging.info("Scheduler shut down")
        print("Scheduler stopped.")