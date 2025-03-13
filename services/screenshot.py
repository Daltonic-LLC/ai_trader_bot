import time
from pathlib import Path
from playwright.sync_api import sync_playwright


class ScreenshotService:
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

        # Create screenshots directory if it doesn’t exist
        screenshots_dir = Path(__file__).parent / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

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
            # Navigate to the URL and wait until the network is idle
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Apply zoom if not 100%
            if zoom != 100:
                page.evaluate("document.body.style.zoom = arguments[0]", f"{zoom}%")
            # Generate a unique filename with a timestamp
            timestamp = int(time.time() * 1000)
            screenshot_path = screenshots_dir / f"screenshot-{timestamp}.{format}"
            # Capture the screenshot
            page.screenshot(path=str(screenshot_path), type=format, full_page=full_page)
            # Close the browser
            browser.close()

        return str(screenshot_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Take a screenshot of a web page.")
    parser.add_argument(
        "--url", required=True, help="URL of the web page to screenshot"
    )
    parser.add_argument("--width", type=int, default=2048, help="Viewport width")
    parser.add_argument("--height", type=int, default=1080, help="Viewport height")
    parser.add_argument(
        "--format", default="png", choices=["png", "jpeg"], help="Image format"
    )
    parser.add_argument(
        "--fullPage",
        type=lambda x: (str(x).lower() == "true"),
        default=False,
        help="Capture full page",
    )
    parser.add_argument("--zoom", type=int, default=100, help="Zoom level in %")
    parser.add_argument("--scale", type=float, default=1, help="Device scale factor")
    args = parser.parse_args()

    service = ScreenshotService()
    try:
        path = service.take_screenshot(
            url=args.url,
            width=args.width,
            height=args.height,
            format=args.format,
            full_page=args.fullPage,
            zoom=args.zoom,
            scale=args.scale,
        )
        print(f"Screenshot saved to {path}")
    except Exception as e:
        print(f"Error: {e}")
