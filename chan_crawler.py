# chan_crawler.py

import logging
import os
import requests
from datetime import datetime, timedelta
from pyfaktory import Client, Consumer, Job, Producer
from chan_client import ChanClient
from pymongo import MongoClient
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer


nltk.download('vader_lexicon')

# Initialize Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

# Logger setup
logger = logging.getLogger("ChanCrawler")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# MongoDB setup
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['new_crawler_db']
chan_collection = db['chan_posts']
chan_collection.create_index([("post_no", 1)], unique=True)

# Hate Speech Check Function
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
        response = requests.post(
            "https://api.moderatehatespeech.com/api/v1/moderate/",
            json=data,
            timeout=10
        )
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

def store_data_4chan(data, board):
    posts = data.get("posts", [])
    for post in posts:
        comment = post.get('com', '')
        sentiment_score = compute_sentiment(comment) if comment else None  # Compute sentiment

        post_data = {
            'board': board,
            'thread_no': data['posts'][0]['no'],
            'post_no': post['no'],
            'created_at': datetime.utcfromtimestamp(post.get('time', 0)),
            'name': post.get('name', 'Anonymous'),
            'comment': comment,
            'replies': post.get('replies', 0),
            'images': post.get('images', 0),
            'is_toxic': False,  # Default value
            'sentiment': sentiment_score  # Add sentiment score
        }
        
        # Perform Toxicity Check on Comment
        if comment:
            is_toxic = hs_check_comment(comment)
            post_data['is_toxic'] = is_toxic
        
        try:
            logger.info(f"Storing post No: {post_data['post_no']} from thread {post_data['thread_no']} on /{board}/")
            chan_collection.update_one(
                {'post_no': post_data['post_no']},
                {'$set': post_data},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error storing post {post_data['post_no']} in MongoDB: {e}")

def crawl_thread(board, thread_no):
    chan_client = ChanClient()
    thread_data = chan_client.get_thread(board, thread_no)
    if thread_data is None:
        logger.error(f"Failed to fetch thread {thread_no} from /{board}/")
        return
    store_data_4chan(thread_data, board)

def crawl_catalog(board, previous_thread_numbers=None):
    chan_client = ChanClient()
    catalog = chan_client.get_catalog(board)
    if catalog is None:
        logger.error(f"Failed to fetch catalog for /{board}/")
        return

    current_thread_numbers = []
    for page in catalog:
        for thread in page.get('threads', []):
            thread_no = thread['no']
            current_thread_numbers.append(thread_no)

    # Find new threads
    if previous_thread_numbers:
        new_threads = set(current_thread_numbers) - set(previous_thread_numbers)
    else:
        new_threads = set(current_thread_numbers)

    # Schedule crawl-thread jobs for new threads
    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        for thread_no in new_threads:
            job = Job(
                jobtype="crawl-thread",
                args=[board, thread_no],
                queue="crawl-thread"
            )
            producer.push(job)

    # Schedule next crawl-catalog job after delay
    schedule_crawl_catalog(board, current_thread_numbers, delay_minutes=5)

def handle_crawl_thread(*args):
    """
    Handler function for Faktory worker.
    Expects args: [board, thread_no]
    """
    if not args or len(args) < 2:
        logger.error("Insufficient arguments for crawl-thread job.")
        return
    board, thread_no = args[0], args[1]
    logger.info(f"Starting crawl for thread {thread_no} on /{board}/")
    crawl_thread(board, thread_no)

def handle_crawl_catalog(*args):
    """
    Handler function for Faktory worker.
    Expects args: [board, previous_thread_numbers]
    """
    if not args:
        logger.error("No arguments provided for crawl-catalog job.")
        return
    board = args[0]
    previous_thread_numbers = args[1] if len(args) > 1 else None
    logger.info(f"Starting crawl catalog for /{board}/")
    crawl_catalog(board, previous_thread_numbers)

def schedule_crawl_catalog(board, previous_thread_numbers, delay_minutes=None):
    logger.info(f"Scheduling crawl-catalog job for /{board}/")
    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(
            jobtype="crawl-catalog",
            args=[board, previous_thread_numbers],
            queue="crawl-catalog",
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
            queues=["crawl-catalog", "crawl-thread"],
            concurrency=5
        )
        consumer.register("crawl-catalog", handle_crawl_catalog)
        consumer.register("crawl-thread", handle_crawl_thread)
        consumer.run()

if __name__ == "__main__":
    # Start the Faktory consumer
    start_consumer()