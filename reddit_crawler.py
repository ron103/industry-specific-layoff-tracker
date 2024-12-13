# reddit_crawler.py

import logging
import os
import time
from pyfaktory import Client, Consumer, Job, Producer
from reddit_client import RedditClient
from datetime import datetime, timedelta
from pymongo import MongoClient
import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Ensure NLTK data is downloaded
nltk.download('vader_lexicon')

# Initialize Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

# Logger setup
logger = logging.getLogger("RedditCrawler")
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

def store_data_reddit(data, subreddit):
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
        
        # Perform Toxicity Check on Content
        if content:
            is_toxic = hs_check_comment(content)
            post_data['is_toxic'] = is_toxic
        
        try:
            logger.info(f"Storing post ID: {post_data['post_id']}")
            reddit_collection.update_one(
                {'post_id': post_data['post_id']},
                {'$set': post_data},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error storing post {post_data['post_id']} in MongoDB: {e}")
    
        # Enqueue job to fetch comments for this post
        enqueue_crawl_reddit_comments(subreddit, post_data['post_id'])

def store_comments_reddit(comments, subreddit, post_id):
    for comment in comments:
        body = comment.get('body', '')
        sentiment_score = compute_sentiment(body) if body else None  # Compute sentiment

        comment_data = {
            'subreddit': subreddit,
            'post_id': post_id,
            'comment_id': comment['id'],
            'author': comment.get('author', 'unknown'),
            'created_utc': datetime.utcfromtimestamp(comment.get('created_utc', 0)),
            'body': body,
            'score': comment.get('score', 0),
            'is_toxic': False,  # Default value
            'sentiment': sentiment_score  # Add sentiment score
        }
        
        # Perform Toxicity Check on Comment
        if body:
            is_toxic = hs_check_comment(body)
            comment_data['is_toxic'] = is_toxic
        
        try:
            logger.info(f"Storing comment ID: {comment_data['comment_id']} for post {post_id} in r/{subreddit}")
            comments_collection.update_one(
                {'comment_id': comment_data['comment_id']},
                {'$set': comment_data},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error storing comment {comment_data['comment_id']} in MongoDB: {e}")

def crawl_subreddit(subreddit, after=None):
    reddit_client = RedditClient()
    data = reddit_client.fetch_new_posts(subreddit, after)
    if data is None:
        logger.error(f"Failed to fetch data for subreddit: {subreddit}")
        return None
    store_data_reddit(data, subreddit)
    return data

def crawl_reddit_comments(subreddit, post_id, limit=10):
    reddit_client = RedditClient()
    comments = reddit_client.fetch_top_comments(subreddit, post_id, limit=limit)
    if comments is None:
        logger.error(f"Failed to fetch comments for post {post_id} in r/{subreddit}")
        return
    store_comments_reddit(comments, subreddit, post_id)

def handle_crawl_subreddit(*args):
    """
    Handler function for Faktory worker.
    Expects args: [subreddit, after]
    """
    if not args:
        logger.error("No arguments provided for crawl-subreddit job.")
        return
    subreddit = args[0]
    after = args[1] if len(args) > 1 else None
    logger.info(f"Starting crawl for subreddit: {subreddit}, after: {after}")
    data = crawl_subreddit(subreddit, after)

    if data is None:
        # Schedule retry after 5 minutes
        schedule_crawl_subreddit(subreddit, after=after, delay_minutes=5)
    else:
        next_after = data['data']['after']
        if next_after:
            # Schedule job to fetch next page immediately
            schedule_crawl_subreddit(subreddit, after=next_after)
        # Schedule next crawl after delay
        schedule_crawl_subreddit(subreddit, after=None, delay_minutes=5)

def handle_crawl_reddit_comments(*args):
    """
    Handler function for Faktory worker.
    Expects args: [subreddit, post_id]
    """
    if not args or len(args) < 2:
        logger.error("Insufficient arguments for crawl-reddit-comments job.")
        return
    subreddit, post_id = args[0], args[1]
    logger.info(f"Starting crawl for comments of post {post_id} in r/{subreddit}")
    crawl_reddit_comments(subreddit, post_id)

def enqueue_crawl_reddit_comments(subreddit, post_id):
    logger.info(f"Enqueuing crawl-reddit-comments job for post {post_id} in r/{subreddit}")
    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(
            jobtype="crawl-reddit-comments",
            args=[subreddit, post_id],
            queue="crawl-reddit-comments",
            retry=3,
            backtrace=True
        )
        producer.push(job)

def schedule_crawl_subreddit(subreddit, after=None, delay_minutes=None):
    logger.info(f"Scheduling Reddit crawl job for r/{subreddit}, after: {after}")
    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(
            jobtype="crawl-subreddit",
            args=[subreddit, after],
            queue="crawl-subreddit",
            retry=3,
            backtrace=True
        )
        if delay_minutes:
            run_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
            job.at = run_at.isoformat() + "Z"
        producer.push(job)

def schedule_crawl_reddit_comments(subreddit, post_id, delay_minutes=None):
    logger.info(f"Scheduling Reddit comments crawl job for post {post_id} in r/{subreddit}")
    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(
            jobtype="crawl-reddit-comments",
            args=[subreddit, post_id],
            queue="crawl-reddit-comments",
            retry=3,
            backtrace=True
        )
        if delay_minutes:
            run_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
            job.at = run_at.isoformat() + "Z"
        producer.push(job)

def start_consumer():
    with Client(faktory_url="tcp://:password@localhost:7419", role="consumer") as client:
        consumer = Consumer(
            client=client,
            queues=["crawl-subreddit", "crawl-reddit-comments"],
            concurrency=10  # Increased concurrency for faster processing
        )
        consumer.register("crawl-subreddit", handle_crawl_subreddit)
        consumer.register("crawl-reddit-comments", handle_crawl_reddit_comments)
        consumer.run()

if __name__ == "__main__":
    # Start the Faktory consumer
    start_consumer()