from datetime import datetime, timezone
import time
from app.services.coin_scheduler import CoinScheduler

# Set trading configuration with trading enabled by default
trading_config = {"enabled": True, "initial_capital": 1000.0, "override": False}

# Initialize and start the CoinScheduler
scheduler = CoinScheduler(trading_config=trading_config)
scheduler.start()

# Trigger the top_coins chain
start_time1 = datetime.now(timezone.utc)
scheduler.trigger_top_coins_now()
print("Triggered top_coins. Waiting for data_cleanup to complete...")

# Wait for the data_cleanup job (end of top_coins chain) to complete
while True:
    log_data = scheduler.load_execution_log()
    last_run_str = log_data.get("data_cleanup", {}).get("last_execution")
    if last_run_str:
        last_run_time = datetime.fromisoformat(last_run_str)
        if last_run_time > start_time1:
            break
    time.sleep(10)  # Check every 10 seconds

print("data_cleanup completed.")

# Trigger the news_sentiment chain
start_time2 = datetime.now(timezone.utc)
scheduler.trigger_news_sentiment_now(force=False)
final_job = "trading_bot" if trading_config["enabled"] else "coin_prices"
print(f"Triggered news_sentiment. Waiting for {final_job} to complete...")

# Wait for the final job in the news_sentiment chain to complete
while True:
    log_data = scheduler.load_execution_log()
    last_run_str = log_data.get(final_job, {}).get("last_execution")
    if last_run_str:
        last_run_time = datetime.fromisoformat(last_run_str)
        if last_run_time > start_time2:
            break
    time.sleep(10)  # Check every 10 seconds

print(f"{final_job} completed.")

# Shut down the scheduler
scheduler.shutdown()
