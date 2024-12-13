

import pymongo
from pymongo import MongoClient
from datetime import datetime
import logging
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# MongoDB Connection URI
MONGO_URI = "mongodb://localhost:27017/"  # Replace with your MongoDB URI

# Initialize MongoDB Client
client = MongoClient(MONGO_URI)
db = client['new_crawler_db']  # Replace with your database name

# Collections
reddit_posts = db['reddit_posts']
reddit_comments = db['reddit_comments']
chan_posts = db['chan_posts']

def fetch_reddit_data(start_date, end_date, selected_subreddits=None):
    """
    Fetches Reddit posts and comments within the specified date range and selected subreddits.

    Parameters:
        start_date (datetime): Start of the date range.
        end_date (datetime): End of the date range.
        selected_subreddits (list, optional): List of subreddits to filter. Defaults to None.

    Returns:
        list: Combined list of Reddit posts and comments.
    """
    query = {
        'created_utc': {'$gte': start_date, '$lte': end_date}
    }

    if selected_subreddits and "all" not in selected_subreddits:
        query['subreddit'] = {'$in': selected_subreddits}
        logging.debug(f"Filtering Reddit data for subreddits: {selected_subreddits}")

    # Fetch Posts
    cursor_posts = reddit_posts.find(query)
    posts = list(cursor_posts)
    logging.debug(f"Fetched {len(posts)} Reddit posts between {start_date} and {end_date}")

    # Fetch Comments
    cursor_comments = reddit_comments.find(query)
    comments = list(cursor_comments)
    logging.debug(f"Fetched {len(comments)} Reddit comments between {start_date} and {end_date}")

    # Combine Posts and Comments
    combined_data = posts + comments
    logging.debug(f"Total combined Reddit data fetched: {len(combined_data)}")

    return combined_data

def fetch_4chan_sentiment(start_date, end_date, selected_boards=None):
    """
    Fetches 4chan posts within the specified date range and selected boards.

    Parameters:
        start_date (datetime): Start of the date range.
        end_date (datetime): End of the date range.
        selected_boards (list, optional): List of boards to filter. Defaults to None.

    Returns:
        list: List of 4chan posts.
    """
    query = {
        'created_at': {'$gte': start_date, '$lte': end_date}
    }
    if selected_boards and "all" not in selected_boards:
        query['board'] = {'$in': selected_boards}
        logging.debug(f"Filtering 4chan data for boards: {selected_boards}")

    cursor = chan_posts.find(query)
    data = list(cursor)
    logging.debug(f"Fetched {len(data)} 4chan posts between {start_date} and {end_date}")
    return data

def calculate_sentiment_trend(data):
    """
    Calculates the average sentiment score per day.

    Parameters:
        data (list): List of documents (posts/comments).

    Returns:
        tuple: (sorted_dates, average_sentiments)
    """
    trend = defaultdict(list)
    for doc in data:
        date = doc.get('created_utc') or doc.get('created_at')
        sentiment = doc.get('sentiment')
        # Ensure sentiment is a float, default to 0.0 if None or invalid
        if sentiment is None:
            sentiment = 0.0
        elif not isinstance(sentiment, (int, float)):
            try:
                sentiment = float(sentiment)
            except (ValueError, TypeError):
                sentiment = 0.0

        if not date:
            logging.warning("Skipping document due to missing date")
            continue  # Skip documents with missing date
        try:
            if isinstance(date, (int, float)):
                date = datetime.utcfromtimestamp(date)
            elif isinstance(date, str):
                # Attempt to parse ISO format first
                try:
                    date = datetime.fromisoformat(date)
                except ValueError:
                    date = datetime.strptime(date, '%Y-%m-%d')
        except Exception as date_e:
            logging.warning(f"Invalid date format: {date}. Error: {str(date_e)}")
            continue
        date = date.date()
        trend[date].append(sentiment)

    if not trend:
        logging.warning("No valid data found to calculate sentiment trend.")
        return [], []

    # Calculate average sentiment per day
    dates = sorted(trend.keys())
    avg_sentiments = [sum(trend[date])/len(trend[date]) for date in dates]
    logging.debug(f"Calculated sentiment trend for {len(dates)} days")
    return dates, avg_sentiments

def calculate_toxicity_distribution(data, platform='reddit'):
    """
    Calculates the toxicity distribution in the data.

    Parameters:
        data (list): List of documents (posts/comments).
        platform (str): 'reddit' or '4chan'.

    Returns:
        dict: {'toxic': count, 'non_toxic': count}
    """
    toxicity = defaultdict(int)
    for doc in data:
        is_toxic = doc.get('is_toxic', False)
        
        # Normalize different representations of toxic content
        if isinstance(is_toxic, str):
            is_toxic_normalized = is_toxic.lower() in ['true', '1', 'yes']
        elif isinstance(is_toxic, (int, float)):
            is_toxic_normalized = bool(is_toxic)
        elif isinstance(is_toxic, bool):
            is_toxic_normalized = is_toxic
        else:
            is_toxic_normalized = False  # Default to False if unknown type
        
        if is_toxic_normalized:
            toxicity['toxic'] += 1
        else:
            toxicity['non_toxic'] += 1

    # Ensure both keys exist
    toxicity.setdefault('toxic', 0)
    toxicity.setdefault('non_toxic', 0)
    
    # Logging the distribution
    logging.debug(f"Toxicity Distribution for {platform}: {toxicity}")

    return toxicity

