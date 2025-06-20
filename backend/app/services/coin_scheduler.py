from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
import json
import os
from datetime import datetime, timezone
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
        """Initialize the CoinScheduler with custom timing and dependencies."""
        self.auto_trigger = auto_trigger
        self.continue_on_failure = continue_on_failure
        self._setup_logging(log_file)
        logging.info("Initializing CoinScheduler")

        # Initialize scheduler
        self.scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=5)},
            job_defaults={
                "coalesce": False,
                "max_instances": 1,
                "misfire_grace_time": 600,
            },
        )

        # Initialize services
        self.extractor = TopCoinsExtractor()
        self.history_service = CoinHistory()
        self.sentiment_service = NewsSentimentService()
        self.stats_service = CoinStatsService()
        self.cleaner = DataCleaner()

        # Trading configuration
        self.trading_config = trading_config or {
            "enabled": True,
            "initial_capital": 1000.0,
            "override": False,
        }
        if self.trading_config["enabled"]:
            self.capital_manager = CapitalManager(
                initial_capital=self.trading_config["initial_capital"]
            )

        # Execution log
        self.execution_log_file = execution_log_file
        self.ensure_directory_exists(self.execution_log_file)

        # Progress tracking file
        self.coin_progress_file = "data/scheduler/coin_progress.json"
        self.ensure_directory_exists(self.coin_progress_file)

        # Shared state for job dependencies
        self._last_top_coins_run = None
        self._last_coin_history_run = None
        self._last_news_sentiment_run = None

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
                f"# {'🚨 ' if is_error else ''}{title}\n\n"
                f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"```\n{content}\n```"
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

    def _retry_operation(self, operation, job_name, max_retries=3, retry_delay=5):
        """Handle retries for an operation."""
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Starting {job_name} (attempt {attempt})")
                operation()
                logging.info(f"Completed {job_name}")
                return
            except Exception as e:
                logging.error(f"{job_name} attempt {attempt} failed: {e}")
                self.send_n8n_report(
                    title=f"{job_name} Retry Attempt {attempt} Failed",
                    content=f"Attempt: {attempt}/{max_retries}\nError: {str(e)}",
                    is_error=True,
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise

    def _schedule_dependent_job(
        self,
        delay_seconds,
        job_func,
        job_name,
        next_job_info=None,
        job_args=(),
        job_kwargs={},
    ):
        """Schedule a job to run after a specified delay with optional next job scheduling."""

        def delayed_job():
            time.sleep(delay_seconds)
            start_time = datetime.now(timezone.utc)
            job_failed = False
            try:
                self._retry_operation(
                    lambda: job_func(*job_args, **job_kwargs), job_name
                )
                end_time = datetime.now(timezone.utc)
                self.update_execution_log_with_duration(
                    job_name.lower().replace(" ", "_"), job_name, start_time, end_time
                )
                self.send_n8n_report(
                    title=f"Job Completed: {job_name}",
                    content=f"Status: Success\nDuration: {(end_time - start_time).total_seconds():.2f}s",
                    is_error=False,
                )
            except Exception as e:
                end_time = datetime.now(timezone.utc)
                job_failed = True
                self.update_execution_log_with_duration(
                    job_name.lower().replace(" ", "_"),
                    job_name,
                    start_time,
                    end_time,
                    "failed",
                )
                self.send_n8n_report(
                    title=f"Job Failed: {job_name}",
                    content=f"Error: {str(e)}",
                    is_error=True,
                )
                if not self.continue_on_failure:
                    return

            if next_job_info and (not job_failed or self.continue_on_failure):
                self._schedule_dependent_job(*next_job_info)

        self.scheduler.add_job(
            delayed_job,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"{job_name.lower().replace(' ', '_')}_{int(time.time())}",
        )

    def _top_coins_with_dependencies(self):
        """Top coins extraction with dependent jobs scheduled."""
        start_time = datetime.now(timezone.utc)
        job_failed = False
        try:
            self._retry_operation(self._daily_top_coin_list, "Top Coins Extraction")
            end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "top_coins", "Top Coins Extraction", start_time, end_time
            )
            self._last_top_coins_run = end_time
            self.send_n8n_report(
                title="Job Completed: Top Coins Extraction",
                content=f"Status: Success\nDuration: {(end_time - start_time).total_seconds():.2f}s",
                is_error=False,
            )
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            job_failed = True
            self.update_execution_log_with_duration(
                "top_coins", "Top Coins Extraction", start_time, end_time, "failed"
            )
            self.send_n8n_report(
                title="Top Coins Extraction Error",
                content=f"Error: {str(e)}",
                is_error=True,
            )
            if not self.continue_on_failure:
                return

        if not job_failed or self.continue_on_failure:
            cleanup_info = (5, self._daily_data_cleaner, "Data Cleanup", None, (), {})
            history_info = (
                5,
                self._coin_history_with_cleanup,
                "Coin History with Cleanup",
                cleanup_info,
                (config.coin_limit,),
                {},
            )
            self._schedule_dependent_job(*history_info)

    def _coin_history_with_cleanup(self, limit=None):
        """Coin history extraction with cleanup dependency."""
        self._retry_operation(
            lambda: self._daily_coin_history(limit), "Coin History Extraction"
        )
        self._last_coin_history_run = datetime.now(timezone.utc)

    def _news_sentiment_with_dependencies(self, force=False):
        """News sentiment extraction with dependent jobs, optionally forcing execution."""
        if not force and not self._last_coin_history_run:
            logging.warning("News sentiment skipped - coin history hasn't run yet")
            return
        if force and not self._last_coin_history_run:
            logging.warning(
                "Running news sentiment with force=True, but coin history hasn't run yet"
            )

        start_time = datetime.now(timezone.utc)
        job_failed = False
        try:
            self._retry_operation(
                lambda: self._daily_news_sentiment(config.coin_limit),
                "News Sentiment Extraction",
            )
            end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "news_sentiment", "News Sentiment Extraction", start_time, end_time
            )
            self._last_news_sentiment_run = end_time
            self.send_n8n_report(
                title="Job Completed: News Sentiment Extraction",
                content=f"Status: Success\nDuration: {(end_time - start_time).total_seconds():.2f}s",
                is_error=False,
            )
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            job_failed = True
            self.update_execution_log_with_duration(
                "news_sentiment",
                "News Sentiment Extraction",
                start_time,
                end_time,
                "failed",
            )
            self.send_n8n_report(
                title="News Sentiment Extraction Error",
                content=f"Error: {str(e)}",
                is_error=True,
            )
            if not self.continue_on_failure:
                return

        if not job_failed or self.continue_on_failure:
            trading_info = (
                (
                    5,
                    self._trading_bot_execution,
                    "Trading Bot Execution",
                    None,
                    (config.coin_limit,),
                    {},
                )
                if self.trading_config["enabled"]
                else None
            )
            prices_info = (
                5,
                self._coin_prices_with_trading_chain,
                "Coin Prices with Trading",
                trading_info,
                (config.coin_limit,),
                {},
            )
            self._schedule_dependent_job(*prices_info)

    def _coin_prices_with_trading_chain(self, limit=None):
        """Coin prices update with trading dependency."""
        self._retry_operation(
            lambda: self._daily_coin_prices(limit), "Coin Prices Update"
        )

    def _daily_top_coin_list(self):
        """Extract top coins and save them to a JSON file."""
        top_coins = self.extractor.fetch_coin_data()
        saved_file = self.extractor.save_to_json(top_coins)
        logging.info(f"Saved top coins to: {saved_file}")

    def _daily_coin_history(self, limit=None):
        """Load top coins and extract historical data with progress tracking."""
        coins_data = self.extractor.load_most_recent_data() or []
        if limit:
            coins_data = coins_data[:limit]

        progress = self._load_progress("coin_history")

        for coin in coins_data:
            slug = coin.get("slug")
            if slug and slug != "N/A":
                if slug in progress:
                    logging.info(f"Skipping {slug} as it was already processed.")
                    continue
                try:
                    self.history_service.download_history(coin=slug)
                    progress[slug] = True
                    self._save_progress("coin_history", progress)
                except Exception as e:
                    logging.error(f"Failed to download history for {slug}: {e}")
                    if not self.continue_on_failure:
                        raise
            else:
                logging.warning(
                    f"Skipping invalid slug for {coin.get('name', 'Unknown')}"
                )

    def _daily_news_sentiment(self, limit=None):
        """Load top coins and fetch news sentiment with progress tracking."""
        coins_data = self.extractor.load_most_recent_data() or []
        if limit:
            coins_data = coins_data[:limit]

        progress = self._load_progress("news_sentiment")

        for coin in coins_data:
            slug = coin.get("slug")
            if slug and slug != "N/A":
                if slug in progress:
                    logging.info(f"Skipping {slug} as it was already processed.")
                    continue
                try:
                    self.sentiment_service.fetch_news_and_sentiment(slug)
                    progress[slug] = True
                    self._save_progress("news_sentiment", progress)
                except Exception as e:
                    logging.error(f"Failed to fetch news sentiment for {slug}: {e}")
                    if not self.continue_on_failure:
                        raise
            else:
                logging.warning(
                    f"Skipping invalid slug for {coin.get('name', 'Unknown')}"
                )

    def _daily_coin_prices(self, limit=None):
        """Load top coins and fetch latest prices with progress tracking."""
        coins_data = self.extractor.load_most_recent_data() or []
        if limit:
            coins_data = coins_data[:limit]

        progress = self._load_progress("coin_prices")

        for coin in coins_data:
            slug = coin.get("slug")
            if slug and slug != "N/A":
                if slug in progress:
                    logging.info(f"Skipping {slug} as it was already processed.")
                    continue
                try:
                    self.stats_service.fetch_and_save_coin_stats(slug)
                    progress[slug] = True
                    self._save_progress("coin_prices", progress)
                except Exception as e:
                    logging.error(f"Failed to fetch coin stats for {slug}: {e}")
                    if not self.continue_on_failure:
                        raise
            else:
                logging.warning(
                    f"Skipping invalid slug for {coin.get('name', 'Unknown')}"
                )

    def _daily_data_cleaner(self):
        """Clean up duplicate files in the data directory."""
        self.cleaner.clean_timestamped_files()

    def _trading_bot_execution(self, limit=None):
        """Execute trading bot for configured coins with activities reporting."""
        if not self.trading_config["enabled"]:
            logging.info("Trading bot is disabled in configuration")
            return
        activities_file = "data/activities/coin_reports.json"
        os.makedirs(os.path.dirname(activities_file), exist_ok=True)
        with open(activities_file, "w") as f:
            json.dump({}, f)  # Initialize with empty dictionary

        coins_data = self.extractor.load_most_recent_data() or []
        if limit:
            coins_data = coins_data[:limit]
        for coin in coins_data:
            slug = coin.get("slug")
            if slug and slug != "N/A":
                trader = CoinTrader(
                    coin=slug,
                    override=self.trading_config["override"],
                    capital_manager=self.capital_manager,
                )
                trader.run()
            else:
                logging.warning(
                    f"Skipping invalid slug for {coin.get('name', 'Unknown')}"
                )

        try:
            with open(activities_file, "r") as f:
                activities = json.load(f)
                if isinstance(activities, dict):
                    summary = "Trading Activities:\n"
                    for coin, data in activities.items():
                        report = data.get("report", "N/A")
                        summary += f"- {coin}: {report}\n"
                else:
                    summary = "No trading activities to report"
                self.send_n8n_report(
                    title="Trading Bot Activities", content=summary, is_error=False
                )
        except (IOError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to read trading activities: {e}")
            self.send_n8n_report(
                title="Trading Bot Activities",
                content="Failed to read trading activities file",
                is_error=False,
            )

    def configure_jobs(self):
        """Configure the scheduler with custom timing and dependencies."""
        self.scheduler.add_job(
            self._top_coins_with_dependencies,
            CronTrigger(hour=0, minute=20),
            id="top_coins_daily",
        )
        self.scheduler.add_job(
            self._news_sentiment_with_dependencies,
            IntervalTrigger(hours=4),
            id="news_sentiment_4h",
        )
        if self.auto_trigger:
            self.scheduler.add_job(
                self.check_and_trigger_top_coins,
                IntervalTrigger(hours=1),
                id="check_top_coins",
            )
        logging.info("Scheduler jobs configured")

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

    def start(self):
        """Start the custom scheduler with an initial check only if auto_trigger is True."""
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

    def run_single_cycle(self):
        """Run a single complete cycle immediately (useful for testing)."""
        self._top_coins_with_dependencies()

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

    def trigger_top_coins_now(self):
        """Manually trigger the top coins extraction job."""
        self._top_coins_with_dependencies()

    def trigger_news_sentiment_now(self, force=False):
        """Manually trigger the news sentiment extraction job with an option to force execution."""
        self._news_sentiment_with_dependencies(force=force)

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
            self.trigger_top_coins_now()

    def _load_progress(self, job_type):
        """Load progress for a specific job type from the progress file."""
        try:
            with open(self.coin_progress_file, "r") as f:
                data = json.load(f)
            return data.get(job_type, {})
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_progress(self, job_type, progress):
        """Save progress for a specific job type to the progress file."""
        try:
            data = {}
            if os.path.exists(self.coin_progress_file):
                with open(self.coin_progress_file, "r") as f:
                    data = json.load(f)
            data[job_type] = progress
            with open(self.coin_progress_file, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving progress: {e}")


if __name__ == "__main__":
    scheduler = CoinScheduler(
        trading_config={"enabled": True, "initial_capital": 1000.0, "override": False}
    )
    try:
        scheduler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
