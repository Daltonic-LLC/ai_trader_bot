import time
import random
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
        num_posts: int = 20,  # Default to 20 posts
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
            # Use a larger viewport to potentially load more posts initially
            context = browser.new_context(
                viewport={"width": 1920, "height": 3000},  # Increased height
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                # Navigate to the coin's "Top" news page
                url = f"https://coinmarketcap.com/community/coins/{coin}/top/"
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Add a delay to ensure the page fully loads
                time.sleep(5)  # Increased initial wait time

                # Check if the "Top" tab is already active
                top_tab = page.locator('li[data-test="tab-top"]').first
                if top_tab and top_tab.is_visible():
                    if (
                        "Tab_selected__zLjtL" in top_tab.get_attribute("class")
                        or top_tab.get_attribute("aria-selected") == "true"
                    ):
                        print("'Top' tab is already active.")
                    else:
                        top_tab.click()
                        print("Switched to 'Top' tab.")
                        time.sleep(3)  # Wait after clicking tab
                else:
                    print("Could not locate 'Top' tab; proceeding with default view.")

                # Wait for initial feed items to load
                try:
                    page.wait_for_selector(
                        '[data-test="feed-item"]', state="visible", timeout=self.timeout
                    )
                except PlaywrightTimeoutError:
                    print(
                        "No feed items found within timeout period. Inspect the page structure."
                    )
                    return [], 0.5

                # Advanced loading techniques
                max_attempts = 20  # Increased max attempts
                attempt = 0

                print("Starting advanced loading process...")
                while attempt < max_attempts:
                    current_items = page.locator('[data-test="feed-item"]').all()
                    current_count = len(current_items)
                    print(f"Current feed items count: {current_count}")

                    if current_count >= num_posts:
                        print(
                            f"Target reached: {current_count}/{num_posts} posts loaded"
                        )
                        break

                    # Try various scrolling techniques
                    if attempt % 3 == 0:
                        # Technique 1: Scroll to bottom
                        print("Using scroll to bottom technique")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    elif attempt % 3 == 1:
                        # Technique 2: Scroll to last item (corrected method)
                        print("Using scroll to last item technique")
                        if current_items:
                            try:
                                last_item = current_items[-1]
                                last_item.scroll_into_view_if_needed()  # Correct method
                            except Exception as e:
                                print(f"Error scrolling to last item: {e}")
                    else:
                        # Technique 3: Incremental scrolling with random pauses (refined)
                        print("Using incremental scrolling technique")
                        for i in range(10):  # More iterations
                            scroll_amount = random.randint(300, 600)  # Smaller steps
                            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                            time.sleep(random.uniform(0.5, 1.0))  # Longer pauses

                    # Wait for new content to load with random timing to appear more human-like
                    time.sleep(random.uniform(2.0, 3.5))

                    # Check for new items
                    new_items = page.locator('[data-test="feed-item"]').all()
                    new_count = len(new_items)

                    if new_count > current_count:
                        print(f"Success! Loaded {new_count - current_count} new items")
                    else:
                        print(
                            f"No new items loaded on attempt {attempt+1}/{max_attempts}"
                        )

                        # If we're stuck, try clicking "Load More" button if it exists
                        load_more = page.locator('button:has-text("Load More")').first
                        if load_more and load_more.is_visible():
                            print("Found 'Load More' button, clicking it...")
                            load_more.click()
                            time.sleep(3)
                        else:
                            # Try to interact with the page in different ways to trigger content loading
                            # Method 1: Press End key
                            if attempt % 2 == 0:
                                print("Pressing End key to trigger loading...")
                                page.keyboard.press("End")
                                time.sleep(2)

                    attempt += 1

                # Final check of how many items we have
                feed_items = page.locator('[data-test="feed-item"]').all()
                total_items = len(feed_items)
                print(f"Total items found after all attempts: {total_items}")

                # If fewer posts are loaded than requested, print a warning
                if total_items < num_posts:
                    print(
                        f"Warning: Could only load {total_items} out of {num_posts} requested posts."
                    )

                # Use all the items we found, up to the requested number
                items_to_process = min(total_items, num_posts)
                print(f"Processing {items_to_process} items...")

                # Extract posts
                for i in range(items_to_process):
                    try:
                        item = feed_items[i]
                        post_data = self._extract_post_data(item, coin)
                        if post_data:
                            posts.append(post_data)
                            print(
                                f"Extracted post {i+1}/{items_to_process}: {post_data['username']} - {post_data['text'][0][:50] if post_data['text'] else 'No text'}..."
                            )
                    except Exception as e:
                        print(f"Error processing item {i+1}: {e}")

                # Calculate sentiment score
                sentiment_score = self._calculate_sentiment_score(posts)
                print(f"Calculated sentiment score: {sentiment_score:.2f}")

            except PlaywrightTimeoutError as e:
                raise Exception(
                    f"Timeout error while gathering news for {coin}: {str(e)}"
                )
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
        try:
            username = post_element.locator('[data-test="post-username"]').first
            username_text = (
                username.inner_text().strip()
                if username and username.is_visible()
                else "Anonymous"
            )

            time_element = post_element.locator(".tooltip").first
            time_text = (
                time_element.inner_text().strip()
                if time_element and time_element.is_visible()
                else "Unknown"
            )

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

            # Extract reaction counts
            reaction_elements = post_element.locator(".emoji-list-item span").all()
            for i, span in enumerate(reaction_elements):
                try:
                    count = span.inner_text().strip()
                    if count.isdigit() or (
                        count.replace(".", "").isdigit() and "." in count
                    ):  # Handle decimal counts
                        reaction_type = self._get_reaction_type(
                            post_element.locator(".emoji-list-item").nth(i)
                        )
                        post_data["reactions"][reaction_type] = (
                            float(count) if "." in count else int(count)
                        )
                except Exception as e:
                    print(f"Error processing reaction {i}: {e}")

            return post_data
        except Exception as e:
            print(f"Error extracting post data: {e}")
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
        """Calculate a sentiment score based on reaction counts."""
        if not posts:
            return 0.5  # Neutral if no posts

        total_positive = 0
        total_negative = 0
        weight_positive = {
            "BULL": 2,
            "LIKE": 1,
            "GOOD": 1,
            "HODL": 1,
            "BUIDL": 1,
            "CELEBRATION": 1,
            "FIRE": 1,
        }
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
        posts, sentiment = service.get_news_and_sentiment(coin="xrp", num_posts=25)
        print("\nNews Posts:")
        for post in posts:
            print(
                f"User: {post['username']}, Time: {post['time']}, Text: {''.join(post['text'])[:100]}..."
            )
            print(f"Reactions: {post['reactions']}")
        print(f"Overall Sentiment Score: {sentiment:.2f}")
    except Exception as e:
        print(f"Error: {e}")
