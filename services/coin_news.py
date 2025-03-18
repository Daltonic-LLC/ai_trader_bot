import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import List, Dict, Tuple
import json

class CoinNewsService:
    def __init__(self, timeout: int = 60000):
        """Initialize the CoinNewsService with a default timeout."""
        self.timeout = timeout

    def get_news_and_sentiment(
        self,
        coin: str,
        num_posts: int = 5,
        save_dir: str = "news",
    ) -> Tuple[List[Dict], float]:
        """
        Gather recent news posts and calculate sentiment score for the specified cryptocurrency.

        Args:
            coin (str): The cryptocurrency slug (e.g., 'bitcoin', 'xrp').
            num_posts (int): Number of recent posts to gather. Defaults to 5.
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
            context = browser.new_context()
            page = context.new_page()

            try:
                # Navigate to the coin's "Top" news page
                url = f"https://coinmarketcap.com/community/coins/{coin}/top/"
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Add a delay to ensure the page fully loads
                time.sleep(3)

                # Check if the "Top" tab is already active
                top_tab = page.locator('li[data-test="tab-top"]').first
                if top_tab and top_tab.is_visible():
                    if "Tab_selected__zLjtL" in top_tab.get_attribute("class") or top_tab.get_attribute("aria-selected") == "true":
                        print("'Top' tab is already active.")
                    else:
                        top_tab.click()
                        print("Switched to 'Top' tab.")
                else:
                    print("Could not locate 'Top' tab; proceeding with default view.")

                # Wait for initial feed items to load
                try:
                    page.wait_for_selector('[data-test="feed-item"]', state="visible", timeout=self.timeout)
                except PlaywrightTimeoutError:
                    print("No feed items found within timeout period. Inspect the page structure.")
                    return [], 0.5

                # Scroll to load more posts
                while len(posts) < num_posts:
                    feed_items = page.locator('[data-test="feed-item"]').all()
                    current_count = len(feed_items)
                    print(f"Current feed items count: {current_count}")

                    if current_count >= num_posts:
                        break

                    # Scroll to the bottom of the page directly
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)  # Wait 3 seconds for new content to load

                    # Check if new items have loaded
                    new_count = len(page.locator('[data-test="feed-item"]').all())
                    if new_count == current_count:
                        print(f"No more new posts loaded. Total found: {current_count}")
                        break

                # Extract posts
                feed_items = page.locator('[data-test="feed-item"]').all()[:num_posts]
                print(f"Found {len(feed_items)} feed items on the page.")
                for i, item in enumerate(feed_items):
                    post_data = self._extract_post_data(item, coin)
                    if post_data and any(coin.lower() in text.lower() for text in post_data.get("text", [])):
                        posts.append(post_data)
                        print(f"Extracted post {i+1}/{num_posts}: {post_data['username']} - {post_data['text'][0][:50]}...")
                    if len(posts) >= num_posts:
                        break

                # Calculate sentiment score
                sentiment_score = self._calculate_sentiment_score(posts)
                print(f"Calculated sentiment score: {sentiment_score:.2f}")

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

        return posts, sentiment_score

    def _extract_post_data(self, post_element, coin: str) -> Dict:
        """Extract data from a single post element."""
        post_data = {
            "username": post_element.locator('[data-test="post-username"]').inner_text().strip() or "Anonymous",
            "time": post_element.locator(".tooltip").inner_text().strip() or "Unknown",
            "text": [p.inner_text().strip() for p in post_element.locator(".text-content").all() if p.inner_text().strip()],
            "reactions": {}
        }

        # Extract reaction counts
        reaction_elements = post_element.locator(".emoji-list-item span").all()
        for i, span in enumerate(reaction_elements):
            count = span.inner_text().strip()
            if count.isdigit() or (count.replace(".", "").isdigit() and "." in count):  # Handle decimal counts
                reaction_type = self._get_reaction_type(post_element.locator(".emoji-list-item").nth(i))
                post_data["reactions"][reaction_type] = float(count) if "." in count else int(count)

        return post_data

    def _get_reaction_type(self, reaction_element) -> str:
        """Determine the type of reaction based on the SVG icon."""
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
            "#GOOD": "GOOD"
        }
        return reaction_map.get(svg_use, "UNKNOWN")

    def _calculate_sentiment_score(self, posts: List[Dict]) -> float:
        """Calculate a sentiment score based on reaction counts."""
        if not posts:
            return 0.5  # Neutral if no posts

        total_positive = 0
        total_negative = 0
        weight_positive = {"BULL": 2, "LIKE": 1, "GOOD": 1, "HODL": 1, "BUIDL": 1, "CELEBRATION": 1, "FIRE": 1}
        weight_negative = {"BEAR": 2, "CRY": 1, "LAUGH_CRY": 1, "FOMO": 1}

        for post in posts:
            for reaction, count in post.get("reactions", {}).items():
                if reaction in weight_positive:
                    total_positive += count * weight_positive[reaction]
                elif reaction in weight_negative:
                    total_negative += count * weight_negative[reaction]

        total_reactions = total_positive + total_negative
        if total_reactions == 0:
            return 0.5  # Neutral if no reactions
        sentiment_score = total_positive / total_reactions
        return min(max(sentiment_score, 0.0), 1.0)  # Ensure score is between 0 and 1

# Example usage
if __name__ == "__main__":
    service = CoinNewsService()
    try:
        posts, sentiment = service.get_news_and_sentiment(coin="xrp", num_posts=20)
        print("\nNews Posts:")
        for post in posts:
            print(f"User: {post['username']}, Time: {post['time']}, Text: {''.join(post['text'])[:100]}...")
            print(f"Reactions: {post['reactions']}")
        print(f"Overall Sentiment Score: {sentiment:.2f}")
    except Exception as e:
        print(f"Error: {e}")