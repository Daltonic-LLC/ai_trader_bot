import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import os
import logging

class DataCleaner:
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the DataCleaner with the directory to clean.

        Args:
            data_dir (str): The root directory to scan for timestamped files. Defaults to 'data'.
        """
        self.data_dir = Path(data_dir)
        # Regex pattern to match timestamps in the format '_YYYYMMDD_HHMMSS' before the extension
        self.timestamp_pattern = r"_(\d{8}_\d{6})\.(\w+)$"

    def clean_timestamped_files(self):
        """
        Traverse the data directory, identify timestamped files, group them, and keep only the most recent one.
        Files without timestamps are ignored.
        """
        # Dictionary to group files by (directory, base_name, extension)
        file_groups = defaultdict(list)

        # Step 1: Traverse all files in data_dir and its subdirectories
        for root, _, files in os.walk(self.data_dir):
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                # Step 2: Check if the file matches the timestamp pattern
                match = re.search(self.timestamp_pattern, file)
                if match:
                    timestamp_str = match.group(1)  # e.g., '20250414_120000'
                    extension = match.group(2)      # e.g., 'json'
                    # Extract base name by removing the '_timestamp.extension' part
                    base = file[:match.start(1) - 1]  # e.g., 'top_coins'
                    # Use a tuple of (directory, base, extension) as the key
                    key = (str(root_path), base, extension)
                    
                    # Step 3: Parse the timestamp for comparison
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        file_groups[key].append((file_path, timestamp))
                    except ValueError:
                        logging.warning(f"Invalid timestamp format in file: {file_path}")
                        continue

        # Step 4: Process each group to keep only the most recent file
        for key, files in file_groups.items():
            if len(files) > 1:  # Only proceed if there are duplicates
                # Find the file with the latest timestamp
                latest_file = max(files, key=lambda x: x[1])[0]  # x[1] is the timestamp
                # Remove all other files in the group
                for file_path, _ in files:
                    if file_path != latest_file:
                        logging.info(f"Deleting duplicate file: {file_path}")
                        try:
                            file_path.unlink()  # Delete the file
                        except Exception as e:
                            logging.error(f"Failed to delete {file_path}: {e}")
            else:
                logging.info(f"No duplicates found for {key[1]}.{key[2]} in {key[0]}")