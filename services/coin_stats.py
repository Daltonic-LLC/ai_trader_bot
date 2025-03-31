import csv
import string
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class CoinStatsService:
    """
    A service for fetching and storing cryptocurrency statistics, such as price, market cap, and supply metrics.
    """
    def __init__(self, timeout: int = 60000):
        """
        Initialize the CoinStatsService.

        Args:
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
        """
        self.timeout = timeout
        self.base_dir = Path("data/realtime")
        self.base_dir.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def parse_value(text: Optional[str] = None) -> Union[float, str]:
        """
        Parse a value string into a float, handling currency symbols, suffixes, and units.

        Args:
            text (Optional[str]): The value string to parse (e.g., "$141.86B", "100B XRP").

        Returns:
            Union[float, str]: The parsed value or "N/A" if parsing fails.
        """
        if text is None or not isinstance(text, str) or text.strip() in ("", "No Data"):
            return "N/A"
        
        text = text.strip()
        parts = text.split()
        if not parts:
            return "N/A"
        
        for part in parts:
            if any(char.isdigit() for char in part):
                value_text = part
                break
        else:
            return "N/A"
        
        if value_text.startswith('$'):
            value_text = value_text[1:]
        
        if value_text[-1].isalpha():
            suffix = value_text[-1].upper()
            value_str = value_text[:-1].replace(',', '')
            try:
                value = float(value_str)
                multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
                return value * multipliers.get(suffix, 1)
            except ValueError:
                return "N/A"
        
        try:
            return float(value_text.replace(',', ''))
        except ValueError:
            return "N/A"

    def fetch_coin_stats(self, coin: str) -> Optional[Dict[str, Union[float, str, int]]]:
        """
        Fetch cryptocurrency statistics from CoinMarketCap.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').

        Returns:
            Optional[Dict]: A dictionary with coin statistics, or None if fetch fails.
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
                print(f"Navigating to {url} to fetch stats...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                page.wait_for_selector('span[data-test="text-cdp-price-display"]', timeout=self.timeout)

                data = {"coin": coin}

                price_element = page.locator('span[data-test="text-cdp-price-display"]')
                price_text = price_element.inner_text().strip() if price_element.count() > 0 else "N/A"
                data["price"] = self.parse_value(price_text)

                change_element = page.locator('div[data-role="el"] p[data-change]')
                if change_element.count() > 0:
                    change_text = change_element.inner_text().strip()
                    percentage_str = change_text.split('%')[0].strip()
                    try:
                        percentage = float(percentage_str)
                        direction = change_element.get_attribute('data-change')
                        if direction == 'down':
                            percentage = -percentage
                        data["price_change_24h_percent"] = percentage
                    except ValueError:
                        data["price_change_24h_percent"] = "N/A"
                else:
                    data["price_change_24h_percent"] = "N/A"

                page.wait_for_selector('div.coin-price-performance', timeout=self.timeout)
                low_label = page.locator('text="Low"')
                if low_label.count() > 0:
                    low_value = low_label.locator('xpath=following-sibling::span')
                    low_text = low_value.inner_text().strip() if low_value.count() > 0 else "N/A"
                    data["low_24h"] = self.parse_value(low_text)
                else:
                    data["low_24h"] = "N/A"

                high_label = page.locator('text="High"')
                if high_label.count() > 0:
                    high_value = high_label.locator('xpath=following-sibling::span')
                    high_text = high_value.inner_text().strip() if high_value.count() > 0 else "N/A"
                    data["high_24h"] = self.parse_value(high_text)
                else:
                    data["high_24h"] = "N/A"

                page.wait_for_selector('div.coin-metrics', timeout=self.timeout)
                metrics_container = page.locator('div.coin-metrics-table')
                metric_items = metrics_container.locator('div[data-role="group-item"]').all()

                label_to_key = {
                    "Market cap": "market_cap",
                    "Volume (24h)": "volume_24h",
                    "FDV": "fully_diluted_valuation",
                    "Vol/Mkt Cap (24h)": "vol_mkt_cap_24h",
                    "Total supply": "total_supply",
                    "Max. supply": "max_supply",
                    "Circulating supply": "circulating_supply"
                }

                def normalize_text(text):
                    text = text.replace('\u00a0', ' ')
                    text = text.translate(str.maketrans('', '', string.punctuation))
                    return text.strip().lower()

                for item in metric_items:
                    label_element = item.locator('div.LongTextDisplay_content-wrapper__2ho_9')
                    if label_element.count() > 0:
                        label_text = label_element.inner_text().strip()
                        normalized_label = normalize_text(label_text)
                        for keyword, key in label_to_key.items():
                            normalized_keyword = normalize_text(keyword)
                            if normalized_keyword in normalized_label:
                                value_element = item.locator('div.CoinMetrics_overflow-content__tlFu7 span')
                                value_text = value_element.inner_text().strip() if value_element.count() > 0 else "N/A"
                                data[key] = self.parse_value(value_text)
                                break

                print(f"Successfully fetched stats for {coin}: {data}")
                return data

            except PlaywrightTimeoutError:
                print(f"Timeout fetching stats for {coin}")
                return None
            except Exception as e:
                print(f"Error fetching stats for {coin}: {e}")
                return None
            finally:
                browser.close()

    def save_coin_stats_to_csv(self, coin: str, data: Dict, file_path: Optional[str] = None) -> str:
        """
        Save cryptocurrency statistics to a CSV file.

        Args:
            coin (str): The cryptocurrency slug.
            data (Dict): Dictionary containing coin statistics.
            file_path (Optional[str]): Custom file path. If None, uses default path.

        Returns:
            str: The path where the CSV file was saved.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if file_path is None:
            stats_dir = self.base_dir / coin / "stats"
            stats_dir.mkdir(exist_ok=True, parents=True)
            file_path = stats_dir / f"{coin}_stats.csv"
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
            timestamp, data.get("price", "N/A"), data.get("price_change_24h_percent", "N/A"),
            data.get("low_24h", "N/A"), data.get("high_24h", "N/A"),
            data.get("volume_24h", "N/A"), data.get("market_cap", "N/A"),
            data.get("fully_diluted_valuation", "N/A"), data.get("circulating_supply", "N/A"),
            data.get("total_supply", "N/A"), data.get("max_supply", "N/A")
        ]

        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)

        print(f"Stats saved to {file_path}")
        return str(file_path)

    def fetch_and_save_coin_stats(self, coin: str, save_csv: bool = True, csv_path: Optional[str] = None) -> Dict[str, Union[float, str]]:
        """
        Fetch and save cryptocurrency statistics.

        Args:
            coin (str): The cryptocurrency slug.
            save_csv (bool): Whether to save data to CSV. Default is True.
            csv_path (Optional[str]): Custom CSV path. If None, uses default.

        Returns:
            Dict: Results including coin statistics and file paths.
        """
        result = {"coin": coin, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        data = self.fetch_coin_stats(coin)
        if data:
            result.update(data)
            if save_csv:
                csv_file = self.save_coin_stats_to_csv(coin, data, csv_path)
                result["csv_file"] = csv_file
        else:
            result["error"] = "Failed to fetch stats"
        return result
    
    def get_latest_stats(self, coin: str) -> Optional[Dict[str, Union[str, float]]]:
        """
        Retrieve the most recently captured statistics for the specified cryptocurrency from the download directory.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'ethereum').

        Returns:
            Optional[Dict[str, Union[str, float]]]: A dictionary containing the most recent statistics,
            including price, timestamp, and other metrics, or None if no data is found.
        """
        # Construct the file path
        file_path = self.base_dir / coin / "stats" / f"{coin}_stats.csv"
        
        # Check if the file exists
        if not file_path.exists():
            return None
        
        # Read the CSV file, treating "N/A" as NaN
        df = pd.read_csv(file_path, na_values=["N/A"])
        
        # Check if the DataFrame is empty
        if df.empty:
            return None
        
        # Get the most recent row (last row)
        last_row = df.iloc[-1]
        
        # Define mapping from CSV headers to dictionary keys
        header_to_key = {
            "Timestamp": "timestamp",
            "Price (USD)": "price",
            "Price Change 24h (%)": "price_change_24h_percent",
            "Low 24h (USD)": "low_24h",
            "High 24h (USD)": "high_24h",
            "Volume 24h (USD)": "volume_24h",
            "Market Cap (USD)": "market_cap",
            "Fully Diluted Valuation (USD)": "fully_diluted_valuation",
            "Circulating Supply": "circulating_supply",
            "Total Supply": "total_supply",
            "Max Supply": "max_supply"
        }
        
        # Create the stats dictionary with mapped keys
        stats = {header_to_key[col]: last_row[col] for col in df.columns if col in header_to_key}
        
        # Add the coin name to the dictionary
        stats["coin"] = coin
        
        # Replace NaN values with "N/A" for consistency with fetch_coin_stats
        stats = {k: (v if not pd.isna(v) else "N/A") for k, v in stats.items()}
        
        return stats