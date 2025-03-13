import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from config import config


class RedditSentimentService:
    def __init__(self):
        """Initialize the RedditSentimentService with Reddit authentication and VADER analyzer."""
        # Authenticate with Reddit using credentials from config
        self.reddit = praw.Reddit(
            client_id=config.redit_client_id,
            client_secret=config.redit_client_secret,
            user_agent=config.redit_user_agent,
        )
        # Download VADER lexicon for sentiment analysis (only needs to run once)
        nltk.download("vader_lexicon")
        # Initialize VADER sentiment analyzer
        self.sid = SentimentIntensityAnalyzer()

    def analyze_sentiment(
        self, search_term: str, sort: str = "hot", limit: int = 100
    ) -> float:
        """
        Analyze the sentiment of Reddit posts for a given search term.

        Args:
            search_term (str): The keyword to search for (e.g., 'XRP').
            sort (str): The sort order for the search (e.g., 'hot', 'new', 'top'). Default is 'hot'.
            limit (int): The maximum number of posts to retrieve. Default is 100.

        Returns:
            float: The average sentiment score of the posts (between -1 and 1).

        Raises:
            Exception: If an error occurs during the API request or sentiment analysis.
        """
        try:
            # Search for posts about the keyword across all subreddits
            posts = self.reddit.subreddit("all").search(
                search_term, sort=sort, limit=limit
            )
            # Analyze sentiment of each post title
            sentiments = []
            for post in posts:
                text = post.title  # Use post.selftext if you prefer the post body
                sentiment = self.sid.polarity_scores(text)
                sentiments.append(sentiment["compound"])
            # Calculate and return the average sentiment
            if sentiments:
                average_sentiment = sum(sentiments) / len(sentiments)
                return average_sentiment
            else:
                return 0.0  # Return neutral sentiment if no posts are found
        except Exception as e:
            raise Exception(f"Error fetching posts: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze sentiment of Reddit posts for a keyword."
    )
    parser.add_argument(
        "--search_term", required=True, help="The keyword to search for (e.g., 'XRP')"
    )
    args = parser.parse_args()

    service = RedditSentimentService()
    try:
        sentiment = service.analyze_sentiment(args.search_term)
        print(f"Average sentiment for {args.search_term}: {sentiment}")
    except Exception as e:
        print(f"Error: {e}")
