from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
import json
import os
from datetime import datetime, timezone, timedelta
import time
import requests
from app.services.coin_extractor import TopCoinsExtractor
from app.services.coin_history import CoinHistory
from app.services.coin_news import NewsSentimentService
from app.services.coin_stats import CoinStatsService
from app.services.file_manager import DataCleaner
from app.trader_bot.coin_trader import CoinTrader
from app.services.capital_manager import CapitalManager
from config import config


class CoinScheduler:
    def __init__(
        self,
        log_file="scheduler.log",
        execution_log_file="data/scheduler/execution_log.json",
        trading_config=None,
        auto_trigger=True,
        continue_on_failure=False,
    ):
        self.auto_trigger = auto_trigger
        self.continue_on_failure = continue_on_failure
        self._setup_logging(log_file)
        logging.info("Initializing CoinScheduler")

        self.scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=5)},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 600,
            },
        )

        self.extractor = TopCoinsExtractor()
        self.history_service = CoinHistory()
        self.sentiment_service = NewsSentimentService()
        self.stats_service = CoinStatsService()
        self.cleaner = DataCleaner()

        self.trading_config = trading_config or {
            "enabled": True,
            "initial_capital": 1000.0,
            "override": False,
        }
        if self.trading_config["enabled"]:
            self.capital_manager = CapitalManager(
                initial_capital=self.trading_config["initial_capital"]
            )

        self.execution_log_file = execution_log_file
        self.ensure_directory_exists(self.execution_log_file)

        self._job_locks = {
            "top_coins": False,
            "coin_history": False,
            "news_sentiment": False,
            "coin_prices": False,
            "trading_bot": False,
            "data_cleanup": False,
        }

        self._last_top_coins_run = None
        self._last_coin_history_run = None
        self._last_news_sentiment_run = None

    ### Utility Methods
    def _setup_logging(self, log_file):
        """Configure logging for the scheduler."""
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def ensure_directory_exists(self, file_path):
        """Ensure the directory for the given file path exists."""
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logging.info(f"Created directory: {directory}")

    def load_execution_log(self):
        """Load the execution log from the JSON file."""
        try:
            if os.path.exists(self.execution_log_file):
                with open(self.execution_log_file, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error loading execution log: {e}")
        return {}

    def save_execution_log(self, log_data):
        """Save the execution log to the JSON file."""
        try:
            self.ensure_directory_exists(self.execution_log_file)
            with open(self.execution_log_file, "w") as f:
                json.dump(log_data, f, indent=4)
            logging.info(f"Saved execution log to {self.execution_log_file}")
        except IOError as e:
            logging.error(f"Error saving execution log: {e}")

    def update_execution_log_with_duration(
        self, job_id, job_name, start_time, end_time, status="completed"
    ):
        """Update the execution log with execution duration and status."""
        log_data = self.load_execution_log()
        duration = (end_time - start_time).total_seconds()
        log_data[job_id] = {
            "job_name": job_name,
            "last_execution": start_time.isoformat(),
            "execution_duration": duration,
            "status": status,
        }
        self.save_execution_log(log_data)
        logging.info(
            f"Updated execution log for {job_id}: duration {duration:.2f}s, status: {status}"
        )

    def send_n8n_report(self, title, content, is_error=False):
        """Send a report to n8n webhook endpoint."""
        try:
            markdown_report = (
                f"# {'Error: ' if is_error else ''}{title}\n\n"
                f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"**Status:** {'Failed' if is_error else 'Success'}\n"
                f"**Duration:** {content.split('Duration: ')[1].split('s')[0] + 's' if 'Duration: ' in content else 'N/A'}\n\n"
            )
            headers = {"x-n8n-secret": config.n8n_webhook_secret}
            response = requests.post(
                config.n8n_webhook_url,
                headers=headers,
                json={"text": markdown_report},
                timeout=30,
            )
            response.raise_for_status()
            logging.info(
                f"{'Error' if is_error else 'Success'} report sent to n8n: {title}"
            )
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to send report to n8n: {e}")
            return False

    ### Job Execution Helpers
    def _retry_operation(self, operation, job_name, max_retries=3, retry_delay=5):
        """Handle aprilieHandle retries for an operation."""
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Starting {job_name} (attempt {attempt})")
                operation()
                logging.info(f"Completed {job_name}")
                return
            except Exception as e:
                logging.error(f"{job_name} attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise

    def _execute_with_lock(self, job_key, job_func, job_name, *args, **kwargs):
        """Execute a job with a lock to prevent duplicates."""
        if self._job_locks.get(job_key, False):
            logging.warning(f"Skipping {job_name} - already running")
            return False

        try:
            self._job_locks[job_key] = True
            start_time = datetime.now(timezone.utc)

            self._retry_operation(lambda: job_func(*args, **kwargs), job_name)

            end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                job_key, job_name, start_time, end_time
            )
            return True

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                job_key, job_name, start_time, end_time, "failed"
            )
            self.send_n8n_report(
                title=f"Job Failed: {job_name}",
                content=f"Error: {str(e)}",
                is_error=True,
            )
            return self.continue_on_failure
        finally:
            self._job_locks[job_key] = False

    def _schedule_dependent_job(self, job_func, job_name, delay_seconds, job_prefix):
        """Schedule dependent jobs with error handling."""
        try:
            run_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            job_id = f"{job_prefix}_{int(time.time())}"
            self.scheduler.add_job(
                job_func,
                "date",
                run_date=run_time,
                id=job_id,
                replace_existing=True,
            )
            logging.info(f"Scheduled {job_name} to run at {run_time} with ID {job_id}")
        except Exception as e:
            logging.error(f"Failed to schedule {job_name}: {e}")

    ### Job-Specific Execution Methods
    def execute_top_coins(self):
        """Execute the top coins extraction job."""

        def operation():
            top_coins = self.extractor.fetch_coin_data()
            saved_file = self.extractor.save_to_json(top_coins)
            logging.info(f"Saved top coins to: {saved_file}")

        success = self._execute_with_lock(
            "top_coins", operation, "Top Coins Extraction"
        )
        if success:
            self._last_top_coins_run = datetime.now(timezone.utc)
            self.on_top_coins_success()

    def execute_coin_history(self, limit=None):
        """Execute the coin history download job."""

        def operation():
            coins_data = self.extractor.load_most_recent_data() or []
            effective_limit = limit if limit is not None else config.coin_limit
            coins_data = coins_data[:effective_limit]
            if not coins_data:
                logging.warning("No coins data available for history download")
                return
            successful_downloads = 0
            failed_downloads = 0
            for i, coin in enumerate(coins_data, 1):
                slug = coin.get("slug")
                coin_name = coin.get("name", "Unknown")
                if not slug or slug == "N/A":
                    logging.warning(
                        f"[{i}/{len(coins_data)}] Skipping invalid slug for {coin_name}"
                    )
                    continue
                try:
                    logging.info(
                        f"[{i}/{len(coins_data)}] Starting history download for {coin_name} ({slug})"
                    )
                    self.history_service.download_history(coin=slug)
                    successful_downloads += 1
                    logging.info(
                        f"[{i}/{len(coins_data)}] ✓ Downloaded history for {coin_name} ({slug})"
                    )
                except Exception as e:
                    failed_downloads += 1
                    logging.error(
                        f"[{i}/{len(coins_data)}] ✗ Failed to download history for {coin_name} ({slug}): {e}"
                    )
                    if not self.continue_on_failure:
                        raise
            logging.info(
                f"Coin history download completed: {successful_downloads} successful, {failed_downloads} failed out of {len(coins_data)} total coins"
            )
            self.send_n8n_report(
                title="Coin History Job Completed",
                content=f"Status: Success\nSuccessful downloads: {successful_downloads}\nFailed downloads: {failed_downloads}",
                is_error=False,
            )

        # Fixed call: No extra argument passed
        success = self._execute_with_lock("coin_history", operation, "Coin History")
        if success:
            self._last_coin_history_run = datetime.now(timezone.utc)
            self.on_coin_history_success()

    def execute_news_sentiment(self, limit=None, force=False):
        """Execute the news sentiment extraction job."""
        if not force and not self._last_coin_history_run:
            logging.warning("News sentiment skipped - coin history hasn't run yet")
            return

        def operation():
            coins_data = self.extractor.load_most_recent_data() or []
            effective_limit = limit if limit is not None else config.coin_limit
            coins_data = coins_data[:effective_limit]
            if not coins_data:
                logging.warning("No coins data available for news sentiment")
                return

            successful_fetches = 0
            failed_fetches = 0
            for i, coin in enumerate(coins_data, 1):
                slug = coin.get("slug")
                coin_name = coin.get("name", "Unknown")
                if not slug or slug == "N/A":
                    logging.warning(
                        f"[{i}/{len(coins_data)}] Skipping invalid slug for {coin_name}"
                    )
                    continue
                try:
                    logging.info(
                        f"[{i}/{len(coins_data)}] Fetching news sentiment for {coin_name} ({slug})"
                    )
                    self.sentiment_service.fetch_news_and_sentiment(slug)
                    successful_fetches += 1
                    logging.info(
                        f"[{i}/{len(coins_data)}] ✓ Fetched news sentiment for {coin_name} ({slug})"
                    )
                except Exception as e:
                    failed_fetches += 1
                    logging.error(
                        f"[{i}/{len(coins_data)}] ✗ Failed to fetch news sentiment for {coin_name} ({slug}): {e}"
                    )
                    if not self.continue_on_failure:
                        raise
            logging.info(
                f"News sentiment fetch completed: {successful_fetches} successful, {failed_fetches} failed out of {len(coins_data)} total coins"
            )

        # Fixed call: No extra argument passed beyond the required ones
        success = self._execute_with_lock(
            "news_sentiment", operation, "News Sentiment Extraction"
        )
        if success:
            self._last_news_sentiment_run = datetime.now(timezone.utc)
            self.on_news_sentiment_success()

    def execute_coin_prices(self, limit=None):
        """Execute the coin prices fetch job."""

        def operation():
            coins_data = self.extractor.load_most_recent_data() or []
            effective_limit = limit if limit is not None else config.coin_limit
            coins_data = coins_data[:effective_limit]
            if not coins_data:
                logging.warning("No coins data available for price fetching")
                return

            successful_fetches = 0
            failed_fetches = 0
            for i, coin in enumerate(coins_data, 1):
                slug = coin.get("slug")
                coin_name = coin.get("name", "Unknown")
                if not slug or slug == "N/A":
                    logging.warning(
                        f"[{i}/{len(coins_data)}] Skipping invalid slug for {coin_name}"
                    )
                    continue
                try:
                    logging.info(
                        f"[{i}/{len(coins_data)}] Fetching coin stats for {coin_name} ({slug})"
                    )
                    self.stats_service.fetch_and_save_coin_stats(slug)
                    successful_fetches += 1
                    logging.info(
                        f"[{i}/{len(coins_data)}] ✓ Fetched coin stats for {coin_name} ({slug})"
                    )
                except Exception as e:
                    failed_fetches += 1
                    logging.error(
                        f"[{i}/{len(coins_data)}] ✗ Failed to fetch coin stats for {coin_name} ({slug}): {e}"
                    )
                    if not self.continue_on_failure:
                        raise
            logging.info(
                f"Coin prices fetch completed: {successful_fetches} successful, {failed_fetches} failed out of {len(coins_data)} total coins"
            )

        # Fixed call: No extra argument passed
        success = self._execute_with_lock("coin_prices", operation, "Coin Prices")
        if success:
            self.on_coin_prices_success()

    def execute_trading_bot(self, limit=None):
        """Execute the trading bot job."""
        if not self.trading_config["enabled"]:
            logging.info("Trading bot is disabled")
            return

        def operation():
            activities_file = "data/activities/coin_reports.json"
            os.makedirs(os.path.dirname(activities_file), exist_ok=True)
            with open(activities_file, "w") as f:
                json.dump({}, f)
            coins_data = self.extractor.load_most_recent_data() or []
            effective_limit = limit if limit is not None else config.coin_limit
            coins_data = coins_data[:effective_limit]
            for i, coin in enumerate(coins_data, 1):
                slug = coin.get("slug")
                if slug and slug != "N/A":
                    try:
                        logging.info(
                            f"[{i}/{len(coins_data)}] Executing trading for {slug}"
                        )
                        trader = CoinTrader(
                            coin=slug,
                            override=self.trading_config["override"],
                            capital_manager=self.capital_manager,
                        )
                        trader.run()
                        logging.info(
                            f"[{i}/{len(coins_data)}] Completed trading for {slug}"
                        )
                    except Exception as e:
                        logging.error(f"Trading failed for {slug}: {e}")
                        if not self.continue_on_failure:
                            raise
                else:
                    logging.warning(
                        f"Skipping invalid slug for {coin.get('name', 'Unknown')}"
                    )
            self._save_profit_snapshot()
            with open(activities_file, "r") as f:
                activities = json.load(f)
                summary = (
                    "Trading Activities:\n"
                    if isinstance(activities, dict) and activities
                    else "No trading activities to report\n"
                )
                for coin, data in activities.items():
                    report = data.get("report", "N/A")
                    summary += f"- {coin}: {report}\n"
                self.send_n8n_report(
                    title="Trading Bot Activities",
                    content=summary,
                    is_error=False,
                )

        # Fixed call: No extra argument passed
        self._execute_with_lock("trading_bot", operation, "Trading Bot Execution")

    def execute_data_cleanup(self):
        """Execute the data cleanup job."""

        def operation():
            self.cleaner.clean_timestamped_files()

        self._execute_with_lock("data_cleanup", operation, "Data Cleanup")

    ### Dependency Handling Methods
    def on_top_coins_success(self):
        """Schedule dependent jobs after top coins extraction."""
        self._schedule_dependent_job(
            self.execute_coin_history, "Coin History", 30, "coin_history_dep"
        )
        self._schedule_dependent_job(
            self.execute_data_cleanup, "Data Cleanup", 60, "data_cleanup"
        )

    def on_coin_history_success(self):
        """Schedule dependent jobs after coin history download."""
        self._schedule_dependent_job(
            self.execute_news_sentiment, "News Sentiment", 5, "news_sentiment_dep"
        )

    def on_news_sentiment_success(self):
        """Schedule dependent jobs after news sentiment extraction."""
        self._schedule_dependent_job(
            self.execute_coin_prices, "Coin Prices", 5, "coin_prices_dep"
        )

    def on_coin_prices_success(self):
        """Schedule dependent jobs after coin prices fetch."""
        if self.trading_config["enabled"]:
            self._schedule_dependent_job(
                self.execute_trading_bot, "Trading Bot", 5, "trading_bot"
            )

    ### Main Execution Methods
    def run_complete_pipeline_now(self):
        """Run the complete pipeline immediately for testing."""
        logging.info("=== MANUAL PIPELINE EXECUTION STARTED ===")
        steps = [
            (self.execute_top_coins, "Extracting top coins"),
            (
                lambda: self.execute_coin_history(config.coin_limit),
                "Downloading coin history",
            ),
            (
                lambda: self.execute_news_sentiment(config.coin_limit),
                "Fetching news sentiment",
            ),
            (
                lambda: self.execute_coin_prices(config.coin_limit),
                "Fetching coin prices",
            ),
            (
                lambda: (
                    self.execute_trading_bot(config.coin_limit)
                    if self.trading_config["enabled"]
                    else True
                ),
                "Executing trading bot",
            ),
            (self.execute_data_cleanup, "Cleaning up data"),
        ]
        for step_func, step_name in steps:
            logging.info(f"Step: {step_name}...")
            if not step_func():
                logging.error(f"{step_name} failed, stopping pipeline")
                if not self.continue_on_failure:
                    return
        logging.info("=== MANUAL PIPELINE EXECUTION COMPLETED ===")

    def configure_jobs(self):
        """Configure the scheduler with custom timing."""
        self.scheduler.add_job(
            self.execute_top_coins,
            CronTrigger(hour=0, minute=20),
            id="top_coins_daily",
            replace_existing=True,
        )
        self.scheduler.add_job(
            lambda: self.execute_news_sentiment(force=True),
            IntervalTrigger(hours=4),
            id="news_sentiment_4h",
            replace_existing=True,
        )
        if self.auto_trigger:
            self.scheduler.add_job(
                self.check_and_trigger_top_coins,
                IntervalTrigger(hours=1),
                id="check_top_coins",
                replace_existing=True,
            )
        logging.info("Scheduler jobs configured")

    def start(self):
        """Start the scheduler with an initial check if auto_trigger is True."""
        try:
            if self.auto_trigger:
                self.check_and_trigger_top_coins()
            self.configure_jobs()
            self.scheduler.start()
            self.send_n8n_report(
                title="CoinScheduler Started",
                content=f"Scheduler initialized successfully\nAuto-Trigger: {self.auto_trigger}\nContinue on Failure: {self.continue_on_failure}",
                is_error=False,
            )
        except Exception as e:
            self.send_n8n_report(
                title="Scheduler Startup Error",
                content=f"Error: {str(e)}",
                is_error=True,
            )
            raise

    def shutdown(self):
        """Gracefully shut down the scheduler."""
        try:
            self.scheduler.shutdown()
            trading_summary = (
                self.get_trading_summary()
                if self.trading_config["enabled"]
                else "Trading disabled"
            )
            self.send_n8n_report(
                title="CoinScheduler Shutdown",
                content=f"Scheduler stopped\n{trading_summary}",
                is_error=False,
            )
        except Exception as e:
            self.send_n8n_report(
                title="Scheduler Shutdown Error",
                content=f"Error: {str(e)}",
                is_error=True,
            )

    def check_and_trigger_top_coins(self):
        """Check if top coins job has run in the last 6 hours and trigger if not."""
        log_data = self.load_execution_log()
        last_run_str = log_data.get("top_coins", {}).get("last_execution")
        if (
            not last_run_str
            or (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_run_str)
            ).total_seconds()
            > 6 * 3600
        ):
            logging.info("Top coins job hasn't run in 6 hours. Triggering now.")
            self.execute_top_coins()

    ### Manual Trigger and Utility Methods
    def trigger_top_coins_now(self):
        """Manually trigger the top coins extraction job."""
        self.execute_top_coins()

    def trigger_news_sentiment_now(self, force=False):
        """Manually trigger the news sentiment extraction job."""
        self.execute_news_sentiment(force=force)

    def run_single_cycle(self):
        """Run a single complete cycle immediately (useful for testing)."""
        self.run_complete_pipeline_now()

    def get_trading_summary(self):
        """Get a summary of trading activities and capital status."""
        if not self.trading_config["enabled"]:
            return "Trading is disabled"
        try:
            coins_data = self.extractor.load_most_recent_data() or []
            summary = []
            for coin in coins_data:
                slug = coin.get("slug")
                if slug and slug != "N/A":
                    capital = self.capital_manager.get_capital(slug)
                    position = self.capital_manager.get_position(slug)
                    summary.append(
                        f"{coin.get('name', 'Unknown').upper()} ({slug}): ${capital:.2f} capital, {position:.2f} position"
                    )
            return "\n".join(summary) if summary else "No trading data available"
        except Exception as e:
            return f"Error getting trading summary: {e}"

    def _save_profit_snapshot(self):
        """Save a snapshot of current profit metrics."""
        if not self.trading_config["enabled"]:
            logging.info("Trading is disabled, skipping profit snapshot")
            return
        try:
            self.capital_manager.save_profit_snapshot()
            logging.info("Profit snapshot saved successfully")
        except Exception as e:
            logging.error(f"Failed to save profit snapshot: {str(e)}")
