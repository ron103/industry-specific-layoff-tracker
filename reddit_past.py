# reddit_past.py

import logging
import os
from datetime import datetime, timedelta
from time import sleep
from pyfaktory import Client, Job, Producer
from reddit_client import RedditClient
from pymongo import MongoClient
import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Ensure NLTK data is downloaded
nltk.download('vader_lexicon')

# Initialize Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

# Logger setup
logger = logging.getLogger("RedditHistoricalCrawler")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['new_crawler_db']
reddit_collection = db['reddit_posts']
comments_collection = db['reddit_comments']

# Ensure proper indexing on post_id to avoid duplicates
reddit_collection.create_index([("post_id", 1)], unique=True)
comments_collection.create_index([("comment_id", 1)], unique=True)

# Toxicity Check Function
def hs_check_comment(comment):
    CONF_THRESHOLD = 0.9
    api_token = os.getenv("MODERATEHATESPEECH_TOKEN")
    if not api_token:
        logger.error("ModerateHatespeech API token not set.")
        return False

    data = {
        "token": api_token,
        "text": comment
    }

    try:
        response = requests.post("https://api.moderatehatespeech.com/api/v1/moderate/", json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("class") == "flag" and float(result.get("confidence", 0)) > CONF_THRESHOLD:
            return True
    except requests.exceptions.RequestException as e:
        logger.error(f"ModerateHatespeech API error: {e}")

    return False

# Sentiment Analysis Function
def compute_sentiment(text):
    """
    Compute the compound sentiment score for a given text.
    Returns a float between -1 (most negative) and +1 (most positive).
    """
    if not text or not isinstance(text, str):
        return None
    sentiment = sia.polarity_scores(text)
    return sentiment['compound']

def fetch_historical_posts(subreddit, after, before, limit=100):
    """
    Fetch posts from a subreddit within a specific time range.
    """
    reddit_client = RedditClient()
    data = reddit_client.fetch_posts_by_date(subreddit, after, before, limit)
    if data is None:
        logger.error(f"Failed to fetch historical data for subreddit: {subreddit}")
        return None
    store_historical_data(data, subreddit)
    return data

def store_historical_data(data, subreddit):
    """
    Store fetched historical posts into MongoDB with sentiment scores.
    """
    posts = data['data']['children']
    for post in posts:
        content = post['data'].get('selftext', '')
        sentiment_score = compute_sentiment(content) if content else None  # Compute sentiment

        post_data = {
            'subreddit': subreddit,
            'post_id': post['data']['id'],
            'title': post['data'].get('title', ''),
            'author': post['data'].get('author', 'unknown'),
            'created_utc': datetime.utcfromtimestamp(post['data']['created_utc']),
            'content': content,
            'comments_count': post['data'].get('num_comments', 0),
            'score': post['data'].get('score', 0),
            'url': post['data'].get('url', ''),
            'is_toxic': False,  # Default value
            'sentiment': sentiment_score  # Add sentiment score
        }
        if content:
            post_data['is_toxic'] = hs_check_comment(post_data['content'])

        try:
            reddit_collection.update_one(
                {'post_id': post_data['post_id']},
                {'$set': post_data},
                upsert=True
            )
            logger.info(f"Stored historical post ID: {post_data['post_id']} from subreddit: {subreddit}")
        except Exception as e:
            logger.error(f"Error storing post {post_data['post_id']} in MongoDB: {e}")

        enqueue_crawl_reddit_comments(subreddit, post_data['post_id'])

def enqueue_crawl_reddit_comments(subreddit, post_id):
    """
    Enqueue a job to crawl comments for a given Reddit post.
    """
    logger.info(f"Enqueuing crawl-reddit-comments job for historical post {post_id} in r/{subreddit}")
    with Client(faktory_url="tcp://myuser:mypassword@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(
            jobtype="crawl-reddit-comments",
            args=[subreddit, post_id],
            queue="crawl-reddit-comments",
            retry=3,
            backtrace=True
        )
        producer.push(job)

def fetch_historical_data_for_subreddits(subreddits, daily_limit=100):
    """
    Iterate through each day and fetch a specified number of posts per day.
    """
    current_date = START_DATE
    while True:
        for subreddit in subreddits:
            after = int(current_date.timestamp())
            before = int((current_date + timedelta(days=1)).timestamp()) - 1  # End of the current day

            logger.info(f"Fetching {daily_limit} posts for subreddit: r/{subreddit} on {current_date.strftime('%Y-%m-%d')}")
            fetch_historical_posts(subreddit, after, before, limit=daily_limit)

        # Move to the next day
        current_date += timedelta(days=1)

        # Reset to START_DATE if we've reached beyond END_DATE
        if current_date > END_DATE:
            logger.info("Reached the end of the date range. Restarting from START_DATE.")
            current_date = START_DATE

        # Sleep for a short duration to avoid hitting API rate limits
        sleep(1)  # Adjust sleep duration as needed

def continuous_fetch(subreddits, sleep_duration=600, daily_limit=100):
    """
    Continuously fetch historical data for subreddits, fetching a set number of posts per day.
    """
    while True:
        logger.info("Starting a new iteration of subreddit data fetch.")
        fetch_historical_data_for_subreddits(subreddits, daily_limit=daily_limit)
        logger.info(f"Sleeping for {sleep_duration} seconds before next iteration.")
        sleep(sleep_duration)

if __name__ == "__main__":
    # Define the date range for historical data
    START_DATE = datetime(2024, 12, 1)
    END_DATE = datetime(2024, 12, 11)

    # Define subreddits
    subreddits = [
        "jobs", "recruitinghell", "cscareerquestions", "startups",
        "technology", "layoffs", "leetcode", "ITCareerQuestions",
        "financialindependence", "jobsearch", "digitalnomad", "jobsearchhacks", "politics"
    ]

    # Start continuous fetching with 100 posts per day
    continuous_fetch(subreddits, sleep_duration=600, daily_limit=100)