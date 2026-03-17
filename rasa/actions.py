from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import os

class ActionRecommendQuote(Action):
    def name(self) -> Text:
        return "action_recommend_quote"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        entities = tracker.latest_message.get('entities', [])
        mood = next((e['value'] for e in entities if e['entity'] == 'mood'), None)
        topic = next((e['value'] for e in entities if e['entity'] == 'topic'), None)
        author = next((e['value'] for e in entities if e['entity'] == 'author'), None)
        
        params = {"text": tracker.latest_message['text']}
        if mood: params["mood"] = mood
        if topic: params["topic"] = topic
        if author: params["author_filter"] = author  # Custom backend param
        
        resp = requests.post("http://backend:8000/search_quotes", json=params, timeout=5)
        if resp.status_code == 200:
            quotes = resp.json()
            quote_text = quotes[0]["quote"] if quotes else "No quote found."
            author_name = quotes[0].get("author", "Unknown") if quotes else ""
            dispatcher.utter_message(text=f"Here's the quote: {quote_text} - {author_name}")
        else:
            dispatcher.utter_message(text="Sorry, couldn't fetch a quote right now.")
        return []

class ActionGenerateQuote(Action):
    def name(self) -> Text:
        return "action_generate_quote"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        entities = tracker.latest_message.get('entities', [])
        mood = next((e['value'] for e in entities if e['entity'] == 'mood'), None)
        topic = next((e['value'] for e in entities if e['entity'] == 'topic'), None)
        
        params = {"text": tracker.latest_message['text']}
        if mood: params["mood"] = mood
        if topic: params["topic"] = topic
        
        try:
            resp = requests.post("http://backend:8000/generate", json=params, timeout=5)
            if resp.status_code == 200:
                quote = resp.json().get('generated_quote', 'No quote generated.')
                dispatcher.utter_message(text=f"Generated: {quote}")
            else:
                dispatcher.utter_message(text="Couldn't generate a quote. Try again!")
        except Exception as e:
            dispatcher.utter_message(text=f"Backend unreachable: {str(e)}")
        return []