def calculate_average_scores(data, platform='reddit'):
    """
    Calculates the average score across all documents.

    Parameters:
        data (list): List of documents (posts/comments).
        platform (str): 'reddit' or '4chan'.

    Returns:
        float: Average score.
    """
    scores = []
    for doc in data:
        score = doc.get('score')
        # Ensure score is a float, default to 0.0 if None or invalid
        if score is None:
            score = 0.0
        elif not isinstance(score, (int, float)):
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0.0
        scores.append(score)

    if scores:
        avg_score = sum(scores) / len(scores)
    else:
        avg_score = 0.0
    logging.debug(f"Calculated average score for {'reddit' if platform == 'reddit' else '4chan'}: {avg_score}")
    return avg_score

def calculate_sentiment_score_trend(data, platform='reddit'):
    """
    Calculates the average sentiment * score per day.

    Parameters:
        data (list): List of documents (posts/comments).
        platform (str): 'reddit' or '4chan'.

    Returns:
        tuple: (sorted_dates, average_sentiment_scores)
    """
    trend = defaultdict(list)
    for doc in data:
        date = doc.get('created_utc') or doc.get('created_at')
        sentiment = doc.get('sentiment')
        score = doc.get('score')

        # Ensure sentiment is a float, default to 0.0 if None or invalid
        if sentiment is None:
            sentiment = 0.0
        elif not isinstance(sentiment, (int, float)):
            try:
                sentiment = float(sentiment)
            except (ValueError, TypeError):
                sentiment = 0.0

        # Ensure score is a float, default to 0.0 if None or invalid
        if score is None:
            score = 0.0
        elif not isinstance(score, (int, float)):
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0.0

        if not date:
            logging.warning("Skipping document due to missing date")
            continue  # Skip documents with missing date
        try:
            if isinstance(date, (int, float)):
                date = datetime.utcfromtimestamp(date)
            elif isinstance(date, str):
                # Attempt to parse ISO format first
                try:
                    date = datetime.fromisoformat(date)
                except ValueError:
                    date = datetime.strptime(date, '%Y-%m-%d')
        except Exception as date_e:
            logging.warning(f"Invalid date format: {date}. Error: {str(date_e)}")
            continue
        date = date.date()
        sentiment_score = sentiment * score
        if sentiment < 0 and score < 0:
            sentiment_score = -sentiment_score
        trend[date].append(sentiment_score)

    if not trend:
        logging.warning("No valid data found to calculate sentiment score trend.")
        return [], []

    # Calculate average sentiment*score per day
    dates = sorted(trend.keys())
    avg_sentiment_scores = [sum(trend[date])/len(trend[date]) for date in dates]
    logging.debug(f"Calculated sentiment*score trend for {len(dates)} days")
    return dates, avg_sentiment_scores

def get_available_subreddits():
    """
    Retrieves distinct subreddits from Reddit posts.

    Returns:
        list: List of subreddits.
    """
    subreddits = reddit_posts.distinct('subreddit')
    logging.debug(f"Available subreddits: {subreddits}")
    return subreddits

def get_available_boards():
    """
    Retrieves distinct boards from 4chan posts.

    Returns:
        list: List of boards.
    """
    boards = chan_posts.distinct('board')
    logging.debug(f"Available boards: {boards}")
    return boards

def calculate_keyword_counts(data, positive_synonyms, negative_synonyms):
    """
    Calculates the count of positive and negative keywords in the provided data.

    Parameters:
        data (list): List of documents (posts/comments).
        positive_synonyms (list): List of positive keyword synonyms.
        negative_synonyms (list): List of negative keyword synonyms.

    Returns:
        dict: A dictionary with dates as keys and counts of positive and negative keywords.
              Format: {
                  'YYYY-MM-DD': {'positive': count, 'negative': count},
                  ...
              }
    """
    keyword_counts = defaultdict(lambda: {'positive': 0, 'negative': 0})
    
    # Compile regex patterns for efficiency
    positive_pattern = re.compile(r'\b(' + '|'.join(re.escape(word) for word in positive_synonyms) + r')\b', re.IGNORECASE)
    negative_pattern = re.compile(r'\b(' + '|'.join(re.escape(word) for word in negative_synonyms) + r')\b', re.IGNORECASE)
    
    for doc in data:
        # Extract date
        date = doc.get('created_utc') or doc.get('created_at')
        if not date:
            logging.warning("Skipping document due to missing date")
            continue  # Skip documents without a date
        try:
            if isinstance(date, (int, float)):
                date = datetime.utcfromtimestamp(date)
            elif isinstance(date, str):
                # Attempt to parse ISO format first
                try:
                    date = datetime.fromisoformat(date)
                except ValueError:
                    date = datetime.strptime(date, '%Y-%m-%d')
        except Exception as date_e:
            logging.warning(f"Invalid date format: {date}. Error: {str(date_e)}")
            continue
        date_str = date.date().strftime('%Y-%m-%d')
        
        # Extract text content
        text = doc.get('title') or doc.get('body') or doc.get('text') or ''
        if not isinstance(text, str):
            text = str(text)
        
        # Find all positive and negative matches
        positive_matches = positive_pattern.findall(text)
        negative_matches = negative_pattern.findall(text)
        
        # Update counts
        keyword_counts[date_str]['positive'] += len(positive_matches)
        keyword_counts[date_str]['negative'] += len(negative_matches)
    
    # Convert defaultdict to regular dict for JSON serialization
    keyword_counts = dict(keyword_counts)
    
    logging.debug(f"Calculated keyword counts for {len(keyword_counts)} days")
    return keyword_counts
