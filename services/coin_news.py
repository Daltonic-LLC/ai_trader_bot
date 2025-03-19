import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict
import json
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer


class CoinNewsService:
    def __init__(self, timeout: int = 60000):
        """Initialize the CoinNewsService with a default timeout and VADER sentiment analyzer."""
        self.timeout = timeout
        nltk.download("vader_lexicon", quiet=True)
        self.sid = SentimentIntensityAnalyzer()

    def get_news_posts(
        self,
        coin: str,
        num_posts: int = 20,
        save_dir: str = "news",
    ) -> List[Dict]:
        """
        Gather recent news posts for the specified cryptocurrency and save them to a JSON file.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').
            num_posts (int): Number of recent posts to gather. Defaults to 20.
            save_dir (str): Directory to save raw JSON data. Defaults to 'news'.

        Returns:
            List[Dict]: List of post dictionaries.
        """
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
                url = f"https://coinmarketcap.com/community/coins/{coin}/top/"
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)
                time.sleep(5)  # Allow initial page load

                # Switch to 'Top' tab if not already selected
                top_tab = page.locator('li[data-test="tab-top"]').first
                if top_tab and top_tab.is_visible():
                    if "Tab_selected__zLjtL" not in top_tab.get_attribute("class"):
                        top_tab.click()
                        print("Switched to 'Top' tab.")
                        time.sleep(3)

                print("Waiting for initial feed items...")
                page.wait_for_selector('[data-test="feed-item"]', timeout=self.timeout)

                # Advanced scrolling to load more posts
                max_attempts = 20
                attempt = 0
                current_items = page.locator('[data-test="feed-item"]').all()
                while len(current_items) < num_posts and attempt < max_attempts:
                    previous_count = len(current_items)
                    technique = attempt % 3  # Cycle through 3 scrolling techniques

                    if technique == 0:
                        print("Using scroll to bottom technique...")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    elif technique == 1 and current_items:
                        print("Using scroll to last item technique...")
                        last_item = current_items[-1]
                        last_item.scroll_into_view_if_needed()
                    else:
                        print("Using incremental scrolling technique...")
                        for i in range(10):
                            scroll_amount = random.randint(300, 600)
                            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                            time.sleep(random.uniform(0.5, 1.0))

                    # Wait for new content to load
                    time.sleep(2)

                    new_items = page.locator('[data-test="feed-item"]').all()
                    new_count = len(new_items)
                    if new_count > previous_count:
                        print(
                            f"Loaded {new_count - previous_count} new posts. Total: {new_count}"
                        )
                        current_items = new_items
                    else:
                        print("No new posts loaded after scrolling.")
                        # Fallback methods
                        load_more = page.locator('button:has-text("Load More")').first
                        if load_more and load_more.is_visible():
                            print("Clicking 'Load More' button...")
                            load_more.click()
                            time.sleep(3)
                        else:
                            print("Pressing 'End' key as fallback...")
                            page.keyboard.press("End")
                            time.sleep(2)

                    attempt += 1

                # Final check and logging
                if len(current_items) < num_posts:
                    print(
                        f"Warning: Only {len(current_items)} posts loaded, less than requested {num_posts}."
                    )

                # Extract posts
                feed_items = current_items[:num_posts]  # Limit to requested number
                for i, item in enumerate(feed_items):
                    post_data = self._extract_post_data(item, coin)
                    if post_data:
                        posts.append(post_data)
                        print(f"Extracted post {i+1}/{len(feed_items)}")

                # Save to JSON
                if posts:
                    timestamp = int(time.time())
                    json_file = save_path / f"{coin}_news_{timestamp}.json"
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(posts, f, ensure_ascii=False, indent=4)
                    print(f"Saved {len(posts)} posts to {json_file}")
                else:
                    print("No posts extracted to save.")

            except PlaywrightTimeoutError as e:
                print(f"Timeout error for {coin}: {e}")
                return []
            except Exception as e:
                print(f"Failed to gather news for {coin}: {e}")
                return []
            finally:
                browser.close()

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
