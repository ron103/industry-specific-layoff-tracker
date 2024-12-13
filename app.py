

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from utils import (
    fetch_reddit_data,
    fetch_4chan_sentiment,
    calculate_sentiment_trend,
    calculate_toxicity_distribution,
    calculate_average_scores,
    calculate_sentiment_score_trend,
    get_available_subreddits,
    get_available_boards,
    calculate_keyword_counts
)
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Synonyms for positive and negative phrases
POSITIVE_SYNONYMS = [
    "i got a job", "offer letter", "new position", "hired", "accepted",
    "secure a job", "started a new job", "job secured", "job offer", "employment secured"
]

NEGATIVE_SYNONYMS = [
    "i was rejected", "laid off", "unemployed", "terminated", "fired",
    "job loss", "facing unemployment", "jobless", "dismissed", "let go"
]

@app.route('/')
def index():
    subreddits = get_available_subreddits()
    boards = get_available_boards()
    current_date = datetime.utcnow().strftime('%Y-%m-%d')
    logging.debug(f"Rendering index with {len(subreddits)} subreddits and {len(boards)} boards")
    return render_template('index.html', subreddits=subreddits, boards=boards, current_date=current_date)

@app.route('/api/reddit/data', methods=['GET'])
def reddit_data():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        selected_subreddits = request.args.getlist('subreddits')  # List of subreddits

        logging.debug(f"Received Reddit data request: start_date={start_date_str}, end_date={end_date_str}, subreddits={selected_subreddits}")

        # Convert date strings to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Ensure selected_subreddits is not empty
        if not selected_subreddits:
            logging.warning("No subreddits selected.")
            return jsonify({'error': 'No subreddits selected.'}), 400

        # Fetch combined Reddit posts and comments
        data = fetch_reddit_data(start_date, end_date, selected_subreddits)
        if not data:
            logging.warning("No Reddit data found for the selected criteria.")
            return jsonify({'error': 'No Reddit data found for the selected criteria.'}), 404

        # Calculate metrics for each subreddit
        sentiment_trend = {}
        toxicity_distribution = {}
        average_scores = {}
        sentiment_score_trend = {}

        for subreddit in selected_subreddits:
            # Filter data for the current subreddit
            subreddit_data = [doc for doc in data if doc.get('subreddit') == subreddit]
            if not subreddit_data:
                logging.warning(f"No data found for subreddit: {subreddit}")
                continue

            # Calculate metrics
            dates, avg_sentiments = calculate_sentiment_trend(subreddit_data)
            toxicity = calculate_toxicity_distribution(subreddit_data, platform='reddit')
            avg_score = calculate_average_scores(subreddit_data, platform='reddit')
            dates_ss, avg_sentiment_scores = calculate_sentiment_score_trend(subreddit_data, platform='reddit')

            # Populate response dictionaries
            sentiment_trend[subreddit] = {
                'dates': [date.strftime('%Y-%m-%d') for date in dates],
                'values': avg_sentiments
            }
            toxicity_distribution[subreddit] = toxicity
            average_scores[subreddit] = avg_score
            sentiment_score_trend[subreddit] = {
                'dates': [date.strftime('%Y-%m-%d') for date in dates_ss],
                'values': avg_sentiment_scores
            }

        # Prepare response
        response = {
            'sentiment_trend': sentiment_trend,
            'toxicity_distribution': toxicity_distribution,
            'average_scores': average_scores,
            'sentiment_score_trend': sentiment_score_trend
        }

        logging.debug(f"Responding with Reddit data: {response}")

        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in /api/reddit/data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/4chan/data', methods=['GET'])
def chan_data():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        selected_boards = request.args.getlist('boards')  # List of boards

        logging.debug(f"Received 4chan data request: start_date={start_date_str}, end_date={end_date_str}, boards={selected_boards}")

        # Convert date strings to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Ensure selected_boards is not empty
        if not selected_boards:
            logging.warning("No boards selected.")
            return jsonify({'error': 'No boards selected.'}), 400

        # Fetch 4chan posts
        data = fetch_4chan_sentiment(start_date, end_date, selected_boards)
        if not data:
            logging.warning("No 4chan data found for the selected criteria.")
            return jsonify({'error': 'No 4chan data found for the selected criteria.'}), 404

        # Calculate metrics for each board
        sentiment_trend = {}
        toxicity_distribution = {}
        average_scores = {}
        sentiment_score_trend = {}

        for board in selected_boards:
            # Filter data for the current board
            board_data = [doc for doc in data if doc.get('board') == board]
            if not board_data:
                logging.warning(f"No data found for board: {board}")
                continue

            # Calculate metrics
            dates, avg_sentiments = calculate_sentiment_trend(board_data)
            toxicity = calculate_toxicity_distribution(board_data, platform='4chan')
            avg_score = calculate_average_scores(board_data, platform='4chan')
            dates_ss, avg_sentiment_scores = calculate_sentiment_score_trend(board_data, platform='4chan')

            # Populate response dictionaries
            sentiment_trend[board] = {
                'dates': [date.strftime('%Y-%m-%d') for date in dates],
                'values': avg_sentiments
            }
            toxicity_distribution[board] = toxicity
            average_scores[board] = avg_score
            sentiment_score_trend[board] = {
                'dates': [date.strftime('%Y-%m-%d') for date in dates_ss],
                'values': avg_sentiment_scores
            }

        # Prepare response
        response = {
            'sentiment_trend': sentiment_trend,
            'toxicity_distribution': toxicity_distribution,
            'average_scores': average_scores,
            'sentiment_score_trend': sentiment_score_trend
        }

        logging.debug(f"Responding with 4chan data: {response}")

        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in /api/4chan/data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/word_counts', methods=['GET'])
def word_counts():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        platform = request.args.get('platform')  # 'reddit', '4chan', or 'all'

        logging.debug(f"Received word counts request: start_date={start_date_str}, end_date={end_date_str}, platform={platform}")

        # Convert date strings to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Validate platform parameter
        if platform not in ['reddit', '4chan', 'all']:
            logging.warning("Invalid platform selected.")
            return jsonify({'error': 'Invalid platform selected. Choose from "reddit", "4chan", or "all".'}), 400

        combined_data = []

        if platform in ['reddit', 'all']:
            # Fetch Reddit data
            selected_subreddits = request.args.getlist('subreddits')
            if selected_subreddits:
                reddit_data = fetch_reddit_data(start_date, end_date, selected_subreddits)
                combined_data.extend(reddit_data)
            else:
                logging.warning("No subreddits selected for Reddit data.")

        if platform in ['4chan', 'all']:
            # Fetch 4chan data
            selected_boards = request.args.getlist('boards')
            if selected_boards:
                chan_data = fetch_4chan_sentiment(start_date, end_date, selected_boards)
                combined_data.extend(chan_data)
            else:
                logging.warning("No boards selected for 4chan data.")

        if not combined_data:
            logging.warning("No data found for the selected criteria.")
            return jsonify({'error': 'No data found for the selected criteria.'}), 404

        # Calculate keyword counts
        keyword_counts = calculate_keyword_counts(combined_data, POSITIVE_SYNONYMS, NEGATIVE_SYNONYMS)

        # Prepare response
        response = {
            'keyword_counts': keyword_counts
        }

        logging.debug(f"Responding with keyword counts: {response}")

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error in /api/word_counts: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5019)
