import requests
import logging
import os
import time
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from itertools import cycle
from threading import Semaphore

# Logger setup
logger = logging.getLogger("RedditClient")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables from .env file
load_dotenv()

# Semaphore to limit concurrency
MAX_CONCURRENT_REQUESTS = 10  # Adjust this value based on expected load
semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)

class RedditClient:
    def __init__(self):
        # Load multiple Reddit API credentials from .env
        self.credentials = [
            {
                "client_id": os.getenv(f"REDDIT_CLIENT_ID{i}"),
                "client_secret": os.getenv(f"REDDIT_CLIENT_SECRET{i}"),
                "username": os.getenv(f"REDDIT_USERNAME{i}"),
                "password": os.getenv(f"REDDIT_PASSWORD{i}"),
                "user_agent": f"jobtracker/1.0 (by /u/{os.getenv(f'REDDIT_USERNAME{i}')})",
                "request_count": 0,
                "reset_time": time.time() + 60  # Reset request count every minute
            }
            for i in range(1, 5)
            if os.getenv(f"REDDIT_CLIENT_ID{i}")
        ]

        if not self.credentials:
            logger.error("No Reddit API credentials found in .env file.")
            raise ValueError("API credentials are missing.")

        # Rotate through the credentials to distribute requests
        self.credentials_cycle = cycle(self.credentials)
        self.current_credential = next(self.credentials_cycle)
        self.access_token = None
        self.token_expiry = 0  # Unix timestamp

    def _rotate_credential(self):
        """Rotate to the next credential if rate limits are exceeded."""
        self.current_credential = next(self.credentials_cycle)
        logger.info(f"Switched to credential for {self.current_credential['username']}.")

    def _check_and_reset_request_count(self):
        """Check if the request count needs to be reset."""
        for credential in self.credentials:
            if time.time() > credential["reset_time"]:
                credential["request_count"] = 0
                credential["reset_time"] = time.time() + 60

    def get_access_token(self):
        self._check_and_reset_request_count()
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        # Rotate credential if the current one has hit the limit
        if self.current_credential["request_count"] >= 60:
            logger.warning(f"Rate limit reached for {self.current_credential['username']}. Rotating credentials.")
            self._rotate_credential()

        try:
            auth = HTTPBasicAuth(
                self.current_credential["client_id"], 
                self.current_credential["client_secret"]
            )
            data = {
                "grant_type": "password",
                "username": self.current_credential["username"],
                "password": self.current_credential["password"],
                "scope": "read"
            }
            headers = {"User-Agent": self.current_credential["user_agent"]}

            response = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expiry = time.time() + token_data.get("expires_in", 3600) - 60
            logger.info(f"Successfully retrieved access token for {self.current_credential['username']}")
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token for {self.current_credential['username']}: {e}")
            return None

    def _make_request(self, url, headers, params):
        """Handle the actual request, with concurrency and backoff."""
        with semaphore:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                self.current_credential["request_count"] += 1
                return response
            except requests.exceptions.RequestException as e:
                if response.status_code == 429:  # Rate limit hit
                    logger.warning(f"Rate limit encountered. Backing off for 1 minute.")
                    time.sleep(60)  # Back off
                    self._rotate_credential()
                else:
                    logger.error(f"Request failed: {e}")
                return None

    def fetch_new_posts(self, subreddit, after=None):
        token = self.get_access_token()
        if not token:
            logger.error("Access token is not available.")
            return None

        try:
            url = f'https://oauth.reddit.com/r/{subreddit}/new/.json'
            params = {'limit': 100}
            if after:
                params['after'] = after

            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.current_credential["user_agent"]
            }
            response = self._make_request(url, headers, params)
            if response:
                data = response.json()
                logger.info(f"Fetched {len(data['data']['children'])} posts from r/{subreddit}")
                return data
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to fetch data from {subreddit}: {e}")
            return None

    def fetch_posts_by_date(self, subreddit, after, before, limit=100):
        token = self.get_access_token()
        if not token:
            logger.error("Access token is not available.")
            return None

        try:
            url = f"https://oauth.reddit.com/r/{subreddit}/search.json"
            params = {
                "q": f"timestamp:{after}..{before}",
                "sort": "new",
                "restrict_sr": 1,
                "syntax": "cloudsearch",
                "limit": limit
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.current_credential["user_agent"]
            }
            response = self._make_request(url, headers, params)
            if response:
                return response.json()
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to fetch posts by date from {subreddit}: {e}")
            return None

    def fetch_top_comments(self, subreddit, post_id, limit=10):
        token = self.get_access_token()
        if not token:
            logger.error("Access token is not available.")
            return None

        try:
            url = f'https://oauth.reddit.com/r/{subreddit}/comments/{post_id}/.json'
            params = {'limit': limit, 'sort': 'top'}
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": self.current_credential["user_agent"]
            }
            response = self._make_request(url, headers, params)
            if response:
                data = response.json()
                if len(data) > 1 and 'data' in data[1]:
                    comments = data[1]['data']['children']
                    top_comments = [comment['data'] for comment in comments if comment['kind'] == 't1'][:limit]
                    logger.info(f"Fetched {len(top_comments)} top comments for post {post_id} in r/{subreddit}")
                    return top_comments
                else:
                    logger.info(f"No comments found for post {post_id} in r/{subreddit}")
                    return []
            else:
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch comments for post {post_id} in r/{subreddit}: {e}")
            return None