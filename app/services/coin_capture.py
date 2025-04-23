import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import Optional

class CaptureService:
    """
    A service for capturing screenshots of web pages with configurable parameters.
    """
    def __init__(self, timeout: int = 60000, base_dir: str = "data"):
        """
        Initialize the CaptureService.

        Args:
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
            base_dir (str): Base directory for storing screenshots. Default is 'data'.
        """
        self.timeout = timeout
        self.screenshots_dir = Path(base_dir) / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)

    def take_screenshot(
        self,
        url: str,
        width: int = 2048,
        height: int = 1080,
        format: str = "png",
        full_page: bool = False,
        zoom: int = 100,
        scale: float = 1,
    ) -> str:
        """
        Captures a screenshot of the specified URL with the given parameters.

        Args:
            url (str): The URL of the web page to screenshot.
            width (int): Viewport width in pixels. Default is 2048.
            height (int): Viewport height in pixels. Default is 1080.
            format (str): Image format, either 'png' or 'jpeg'. Default is 'png'.
            full_page (bool): Whether to capture the full page. Default is False.
            zoom (int): Zoom level in percent. Default is 100.
            scale (float): Device scale factor. Default is 1.

        Returns:
            str: The file path where the screenshot was saved.

        Raises:
            ValueError: If the format is not 'png' or 'jpeg'.
            Exception: If an error occurs during the screenshot process (e.g., navigation failure).
        """
        # Validate the format parameter
        if format not in ["png", "jpeg"]:
            raise ValueError("Format must be 'png' or 'jpeg'")

        # Use Playwright to capture the screenshot
        with sync_playwright() as p:
            # Launch headless Chromium browser
            browser = p.chromium.launch(headless=True)
            # Set up browser context with viewport and scale
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
            )
            page = context.new_page()
            try:
                # Navigate to the URL and wait until the network is idle
                page.goto(url, wait_until="networkidle", timeout=self.timeout)
                # Apply zoom if not 100%
                if zoom != 100:
                    page.evaluate("document.body.style.zoom = arguments[0]", f"{zoom}%")
                # Generate a unique filename with a timestamp
                timestamp = int(time.time() * 1000)
                screenshot_path = self.screenshots_dir / f"screenshot-{timestamp}.{format}"
                # Capture the screenshot
                page.screenshot(path=str(screenshot_path), type=format, full_page=full_page)
            except PlaywrightTimeoutError as e:
                raise Exception(f"Timeout error while navigating to {url}: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to capture screenshot for {url}: {str(e)}")
            finally:
                browser.close()

        return str(screenshot_path)

# Example usage
if __name__ == "__main__":
    service = CaptureService()
    try:
        path = service.take_screenshot(url="https://coinmarketcap.com/currencies/xrp/")
        print(f"Screenshot saved to {path}")
    except Exception as e:
        print(f"Error: {e}")