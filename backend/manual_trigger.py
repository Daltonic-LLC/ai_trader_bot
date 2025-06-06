import argparse
from datetime import datetime, timezone
import time
from app.services.coin_scheduler import CoinScheduler

# Set up command-line argument parser
parser = argparse.ArgumentParser(
    description="Manually trigger CoinScheduler jobs for testing."
)
parser.add_argument(
    "--job",
    required=True,
    choices=["top_coins", "news_sentiment"],
    help="The job to trigger: 'top_coins' or 'news_sentiment'",
)
parser.add_argument(
    "--trading",
    action="store_true",
    help="Enable trading with default settings (initial capital: 1000.0, override: False)",
)
parser.add_argument(
    "--force",
    action="store_true",
    help="Force the job to run even if dependencies are not met",
)
args = parser.parse_args()

# Configure trading settings based on the --trading flag
trading_config = {"enabled": args.trading, "initial_capital": 1000.0, "override": False}

# Initialize and start the CoinScheduler
scheduler = CoinScheduler(trading_config=trading_config)
scheduler.start()

# Record the start time to track job completion
start_time = datetime.now(timezone.utc)

# Trigger the specified job and determine the final job in the chain
if args.job == "top_coins":
    scheduler.trigger_top_coins_now()
    final_job = "data_cleanup"  # Last job in the top_coins chain
elif args.job == "news_sentiment":
    scheduler.trigger_news_sentiment_now(force=args.force)
    final_job = (
        "trading_bot" if args.trading else "coin_prices"
    )  # Depends on trading status

# Inform the user that the job has been triggered
print(f"Triggered {args.job}. Waiting for {final_job} to complete...")

# Wait for the final job in the chain to complete by checking the execution log
while True:
    log_data = scheduler.load_execution_log()
    last_run_str = log_data.get(final_job, {}).get("last_execution")
    if last_run_str:
        last_run_time = datetime.fromisoformat(last_run_str)
        if last_run_time > start_time:
            break
    time.sleep(10)  # Check every 10 seconds

# Confirm completion and shut down the scheduler
print("All dependent jobs completed.")
scheduler.shutdown()
