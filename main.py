import asyncio
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig, CrawlerRunConfig

url = "https://www.tradingview.com/chart/?symbol=BINANCE%3AXRPUSDT"


async def main():
    # JavaScript code to wait for page load plus an additional 5 seconds
    js_code = """
    await new Promise(resolve => {
        window.addEventListener('load', () => {
            setTimeout(resolve, 5000);  // Wait 5 seconds after load
        });
    });
    """

    config = CrawlerRunConfig(
        # Force the crawler to wait until images are fully loaded
        wait_for_images=True,
        screenshot=True,
        js_code=js_code,
        screenshot_wait_for=10000,
        cache_mode=CacheMode.BYPASS,
        magic=True,
        verbose=True,
    )

    async with AsyncWebCrawler(
        config=BrowserConfig(headless=True, viewport_width=2048, viewport_height=1080)
    ) as crawler:
        result = await crawler.arun(url=url, config=config)

        if result.success:
            # Save screenshot
            if result.screenshot:
                with open("screenshot.png", "wb") as f:
                    f.write(b64decode(result.screenshot))

            print("[OK] screenshot captured.")
        else:
            print("[ERROR]", result.error_message)


if __name__ == "__main__":
    asyncio.run(main())
