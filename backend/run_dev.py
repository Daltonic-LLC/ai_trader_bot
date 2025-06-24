import asyncio
import uvicorn
import logging
import multiprocessing
import os
import sys
from watchdog.observers import Observer
from config import config
from app.services.file_handler import FileChangeHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("server")


class FastAPIServer:
    def __init__(self):
        self.config = uvicorn.Config(
            "app.main:app",
            host="0.0.0.0",
            port=config.get_port,
            reload=False,  # We handle reload manually
            loop="asyncio",
        )
        self.server = uvicorn.Server(self.config)

    async def start(self):
        try:
            await self.server.serve()
        except Exception as e:
            logger.error(f"Error starting FastAPI server: {e}")


def run_fastapi():
    """Run FastAPI server in a separate process"""
    server = FastAPIServer()
    asyncio.run(server.start())


def main():
    """Run FastAPI with file and folder change watching for .log files"""
    if len(sys.argv) > 1:
        folder_to_watch = os.path.abspath(sys.argv[1])
    else:
        folder_to_watch = os.path.abspath("./data")

    logger.info(f"Watching folder: {folder_to_watch} 👀")
    logger.info("Monitoring for changes in log files...")

    fastapi_process = multiprocessing.Process(target=run_fastapi)
    fastapi_process.start()

    observer = Observer()

    # Handler for log file changes (watching .log files in current directory)
    log_handler = FileChangeHandler(
        observer,
        fastapi_process,
        folder_to_watch=".",
        patterns=[".py"],
    )

    # Handler for log file changes in specified folder
    folder_log_handler = FileChangeHandler(
        observer,
        fastapi_process,
        folder_to_watch=folder_to_watch,
        patterns=[".log"],
    )

    # Schedule both handlers
    observer.schedule(log_handler, path=".", recursive=True)
    observer.schedule(folder_log_handler, path=folder_to_watch, recursive=True)
    observer.start()

    try:
        fastapi_process.join()
    except KeyboardInterrupt:
        logger.info("Shutting down... 👋")
    finally:
        fastapi_process.terminate()
        observer.stop()
        observer.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
