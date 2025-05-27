from app.services.coin_scheduler import CoinScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor  # Use APScheduler's ThreadPoolExecutor
from datetime import datetime, timedelta
import time
import logging
import json
import os

# Set up logging to console for easy observation during testing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path to execution log file (must match CoinScheduler)
EXECUTION_LOG_FILE = 'data/scheduler/execution_log.json'

def load_execution_durations():
    """Load execution durations from execution_log.json."""
    if os.path.exists(EXECUTION_LOG_FILE):
        try:
            with open(EXECUTION_LOG_FILE, 'r') as f:
                log_data = json.load(f)
                # Return durations for each job (in seconds) or None if not available
                return {
                    'top_coins': log_data.get('top_coins', {}).get('execution_duration'),
                    'coin_history': log_data.get('coin_history', {}).get('execution_duration'),
                    'news_sentiment': log_data.get('news_sentiment', {}).get('execution_duration'),
                    'coin_prices': log_data.get('coin_prices', {}).get('execution_duration'),
                    'data_cleanup': log_data.get('data_cleanup', {}).get('execution_duration'),
                }
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading execution log: {e}")
    return {
        'top_coins': None,
        'coin_history': None,
        'news_sentiment': None,
        'coin_prices': None,
        'data_cleanup': None,
    }

# Define job order and default durations (in seconds) if no prior data
JOB_ORDER = [
    ('top_coins', 'Top Coins Extraction'),
    ('coin_history', 'Coin History Extraction'),
    ('news_sentiment', 'News Sentiment Extraction'),
    ('coin_prices', 'Coin Prices Update'),
    ('data_cleanup', 'Data Cleanup'),
]
DEFAULT_DURATION = 60  # Default duration for jobs with no prior run
BUFFER_SECONDS = 10    # Buffer between jobs to avoid overlap

# Calculate run times based on previous durations
durations = load_execution_durations()
run_times = {}
current_time = datetime.now() + timedelta(seconds=30)  # Start first job in 30 seconds
for job_id, job_name in JOB_ORDER:
    duration = durations[job_id] if durations[job_id] is not None else DEFAULT_DURATION
    run_times[job_id] = current_time
    current_time += timedelta(seconds=duration + BUFFER_SECONDS)  # Add duration + buffer

# Log the planned schedule
for job_id, job_name in JOB_ORDER:
    logging.info(f"Scheduled {job_name} to start at {run_times[job_id]} (estimated duration: {durations[job_id] or DEFAULT_DURATION}s)")

# Test scheduler class
class TestCoinScheduler(CoinScheduler):
    def __init__(self, log_file='scheduler_test.log'):
        super().__init__(log_file)
        self.scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(max_workers=1)})  # Use APScheduler's ThreadPoolExecutor

    def configure_jobs(self):
        """Configure jobs to run once at dynamically calculated times."""
        # self.scheduler.add_job(
        #     self._daily_top_coin_list,
        #     DateTrigger(run_date=run_times['top_coins']),
        #     id='top_coins',
        #     name='Top Coins Extraction'
        # )
        self.scheduler.add_job(
            self._daily_coin_history,
            DateTrigger(run_date=run_times['coin_history']),
            id='coin_history',
            name='Coin History Extraction',
            kwargs={'limit': 15}  # Pass the 'limit' parameter here
        )
        self.scheduler.add_job(
            self._daily_news_sentiment,
            DateTrigger(run_date=run_times['news_sentiment']),
            id='news_sentiment',
            name='News Sentiment Extraction'
        )
        self.scheduler.add_job(
            self._daily_coin_prices,
            DateTrigger(run_date=run_times['coin_prices']),
            id='coin_prices',
            name='Coin Prices Update'
        )
        self.scheduler.add_job(
            self._daily_data_cleaner,
            DateTrigger(run_date=run_times['data_cleanup']),
            id='data_cleanup',
            name='Data Cleanup'
        )
        logging.info("Test scheduler jobs configured to run sequentially")

# Run the scheduler
if __name__ == "__main__":
    test_scheduler = TestCoinScheduler()
    test_scheduler.start()
    try:
        # Calculate total wait time: last job start + max possible duration + buffer
        last_start = max(run_times.values())
        total_wait = (last_start - datetime.now()).total_seconds() + DEFAULT_DURATION + BUFFER_SECONDS
        logging.info(f"Waiting {total_wait:.0f} seconds for all jobs to complete")
        time.sleep(total_wait)
    except KeyboardInterrupt:
        print("Test interrupted by user")
    finally:
        test_scheduler.shutdown()
        print("Test scheduler shut down")