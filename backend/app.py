"""Flask backend API for Quotes Recommendation Bot."""

import json
import logging
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from quote_service import create_chatbot

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Get configuration from environment variables
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
QUOTES_DB = os.getenv("QUOTES_DB", "database/quotes.json")

# Path to quotes database
QUOTES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    QUOTES_DB
)


def load_quotes():
    """Load quotes from JSON file."""
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading quotes: {e}")
        return []


# Cache quotes at startup for performance
logger.info("Loading quotes into cache...")
QUOTES = load_quotes()
logger.info(f"Loaded {len(QUOTES)} quotes into cache")

# Initialize the chatbot
chatbot = create_chatbot(QUOTES)
logger.info("Chatbot initialized")


def get_quotes_by_category(category: str):
    """Get quotes filtered by category."""
    category = category.lower()
    return [q for q in QUOTES if q.get("category", "").lower() == category]


def get_quotes_by_author(author: str):
    """Get quotes filtered by author."""
    author = author.lower()
    return [q for q in QUOTES if author in q.get("author", "").lower()]


def get_all_authors():
    """Get list of all unique authors."""
    authors = set()
    for quote in QUOTES:
        if quote.get("author"):
            authors.add(quote["author"])
    return sorted(list(authors))


def get_all_categories():
    """Get list of all unique categories."""
    categories = set()
    for quote in QUOTES:
        if quote.get("category"):
            categories.add(quote["category"])
    return sorted(list(categories))


def format_quote(quote_data):
    """Format a quote for display."""
    quote = quote_data.get("quote", "")
    author = quote_data.get("author", "Unknown")
    category = quote_data.get("category", "")
    return {
        "quote": quote,
        "author": author,
        "category": category
    }


# Security headers middleware
@app.after_request
def secure_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# Error handling middleware
@app.errorhandler(Exception)
def handle_error(e):
    """Global error handler."""
    logger.error(f"Unhandled error: {str(e)}")
    return jsonify({
        "error": str(e),
        "status": "failed"
    }), 500


@app.route("/")
def home():
    """Home endpoint."""
    return jsonify({
        "name": "Quotes Recommendation Bot API",
        "version": "2.0.0",
        "chatbot": "Built-in Rule-Based Chatbot (No RASA required)",
        "endpoints": {
            "/": "API information",
            "/chat": "Send a message to the chatbot",
            "/quotes": "Get all quotes with optional filters",
            "/quotes/random": "Get a random quote",
            "/quotes/category/<category>": "Get quotes by category",
            "/quotes/author/<author>": "Get quotes by author",
            "/authors": "Get list of all authors",
            "/categories": "Get list of all categories",
            "/health": "Health check endpoint"
        }
    })


@app.route("/chat", methods=["POST"])
def chat():
    """Chat endpoint - uses built-in rule-based chatbot."""
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message is required"}), 400

    message = data["message"]
    sender_id = data.get("sender_id", "web_user")

    logger.info(f"User message: {message} | Sender: {sender_id}")

    try:
        # Process message with the built-in chatbot
        bot_response = chatbot.process_message(message)

        logger.info(f"Bot intent: {bot_response.get('intent')}")
        
        # Format response similar to RASA format
        responses = [{"text": bot_response.get("response", "")}]
        
        return jsonify({
            "responses": responses,
            "intent": bot_response.get("intent", "")
        })

    except Exception as e:
        logger.error(f"Unexpected error in chat: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/quotes", methods=["GET"])
def get_all_quotes():
    """Get all quotes with optional filters."""
    category = request.args.get("category")
    author = request.args.get("author")
    limit = request.args.get("limit", type=int)

    quotes = QUOTES.copy()

    # Apply filters
    if category:
        quotes = [q for q in quotes
                  if q.get("category", "").lower() == category.lower()]

    if author:
        quotes = [q for q in quotes
                  if author.lower() in q.get("author", "").lower()]

    # Apply limit
    if limit and limit > 0:
        quotes = quotes[:limit]

    msg = f"Retrieved {len(quotes)} quotes"
    if category:
        msg += f" (cat: {category})"
    if author:
        msg += f" (auth: {author})"
    logger.info(msg)

    return jsonify({
        "count": len(quotes),
        "quotes": [format_quote(q) for q in quotes]
    })


@app.route("/quotes/random", methods=["GET"])
def random_quote():
    """Get a random quote."""
    if not QUOTES:
        return jsonify({"error": "No quotes found"}), 404

    quote = random.choice(QUOTES)
    logger.info("Random quote retrieved")
    return jsonify(format_quote(quote))


@app.route("/quotes/category/<category>", methods=["GET"])
def quotes_by_category(category):
    """Get quotes by category."""
    quotes = get_quotes_by_category(category)

    if not quotes:
        return jsonify({
            "error": f"No quotes found for category '{category}'",
            "available_categories": get_all_categories()
        }), 404

    limit = request.args.get("limit", type=int)
    if limit and limit > 0:
        quotes = quotes[:limit]

    logger.info(f"Retrieved {len(quotes)} quotes for category: {category}")

    return jsonify({
        "category": category,
        "count": len(quotes),
        "quotes": [format_quote(q) for q in quotes]
    })


@app.route("/quotes/author/<author>", methods=["GET"])
def quotes_by_author(author):
    """Get quotes by author."""
    quotes = get_quotes_by_author(author)

    if not quotes:
        return jsonify({
            "error": f"No quotes found by author '{author}'"
        }), 404

    limit = request.args.get("limit", type=int)
    if limit and limit > 0:
        quotes = quotes[:limit]

    logger.info(f"Retrieved {len(quotes)} quotes for author: {author}")

    return jsonify({
        "author": author,
        "count": len(quotes),
        "quotes": [format_quote(q) for q in quotes]
    })


@app.route("/authors", methods=["GET"])
def authors():
    """Get list of all authors."""
    logger.info("Authors list retrieved")
    return jsonify({
        "count": len(get_all_authors()),
        "authors": get_all_authors()
    })


@app.route("/categories", methods=["GET"])
def categories():
    """Get list of all categories."""
    logger.info("Categories list retrieved")
    return jsonify({
        "count": len(get_all_categories()),
        "categories": get_all_categories()
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    logger.info("Health check endpoint called")
    return jsonify({
        "status": "running",
        "service": "Quotes Bot API",
        "chatbot": "active"
    })


if __name__ == "__main__":
    logger.info(f"Starting Quotes Bot API on port {PORT}, debug={DEBUG}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)