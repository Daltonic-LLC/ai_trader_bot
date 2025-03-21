import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from pathlib import Path
from typing import Optional
from config import config

class RedditSentimentService:
    """
    A service for analyzing sentiment of Reddit posts related to a cryptocurrency or search term.
    """
    def __init__(self, base_dir: str = "data/redit", download_lexicon: bool = True):
        """
        Initialize the RedditSentimentService with Reddit authentication and VADER analyzer.

        Args:
            base_dir (str): Base directory for storing sentiment data. Default is 'data/redit'.
            download_lexicon (bool): Whether to download the VADER lexicon on init. Default is True.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Authenticate with Reddit using credentials from config
        self.reddit = praw.Reddit(
            client_id=config.redit_client_id,  # Typo in original: 'redit' instead of 'reddit'
            client_secret=config.redit_client_secret,
            user_agent=config.redit_user_agent,
        )
        
        # Initialize VADER sentiment analyzer
        if download_lexicon:
            nltk.download("vader_lexicon", quiet=True)
        self.sid = SentimentIntensityAnalyzer()

    def analyze_sentiment(
        self,
        search_term: str,
        sort: str = "hot",
        limit: int = 100,
        save_data: bool = True,
        output_file: Optional[str] = None
    ) -> float:
        """
        Analyze the sentiment of Reddit posts for a given search term and optionally save the data.

        Args:
            search_term (str): The keyword to search for (e.g., 'XRP').
            sort (str): The sort order for the search ('hot', 'new', 'top'). Default is 'hot'.
            limit (int): The maximum number of posts to retrieve. Default is 100.
            save_data (bool): Whether to save the post data to a file. Default is True.
            output_file (Optional[str]): Custom file path for saving data. If None, uses default path.

        Returns:
            float: The average sentiment score of the posts (between -1 and 1).

        Raises:
            ValueError: If the sort parameter is invalid.
            Exception: If an error occurs during the API request or sentiment analysis.
        """
        # Validate sort parameter
        valid_sorts = ["hot", "new", "top"]
        if sort not in valid_sorts:
            raise ValueError(f"Sort must be one of {valid_sorts}")

        try:
            # Search for posts across all subreddits
            posts = self.reddit.subreddit("all").search(
                search_term, sort=sort, limit=limit
            )

            # Analyze sentiment and collect post data
            post_data = []
            sentiments = []
            for post in posts:
                text = post.title  # Could extend to post.selftext if desired
                sentiment = self.sid.polarity_scores(text)
                compound_score = sentiment["compound"]
                sentiments.append(compound_score)
                post_data.append({
                    "title": post.title,
                    "score": post.score,
                    "created_utc": post.created_utc,
                    "sentiment": compound_score
                })

            # Calculate average sentiment
            average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            # Save data if requested
            if save_data and post_data:
                if output_file is None:
                    output_path = self.base_dir / f"{search_term}_sentiment.json"
                else:
                    output_path = Path(output_file)
                    output_path.parent.mkdir(exist_ok=True, parents=True)
                
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, indent=2)
                print(f"Sentiment data saved to {output_path}")

            return average_sentiment

        except praw.exceptions.RedditAPIException as e:
            raise Exception(f"Reddit API error while fetching posts for '{search_term}': {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing sentiment for '{search_term}': {str(e)}")

# Example usage
if __name__ == "__main__":
    coin = "xpr"
    service = RedditSentimentService()
    try:
        sentiment = service.analyze_sentiment(search_term=coin)
        print(f"Average sentiment for {coin.upper()}: {sentiment:.4f}")
    except Exception as e:
        print(f"Error: {e}")