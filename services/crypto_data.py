import time
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Union
import json
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class CryptoDataService:
    """
    A service for fetching and storing comprehensive cryptocurrency data, including price and market metrics.
    """

    def __init__(self, timeout: int = 60000):
        """
        Initialize the CryptoDataService.

        Args:
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
        """
        self.timeout = timeout
        self.base_dir = Path("realtime_data")
        self.base_dir.mkdir(exist_ok=True, parents=True)
        nltk.download("vader_lexicon", quiet=True)
        self.sid = SentimentIntensityAnalyzer()

    @staticmethod
    def parse_value(text: str) -> Union[float, str]:
        """
        Parse a value string into a float, handling currency symbols and suffixes.

        Args:
            text (str): The value string to parse (e.g., "$141.86B", "58.1B").

        Returns:
            Union[float, str]: The parsed value or "N/A" if parsing fails.
        """
        text = text.strip()
        if text == "No Data":
            return "N/A"
        if text.startswith('$'):
            text = text[1:]
        if text[-1].isalpha():
            suffix = text[-1].upper()
            value_str = text[:-1].replace(',', '')
            try:
                value = float(value_str)
            except ValueError:
                return "N/A"
            multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
            if suffix in multipliers:
                return value * multipliers[suffix]
            else:
                return "N/A"
        else:
            try:
                return float(text.replace(',', ''))
            except ValueError:
                return "N/A"

    def fetch_crypto_data(self, coin: str) -> Optional[Dict[str, Union[float, str, int]]]:
        """
        Fetch comprehensive cryptocurrency data from CoinMarketCap.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').

        Returns:
            Optional[Dict]: A dictionary with price and market data, or None if fetch fails.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()
                url = f"https://coinmarketcap.com/currencies/{coin}/"
                print(f"Navigating to {url} to fetch data...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Wait for the price element to ensure the page is loaded
                page.wait_for_selector('span[data-test="text-cdp-price-display"]', timeout=self.timeout)

                data = {"coin": coin}

                # Extract Price
                price_element = page.locator('span[data-test="text-cdp-price-display"]')
                price_text = price_element.inner_text().strip()
                data["price"] = self.parse_value(price_text)

                # Extract 24h Price Change (scoped to the overview section)
                change_element = page.locator('#section-coin-overview p.change-text')
                if change_element.count() == 1:
                    change_text = change_element.inner_text().strip().split('%')[0]
                    data["price_change_24h_percent"] = float(change_text)
                else:
                    print(f"Error: Expected 1 change element, found {change_element.count()}")
                    data["price_change_24h_percent"] = "N/A"

                # Extract 24h Low/High
                low_high_div = page.locator('div:has(div:text("Low")):has(div:text("High"))')
                if low_high_div.count() >= 1:
                    low_text = low_high_div.locator('span').nth(0).inner_text().strip()
                    high_text = low_high_div.locator('span').nth(1).inner_text().strip()
                    data["low_24h"] = self.parse_value(low_text)
                    data["high_24h"] = self.parse_value(high_text)
                else:
                    print(f"Error: Expected at least 1 low/high div, found {low_high_div.count()}")
                    data["low_24h"] = "N/A"
                    data["high_24h"] = "N/A"

                # Fetch all metrics from the coin-metrics-table
                metrics_container = page.locator('div.coin-metrics-table')
                if metrics_container.count() == 0:
                    print("Error: Coin metrics container not found.")
                    return data

                metric_items = metrics_container.locator('div[data-role="group-item"]').all()

                # Map labels to data keys
                label_to_key = {
                    "Market cap": "market_cap",
                    "Volume (24h)": "volume_24h",
                    "FDV": "fully_diluted_valuation",
                    "Vol/Mkt Cap (24h)": "vol_mkt_cap_24h",
                    "Total supply": "total_supply",
                    "Max. supply": "max_supply",
                    "Circulating supply": "circulating_supply"
                }

                for item in metric_items:
                    label_element = item.locator('dt div.LongTextDisplay_content-wrapper__2ho_9')
                    value_element = item.locator('dd div.CoinMetrics_overflow-content__tlFu7 span')

                    label = label_element.inner_text().strip() if label_element.count() == 1 else None
                    value_text = value_element.inner_text().strip() if value_element.count() == 1 else "N/A"

                    if label and label in label_to_key:
                        data[label_to_key[label]] = self.parse_value(value_text) if value_text != "N/A" else "N/A"

                print(f"Successfully fetched data for {coin}: Price=${data['price']}, Change={data['price_change_24h_percent']}%")
                return data

            except PlaywrightTimeoutError:
                print(f"Timeout fetching data for {coin}")
                return None
            except Exception as e:
                print(f"Error fetching data for {coin}: {e}")
                return None
            finally:
                browser.close()

    def save_price_to_csv(self, coin: str, data: Dict, file_path: Optional[str] = None) -> str:
        """
        Save cryptocurrency data to a CSV file.

        Args:
            coin (str): The cryptocurrency slug.
            data (Dict): Dictionary containing price and market data.
            file_path (Optional[str]): Custom file path. If None, uses default path.

        Returns:
            str: The path where the CSV file was saved.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if file_path is None:
            price_dir = self.base_dir / coin / "price_data"
            price_dir.mkdir(exist_ok=True, parents=True)
            file_path = price_dir / f"{coin}_price_data.csv"
        else:
            file_path = Path(file_path)
            file_path.parent.mkdir(exist_ok=True, parents=True)

        file_exists = file_path.exists()
        headers = [
            "Timestamp", "Price (USD)", "Price Change 24h (%)", "Low 24h (USD)", "High 24h (USD)",
            "Volume 24h (USD)", "Market Cap (USD)", "Fully Diluted Valuation (USD)",
            "Circulating Supply", "Total Supply", "Max Supply"
        ]
        row = [
            timestamp, data["price"], data["price_change_24h_percent"], data.get("low_24h", "N/A"), data.get("high_24h", "N/A"),
            data.get("volume_24h", "N/A"), data.get("market_cap", "N/A"), data.get("fully_diluted_valuation", "N/A"),
            data.get("circulating_supply", "N/A"), data.get("total_supply", "N/A"), data.get("max_supply", "N/A")
        ]

        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)

        print(f"Data saved to {file_path}")
        return str(file_path)

    def get_news_and_sentiment(self, coin: str, num_posts: int = 20, save_dir: Optional[str] = None) -> Tuple[List[Dict], float]:
        """
        Gather news posts and calculate sentiment score from CoinMarketCap.

        Args:
            coin (str): The cryptocurrency slug.
            num_posts (int): Number of news posts to fetch. Default is 20.
            save_dir (Optional[str]): Directory to save news data. If None, uses default.

        Returns:
            Tuple[List[Dict], float]: List of news posts and compound sentiment score.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_context().new_page()
                url = f"https://coinmarketcap.com/currencies/{coin}/news/"
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Assuming news articles are in a list with a specific class or structure
                news_items = page.locator('article').all()[:num_posts]
                posts = []
                total_sentiment = 0.0
                for item in news_items:
                    title = item.locator('h3').inner_text().strip() if item.locator('h3').count() > 0 else "No title"
                    summary = item.locator('p').inner_text().strip() if item.locator('p').count() > 0 else ""
                    sentiment = self.sid.polarity_scores(summary or title)['compound']
                    posts.append({"title": title, "summary": summary, "sentiment": sentiment})
                    total_sentiment += sentiment

                sentiment_score = total_sentiment / len(posts) if posts else 0.0

                if save_dir is None:
                    news_dir = self.base_dir / coin / "news_data"
                else:
                    news_dir = Path(save_dir)
                news_dir.mkdir(exist_ok=True, parents=True)

                news_file = news_dir / f"{coin}_news.json"
                with open(news_file, 'w') as f:
                    json.dump(posts, f, indent=2)
                print(f"News data saved to {news_file}")

                return posts, sentiment_score

            except Exception as e:
                print(f"Error fetching news for {coin}: {e}")
                return [], 0.0
            finally:
                browser.close()

    def fetch_and_save_crypto_data(
        self,
        coin: str,
        include_news: bool = True,
        news_posts: int = 20,
        save_csv: bool = True,
        csv_path: Optional[str] = None
    ) -> Dict[str, Union[float, str]]:
        """
        Fetch and save cryptocurrency data, optionally including news sentiment.

        Args:
            coin (str): The cryptocurrency slug.
            include_news (bool): Whether to fetch news sentiment. Default is True.
            news_posts (int): Number of news posts to fetch. Default is 20.
            save_csv (bool): Whether to save data to CSV. Default is True.
            csv_path (Optional[str]): Custom CSV path. If None, uses default.

        Returns:
            Dict: Results including price, market data, and file paths.
        """
        result = {"coin": coin, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        # Fetch cryptocurrency data
        data = self.fetch_crypto_data(coin)
        if data:
            result.update(data)
            if save_csv:
                csv_file = self.save_price_to_csv(coin, data, csv_path)
                result["csv_file"] = csv_file
        else:
            result["error"] = "Failed to fetch data"

        # Fetch news sentiment if requested
        if include_news:
            posts, sentiment = self.get_news_and_sentiment(coin, news_posts)
            result["sentiment"] = sentiment
            result["news_count"] = len(posts)

        return result


if __name__ == "__main__":
    # Example usage
    service = CryptoDataService()
    result = service.fetch_and_save_crypto_data("xrp", include_news=False)
    print("\nSummary of fetched data:")
    for key, value in result.items():
        print(f"{key.replace('_', ' ').title()}: {value}")