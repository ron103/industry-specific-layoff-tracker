import logging
import requests

# Logger setup
logger = logging.getLogger("ChanClient")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

class ChanClient:
    API_BASE = "https://a.4cdn.org"

    def get_thread(self, board, thread_number):
        url = f'{self.API_BASE}/{board}/thread/{thread_number}.json'
        return self.execute_request(url)

    def get_catalog(self, board):
        url = f'{self.API_BASE}/{board}/catalog.json'
        return self.execute_request(url)

    def execute_request(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            json_data = response.json()
            logger.info(f"Fetched data from {url}")
            return json_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            return None