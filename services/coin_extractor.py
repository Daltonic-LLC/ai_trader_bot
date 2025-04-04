import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Optional


class TopCoinsExtractor:
    """
    A service for extracting the top N coins from a CoinMarketCap-like page and saving/loading the data.
    """

    def __init__(
        self,
        url: str = "https://coinmarketcap.com/all/views/all/",
        num_coins: int = 20,
        timeout: int = 60000,
        data_dir: str = "data/currencies",
    ):
        """
        Initialize the TopCoinsExtractor.

        Args:
            url (str): The URL of the CoinMarketCap page to extract from. Default is "https://coinmarketcap.com/all/views/all/".
            num_coins (int): The number of top coins to extract. Default is 20.
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
            data_dir (str): Directory to save JSON files. Default is "coin_data".
        """
        self.url = url
        self.num_coins = num_coins
        self.timeout = timeout
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(
            exist_ok=True, parents=True
        )  # Create the directory if it doesn’t exist

    def extract_top_coins(self) -> List[Dict[str, str]]:
        """
        Extracts the top N coins from the specified CoinMarketCap page.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each containing data for one coin.

        Raises:
            Exception: If extraction fails due to timeout or other errors.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                print(f"Navigating to {self.url}...")
                page.goto(self.url, wait_until="networkidle", timeout=self.timeout)

                # Load all required coins
                self._load_all_coins(page)

                # Extract data from the table using JavaScript evaluation
                coins_data = self._extract_data(page)

            except PlaywrightTimeoutError as e:
                raise Exception(f"Timeout error while extracting top coins: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to extract top coins: {str(e)}")
            finally:
                browser.close()

        # Return only the requested number of coins
        return coins_data[: self.num_coins]

    def _load_all_coins(self, page):
        """
        Loads all coins by clicking "Load More" or scrolling until at least num_coins are loaded.
        """
        attempts = 0
        max_attempts = 10  # Prevent infinite loops

        while attempts < max_attempts:
            page.wait_for_selector("tbody tr.cmc-table-row", timeout=self.timeout)
            rows = page.locator("tbody tr.cmc-table-row")
            row_count = rows.count()
            print(f"Current row count: {row_count}")
            if row_count >= self.num_coins:
                print(f"Loaded {row_count} coins, sufficient for requirement.")
                break

            load_more_button = page.get_by_role("button", name="Load More")
            if load_more_button.is_visible():
                print("Clicking 'Load More' button...")
                load_more_button.click()
                page.wait_for_timeout(1000)
            else:
                print("Scrolling to load more coins...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)

            attempts += 1

        final_row_count = page.locator("tbody tr.cmc-table-row").count()
        if final_row_count < self.num_coins:
            print(
                f"Warning: Only {final_row_count} coins loaded after {max_attempts} attempts."
            )

    def _extract_data(self, page) -> List[Dict[str, str]]:
        """
        Extracts data from the loaded table rows, including the cryptocurrency slug.

        Args:
            page: The page object from a web scraping library (e.g., Playwright).

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing coin data, including the slug.
        """
        coins_data = page.evaluate("""
            () => {
                const rows = document.querySelectorAll("tbody tr.cmc-table-row");
                return Array.from(rows).map(row => {
                    const cells = row.querySelectorAll("td");
                    if (cells.length < 10) return null;
                    const nameLink = cells[1].querySelector("a:last-child");
                    return {
                        rank: cells[0].innerText || "N/A",
                        name: nameLink?.innerText || "N/A",
                        slug: nameLink?.getAttribute("href")?.split('/').filter(Boolean).pop() || "N/A",
                        symbol: cells[2].innerText || "N/A",
                        market_cap: cells[3].querySelector("p span")?.innerText || "N/A",
                        price: cells[4].querySelector("div span")?.innerText || "N/A",
                        circulating_supply: cells[5].innerText || "N/A",
                        volume_24h: cells[6].querySelector("p span")?.innerText || "N/A",
                        percent_1h: cells[7].innerText || "N/A",
                        percent_24h: cells[8].innerText || "N/A",
                        percent_7d: cells[9].innerText || "N/A",
                    };
                }).filter(row => row !== null);
            }
        """)
        return coins_data

    def save_to_json(self, coins_data: List[Dict[str, str]]) -> str:
        """
        Saves the extracted coin data to a JSON file with a timestamp in the specified folder.

        Args:
            coins_data (List[Dict[str, str]]): The list of coin data to save.

        Returns:
            str: The file path where the data was saved.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"top_coins_{timestamp}.json"
        filepath = self.data_dir / filename
        with open(filepath, "w") as f:
            json.dump(coins_data, f, indent=4)  # Pretty-print with indentation
        return str(filepath)

    def get_most_recent_file(self) -> Optional[str]:
        """
        Returns the path to the most recent "top_coins_*.json" file in the data directory.

        Returns:
            Optional[str]: The path to the most recent file, or None if no files are found.
        """
        files = sorted(self.data_dir.glob("top_coins_*.json"))
        if not files:
            return None
        return str(files[-1])

    def load_most_recent_data(self) -> Optional[List[Dict[str, str]]]:
        """
        Loads the coin data from the most recent JSON file.

        Returns:
            Optional[List[Dict[str, str]]]: The list of coin data, or None if no files are found.
        """
        recent_file = self.get_most_recent_file()
        if recent_file is None:
            return None
        with open(recent_file, "r") as f:
            return json.load(f)


# Example usage
if __name__ == "__main__":
    # Initialize the extractor with a custom data directory (optional)
    extractor = TopCoinsExtractor()

    # Extract top coins
    top_coins = extractor.extract_top_coins()

    # Save the data to a JSON file
    saved_file = extractor.save_to_json(top_coins)
    print(f"Saved top coins to: {saved_file}")
