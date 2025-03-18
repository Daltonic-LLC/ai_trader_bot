import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class FileDownloadService:
    def download_file(
        self,
        url: str,
        download_dir: str = "downloads",
        timeout: int = 30000,
    ) -> str:
        """
        Downloads a file from the specified URL by clicking a button with specific characteristics.

        Args:
            url (str): The URL of the web page to navigate to.
            download_dir (str): The directory to save the downloaded file. Default is 'downloads'.
            timeout (int): The timeout in milliseconds to wait for events. Default is 30000 (30 seconds).

        Returns:
            str: The file path where the downloaded file was saved.

        Raises:
            Exception: If the button is not found or the download fails.
        """
        # Ensure download_dir is a Path object and create it
        download_path = Path(download_dir)
        download_path.mkdir(exist_ok=True, parents=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                accept_downloads=True  # Ensure downloads are enabled
            )
            page = context.new_page()

            try:
                # Navigate to the URL
                page.goto(url, wait_until="networkidle", timeout=timeout)

                # Locate the "Download CSV" button
                button = page.locator('button:has(svg use[href="#download"])').filter(
                    has_text="Download CSV"
                )

                if button.count() == 0:
                    raise Exception("No 'Download CSV' button found on the page")

                # Wait for the button to be clickable and initiate download
                with page.expect_download(timeout=timeout) as download_info:
                    button.click()
                download = download_info.value

                # Generate unique filename
                suggested_filename = download.suggested_filename()
                timestamp = int(time.time() * 1000)
                file_path = download_path / f"{timestamp}-{suggested_filename}"

                # Save the file
                download.save_as(file_path)

            except PlaywrightTimeoutError as e:
                raise Exception(f"Timeout error: {str(e)}")
            except Exception as e:
                raise Exception(f"Download failed: {str(e)}")
            finally:
                browser.close()

        return str(file_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download a file from a web page.")
    parser.add_argument("--url", required=True, help="URL of the web page")
    parser.add_argument(
        "--download_dir", default="downloads", help="Directory to save the file"
    )
    parser.add_argument(
        "--timeout", type=int, default=30000, help="Timeout in milliseconds"
    )
    args = parser.parse_args()

    service = FileDownloadService()
    try:
        path = service.download_file(
            url=args.url,
            download_dir=args.download_dir,
            timeout=args.timeout,
        )
        print(f"File downloaded to {path}")
    except Exception as e:
        print(f"Error: {e}")
