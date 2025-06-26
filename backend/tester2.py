from app.services.coin_scheduler import CoinScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
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

# Test scheduler class with parallel execution capability
class TestCoinScheduler(CoinScheduler):
    def __init__(self, log_file='scheduler_test.log', trading_config=None):
        super().__init__(log_file, trading_config=trading_config)
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=5)},  # Allow up to 5 concurrent jobs
            job_defaults={
                'coalesce': False,  # Don't skip missed jobs
                'max_instances': 1,  # Only one instance of each job at a time
                'misfire_grace_time': 300  # Allow 5 minutes grace period for missed jobs
            }
        )

    def configure_jobs(self):
        """Configure jobs to run once, allowing for parallel execution."""
        base_time = datetime.now() + timedelta(seconds=30)
        
        self.scheduler.add_job(
            self._daily_top_coin_list,
            DateTrigger(run_date=base_time),
            id='top_coins',
            name='Top Coins Extraction'
        )
        
        self.scheduler.add_job(
            self._daily_coin_history,
            DateTrigger(run_date=base_time + timedelta(seconds=30)),
            id='coin_history',
            name='Coin History Extraction',
            kwargs={'limit': 1}
        )
        
        self.scheduler.add_job(
            self._daily_news_sentiment,
            DateTrigger(run_date=base_time + timedelta(seconds=35)),
            id='news_sentiment',
            name='News Sentiment Extraction',
            kwargs={'limit': 1}
        )
        
        self.scheduler.add_job(
            self._daily_coin_prices,
            DateTrigger(run_date=base_time + timedelta(seconds=40)),
            id='coin_prices',
            name='Coin Prices Update',
            kwargs={'limit': 1}
        )
        
        self.scheduler.add_job(
            self._daily_data_cleaner,
            DateTrigger(run_date=base_time + timedelta(seconds=45)),
            id='data_cleanup',
            name='Data Cleanup'
        )
        
        # Add trading bot job if trading is enabled
        if self.trading_config.get('enabled', False):
            self.scheduler.add_job(
                self._trading_bot_execution,
                DateTrigger(run_date=base_time + timedelta(seconds=50)),
                id='trading_bot',
                name='Trading Bot Execution',
                kwargs={'limit': 1}
            )
        
        logging.info("Test scheduler jobs configured for parallel execution")
        
        for job in self.scheduler.get_jobs():
            logging.info(f"Scheduled {job.name} at {job.next_run_time}")

# Alternative approach: Sequential with proper timing
class SequentialTestScheduler(CoinScheduler):
    def __init__(self, log_file='scheduler_test.log', trading_config=None):
        super().__init__(log_file, trading_config=trading_config)
        self.scheduler = BackgroundScheduler(
            executors={'default': ThreadPoolExecutor(max_workers=1)},
            job_defaults={
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 600  # 10 minutes grace period
            }
        )

    def configure_jobs(self):
        """Configure jobs to run sequentially with proper timing based on estimated durations."""
        durations = {
            'top_coins': 30,      # ~17 seconds actual + buffer
            'coin_history': 180,  # ~162 seconds actual + buffer
            'news_sentiment': 60, # Estimated
            'coin_prices': 60,    # Estimated
            'data_cleanup': 30,   # ~5 seconds actual + buffer
            'trading_bot': 60     # Estimated duration for trading bot
        }
        
        base_time = datetime.now() + timedelta(seconds=30)
        current_time = base_time
        
        jobs_config = [
            ('top_coins', 'Top Coins Extraction', self._daily_top_coin_list, {}),
            ('coin_history', 'Coin History Extraction', self._daily_coin_history, {'limit': 1}),
            ('news_sentiment', 'News Sentiment Extraction', self._daily_news_sentiment, {'limit': 1}),
            ('coin_prices', 'Coin Prices Update', self._daily_coin_prices, {'limit': 1}),
            ('data_cleanup', 'Data Cleanup', self._daily_data_cleaner, {})
        ]
        
        # Add trading bot job if trading is enabled
        if self.trading_config.get('enabled', False):
            jobs_config.append(('trading_bot', 'Trading Bot Execution', self._trading_bot_execution, {'limit': 1}))
        
        for job_id, job_name, job_func, job_kwargs in jobs_config:
            self.scheduler.add_job(
                job_func,
                DateTrigger(run_date=current_time),
                id=job_id,
                name=job_name,
                kwargs=job_kwargs
            )
            logging.info(f"Scheduled {job_name} at {current_time}")
            current_time += timedelta(seconds=durations[job_id])

# Run the scheduler
if __name__ == "__main__":
    print("Choose scheduler type:")
    print("1. Parallel execution (faster, but may have resource conflicts)")
    print("2. Sequential execution (safer, properly timed)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    # Example trading configuration
    trading_config = {
        'enabled': True,
        'coins': ['bitcoin'],
        'initial_capital': 1000.0,
        'override': False
    }
    
    if choice == "1":
        test_scheduler = TestCoinScheduler(trading_config=trading_config)
        total_wait_time = 300  # 5 minutes for parallel execution
    else:
        test_scheduler = SequentialTestScheduler(trading_config=trading_config)
        total_wait_time = 600  # 10 minutes for sequential execution to include trading bot
    
    test_scheduler.start()
    try:
        logging.info(f"Waiting {total_wait_time} seconds for all jobs to complete")
        time.sleep(total_wait_time)
    except KeyboardInterrupt:
        print("Test interrupted by user")
    finally:
        test_scheduler.shutdown()
        print("Test scheduler shut down")