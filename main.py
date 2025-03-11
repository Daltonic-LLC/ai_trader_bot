url = "https://www.tradingview.com/chart/?symbol=BINANCE%3AXRPUSDT"

import os, asyncio
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode


async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/List_of_common_misconceptions",
            cache_mode=CacheMode.BYPASS,
            pdf=True,
            screenshot=True,
        )

        if result.success:
            # Save screenshot
            if result.screenshot:
                with open("wikipedia_screenshot.png", "wb") as f:
                    f.write(b64decode(result.screenshot))

            # Save PDF
            if result.pdf:
                with open("wikipedia_page.pdf", "wb") as f:
                    f.write(result.pdf)

            print("[OK] PDF & screenshot captured.")
        else:
            print("[ERROR]", result.error_message)


if __name__ == "__main__":
    asyncio.run(main())
