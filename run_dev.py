import asyncio
import uvicorn
import logging
import multiprocessing
import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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
            reload=True,  # Enable auto-reload for development
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


class CodeChangeHandler(FileSystemEventHandler):
    """Handler to restart FastAPI process on .py file changes."""
    def __init__(self, fastapi_process_getter):
        self.fastapi_process_getter = fastapi_process_getter
        self.last_modified = time.time()

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return

        current_time = time.time()
        if current_time - self.last_modified < 1:  # Debounce: ignore changes within 1 second
            return

        self.last_modified = current_time
        logger.info(f"Detected change in {event.src_path}, restarting FastAPI process...")

        # Terminate the current FastAPI process
        fastapi_process = self.fastapi_process_getter()
        if fastapi_process and fastapi_process.is_alive():
            fastapi_process.terminate()
            fastapi_process.join()

        # Start a new FastAPI process
        new_fastapi_process = multiprocessing.Process(target=run_fastapi)
        new_fastapi_process.start()
        logger.info("FastAPI process restarted.")

        # Update the process in the getter
        self.fastapi_process_getter.current_process = new_fastapi_process


def main():
    """Run FastAPI with auto-reload and CoinScheduler."""
    logger.info("Starting FastAPI (with auto-reload) and CoinScheduler services...")

    # Create processes for FastAPI and CoinScheduler
    fastapi_process = multiprocessing.Process(target=run_fastapi)
    scheduler_process = multiprocessing.Process(target=run_coin_scheduler)

    # Store FastAPI process in a mutable container for the handler
    class ProcessContainer:
        def __init__(self, process):
            self.current_process = process

        def __call__(self):
            return self.current_process

    fastapi_process_container = ProcessContainer(fastapi_process)

    # Start the processes
    fastapi_process.start()
    scheduler_process.start()

    # Set up code change watching for .py files
    observer = Observer()
    code_handler = CodeChangeHandler(fastapi_process_container)
    observer.schedule(code_handler, path=".", recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down... 👋")
    finally:
        # Terminate processes
        fastapi_process_container().terminate()
        scheduler_process.terminate()
        observer.stop()
        observer.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()