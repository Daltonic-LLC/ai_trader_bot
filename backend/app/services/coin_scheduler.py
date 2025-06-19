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


def retry_on_failure(job_name, max_retries=3, retry_delay=5):
    """Decorator to handle retries, logging, and reporting for job methods."""

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            job_start_time = datetime.now(timezone.utc)
            for attempt in range(1, max_retries + 1):
                try:
                    logging.info(f"Starting {job_name} (attempt {attempt})")
                    result = func(self, *args, **kwargs)
                    job_end_time = datetime.now(timezone.utc)
                    self.update_execution_log_with_duration(
                        job_name.lower().replace(" ", "_"),
                        job_name,
                        job_start_time,
                        job_end_time,
                        "completed",
                    )
                    logging.info(f"Completed {job_name}")
                    self.send_n8n_report(
                        title=f"Job Completed: {job_name}",
                        content=(
                            f"Job: {job_name}\n"
                            f"Status: Success\n"
                            f"Duration: {(job_end_time - job_start_time).total_seconds():.2f} seconds\n"
                            f"Start Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        ),
                        is_error=False,
                    )
                    return result
                except Exception as e:
                    logging.error(f"Attempt {attempt} failed: {e}")
                    self.send_n8n_report(
                        title=f"{job_name} Retry Attempt {attempt} Failed",
                        content=(
                            f"Job: {job_name}\n"
                            f"Attempt: {attempt}/{max_retries}\n"
                            f"Error: {str(e)}\n"
                            f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                            f"{'Retrying in ' + str(retry_delay) + ' seconds' if attempt < max_retries else 'No more retries'}"
                        ),
                        is_error=True,
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                    else:
                        job_end_time = datetime.now(timezone.utc)
                        self.update_execution_log_with_duration(
                            job_name.lower().replace(" ", "_"),
                            job_name,
                            job_start_time,
                            job_end_time,
                            "failed",
                        )
                        raise

        return wrapper

    return decorator


class CoinScheduler:
    def __init__(
        self,
        log_file="scheduler.log",
        execution_log_file="data/scheduler/execution_log.json",
        trading_config=None,
        auto_trigger=True,
        continue_on_failure=False,
    ):
        """Initialize the CoinScheduler with custom timing and dependencies.

        Args:
            log_file (str): Path to the log file.
            execution_log_file (str): Path to the execution log JSON file.
            trading_config (dict, optional): Configuration for trading bot.
            auto_trigger (bool): Whether to auto-trigger jobs on start.
            continue_on_failure (bool): Whether to continue dependent jobs on failure.
        """
        self.auto_trigger = auto_trigger
        self.continue_on_failure = continue_on_failure

        # Set up logging
        self._setup_logging(log_file)
        logging.info("Initializing CoinScheduler with custom timing")

        # Initialize the background scheduler
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

        # Initialize trading configuration
        self.trading_config = trading_config or {
            "enabled": True,
            "initial_capital": 1000.0,
            "override": False,
        }
        if self.trading_config.get("enabled", False):
            self.capital_manager = CapitalManager(
                initial_capital=self.trading_config.get("initial_capital", 1000.0)
            )

        # Execution log file path
        self.execution_log_file = execution_log_file
        self.ensure_directory_exists()

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
                with open(self.execution_log_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading execution log: {e}")
                return {}
        return {}

    def save_execution_log(self, log_data):
        """Save the execution log to the JSON file."""
        try:
            self.ensure_directory_exists()
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
                f"# {' ' if is_error else ''}{title}\n\n"
                f"**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"```\n{content}\n```"
            )
            headers = {"x-n8n-secret": config.n8n_webhook_secret}
            payload = {"text": markdown_report}
            response = requests.post(
                config.n8n_webhook_url, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()
            logging.info(
                f"{'Error' if is_error else 'Trading'} report sent to n8n: {title}"
            )
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to send report to n8n: {e}")
            return False

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
            job_start_time = datetime.now(timezone.utc)
            logging.info(f"Starting delayed job: {job_name}")
            job_failed = False

            try:
                job_func(*job_args, **job_kwargs)
            except Exception as e:
                job_failed = True
                logging.error(f"✗ {job_name} failed: {e}")
                self.send_n8n_report(
                    title=f"Job Execution Error: {job_name}",
                    content=f"Job: {job_name}\nError: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    is_error=True,
                )
                if not self.continue_on_failure:
                    return

            if next_job_info and (not job_failed or self.continue_on_failure):
                delay, next_func, next_name, next_next_info = next_job_info[:4]
                next_args = next_job_info[4] if len(next_job_info) > 4 else ()
                next_kwargs = next_job_info[5] if len(next_job_info) > 5 else {}
                logging.info(
                    f"Scheduling next job: {next_name} (previous job {'failed but continuing' if job_failed else 'succeeded'})"
                )
                self._schedule_dependent_job(
                    delay, next_func, next_name, next_next_info, next_args, next_kwargs
                )

        self.scheduler.add_job(
            delayed_job,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"delayed_{job_name.lower().replace(' ', '_')}_{int(time.time())}",
            max_instances=1,
        )

    def _top_coins_with_dependencies(self):
        """Top coins extraction with dependent jobs scheduled."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting top coins extraction with dependencies")
        job_failed = False

        try:
            self._daily_top_coin_list()
            self._last_top_coins_run = datetime.now(timezone.utc)
        except Exception as e:
            job_failed = True
            logging.error(f"Error in top coins extraction: {e}")
            self.send_n8n_report(
                title="Top Coins Extraction Error",
                content=f"Error: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )

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
            logging.info(
                f"Scheduling coin history job (top coins {'failed but continuing' if job_failed else 'succeeded'})"
            )
            self._schedule_dependent_job(*history_info)

    def _coin_history_with_cleanup(self, limit=None):
        """Coin history extraction with cleanup scheduling."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting coin history extraction")
        job_failed = False

        try:
            self._daily_coin_history(limit=limit)
            self._last_coin_history_run = datetime.now(timezone.utc)
        except Exception as e:
            job_failed = True
            logging.error(f"Error in coin history extraction: {e}")
            self.send_n8n_report(
                title="Coin History Extraction Error",
                content=f"Error: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )

    def _news_sentiment_with_dependencies(self, force=False):
        """News sentiment extraction with dependent jobs, optionally forcing execution."""
        if not force and self._last_coin_history_run is None:
            logging.warning("News sentiment skipped - coin history hasn't run yet")
            return
        if force and self._last_coin_history_run is None:
            logging.warning(
                "Running news sentiment with force=True, but coin history hasn't run yet. Results may be incomplete."
            )

        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting news sentiment extraction with dependencies")
        job_failed = False

        try:
            self._daily_news_sentiment(limit=config.coin_limit)
            self._last_news_sentiment_run = datetime.now(timezone.utc)
        except Exception as e:
            job_failed = True
            logging.error(f"Error in news sentiment extraction: {e}")
            self.send_n8n_report(
                title="News Sentiment Extraction Error",
                content=f"Error: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )

        if not job_failed or self.continue_on_failure:
            if self.trading_config.get("enabled", False):
                trading_info = (
                    5,
                    self._trading_bot_execution,
                    "Trading Bot Execution",
                    None,
                    (config.coin_limit,),
                    {},
                )
                prices_info = (
                    5,
                    self._coin_prices_with_trading_chain,
                    "Coin Prices with Trading",
                    trading_info,
                    (config.coin_limit,),
                    {},
                )
            else:
                prices_info = (
                    5,
                    self._coin_prices_with_trading_chain,
                    "Coin Prices Update",
                    None,
                    (config.coin_limit,),
                    {},
                )
            logging.info(
                f"Scheduling coin prices job (news sentiment {'failed but continuing' if job_failed else 'succeeded'})"
            )
            self._schedule_dependent_job(*prices_info)

    def _coin_prices_with_trading_chain(self, limit=None):
        """Coin prices update with trading chain scheduling."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting coin prices update")
        job_failed = False

        try:
            self._daily_coin_prices(limit=limit)
        except Exception as e:
            job_failed = True
            logging.error(f"Error in coin prices update: {e}")
            self.send_n8n_report(
                title="Coin Prices Update Error",
                content=f"Error: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )

    @retry_on_failure("Top Coins Extraction")
    def _daily_top_coin_list(self):
        """Extract top coins and save them to a JSON file."""
        top_coins = self.extractor.fetch_coin_data()
        saved_file = self.extractor.save_to_json(top_coins)
        logging.info(f"Saved top coins to: {saved_file}")

    @retry_on_failure("Coin History Extraction")
    def _daily_coin_history(self, limit=None):
        """Load top coins and extract historical data."""
        coins_data = self.extractor.load_most_recent_data()
        if coins_data is None:
            logging.warning("No top coins data found for history extraction")
            return
        if limit is not None:
            coins_data = coins_data[:limit]
        for coin in coins_data:
            slug = coin.get("slug")
            if not slug or slug == "N/A":
                logging.warning(
                    f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}"
                )
                continue
            logging.info(f"Extracting history for {coin['name']} ({slug})")
            self.history_service.download_history(coin=slug)
        logging.info("Completed coin history extraction")

    @retry_on_failure("News Sentiment Extraction")
    def _daily_news_sentiment(self, limit=None):
        """Load top coins and fetch news sentiment."""
        coins_data = self.extractor.load_most_recent_data()
        if coins_data is None:
            logging.warning("No top coins data found for news sentiment extraction")
            return
        if limit is not None:
            coins_data = coins_data[:limit]
        for coin in coins_data:
            slug = coin.get("slug")
            if not slug or slug == "N/A":
                logging.warning(
                    f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}"
                )
                continue
            logging.info(f"Fetching news sentiment for {coin['name']} ({slug})")
            self.sentiment_service.fetch_news_and_sentiment(slug)
        logging.info("Completed news sentiment extraction")

    @retry_on_failure("Coin Prices Update")
    def _daily_coin_prices(self, limit=None):
        """Load top coins and fetch latest prices."""
        coins_data = self.extractor.load_most_recent_data()
        if coins_data is None:
            logging.warning("No top coins data found for price updates")
            return
        if limit is not None:
            coins_data = coins_data[:limit]
        for coin in coins_data:
            slug = coin.get("slug")
            if not slug or slug == "N/A":
                logging.warning(
                    f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}"
                )
                continue
            logging.info(f"Fetching stats for {coin['name']} ({slug})")
            self.stats_service.fetch_and_save_coin_stats(slug)
        logging.info("Completed coin prices update")

    @retry_on_failure("Data Cleanup")
    def _daily_data_cleaner(self):
        """Clean up duplicate files in the data directory."""
        self.cleaner.clean_timestamped_files()
        logging.info("Completed data cleanup")

    @retry_on_failure("Trading Bot Execution")
    def _trading_bot_execution(self, limit=None):
        """Execute trading bot for configured coins with activities reporting."""
        if not self.trading_config.get("enabled", False):
            logging.info("Trading bot is disabled in configuration")
            return
        # Clear the coin_reports.json file at the start
        activities_file = "data/activities/coin_reports.json"
        os.makedirs(os.path.dirname(activities_file), exist_ok=True)
        with open(activities_file, "w") as f:
            json.dump([], f)

        coins_data = self.extractor.load_most_recent_data()
        if coins_data is None:
            logging.warning("No top coins data found for trading bot execution")
            return
        if limit is not None:
            coins_data = coins_data[:limit]
        for coin in coins_data:
            slug = coin.get("slug")
            if not slug or slug == "N/A":
                logging.warning(
                    f"Skipping coin with invalid slug: {coin.get('name', 'Unknown')}"
                )
                continue
            logging.info(f"Executing trading bot for {coin['name']} ({slug})")
            trader = CoinTrader(
                coin=slug,
                override=self.trading_config.get("override", False),
                capital_manager=self.capital_manager,
            )
            trader.run()

        # Report trading activities
        if os.path.exists(activities_file):
            with open(activities_file, "r") as f:
                activities = json.load(f)
                if activities:
                    summary = "Trading Activities:\n"
                    for activity in activities:
                        summary += (
                            f"- {activity.get('coin', 'Unknown')}: "
                            f"{activity.get('action', 'N/A')} "
                            f"{activity.get('amount', 0)} at "
                            f"{activity.get('price', 'N/A')}\n"
                        )
                    self.send_n8n_report(
                        title="Trading Bot Activities",
                        content=summary,
                        is_error=False,
                    )
                else:
                    self.send_n8n_report(
                        title="Trading Bot Activities",
                        content="No trading activities to report",
                        is_error=False,
                    )
        else:
            logging.warning("Trading activities file not found")
            self.send_n8n_report(
                title="Trading Bot Activities",
                content="Trading activities file not found",
                is_error=False,
            )

    def configure_jobs(self):
        """Configure the scheduler with custom timing and dependencies."""
        self.scheduler.add_job(
            self._top_coins_with_dependencies,
            CronTrigger(hour=0, minute=20),
            id="top_coins_daily",
            name="Daily Top Coins Extraction with Dependencies",
            max_instances=1,
        )
        self.scheduler.add_job(
            self._news_sentiment_with_dependencies,
            IntervalTrigger(hours=4),
            id="news_sentiment_4h",
            name="News Sentiment Every 4 Hours with Dependencies",
            max_instances=1,
        )
        if self.auto_trigger:
            self.scheduler.add_job(
                self.check_and_trigger_top_coins,
                IntervalTrigger(hours=1),
                id="check_top_coins",
                name="Check and Trigger Top Coins if Necessary",
                max_instances=1,
            )
        logging.info(
            f"Custom scheduler jobs configured with failure recovery {'enabled' if self.continue_on_failure else 'disabled'}."
        )

    def get_trading_summary(self):
        """Get a summary of trading activities and capital status."""
        if not self.trading_config.get("enabled", False):
            return "Trading is disabled"
        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                return "No coin data available for trading summary"
            summary = []
            for coin in coins_data:
                slug = coin.get("slug")
                if not slug or slug == "N/A":
                    continue
                capital = self.capital_manager.get_capital(slug)
                position = self.capital_manager.get_position(slug)
                summary.append(
                    f"{coin.get('name', 'Unknown').upper()} ({slug}): "
                    f"${capital:.2f} capital, {position:.2f} position"
                )
            return "\n".join(summary) if summary else "No trading data available"
        except Exception as e:
            return f"Error getting trading summary: {e}"

    def start(self):
        """Start the custom scheduler with an initial check if auto_trigger is True."""
        try:
            if self.auto_trigger:
                self.check_and_trigger_top_coins()
            self.configure_jobs()
            self.scheduler.start()
            logging.info(
                f"Custom CoinScheduler started with failure recovery {'enabled' if self.continue_on_failure else 'disabled'}"
            )
            self.send_n8n_report(
                title="CoinScheduler Started",
                content=(
                    f"**Configuration:**\n"
                    f"- Trading Enabled: {self.trading_config.get('enabled', False)}\n"
                    f"- Initial Capital: ${self.trading_config.get('initial_capital', 1000.0):.2f}\n"
                    f"- Override Mode: {self.trading_config.get('override', False)}\n"
                    f"- Auto-Start Enabled: {'Yes' if self.auto_trigger else 'No'}\n"
                    f"- Continue on Failure: {'Yes' if self.continue_on_failure else 'No'}\n"
                    f"- Manual Triggering: Available"
                ),
                is_error=False,
            )
        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            self.send_n8n_report(
                title="Scheduler Startup Error",
                content=f"Failed to start CoinScheduler:\n{str(e)}",
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
            logging.info("Custom CoinScheduler shut down")
            if self.trading_config.get("enabled", False):
                trading_summary = self.get_trading_summary()
                self.send_n8n_report(
                    title="CoinScheduler Shutdown",
                    content=f"**Final Trading Summary:**\n```\n{trading_summary}\n```",
                    is_error=False,
                )
        except Exception as e:
            logging.error(f"Error shutting down scheduler: {e}")
            self.send_n8n_report(
                title="Scheduler Shutdown Error",
                content=f"Error during shutdown:\n{str(e)}",
                is_error=True,
            )

    def trigger_top_coins_now(self):
        """Manually trigger the top coins extraction job."""
        self.scheduler.add_job(
            self._top_coins_with_dependencies,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"manual_top_coins_{int(time.time())}",
            max_instances=1,
            misfire_grace_time=600,
        )
        logging.info("Manually triggered top coins extraction")

    def trigger_news_sentiment_now(self, force=False):
        """Manually trigger the news sentiment extraction job with an option to force execution."""
        self.scheduler.add_job(
            self._news_sentiment_with_dependencies,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"manual_news_sentiment_{int(time.time())}",
            max_instances=1,
            misfire_grace_time=600,
            args=[force],
        )
        logging.info("Manually triggered news sentiment extraction")

    def check_and_trigger_top_coins(self):
        """Check if top coins job has run in the last 6 hours and trigger if not."""
        log_data = self.load_execution_log()
        last_run_str = log_data.get("top_coins", {}).get("last_execution")
        if last_run_str:
            last_run_time = datetime.fromisoformat(last_run_str)
            if (datetime.now(timezone.utc) - last_run_time).total_seconds() > 6 * 3600:
                logging.info("Top coins job hasn't run in 6 hours. Triggering now.")
                self.trigger_top_coins_now()
        else:
            logging.info("No record of top coins job. Triggering now.")
            self.trigger_top_coins_now()


if __name__ == "__main__":
    trading_config = {"enabled": True, "initial_capital": 1000.0, "override": False}
    scheduler = CoinScheduler(
        trading_config=trading_config,
        auto_trigger=True,
        continue_on_failure=False,
    )
    try:
        scheduler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.shutdown()
