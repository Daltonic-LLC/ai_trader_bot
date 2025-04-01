import json
import random
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class NewsSentimentService:
    """
    A service for fetching community posts and calculating sentiment scores for cryptocurrencies from CoinMarketCap.
    """
    def __init__(self, timeout: int = 60000):
        """
        Initialize the NewsSentimentService.

        Args:
            timeout (int): Timeout in milliseconds for browser operations. Default is 60 seconds.
        """
        self.timeout = timeout
        self.base_dir = Path("data/realtime")
        self.base_dir.mkdir(exist_ok=True, parents=True)
        nltk.download("vader_lexicon", quiet=True)
        self.sid = SentimentIntensityAnalyzer()

    #### New Helper Methods ####

    def calculate_sentiment_score(self, posts: List[Dict]) -> float:
        """
        Calculate the average sentiment score from a list of posts.

        Args:
            posts (List[Dict]): List of post dictionaries with 'sentiment' key.

        Returns:
            float: Average sentiment score.
        """
        if not posts:
            return 0.0
        total_sentiment = sum(post.get("sentiment", 0.0) for post in posts)
        return total_sentiment / len(posts)

    def process_posts(self, posts: List[Dict]) -> List[Dict]:
        """
        Analyze sentiment for each post and update the post dictionary.

        Args:
            posts (List[Dict]): List of post dictionaries.

        Returns:
            List[Dict]: Updated list with sentiment scores.
        """
        for post in posts:
            text = " ".join(post.get("text", []))
            sentiment = self.sid.polarity_scores(text)['compound'] if text else 0.0
            post["sentiment"] = sentiment
        return posts

    #### Renamed and Updated Method ####

    def fetch_news_and_sentiment(self, coin: str, num_posts: int = 20, save_dir: Optional[str] = None) -> Tuple[List[Dict], float]:
        """
        Fetch community posts and calculate sentiment score from CoinMarketCap's community page.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').
            num_posts (int): Number of posts to fetch. Default is 20.
            save_dir (Optional[str]): Directory to save news data. If None, uses default.

        Returns:
            Tuple[List[Dict], float]: List of post dictionaries and compound sentiment score.
        """
        posts = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 3000},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            url = f"https://coinmarketcap.com/community/coins/{coin}/top/"
            print(f"Navigating to {url}...")
            page.goto(url, wait_until="networkidle", timeout=self.timeout)
            time.sleep(5)  # Initial wait for page load

            try:
                # Wait for feed items to appear
                try:
                    page.wait_for_selector('[data-test="feed-item"]', state="visible", timeout=self.timeout)
                except PlaywrightTimeoutError:
                    print("No feed items found within timeout period.")
                    return [], 0.0

                # Advanced loading process to ensure enough posts are fetched
                max_attempts = num_posts
                consecutive_failures = 0
                attempt = 0

                print("Starting advanced loading process...")
                while attempt < max_attempts:
                    current_items = page.locator('[data-test="feed-item"]').all()
                    current_count = len(current_items)
                    if current_count >= num_posts:
                        print(f"Target reached: {current_count}/{num_posts} posts loaded")
                        break

                    print(f"Attempt {attempt + 1}: Current posts: {current_count}")

                    # Check for "Load More" button
                    load_more = page.locator('button:has-text("Load More")').first
                    if load_more and load_more.is_visible():
                        print("Clicking 'Load More' button...")
                        load_more.click()
                        time.sleep(3)
                        consecutive_failures = 0
                    else:
                        # Apply scrolling technique
                        technique = attempt % 3
                        if technique == 0:
                            print("Scrolling to bottom...")
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        elif technique == 1 and current_items:
                            print("Scrolling to last item...")
                            last_item = current_items[-1]
                            last_item.scroll_into_view_if_needed()
                        else:
                            print("Performing incremental scrolling...")
                            for i in range(10):
                                scroll_amount = random.randint(300, 600)
                                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                                time.sleep(random.uniform(0.5, 1.0))

                        time.sleep(random.uniform(2.0, 3.5))

                    # Check if new posts loaded
                    new_items = page.locator('[data-test="feed-item"]').all()
                    new_count = len(new_items)
                    if new_count > current_count:
                        print(f"Loaded {new_count - current_count} new posts. Total: {new_count}")
                        consecutive_failures = 0
                    else:
                        print("No new posts loaded.")
                        consecutive_failures += 1
                        if consecutive_failures >= 5:
                            print("Stopping after 5 consecutive failures to load new posts.")
                            break

                    attempt += 1

                # Process fetched posts
                feed_items = page.locator('[data-test="feed-item"]').all()
                total_items = len(feed_items)
                print(f"Total items found: {total_items}")
                if total_items < num_posts:
                    print(f"Warning: Loaded only {total_items} out of {num_posts} requested posts.")

                items_to_process = min(total_items, num_posts)
                for i in range(items_to_process):
                    try:
                        item = feed_items[i]
                        post_data = self._extract_post_data(item)
                        if post_data:
                            posts.append(post_data)
                            print(f"Extracted post {i+1}/{items_to_process}: {post_data['title'][:50]}...")
                    except Exception as e:
                        print(f"Error processing item {i+1}: {e}")

            except Exception as e:
                print(f"Failed to gather posts for {coin}: {str(e)}")
                return [], 0.0
            finally:
                browser.close()

            # Process posts to calculate sentiment
            posts = self.process_posts(posts)
            sentiment_score = self.calculate_sentiment_score(posts)

            # Save to file
            news_dir = Path(save_dir) if save_dir else self.base_dir / coin / "news"
            news_dir.mkdir(exist_ok=True, parents=True)
            news_file = news_dir / f"{coin}_news.json"
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2)
            print(f"Posts saved to {news_file}")

            return posts, sentiment_score

    def _extract_post_data(self, post_element) -> Dict:
        """
        Extract data from a single community post element.

        Args:
            post_element: The Playwright element handle for the post.

        Returns:
            Dict: Dictionary containing post data (username, time, text, sentiment).
        """
        try:
            username = post_element.locator('[data-test="post-username"]').first
            username_text = username.inner_text().strip() if username else "Anonymous"

            time_element = post_element.locator(".tooltip").first
            time_text = time_element.inner_text().strip() if time_element else "Unknown"

            text_elements = post_element.locator(".text-content").all()
            text_contents = [p.inner_text().strip() for p in text_elements if p.inner_text().strip()]

            title = text_contents[0] if text_contents else "No title"

            return {
                "username": username_text,
                "time": time_text,
                "title": title,
                "text": text_contents,
                "sentiment": 0.0  # Placeholder, calculated later
            }
        except Exception:
            return None

    #### New Method for Saved Data ####

    def get_saved_news_and_sentiment(self, coin: str) -> Tuple[List[Dict], float]:
        """
        Load saved news posts and calculate sentiment score for a cryptocurrency from stored data.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').

        Returns:
            Tuple[List[Dict], float]: List of post dictionaries and compound sentiment score.
        """
        news_dir = self.base_dir / coin / "news"
        news_file = news_dir / f"{coin}_news.json"
        if not news_file.exists():
            print(f"No saved news data found for {coin} at {news_file}")
            return [], 0.0
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {news_file}: {e}")
            return [], 0.0
        except Exception as e:
            print(f"Error reading {news_file}: {e}")
            return [], 0.0
        if not posts:
            print(f"No posts found in saved data for {coin}")
            return [], 0.0
        sentiment_score = self.calculate_sentiment_score(posts)
        return posts, sentiment_score

if __name__ == "__main__":
    service = NewsSentimentService()
    posts, sentiment = service.fetch_news_and_sentiment("xrp")
    print(f"Gathered {len(posts)} posts with average sentiment {sentiment:.2f}")
    # Optional: Test the new method
    saved_posts, saved_sentiment = service.get_saved_news_and_sentiment("xrp")
    print(f"Loaded {len(saved_posts)} saved posts with average sentiment {saved_sentiment:.2f}")