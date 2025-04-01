import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import praw
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from config import config
import json

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
            client_id=config.redit_client_id,
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
                text = post.title
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
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, indent=2)
                print(f"Sentiment data saved to {output_path}")

            return average_sentiment

        except praw.exceptions.RedditAPIException as e:
            raise Exception(f"Reddit API error while fetching posts for '{search_term}': {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing sentiment for '{search_term}': {str(e)}")

    def load_saved_sentiment(self, search_term: str) -> Tuple[List[Dict], float]:
        """
        Load saved Reddit posts and calculate the average sentiment score for a given search term.

        Args:
            search_term (str): The keyword used for the saved data (e.g., 'XRP').

        Returns:
            Tuple[List[Dict], float]: List of post dictionaries and the average sentiment score.

        Raises:
            FileNotFoundError: If no saved data is found for the search term.
            ValueError: If the saved JSON data is invalid.
            Exception: If an error occurs while loading the data.
        """
        file_path = self.base_dir / f"{search_term}_sentiment.json"
        if not file_path.exists():
            raise FileNotFoundError(f"No saved data found for {search_term} at {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            if not post_data:
                return [], 0.0
            sentiments = [post.get('sentiment', 0.0) for post in post_data]
            average_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            return post_data, average_sentiment
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise Exception(f"Error loading sentiment data for '{search_term}': {e}")

# Example usage
if __name__ == "__main__":
    coin = "xpr"
    service = RedditSentimentService()
    try:
        # First, analyze and save sentiment
        sentiment = service.analyze_sentiment(search_term=coin, save_data=True)
        print(f"Average sentiment for {coin.upper()}: {sentiment:.4f}")
        
        # Then, load the saved sentiment
        posts, loaded_sentiment = service.load_saved_sentiment(search_term=coin)
        print(f"Loaded {len(posts)} posts with average sentiment: {loaded_sentiment:.4f}")
    except Exception as e:
        print(f"Error: {e}")