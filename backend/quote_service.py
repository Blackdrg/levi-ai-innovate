"""Simple Rule-Based Quote Service - Production Ready"""

import random
from typing import Dict, List


class QuoteChatbot:
    \"\"\"A simple rule-based chatbot for quotes without RASA dependency.\"\"\"

    def __init__(self, quotes_db):
        self.quotes = quotes_db
        self.categories = self._get_categories()
        self.intent_patterns = {
            # Greeting intents
            "greet": ["hello", "hi", "hey", "greetings", "good morning",
                      "good evening"],
            "goodbye": ["bye", "goodbye", "see you", "later", "farewell"],
            "thank_you": ["thank", "thanks", "appreciate", "grateful"],
            "help": ["help", "what can you do", "commands", "options"],
            "about": ["who are you", "about you", "what are you"],

            # Quote intents
            "random_quote": ["random", "any quote", "surprise me",
                             "random quote"],
            "motivation": ["motivation", "motivational", "inspire",
                           "inspired", "boost"],
            "love": ["love", "romantic", "heart", "love quote"],
            "sad": ["sad", "sadness", "comfort", "comforting", "down",
                    "depressed"],
            "life": ["life", "living", "life quote"],
            "success": ["success", "successful", "achievement", "accomplish"],
            "wisdom": ["wisdom", "wise", "philosophy", "thoughtful"],
            "friendship": ["friend", "friendship", "buddy", "companion"],
            "happiness": ["happy", "happiness", "joy", "joyful", "cheerful"],
            "more": ["more", "another", "one more", "continue"],
        }

        self.responses = {
            "greet": "Hello! I'm your Quotes Companion. I can share quotes "
                     "about motivation, love, life, success, wisdom, "
                     "friendship, happiness, and more. What would you "
                     "like to hear?",
            "goodbye": "Goodbye! Come back whenever you need some "
                       "inspiration. Have a great day!",
            "thank_you": "You're welcome! I'm happy to help. Would you "
                         "like another quote?",
            "about": "I'm a Quotes Recommendation Bot! I can share quotes "
                     "about various topics like motivation, love, life, "
                     "success, wisdom, friendship, and happiness. Just "
                     "tell me what you'd like!",
            "help": "Here are things I can help you with:\n"
                    "• Get a random quote\n"
                    "• Quotes about motivation, love, life, success, "
                    "wisdom, friendship, happiness\n"
                    "• Quotes by a specific author\n"
                    "• Comforting quotes when you're feeling down\n\n"
                    "Just tell me what you'd like!",
            "not_understood": "I'm not sure I understood that. Would you "
                              "like a quote? Just tell me what topic or "
                              "mood you're in!",
        }

    def _get_categories(self) -> set:
        \"\"\"Get all unique categories from quotes.\"\"\"
        categories = set()
        for quote in self.quotes:
            if quote.get("category"):
                categories.add(quote["category"].lower())
        return categories

    def _classify_intent(self, message: str) -> str:
        \"\"\"Classify user message into intent.\"\"\"
        message = message.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message:
                    return intent

        # Check for category keywords
        for category in self.categories:
            if category in message:
                return f"category_{category}"

        # Check for author
        if "by" in message:
            for quote in self.quotes:
                author = quote.get("author", "")
                if author and author.lower() in message:
                    return "author"

        return "not_understood"

    def _get_random_quote(self) -> Dict:
        \"\"\"Get a random quote.\"\"\"
        if not self.quotes:
            return {"quote": "No quotes available", "author": "Unknown"}
        return random.choice(self.quotes)

    def _get_quotes_by_category(self, category: str) -> List[Dict]:
        \"\"\"Get quotes by category.\"\"\"
        category = category.lower()
        return [q for q in self.quotes
                if q.get("category", "").lower() == category]

    def _get_quotes_by_author(self, author: str) -> List[Dict]:
        \"\"\"Get quotes by author.\"\"\"
        author = author.lower()
        return [q for q in self.quotes
                if author in q.get("author", "").lower()]

    def _format_response(self, quote: Dict) -> str:
        \"\"\"Format a quote for display.\"\"\"
        quote_text = quote.get("quote", "")
        author = quote.get("author", "Unknown")
        return f'"{quote_text}"\n\n— {author}'

    def process_message(self, message: str) -> Dict:
        \"\"\"Process user message and return response.\"\"\"
        intent = self._classify_intent(message)

        # Handle greeting
        if intent == "greet":
            return {
                "intent": "greet",
                "response": self.responses["greet"]
            }

        # Handle goodbye
        if intent == "goodbye":
            return {
                "intent": "goodbye",
                "response": self.responses["goodbye"]
            }

        # Handle thank you
        if intent == "thank_you":
            return {
                "intent": "thank_you",
                "response": self.responses["thank_you"]
            }

        # Handle help
        if intent == "help":
            return {
                "intent": "help",
                "response": self.responses["help"]
            }

        # Handle about
        if intent == "about":
            return {
                "intent": "about",
                "response": self.responses["about"]
            }

        # Handle random quote
        if intent == "random_quote":
            quote = self._get_random_quote()
            return {
                "intent": "random_quote",
                "response": self._format_response(quote),
                "category": quote.get("category", ""),
                "author": quote.get("author", "")
            }

        # Handle specific categories
        category_intents = {
            "motivation": "motivation_quote",
            "love": "love_quote",
            "sad": "sad_quote",
            "life": "life_quote",
            "success": "success_quote",
            "wisdom": "wisdom_quote",
            "friendship": "friendship_quote",
            "happiness": "happiness_quote",
        }

        if intent in category_intents:
            category_map = {
                "motivation": "motivation",
                "love": "love",
                "sad": "sad",
                "life": "life",
                "success": "success",
                "wisdom": "wisdom",
                "friendship": "friendship",
                "happiness": "happiness"
            }
            category = category_map.get(intent, intent)
            quotes = self._get_quotes_by_category(category)

            if quotes:
                quote = random.choice(quotes)
                return {
                    "intent": intent,
                    "response": self._format_response(quote),
                    "category": category,
                    "author": quote.get("author", "")
                }
            else:
                return {
                    "intent": intent,
                    "response": f"I couldn't find any {category} quotes."
                }

        # Handle author search
        if intent == "author":
            # Extract author name from message
            words = message.lower().split()
            author = None
            for i, word in enumerate(words):
                if word == "by" and i + 1 < len(words):
                    author = " ".join(words[i+1:])
                    break

            if author:
                quotes = self._get_quotes_by_author(author)
                if quotes:
                    quote = random.choice(quotes)
                    return {
                        "intent": "author_quote",
                        "response": self._format_response(quote),
                        "author": quote.get("author", "")
                    }
                else:
                    return {
                        "intent": "author_quote",
                        "response": f"I couldn't find quotes by {author}. "
                                    f"Would you like to try a different "
                                    f"author?"
                    }

        # Handle "more quotes"
        if intent == "more":
            quote = self._get_random_quote()
            return {
                "intent": "more_quotes",
                "response": self._format_response(quote)
            }

        # Default response
        return {
            "intent": "not_understood",
            "response": self.responses["not_understood"]
        }


def create_chatbot(quotes_db):
    \"\"\"Factory function to create chatbot instance.\"\"\"
    return QuoteChatbot(quotes_db)

