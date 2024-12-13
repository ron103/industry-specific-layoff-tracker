import logging
from pyfaktory import Client, Consumer
from reddit_crawler import handle_crawl_subreddit
from chan_crawler import handle_crawl_catalog, handle_crawl_thread

# Logger setup
logger = logging.getLogger("FaktoryWorker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def start_worker():
    with Client(faktory_url="tcp://:password@localhost:7419", role="consumer") as client:
        consumer = Consumer(
            client=client,
            queues=["crawl-subreddit", "crawl-catalog", "crawl-thread"],
            concurrency=10  
        )
        # Register Reddit handlers
        consumer.register("crawl-subreddit", handle_crawl_subreddit)
        # Register 4chan handlers
        consumer.register("crawl-catalog", handle_crawl_catalog)
        consumer.register("crawl-thread", handle_crawl_thread)
        consumer.run()

if __name__ == "__main__":
    start_worker()