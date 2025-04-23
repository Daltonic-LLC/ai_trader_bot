from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from app.services.coin_extractor import TopCoinsExtractor
from app.services.coin_history import CoinHistory
from app.services.coin_news import NewsSentimentService
from app.services.coin_stats import CoinStatsService
from app.services.file_manager import DataCleaner


class CoinScheduler:
    def __init__(self, log_file='scheduler.log'):
        """Initialize the CoinScheduler with a background scheduler and logging."""
        # Set up logging
        self._setup_logging(log_file)
        logging.info("Initializing CoinScheduler")

        # Initialize the background scheduler
        self.scheduler = BackgroundScheduler()

        # Initialize services
        self.extractor = TopCoinsExtractor()
        self.history_service = CoinHistory()
        self.sentiment_service = NewsSentimentService()
        self.stats_service = CoinStatsService()
        self.cleaner = DataCleaner()

    def _setup_logging(self, log_file):
        """Configure logging for the scheduler."""
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _daily_top_coin_list(self):
        """Extract top coins and save them to a JSON file."""
        logging.info("Starting daily top coins extraction")
        try:
            top_coins = self.extractor.extract_top_coins()
            saved_file = self.extractor.save_to_json(top_coins)
            message = f"Saved top coins to: {saved_file}"
            logging.info(message)
            print(message)
        except Exception as e:
            logging.error(f"Error during top coins extraction: {e}")
            print(f"Error: {e}")

    def _daily_coin_history(self):
        """Load top coins and extract historical data for each slug."""
        logging.info("Starting daily coin history extraction")
        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for history extraction")
                print("No top coins data found. Run top coins extraction first.")
                return

            for coin in coins_data:
                slug = coin.get('slug')
                if not slug or slug == "N/A":
                    logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                    continue

                logging.info(f"Extracting history for {coin['name']} ({slug})")
                try:
                    file_path = self.history_service.download_history(coin=slug)
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

    def _daily_news_sentiment(self):
        """Load top coins and fetch news sentiment for each slug."""
        logging.info("Starting daily news sentiment extraction")
        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for news sentiment extraction")
                print("No top coins data found. Run top coins extraction first.")
                return

            for coin in coins_data:
                slug = coin.get('slug')
                if not slug or slug == "N/A":
                    logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                    continue

                logging.info(f"Fetching news sentiment for {coin['name']} ({slug})")
                try:
                    posts, sentiment = self.sentiment_service.fetch_news_and_sentiment(slug)
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

    def _daily_coin_prices(self):
        """Load top coins and fetch latest prices."""
        logging.info("Starting coin prices update")
        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for price updates")
                print("No top coins data found. Run top coins extraction first.")
                return

            for coin in coins_data:
                slug = coin.get('slug')
                if not slug or slug == "N/A":
                    logging.warning(f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}")
                    continue

                logging.info(f"Fetching stats for {coin['name']} ({slug})")
                try:
                    result = self.stats_service.fetch_and_save_coin_stats(slug)
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

    def _daily_data_cleaner(self):
        """Clean up duplicate files in the data directory."""
        logging.info("Starting daily data cleanup")
        try:
            self.cleaner.clean_timestamped_files()
            logging.info("Completed daily data cleanup")
        except Exception as e:
            logging.error(f"Error during data cleanup: {e}")
            print(f"Error during data cleanup: {e}")

    def configure_jobs(self):
        """Configure the scheduler with all jobs and their triggers."""
        # Top coins extraction every 12 hours
        self.scheduler.add_job(
            self._daily_top_coin_list,
            IntervalTrigger(hours=12),
            id='top_coins',
            name='Top Coins Extraction'
        )

        # Coin history extraction daily at 00:20
        self.scheduler.add_job(
            self._daily_coin_history,
            CronTrigger(hour=0, minute=20),
            id='coin_history',
            name='Coin History Extraction'
        )

        # News sentiment extraction every 4 hours
        self.scheduler.add_job(
            self._daily_news_sentiment,
            IntervalTrigger(hours=4),
            id='news_sentiment',
            name='News Sentiment Extraction'
        )

        # Coin prices update every 1 hour
        self.scheduler.add_job(
            self._daily_coin_prices,
            IntervalTrigger(hours=1),
            id='coin_prices',
            name='Coin Prices Update'
        )

        # Data cleanup daily at 1:00 AM
        self.scheduler.add_job(
            self._daily_data_cleaner,
            CronTrigger(hour=1, minute=0),
            id='data_cleanup',
            name='Data Cleanup'
        )

        logging.info("Scheduler jobs configured")

    def start(self):
        """Start the scheduler and run the jobs."""
        try:
            self.configure_jobs()
            self.scheduler.start()
            logging.info("CoinScheduler started, executing coin jobs")
            print("CoinScheduler started, executing coin jobs. Press Ctrl+C to stop.")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            print(f"Error starting scheduler: {e}")
            raise

    def shutdown(self):
        """Gracefully shut down the scheduler."""
        try:
            self.scheduler.shutdown()
            logging.info("CoinScheduler shut down")
            print("CoinScheduler stopped.")
        except Exception as e:
            logging.error(f"Error shutting down scheduler: {e}")
            print(f"Error shutting down scheduler: {e}")