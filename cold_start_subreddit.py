import logging
from pyfaktory import Client, Job, Producer
import sys

# Logger setup
logger = logging.getLogger("ColdStartSubreddit")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cold_start_subreddit.py <subreddit>")
        sys.exit(1)
    subreddit = sys.argv[1]
    logger.info(f"Cold starting crawl for subreddit {subreddit}")

    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(jobtype="crawl-subreddit", args=[subreddit, None], queue="crawl-subreddit")
        producer.push(job)