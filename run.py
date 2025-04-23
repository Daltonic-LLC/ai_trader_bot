import asyncio
import uvicorn
import logging
import multiprocessing
import time
from app.services.coin_scheduler import CoinScheduler 
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("server")


class FastAPIServer:
    def __init__(self):
        self.config = uvicorn.Config(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            loop="asyncio",
        )
        self.server = uvicorn.Server(self.config)

    async def start(self):
        try:
            await self.server.serve()
        except Exception as e:
            logger.error(f"Error starting FastAPI server: {e}")


def run_fastapi():
    """Run FastAPI server in a separate process."""
    server = FastAPIServer()
    asyncio.run(server.start())


def run_coin_scheduler():
    """Run CoinScheduler in a separate process."""
    scheduler = CoinScheduler(log_file='scheduler.log')
    try:
        scheduler.start()
        # Keep the process running
        while True:
            time.sleep(60)  # Sleep to reduce CPU usage
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
    except Exception as e:
        logger.error(f"Error running CoinScheduler: {e}")
        scheduler.shutdown()


def main():
    """Run FastAPI and CoinScheduler processes."""
    logger.info("Starting FastAPI and CoinScheduler services...")

    # Create processes for FastAPI and CoinScheduler
    fastapi_process = multiprocessing.Process(target=run_fastapi)
    scheduler_process = multiprocessing.Process(target=run_coin_scheduler)

    # Start the processes
    fastapi_process.start()
    scheduler_process.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down... 👋")
    finally:
        # Terminate processes
        fastapi_process.terminate()
        scheduler_process.terminate()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()