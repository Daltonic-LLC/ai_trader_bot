import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import Optional
import re

class FileDownloadService:
    """
    A service for downloading historical data CSV files for cryptocurrencies from CoinMarketCap.
    """
    def __init__(self, timeout: int = 60000, base_dir: str = "data/historical"):
        """
        Initialize the FileDownloadService.

        Args:
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
            base_dir (str): Base directory for storing downloaded files. Default is 'data/historical'.
        """
        self.timeout = timeout
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True, parents=True)

    def download_file(
        self,
        coin: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        download_dir: Optional[str] = None,
    ) -> str:
        """
        Downloads the historical data CSV file for the specified cryptocurrency from CoinMarketCap.
        Clicks "Load More" until exhausted, then downloads the CSV.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'ethereum').
            start_date (Optional[str]): The start date in 'YYYYMMDD' format (e.g., '20130428').
            end_date (Optional[str]): The end date in 'YYYYMMDD' format (e.g., '20191020').
            download_dir (Optional[str]): Custom directory to save the downloaded file. 
                                          If None, uses 'base_dir / coin'.

        Returns:
            str: The file path where the downloaded file was saved.

        Raises:
            Exception: If the button is not found or the download fails.
        """
        # Determine the download path
        if download_dir is None:
            download_path = self.base_dir / coin
        else:
            download_path = Path(download_dir)
        download_path.mkdir(exist_ok=True, parents=True)

        # Construct the URL
        base_url = f"https://coinmarketcap.com/currencies/{coin}/historical-data/"
        if start_date and end_date:
            url = f"{base_url}?start={start_date}&end={end_date}"
        elif start_date:
            url = f"{base_url}?start={start_date}"
        elif end_date:
            url = f"{base_url}?end={end_date}"
        else:
            url = base_url

        # Launch Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            try:
                # Navigate to the page
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Click "Load More" until no more buttons are available
                print("Loading all historical data by clicking 'Load More'...")
                click_count = 0
                while True:
                    load_more_button = page.get_by_role("button", name="Load More")
                    if load_more_button.count() == 0 or not load_more_button.is_visible():
                        print("No more 'Load More' buttons found or button is not visible.")
                        break
                    load_more_button.click()
                    click_count += 1
                    print(f"Clicked 'Load More' button {click_count} time(s).")
                    page.wait_for_timeout(1000)  # Wait 1 second for data to load

                # Download the CSV
                print("Locating 'Download CSV' button...")
                download_button = page.get_by_role("button", name="Download CSV")
                if download_button.count() == 0:
                    raise Exception(f"No 'Download CSV' button found for {coin} at {url}")

                print("Initiating download...")
                with page.expect_download(timeout=self.timeout) as download_info:
                    download_button.click()
                download = download_info.value

                # Save the file with timestamp prepended to suggested filename
                suggested_filename = download.suggested_filename
                timestamp = int(time.time() * 1000)
                file_path = download_path / f"{timestamp}-{suggested_filename}"
                download.save_as(file_path)

            except PlaywrightTimeoutError as e:
                raise Exception(f"Timeout error while downloading {coin} data: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to download {coin} data: {str(e)}")
            finally:
                browser.close()

        return str(file_path)
    
    def get_latest_file(self, coin: str) -> Optional[str]:
        """
        Returns the path to the most recently downloaded historical data file for the specified coin.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'ethereum').

        Returns:
            Optional[str]: The full path to the most recent file, or None if no files are found.

        Note:
            This method assumes files are stored in 'base_dir / coin'. If a custom 'download_dir' was
            used in 'download_file', this method will not find those files unless the custom directory
            matches 'base_dir / coin'.
        """
        dir_path = self.base_dir / coin
        if not dir_path.exists() or not dir_path.is_dir():
            return None
        
        # List files that match the pattern: starts with digits followed by a hyphen
        files = [f for f in dir_path.iterdir() if f.is_file() and re.match(r'^\d+-', f.name)]
        if not files:
            return None
        
        # Find the file with the maximum timestamp
        latest_file = max(files, key=lambda f: int(f.name.split('-')[0]))
        return str(latest_file)

# Example usage
if __name__ == "__main__":
    coin = "xrp"
    service = FileDownloadService()
    file_path = service.download_file(coin=coin, start_date="20130428", end_date="20191020")
    print(f"{coin.upper()} historical data downloaded to: {file_path}")