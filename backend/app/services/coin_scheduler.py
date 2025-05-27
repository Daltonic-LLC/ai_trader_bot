from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import json
import os
from datetime import datetime
from app.services.coin_extractor import TopCoinsExtractor
from app.services.coin_history import CoinHistory
from app.services.coin_news import NewsSentimentService
from app.services.coin_stats import CoinStatsService
from app.services.file_manager import DataCleaner

class CoinScheduler:
    def __init__(self, log_file='scheduler.log', execution_log_file='data/scheduler/execution_log.json'):
        """Initialize the CoinScheduler with a background scheduler, logging, and execution log file."""
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

        # Execution log file path
        self.execution_log_file = execution_log_file
        self.ensure_directory_exists()

    def _setup_logging(self, log_file):
        """Configure logging for the scheduler."""
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def ensure_directory_exists(self):
        """Ensure the directory for the execution log file exists."""
        directory = os.path.dirname(self.execution_log_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Created directory: {directory}")

    def load_execution_log(self):
        """Load the execution log from the JSON file."""
        if os.path.exists(self.execution_log_file):
            try:
                with open(self.execution_log_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading execution log from {self.execution_log_file}: {e}")
                return {}
        return {}

    def save_execution_log(self, log_data):
        """Save the execution log to the JSON file."""
        try:
            self.ensure_directory_exists()
            with open(self.execution_log_file, 'w') as f:
                json.dump(log_data, f, indent=4)
            logging.info(f"Saved execution log to {self.execution_log_file}")
        except IOError as e:
            logging.error(f"Error saving execution log to {self.execution_log_file}: {e}")

    def update_execution_log(self, job_id, job_name, last_execution=None):
        """Update the execution log for a job with last and next execution times."""
        log_data = self.load_execution_log()
        job = self.scheduler.get_job(job_id)
        if job:
            next_run_time = job.next_run_time
            if next_run_time is None and last_execution:
                # Calculate next run time manually using the job's trigger
                now = datetime.now(job.trigger.timezone)
                next_run_time = job.trigger.get_next_fire_time(last_execution, now)
            next_execution = next_run_time.isoformat() if next_run_time else None
        else:
            next_execution = None

        log_data[job_id] = {
            "job_name": job_name,
            "last_execution": last_execution.isoformat() if last_execution else log_data.get(job_id, {}).get("last_execution"),
            "next_execution": next_execution
        }
        self.save_execution_log(log_data)

    def _daily_top_coin_list(self):
        """Extract top coins and save them to a JSON file."""
        logging.info("Starting daily top coins extraction")
        try:
            top_coins = self.extractor.fetch_coin_data()  # Use the correct method name
            saved_file = self.extractor.save_to_json(top_coins)
            message = f"Saved top coins to: {saved_file}"
            logging.info(message)
            print(message)
            # Update execution log if applicable
            self.update_execution_log("top_coins", "Top Coins Extraction", last_execution=datetime.now())
        except Exception as e:
            logging.error(f"Error during top coins extraction: {e}")
            print(f"Error: {e}")

    def _daily_coin_history(self, limit=None):
        """Load top coins and extract historical data for a specified number of slugs."""
        logging.info("Starting daily coin history extraction")
        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for history extraction")
                print("No top coins data found. Run top coins extraction first.")
                return

            # Limit the number of coins to process if a limit is specified
            if limit is not None:
                coins_data = coins_data[:limit]

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
            # Update execution log on successful completion
            self.update_execution_log("coin_history", "Coin History Extraction", last_execution=datetime.now())
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
            # Update execution log on successful completion
            self.update_execution_log("news_sentiment", "News Sentiment Extraction", last_execution=datetime.now())
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
            # Update execution log on successful completion
            self.update_execution_log("coin_prices", "Coin Prices Update", last_execution=datetime.now())
        except Exception as e:
            logging.error(f"Error during coin prices job: {e}")
            print(f"Error in coin prices job: {e}")

    def _daily_data_cleaner(self):
        """Clean up duplicate files in the data directory."""
        logging.info("Starting daily data cleanup")
        try:
            self.cleaner.clean_timestamped_files()
            logging.info("Completed daily data cleanup")
            # Update execution log on successful completion
            self.update_execution_log("data_cleanup", "Data Cleanup", last_execution=datetime.now())
        except Exception as e:
            logging.error(f"Error during data cleanup: {e}")
            print(f"Error during data cleanup: {e}")

    def configure_jobs(self):
        """Configure the scheduler with all jobs and their triggers."""
        # Define jobs with their IDs, names, and triggers
        jobs = [
            {
                "id": "top_coins",
                "name": "Top Coins Extraction",
                "func": self._daily_top_coin_list,
                "trigger": IntervalTrigger(hours=12)
            },
            {
                "id": "coin_history",
                "name": "Coin History Extraction",
                "func": lambda: self._daily_coin_history(limit=15),
                "trigger": CronTrigger(hour=0, minute=20)
            },
            {
                "id": "news_sentiment",
                "name": "News Sentiment Extraction",
                "func": self._daily_news_sentiment,
                "trigger": IntervalTrigger(hours=4)
            },
            {
                "id": "coin_prices",
                "name": "Coin Prices Update",
                "func": self._daily_coin_prices,
                "trigger": IntervalTrigger(hours=1)
            },
            {
                "id": "data_cleanup",
                "name": "Data Cleanup",
                "func": self._daily_data_cleaner,
                "trigger": CronTrigger(hour=1, minute=0)
            }
        ]

        # Add jobs to scheduler and initialize execution log
        log_data = self.load_execution_log()
        for job in jobs:
            self.scheduler.add_job(
                job["func"],
                job["trigger"],
                id=job["id"],
                name=job["name"]
            )
            # Initialize log entry if not present
            if job["id"] not in log_data:
                next_execution = self.scheduler.get_job(job["id"]).next_run_time.isoformat() if self.scheduler.get_job(job["id"]) else None
                log_data[job["id"]] = {
                    "job_name": job["name"],
                    "last_execution": None,
                    "next_execution": next_execution
                }
        self.save_execution_log(log_data)

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