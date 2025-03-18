import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class FileDownloadService:
    def download_file(
        self,
        coin: str,
        start_date: str = None,
        end_date: str = None,
        download_dir: str = "downloads",
        timeout: int = 30000,
    ) -> str:
        """
        Downloads the historical data CSV file for the specified cryptocurrency from CoinMarketCap.
        Clicks "Load More" until exhausted, then downloads the CSV.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'ethereum').
            start_date (str, optional): The start date in 'YYYYMMDD' format (e.g., '20130428').
            end_date (str, optional): The end date in 'YYYYMMDD' format (e.g., '20191020').
            download_dir (str): The directory to save the downloaded file. Defaults to 'downloads'.
            timeout (int): The timeout in milliseconds for operations. Defaults to 30000 (30 seconds).

        Returns:
            str: The file path where the downloaded file was saved.

        Raises:
            Exception: If the button is not found or the download fails.
        """
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

        # Create download directory
        download_path = Path(download_dir)
        download_path.mkdir(exist_ok=True, parents=True)

        # Launch Playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            try:
                # Navigate to the page
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=timeout)

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
                with page.expect_download(timeout=timeout) as download_info:
                    download_button.click()
                download = download_info.value

                # Save the file
                print("Saving the file...")
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

# Example usage
if __name__ == "__main__":
    service = FileDownloadService()
    file_path = service.download_file(coin="bitcoin", start_date="20130428", end_date="20191020")
    print(f"Bitcoin data downloaded to: {file_path}")