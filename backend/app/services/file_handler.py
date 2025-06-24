import os
import sys
import psutil
import time
import logging
from watchdog.events import FileSystemEventHandler
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")


class FileChangeHandler(FileSystemEventHandler):
    """Handles changes in specified folders with optional patterns"""

    def __init__(
        self,
        observer,
        fastapi_process,
        folder_to_watch,
        patterns=None,
    ):
        self.observer = observer
        self.fastapi_process = fastapi_process
        self.folder_to_watch = os.path.abspath(folder_to_watch)
        self.patterns = patterns
        self.last_reload_time = 0
        self.reload_cooldown = 2  # Minimum seconds between reloads

    def kill_process_on_port(self, port):
        """Find and kill process using the given port"""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for conn in proc.connections(kind="inet"):
                    if conn.laddr.port == port:
                        logger.info(
                            f"Killing process {proc.pid} ({proc.name()}) using port {port}... 🚀"
                        )
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def should_reload(self, event):
        """Determine if the change should trigger a reload"""
        # Ensure the event is within the watched folder (safety check)
        if not event.src_path.startswith(self.folder_to_watch):
            return False

        # Check cooldown period
        current_time = time.time()
        if current_time - self.last_reload_time < self.reload_cooldown:
            return False

        # If no patterns specified, reload on any change
        if self.patterns is None:
            return True

        # Reload if the file matches any of the specified patterns
        return any(event.src_path.endswith(pattern) for pattern in self.patterns)

    def on_modified(self, event):
        """Handle file modifications"""
        if self.should_reload(event):
            self.last_reload_time = time.time()
            logger.info(f"File modified: {event.src_path}")
            self._restart_all()

    def on_created(self, event):
        """Handle file creations"""
        if self.should_reload(event):
            self.last_reload_time = time.time()
            logger.info(f"File created: {event.src_path}")
            self._restart_all()

    def on_deleted(self, event):
        """Handle file deletions"""
        if self.should_reload(event):
            self.last_reload_time = time.time()
            logger.info(f"File deleted: {event.src_path}")
            self._restart_all()

    def _restart_all(self):
        """Restart FastAPI process"""
        self.observer.stop()

        # Terminate existing FastAPI process safely
        self.fastapi_process.terminate()
        self.fastapi_process.join()

        logger.info("Restarting FastAPI service... 🔄")
        self.kill_process_on_port(
            config.get_port,
        )

        # Restart the entire process
        os.execv(sys.executable, [sys.executable] + sys.argv)
