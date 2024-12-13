import logging
from pyfaktory import Client, Job, Producer
import sys

# Logger setup
logger = logging.getLogger("ColdStartBoard")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cold_start_board.py <board>")
        sys.exit(1)
    board = sys.argv[1]
    logger.info(f"Cold starting crawl catalog for board /{board}/")

    with Client(faktory_url="tcp://:password@localhost:7419", role="producer") as client:
        producer = Producer(client=client)
        job = Job(jobtype="crawl-catalog", args=[board, None], queue="crawl-catalog")
        producer.push(job)