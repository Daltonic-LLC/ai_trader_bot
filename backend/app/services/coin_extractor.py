import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class TopCoinsExtractor:
    def __init__(self, url: str = "https://coinmarketcap.com/all/views/all/", num_coins: int = 50, timeout: int = 60000):
        """Initialize the scraper with URL, target coin count, and timeout."""
        self.url = url
        self.num_coins = num_coins
        self.timeout = timeout
        self.data_dir = Path("data/currencies")
        self.data_dir.mkdir(exist_ok=True, parents=True)

    def extract_row_data(self, row):
        """Extract data from a single table row."""
        try:
            cells = row.query_selector_all('td')
            if len(cells) < 10:  # Ensure enough columns are present
                return None

            name_link = cells[1].query_selector('a')
            if not name_link:
                return None

            data = {
                'rank': cells[0].inner_text().strip(),
                'name': name_link.inner_text().strip(),
                'slug': name_link.get_attribute('href').split('/')[-2] if name_link.get_attribute('href') else 'N/A',
                'symbol': cells[2].inner_text().strip(),
                'market_cap': cells[3].inner_text().strip(),
                'price': cells[4].inner_text().strip(),
                'circulating_supply': cells[5].inner_text().strip(),
                'volume_24h': cells[6].inner_text().strip(),
                'percent_1h': cells[7].inner_text().strip(),
                'percent_24h': cells[8].inner_text().strip(),
                'percent_7d': cells[9].inner_text().strip(),
            }
            return data
        except Exception as e:
            print(f"Error extracting row: {e}")
            return None

    def fetch_coin_data(self):
        """Fetch data by gently scrolling and loading the entire table."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the page
            print(f"Navigating to {self.url}...")
            try:
                page.goto(self.url, wait_until='networkidle', timeout=self.timeout)
                print("Page loaded, waiting for table...")
                page.wait_for_selector('.cmc-table tbody tr', state='visible', timeout=self.timeout)
            except PlaywrightTimeoutError:
                print("Timeout waiting for table. Exiting.")
                browser.close()
                return []

            # Gentle scrolling to load the entire table
            max_scroll_attempts = 50  # Maximum number of scroll attempts
            attempt = 0
            last_row_count = 0
            no_new_rows_limit = 5     # Stop after 5 attempts with no new rows
            no_new_rows_count = 0

            while attempt < max_scroll_attempts:
                # Scroll down gently (500 pixels)
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(1)  # Wait for lazy-loaded content to appear

                # Count the current number of rows
                rows = page.query_selector_all('.cmc-table tbody tr')
                current_row_count = len(rows)
                print(f"Scroll attempt {attempt + 1}: {current_row_count} rows loaded")

                # Check if new rows were loaded
                if current_row_count > last_row_count:
                    last_row_count = current_row_count
                    no_new_rows_count = 0  # Reset if new rows appear
                else:
                    no_new_rows_count += 1
                    print(f"No new rows detected ({no_new_rows_count}/{no_new_rows_limit})")

                # Stop if no new rows load for several attempts
                if no_new_rows_count >= no_new_rows_limit:
                    print("Entire table loaded (no new rows after several scrolls).")
                    break

                attempt += 1

            # Extract data for the top 50 coins from the fully loaded table
            print(f"Extracting data for the top {self.num_coins} coins...")
            rows = page.query_selector_all('.cmc-table tbody tr')[:self.num_coins]
            coin_data = []
            for row in rows:
                data = self.extract_row_data(row)
                if data:
                    coin_data.append(data)

            browser.close()
            print(f"Extracted data for {len(coin_data)} coins.")
            return coin_data
        
    def save_to_json(self, coins_data):
        """Save extracted coin data to a JSON file."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"top_coins_{timestamp}.json"
        filepath = self.data_dir / filename
        with open(filepath, "w") as f:
            json.dump(coins_data, f, indent=4)
        print(f"Saved top coins to: {filepath}")
        return str(filepath)
    
    def get_most_recent_file(self) -> Optional[str]:
        """
        Get the most recent JSON file saved in the data directory.

        Returns:
            Optional[str]: Path to the most recent file, or None if no files exist.
        """
        files = sorted(self.data_dir.glob("top_coins_*.json"))
        if not files:
            return None
        return str(files[-1])

    def load_most_recent_data(self) -> Optional[List[Dict[str, str]]]:
        """
        Load coin data from the most recent JSON file.

        Returns:
            Optional[List[Dict[str, str]]]: Loaded coin data, or None if no file exists.
        """
        recent_file = self.get_most_recent_file()
        if recent_file is None:
            return None
        with open(recent_file, "r") as f:
            return json.load(f)

# Example usage
if __name__ == "__main__":
    scraper = TopCoinsExtractor(num_coins=50)
    coins = scraper.fetch_coin_data()
    scraper.save_to_json(coins)