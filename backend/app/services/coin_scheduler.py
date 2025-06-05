from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
import json
import os
from datetime import datetime, timezone
import time
from app.services.coin_extractor import TopCoinsExtractor
from app.services.coin_history import CoinHistory
from app.services.coin_news import NewsSentimentService
from app.services.coin_stats import CoinStatsService
from app.services.file_manager import DataCleaner
from app.trader_bot.coin_trader import CoinTrader
from app.services.capital_manager import CapitalManager
import requests
from config import config


class CoinScheduler:
    def __init__(
        self,
        log_file="scheduler.log",
        execution_log_file="data/scheduler/execution_log.json",
        trading_config=None,
    ):
        """Initialize the CoinScheduler with custom timing and dependencies."""
        # Set up logging
        self._setup_logging(log_file)
        logging.info("Initializing CoinScheduler with custom timing")

        # Initialize the background scheduler
        self.scheduler = BackgroundScheduler(
            executors={
                "default": ThreadPoolExecutor(
                    max_workers=5
                )  # Allow multiple concurrent jobs
            },
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

        # Initialize capital manager for trading
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
                logging.error(
                    f"Error loading execution log from {self.execution_log_file}: {e}"
                )
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
            logging.error(
                f"Error saving execution log to {self.execution_log_file}: {e}"
            )

    def update_execution_log_with_duration(
        self, job_id, job_name, start_time, end_time
    ):
        """Update the execution log with execution duration."""
        log_data = self.load_execution_log()

        duration = (end_time - start_time).total_seconds()

        log_data[job_id] = {
            "job_name": job_name,
            "last_execution": start_time.isoformat(),
            "execution_duration": duration,
            "status": "completed",
        }

        self.save_execution_log(log_data)
        logging.info(f"Updated execution log for {job_id}: duration {duration:.2f}s")

    def send_n8n_report(self, title, content, is_error=False):
        """
        Send a report to n8n webhook endpoint.

        Args:
            title (str): The title of the report
            content (str): The content/body of the report (can be markdown)
            is_error (bool): Whether this is an error report (affects formatting)

        Returns:
            bool: True if report was sent successfully, False otherwise
        """
        try:
            # Format the report based on type
            if is_error:
                markdown_report = f"# 🚨 {title}\n\n**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n```\n{content}\n```"
            else:
                markdown_report = f"# {title}\n\n**Timestamp:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n{content}"

            headers = {"x-n8n-secret": config.n8n_webhook_secret}
            payload = {"text": markdown_report}

            response = requests.post(
                config.n8n_webhook_url,
                headers=headers,
                json=payload,
                timeout=30,  # Add timeout to prevent hanging
            )
            response.raise_for_status()

            log_message = f"{'Error' if is_error else 'Trading'} report sent to n8n successfully: {title}"
            logging.info(log_message)
            print(log_message)
            return True

        except requests.exceptions.RequestException as e:
            error_message = f"Failed to send {'error' if is_error else 'trading'} report to n8n: {e}"
            logging.error(error_message)
            print(error_message)
            return False
        except Exception as e:
            error_message = f"Unexpected error sending {'error' if is_error else 'trading'} report to n8n: {e}"
            logging.error(error_message)
            print(error_message)
            return False

    def _schedule_dependent_job(
        self, delay_seconds, job_func, job_name, *args, **kwargs
    ):
        """Schedule a job to run after a specified delay."""

        def delayed_job():
            time.sleep(delay_seconds)
            job_start_time = datetime.now(timezone.utc)
            logging.info(f"Starting delayed job: {job_name}")
            print(f"Starting {job_name}")

            try:
                if args or kwargs:
                    job_func(*args, **kwargs)
                else:
                    job_func()

                job_end_time = datetime.now(timezone.utc)
                duration = (job_end_time - job_start_time).total_seconds()

                success_message = f"✓ {job_name} completed in {duration:.2f} seconds"
                logging.info(success_message)
                print(success_message)

            except Exception as e:
                error_message = f"✗ {job_name} failed: {e}"
                logging.error(error_message)
                print(error_message)

                # Send error report to n8n
                self.send_n8n_report(
                    title=f"Job Execution Error: {job_name}",
                    content=f"Job: {job_name}\nError: {str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    is_error=True,
                )

        # Schedule the delayed job to run in a separate thread
        self.scheduler.add_job(
            delayed_job,
            "date",
            run_date=datetime.now(timezone.utc),
            id=f"delayed_{job_name.lower().replace(' ', '_')}_{int(time.time())}",
            max_instances=1,
        )

    def _top_coins_with_dependencies(self):
        """Top coins extraction at 00:20, with dependent jobs scheduled."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting top coins extraction with dependencies")
        print("=== Starting Top Coins Extraction ===")

        try:
            # Execute top coins extraction
            self._daily_top_coin_list()

            job_end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "top_coins", "Top Coins Extraction", job_start_time, job_end_time
            )

            self._last_top_coins_run = job_end_time

            # Schedule immediate dependent jobs
            print("Scheduling dependent jobs...")

            # 1. Coin History - runs immediately after top coins (limited to 15 coins)
            self._schedule_dependent_job(
                5,
                self._coin_history_with_cleanup,
                "Coin History with Cleanup",
                limit=15,
            )

        except Exception as e:
            logging.error(f"Error in top coins extraction: {e}")
            print(f"Error in top coins extraction: {e}")

            # Send error report to n8n
            self.send_n8n_report(
                title="Top Coins Extraction Error",
                content=f"Error during top coins extraction:\n{str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )
            raise

    def _coin_history_with_cleanup(self, limit=None):
        """Coin history extraction with immediate data cleanup."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting coin history extraction")

        try:
            # Execute coin history
            self._daily_coin_history(limit=limit)

            job_end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "coin_history", "Coin History Extraction", job_start_time, job_end_time
            )

            self._last_coin_history_run = job_end_time

            # Schedule immediate data cleanup
            print("Scheduling immediate data cleanup...")
            self._schedule_dependent_job(5, self._daily_data_cleaner, "Data Cleanup")

        except Exception as e:
            logging.error(f"Error in coin history extraction: {e}")
            print(f"Error in coin history extraction: {e}")

            # Send error report to n8n
            self.send_n8n_report(
                title="Coin History Extraction Error",
                content=f"Error during coin history extraction:\n{str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )
            raise

    def _news_sentiment_with_dependencies(self):
        """News sentiment extraction with dependent jobs (every 4 hours after coin history)."""
        # Check if coin history has run recently
        if self._last_coin_history_run is None:
            logging.warning("News sentiment skipped - coin history hasn't run yet")
            print("News sentiment skipped - waiting for coin history to complete")
            return

        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting news sentiment extraction with dependencies")
        print("=== Starting News Sentiment Extraction ===")

        try:
            # Execute news sentiment (limited to 15 coins)
            self._daily_news_sentiment(limit=15)

            job_end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "news_sentiment",
                "News Sentiment Extraction",
                job_start_time,
                job_end_time,
            )

            self._last_news_sentiment_run = job_end_time

            # Schedule immediate dependent jobs
            print("Scheduling dependent jobs...")

            # 1. Coin Prices - runs immediately after news sentiment (limited to 15 coins)
            self._schedule_dependent_job(
                5, self._coin_prices_with_trading, "Coin Prices with Trading", limit=15
            )

        except Exception as e:
            logging.error(f"Error in news sentiment extraction: {e}")
            print(f"Error in news sentiment extraction: {e}")

            # Send error report to n8n
            self.send_n8n_report(
                title="News Sentiment Extraction Error",
                content=f"Error during news sentiment extraction:\n{str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )
            raise

    def _coin_prices_with_trading(self, limit=None):
        """Coin prices update with immediate trading bot execution."""
        job_start_time = datetime.now(timezone.utc)
        logging.info("Starting coin prices update")

        try:
            # Execute coin prices update (limited to 15 coins)
            self._daily_coin_prices(limit=limit)

            job_end_time = datetime.now(timezone.utc)
            self.update_execution_log_with_duration(
                "coin_prices", "Coin Prices Update", job_start_time, job_end_time
            )

            # Schedule immediate trading bot if enabled (limited to 15 coins)
            if self.trading_config.get("enabled", False):
                print("Scheduling immediate trading bot execution...")
                self._schedule_dependent_job(
                    5, self._trading_bot_execution, "Trading Bot Execution", limit=15
                )

        except Exception as e:
            logging.error(f"Error in coin prices update: {e}")
            print(f"Error in coin prices update: {e}")

            # Send error report to n8n
            self.send_n8n_report(
                title="Coin Prices Update Error",
                content=f"Error during coin prices update:\n{str(e)}\nStart Time: {job_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                is_error=True,
            )
            raise

    # Individual job methods (unchanged from original)
    def _daily_top_coin_list(self):
        """Extract top coins and save them to a JSON file."""
        logging.info("Starting top coins extraction")

        try:
            top_coins = self.extractor.fetch_coin_data()
            saved_file = self.extractor.save_to_json(top_coins)
            message = f"Saved top coins to: {saved_file}"
            logging.info(message)
            print(message)

        except Exception as e:
            logging.error(f"Error during top coins extraction: {e}")
            print(f"Error: {e}")
            raise

    def _daily_coin_history(self, limit=None):
        """Load top coins and extract historical data for a specified number of slugs."""
        logging.info("Starting coin history extraction")

        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for history extraction")
                print("No top coins data found. Run top coins extraction first.")
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
            raise

    def _daily_news_sentiment(self, limit=None):
        """Load top coins and fetch news sentiment for each slug."""
        logging.info("Starting news sentiment extraction")

        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for news sentiment extraction")
                print("No top coins data found. Run top coins extraction first.")
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
                try:
                    posts, sentiment = self.sentiment_service.fetch_news_and_sentiment(
                        slug
                    )
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
            raise

    def _daily_coin_prices(self, limit=None):
        """Load top coins and fetch latest prices."""
        logging.info("Starting coin prices update")

        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for price updates")
                print("No top coins data found. Run top coins extraction first.")
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
                try:
                    result = self.stats_service.fetch_and_save_coin_stats(slug)
                    if "error" not in result:
                        message = f"Updated {coin['name'].upper()} price: ${result.get('price', 'N/A')} saved to {result.get('csv_file', 'N/A')}"
                        logging.info(message)
                        print(message)
                    else:
                        logging.warning(
                            f"Failed to fetch stats for {slug}: {result['error']}"
                        )
                        print(f"Failed to fetch stats for {slug}: {result['error']}")
                except Exception as e:
                    logging.error(f"Error fetching stats for {slug}: {e}")
                    print(f"Error fetching stats for {slug}: {e}")

            logging.info("Completed coin prices update")

        except Exception as e:
            logging.error(f"Error during coin prices job: {e}")
            print(f"Error in coin prices job: {e}")
            raise

    def _daily_data_cleaner(self):
        """Clean up duplicate files in the data directory."""
        logging.info("Starting data cleanup")

        try:
            self.cleaner.clean_timestamped_files()
            logging.info("Completed data cleanup")

        except Exception as e:
            logging.error(f"Error during data cleanup: {e}")
            print(f"Error during data cleanup: {e}")
            raise

    def _trading_bot_execution(self, limit=None):
        """Execute trading bot for configured coins and send report to webhook."""

        logging.info("Starting trading bot execution")

        if not self.trading_config.get("enabled", False):
            logging.info("Trading bot is disabled in configuration")
            print("Trading bot execution skipped - disabled in configuration")
            return

        try:
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                logging.warning("No top coins data found for trading bot execution")
                print("No top coins data found. Run top coins extraction first.")
                return

            if limit is not None:
                coins_data = coins_data[:limit]

            successful_trades = 0
            failed_trades = 0
            reports = []
            error_reports = []

            for coin in coins_data:
                slug = coin.get("slug")
                coin_name = coin.get("name", "Unknown")

                if not slug or slug == "N/A":
                    logging.warning(f"Skipping coin with invalid slug: {coin_name}")
                    continue

                logging.info(f"Executing trading bot for {coin_name} ({slug})")
                print(f"Running trading analysis for {coin_name.upper()}...")

                try:
                    trader = CoinTrader(
                        coin=slug,
                        override=self.trading_config.get("override", False),
                        capital_manager=self.capital_manager,
                    )

                    full_report, report = trader.run()
                    reports.append(
                        f"### {coin_name.upper()} ({slug})\n```\n{report}\n```"
                    )

                    logging.info(f"Trading bot completed for {coin_name} ({slug})")
                    print(f"Trading analysis completed for {coin_name.upper()}")
                    print(f"Report summary: {report[:200]}...")

                    successful_trades += 1

                except Exception as e:
                    error_msg = f"Error during trading bot execution for {coin_name} ({slug}): {e}"
                    logging.error(error_msg)
                    print(f"Error executing trading bot for {coin_name}: {e}")

                    # Collect error for reporting
                    error_reports.append(f"**{coin_name.upper()} ({slug}):** {str(e)}")
                    failed_trades += 1

            total_coins = len(coins_data)
            summary_message = f"Trading bot execution completed: {successful_trades}/{total_coins} successful"
            logging.info(summary_message)
            print(summary_message)

            if failed_trades > 0:
                error_message = f"Failed trades: {failed_trades}/{total_coins}"
                logging.warning(error_message)
                print(error_message)

            # Send successful trading reports to n8n webhook
            if reports:
                trading_content = "\n\n".join(reports)
                self.send_n8n_report(
                    title="📈 Trading Bot Reports",
                    content=trading_content,
                    is_error=False,
                )

            # Send error reports to n8n webhook if there were failures
            if error_reports:
                error_content = (
                    f"**Failed Trades: {failed_trades}/{total_coins}**\n\n"
                    + "\n\n".join(error_reports)
                )
                self.send_n8n_report(
                    title="Trading Bot Execution Errors",
                    content=error_content,
                    is_error=True,
                )

        except Exception as e:
            logging.error(f"Error during trading bot job: {e}")
            print(f"Error in trading bot job: {e}")

            # Send critical error report to n8n
            self.send_n8n_report(
                title="Critical Trading Bot Error",
                content=f"Critical error during trading bot execution:\n{str(e)}",
                is_error=True,
            )
            raise

    def configure_jobs(self):
        """Configure the scheduler with custom timing and dependencies."""

        # 1. Top coins extraction at 00:20 every day (with dependencies)
        self.scheduler.add_job(
            self._top_coins_with_dependencies,
            CronTrigger(hour=0, minute=20),
            id="top_coins_daily",
            name="Daily Top Coins Extraction with Dependencies",
            max_instances=1,
        )

        # 2. News sentiment every 4 hours (after coin history, with dependencies)
        self.scheduler.add_job(
            self._news_sentiment_with_dependencies,
            IntervalTrigger(hours=4),
            id="news_sentiment_4h",
            name="News Sentiment Every 4 Hours with Dependencies",
            max_instances=1,
        )

        logging.info("Custom scheduler jobs configured:")
        logging.info(
            "- Top coins extraction: Daily at 00:20 (with immediate coin history and data cleanup)"
        )
        logging.info(
            "- News sentiment: Every 4 hours (with immediate coin prices and trading bot)"
        )

        print("Custom scheduler configured:")
        print("- Top coins extraction: Daily at 00:20")
        print("  └── Followed immediately by: Coin history → Data cleanup")
        print("- News sentiment: Every 4 hours")
        print("  └── Followed immediately by: Coin prices → Trading bot")

    def get_trading_summary(self):
        """Get a summary of trading activities and capital status."""
        if not self.trading_config.get("enabled", False):
            return "Trading is disabled"

        try:
            summary = []
            coins_data = self.extractor.load_most_recent_data()
            if coins_data is None:
                return "No coin data available for trading summary"

            for coin in coins_data:
                slug = coin.get("slug")
                coin_name = coin.get("name", "Unknown")

                if not slug or slug == "N/A":
                    continue

                try:
                    capital = self.capital_manager.get_capital(slug)
                    position = self.capital_manager.get_position(slug)
                    summary.append(
                        f"{coin_name.upper()} ({slug}): ${capital:.2f} capital, {position:.2f} position"
                    )
                except Exception as e:
                    summary.append(
                        f"{coin_name.upper()} ({slug}): Error getting data - {e}"
                    )

            return "\n".join(summary) if summary else "No trading data available"
        except Exception as e:
            return f"Error getting trading summary: {e}"

    def start(self):
        """Start the custom scheduler."""
        try:
            self.configure_jobs()
            self.scheduler.start()

            startup_message = "Custom CoinScheduler started"
            if self.trading_config.get("enabled", False):
                coins_data = self.extractor.load_most_recent_data()
                coin_count = len(coins_data) if coins_data else 0
                startup_message += f" with trading bot for up to {coin_count} coins"

            logging.info(startup_message)
            print(startup_message)
            print("Jobs will run with custom timing and dependencies.")
            print("Press Ctrl+C to stop.")

            if self.trading_config.get("enabled", False):
                print("\nTrading Configuration:")
                print(f"- Coins: Loaded dynamically from extracted data")
                print(
                    f"- Initial Capital: ${self.trading_config.get('initial_capital', 1000.0):.2f}"
                )
                print(f"- Override Mode: {self.trading_config.get('override', False)}")

            # Send startup notification to n8n
            startup_report = f"**Configuration:**\n- Trading Enabled: {self.trading_config.get('enabled', False)}\n- Initial Capital: ${self.trading_config.get('initial_capital', 1000.0):.2f}\n- Override Mode: {self.trading_config.get('override', False)}"
            self.send_n8n_report(
                title="🚀 CoinScheduler Started", content=startup_report, is_error=False
            )

        except Exception as e:
            logging.error(f"Failed to start scheduler: {e}")
            print(f"Error starting scheduler: {e}")

            # Send startup error to n8n
            self.send_n8n_report(
                title="Scheduler Startup Error",
                content=f"Failed to start CoinScheduler:\n{str(e)}",
                is_error=True,
            )
            raise

    def run_single_cycle(self):
        """Run a single complete cycle immediately (useful for testing)."""
        print("Running single complete cycle...")
        self._top_coins_with_dependencies()

    def shutdown(self):
        """Gracefully shut down the scheduler."""
        try:
            self.scheduler.shutdown()
            logging.info("Custom CoinScheduler shut down")
            print("Custom CoinScheduler stopped.")

            if self.trading_config.get("enabled", False):
                print("\nFinal Trading Summary:")
                trading_summary = self.get_trading_summary()
                print(trading_summary)

                # Send shutdown report to n8n
                self.send_n8n_report(
                    title="🛑 CoinScheduler Shutdown",
                    content=f"**Final Trading Summary:**\n```\n{trading_summary}\n```",
                    is_error=False,
                )

        except Exception as e:
            logging.error(f"Error shutting down scheduler: {e}")
            print(f"Error shutting down scheduler: {e}")

            # Send shutdown error to n8n
            self.send_n8n_report(
                title="Scheduler Shutdown Error",
                content=f"Error during CoinScheduler shutdown:\n{str(e)}",
                is_error=True,
            )


if __name__ == "__main__":
    # Configuration for trading
    trading_config = {"enabled": True, "initial_capital": 1000.0, "override": False}

    # Initialize custom scheduler
    scheduler = CoinScheduler(trading_config=trading_config)

    # Start the scheduler
    try:
        scheduler.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.shutdown()
