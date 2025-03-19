import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Tuple
import json
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer


class CoinNewsService:
    def __init__(self, timeout: int = 60000):
        """Initialize the CoinNewsService with a default timeout and VADER sentiment analyzer."""
        self.timeout = timeout
        nltk.download("vader_lexicon", quiet=True)
        self.sid = SentimentIntensityAnalyzer()

    def get_news_and_sentiment(
        self,
        coin: str,
        num_posts: int = 20,
        save_dir: str = "news",
    ) -> Tuple[List[Dict], float]:
        """
        Gather recent news posts and calculate sentiment score for the specified cryptocurrency.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').
            num_posts (int): Number of recent posts to gather. Defaults to 20.
            save_dir (str): Directory to save raw JSON data. Defaults to 'news'.

        Returns:
            Tuple[List[Dict], float]: A tuple containing a list of post dictionaries and the sentiment score.

        Raises:
            Exception: If navigation or data extraction fails.
        """
        # Ensure save directory exists
        save_path = Path(save_dir)
        save_path.mkdir(exist_ok=True, parents=True)

        posts = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 3000},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                # Navigate to the coin's "Top" news page
                url = f"https://coinmarketcap.com/community/coins/{coin}/top/"
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)
                time.sleep(5)  # Initial wait for page load

                # Wait for initial feed items
                try:
                    page.wait_for_selector(
                        '[data-test="feed-item"]', state="visible", timeout=self.timeout
                    )
                except PlaywrightTimeoutError:
                    print("No feed items found within timeout period.")
                    return [], 0.5

                # Initialize variables for advanced loading
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

                    # Check for "Load More" button first
                    load_more = page.locator('button:has-text("Load More")').first
                    if load_more and load_more.is_visible():
                        print("Clicking 'Load More' button...")
                        load_more.click()
                        time.sleep(3)
                        consecutive_failures = 0
                    else:
                        # Apply scrolling technique based on attempt number
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

                        # Wait for new content to load
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

                # Final check of loaded items
                feed_items = page.locator('[data-test="feed-item"]').all()
                total_items = len(feed_items)
                print(f"Total items found: {total_items}")
                if total_items < num_posts:
                    print(f"Warning: Loaded only {total_items} out of {num_posts} requested posts.")

                # Process up to num_posts items
                items_to_process = min(total_items, num_posts)
                for i in range(items_to_process):
                    try:
                        item = feed_items[i]
                        post_data = self._extract_post_data(item, coin)
                        if post_data:
                            posts.append(post_data)
                            print(
                                f"Extracted post {i+1}/{items_to_process}: {post_data['username']} - "
                                f"{post_data['text'][0][:50] if post_data['text'] else 'No text'}..."
                            )
                    except Exception as e:
                        print(f"Error processing item {i+1}: {e}")

            except PlaywrightTimeoutError as e:
                raise Exception(f"Timeout error while gathering news for {coin}: {str(e)}")
            except Exception as e:
                raise Exception(f"Failed to gather news for {coin}: {str(e)}")
            finally:
                browser.close()

        # Save posts as JSON
        if posts:
            timestamp = int(time.time())
            json_file = save_path / f"{coin}_news_{timestamp}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(posts, f, ensure_ascii=False, indent=4)
            print(f"Saved posts to {json_file}")

        return posts
    def _extract_post_data(self, post_element, coin: str) -> Dict:
        """Extract data from a single post element."""
        try:
            username = post_element.locator('[data-test="post-username"]').first
            username_text = username.inner_text().strip() if username else "Anonymous"

            time_element = post_element.locator(".tooltip").first
            time_text = time_element.inner_text().strip() if time_element else "Unknown"

            text_elements = post_element.locator(".text-content").all()
            text_contents = [
                p.inner_text().strip() for p in text_elements if p.inner_text().strip()
            ]

            post_data = {
                "username": username_text,
                "time": time_text,
                "text": text_contents,
                "reactions": {},
            }

            reaction_elements = post_element.locator(".emoji-list-item span").all()
            for i, span in enumerate(reaction_elements):
                count = span.inner_text().strip()
                if count.isdigit() or (
                    count.replace(".", "").isdigit() and "." in count
                ):
                    reaction_type = self._get_reaction_type(
                        post_element.locator(".emoji-list-item").nth(i)
                    )
                    post_data["reactions"][reaction_type] = (
                        float(count) if "." in count else int(count)
                    )

            return post_data
        except Exception:
            return None

    def _get_reaction_type(self, reaction_element) -> str:
        """Determine the type of reaction based on the SVG icon."""
        try:
            svg_use = reaction_element.locator("svg use").get_attribute("href")
            reaction_map = {
                "#LIKE": "LIKE",
                "#profit": "BULL",
                "#lost": "BEAR",
                "#HODL": "HODL",
                "#BUILD": "BUIDL",
                "#FIRE": "FIRE",
                "#laughcry": "LAUGH_CRY",
                "#CRY": "CRY",
                "#FOMO": "FOMO",
                "#CELEBRATION": "CELEBRATION",
                "#GOOD": "GOOD",
            }
            return reaction_map.get(svg_use, "UNKNOWN")
        except Exception:
            return "UNKNOWN"

    def _calculate_sentiment_score(self, posts: List[Dict]) -> float:
        """Calculate sentiment score based on post text using VADER."""
        if not posts:
            return 0.5

        text_scores = []
        for post in posts:
            text = " ".join(post.get("text", []))
            if text:
                sentiment = self.sid.polarity_scores(text)
                score = (sentiment["compound"] + 1) / 2  # Normalize to 0-1
                text_scores.append(score)
        return sum(text_scores) / len(text_scores) if text_scores else 0.5

    def _get_last_json_file(self, coin: str, save_dir: str) -> str:
        """Find the most recent JSON file for the specified coin."""
        save_path = Path(save_dir)
        files = list(save_path.glob(f"{coin}_news_*.json"))
        if not files:
            raise FileNotFoundError(f"No JSON files found for {coin} in {save_dir}")
        timestamps = [(file, int(file.stem.split("_")[-1])) for file in files]
        last_file = max(timestamps, key=lambda x: x[1])[0]
        return str(last_file)

    def calculate_sentiment_from_last_file(
        self, coin: str, save_dir: str = "news"
    ) -> float:
        """Calculate sentiment score from the most recent JSON file for the coin."""
        last_file = self._get_last_json_file(coin, save_dir)
        with open(last_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
        return self._calculate_sentiment_score(posts)


if __name__ == "__main__":
    service = CoinNewsService()
    try:
        posts = service.get_news_posts(coin="xrp", num_posts=20)
        print(f"Gathered {len(posts)} posts.")
        sentiment = service.calculate_sentiment_from_last_file(coin="xrp")
        print(f"Sentiment score from last file: {sentiment:.2f}")
    except Exception as e:
        print(f"Error: {e}")
