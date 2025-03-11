import asyncio
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode, BrowserConfig

url = "https://poloniex.com/trade/XRP_USDT"


async def main():
    # JavaScript code to wait for page load plus an additional 5 seconds
    js_code = """
    await new Promise(resolve => {
        window.addEventListener('load', () => {
            setTimeout(resolve, 5000);  // Wait 5 seconds after load
        });
    });
    """

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(
            url=url,
            cache_mode=CacheMode.BYPASS,
            pdf=True,
            screenshot=True,
            js_code=js_code,  # Execute this before capturing
        )

        if result.success:
            # Save screenshot
            if result.screenshot:
                with open("screenshot.png", "wb") as f:
                    f.write(b64decode(result.screenshot))

            # Save PDF
            if result.pdf:
                with open("page.pdf", "wb") as f:
                    f.write(result.pdf)

            print("[OK] PDF & screenshot captured.")
        else:
            print("[ERROR]", result.error_message)


if __name__ == "__main__":
    asyncio.run(main())
