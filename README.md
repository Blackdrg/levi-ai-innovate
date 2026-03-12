# Quotes Recommendation Bot 🤖💬

A conversational Quotes Recommendation Bot built with Flask backend + rule-based chatbot and vanilla JavaScript frontend (no RASA runtime required). Recommends inspiring quotes by category, author, mood, or randomly.

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![Rule-based](https://img.shields.io/badge/Chatbot-Rule-based-orange.svg)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Bot Capabilities](#bot-capabilities)
- [Configuration](#configuration)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## ✨ Features

- **Conversational Interface**: Natural language chat to get quotes
- **Category-based Quotes**: Motivation, Love, Life, Success, Wisdom, Friendship, Happiness, Sadness
- **Mood-based Recommendations**: Get quotes that match your current mood
- **Author Search**: Find quotes by specific authors
- **Topic-based Quotes**: Search quotes by topics like success, dreams, courage, etc.
- **Random Quotes**: Get a random inspiring quote anytime
- **REST API**: Programmatic access to quotes database
- **Dark/Light Theme**: Toggle between dark and light modes
- **Responsive Design**: Works on desktop and mobile devices
- **Glassmorphism UI**: Modern blurred glass effects (recently updated)
- **Zero ML Dependencies**: Pure Python rule-based – fast startup, no training

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   index.html    │  │    chat.js      │  │  style.css      ││
│  │(Glassmorphism  │  │(Vanilla JS)     │  │(Responsive)    ││
│  │ UI)             │  │                  │  │                 ││
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘│
│           │                      │                      │       │
└───────────┼──────────────────────┼──────────────────────┼───────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   │ HTTP Requests
                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (Flask API)                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                     app.py                              │  │
│  │  ┌─────────────────────────────┐                        │  │
│  │  │ backend/chatbot.py          │  - Rule-based intents │  │
│  │  │ (Rule-based Chatbot)        │  - Keyword matching   │  │
│  │  │                             │  - Category/author    │  │
│  │  │                             │    filtering          │  │
│  │  └─────────────────────────────┘  - /chat endpoint     │  │
│  │                     │                                   │  │
│  │                     │  ┌────────────Quote API─────────┐ │  │
│  │                     │  │ /quotes, /random, /category │ │  │
│  │                     │  │ /authors, /categories      │ │  │
│  │                     │  └─────────────────────────────┘ │  │
│  └─────────────────────┬──────────────────────────────────┘  │
│                        │ JSON File                          │
└────────────────────────┼────────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      Database                                 │
│                   database/quotes.json                        │
└──────────────────────────────────────────────────────────────┘
```

**Note**: rasa_bot/ and actions/ directories contain legacy RASA files (unused at runtime).


## 📂 Project Structure

```
LEVI/
├── backend/                  # Flask backend API
│   ├── __init__.py
│   └── app.py               # Main Flask application
├── frontend/                 # Frontend chat interface
│   ├── index.html          # Main HTML file
│   ├── style.css           # CSS styles
│   └── chat.js             # JavaScript chat functionality
├── actions/                  # Legacy RASA custom actions (unused)
│   ├── __init__.py
│   └── actions.py          # Custom action classes (unused)
├── rasa_bot/                 # Legacy RASA config (unused at runtime)
│   ├── config.yml          # NLU pipeline & policies
│   ├── domain.yml          # Bot domain (intents, slots, responses)
│   ├── endpoints.yml       # Action server endpoints
│   └── data/               # Training data
│       ├── nlu.yml         # NLU training examples
│       ├── stories.yml     # Conversation stories
│       └── rules.yml       # Conversation rules
├── database/                 # Data storage
│   └── quotes.json         # Quotes database
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Prerequisites

- **Python 3.8+** (tested on 3.14+)
- **Flask** and related packages (see requirements.txt)
- **Modern web browser** (Chrome, Firefox, Edge, Safari)

## 📦 Installation

### 1. Clone the Repository

```bash
cd c:/Users/mehta/Desktop/LEVI
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```
</xai:function_call name="edit_file">

<parameter name="path">c:/Users/mehta/Desktop/LEVI/README.md

## 🚀 Running the Application

## 🚀 Running the Application (Single Command Setup)

### Step 1: Start Flask Backend (includes rule-based chatbot)

```bash
cd c:/Users/mehta/Desktop/LEVI
python backend/app.py
```

Flask API + Chatbot runs on `http://localhost:5000`

### Step 2: Open Frontend

Simply open `frontend/index.html` in your browser (double-click or drag to browser), or serve statically:

```bash
# Terminal 2 (optional, for live reload)
cd frontend
python -m http.server 8000
```

Navigate to `http://localhost:8000` – **Glassmorphism chat UI ready!**

## 🔌 API Endpoints

### Base Information

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/chat` | POST | Send message to chatbot |

### Quotes API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/quotes` | GET | Get all quotes with optional filters |
| `/quotes/random` | GET | Get a random quote |
| `/quotes/category/<category>` | GET | Get quotes by category |
| `/quotes/author/<author>` | GET | Get quotes by author |
| `/authors` | GET | Get list of all authors |
| `/categories` | GET | Get list of all categories |

### Example Usage

```bash
# Get all quotes
curl http://localhost:5000/quotes

# Get quotes by category
curl http://localhost:5000/quotes/category/motivation

# Get random quote
curl http://localhost:5000/quotes/random

# Get list of authors
curl http://localhost:5000/authors

# Send chat message
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Give me a motivational quote"}'
```

## 🤖 Bot Capabilities

The chatbot understands the following intents:

### Greetings & Farewell
- `greet` - Hello, hi, hey, good morning, etc.
- `goodbye` - Bye, see you, take care, etc.

### Quote Requests
- `random_quote` - "Give me a quote", "Inspire me"
- `motivation_quote` - "I need motivation", "Encourage me"
- `love_quote` - "Give me a love quote", "Romantic words"
- `sad_quote` - "I feel sad", "Comforting quote"
- `life_quote` - "Quote about life", "Life wisdom"
- `success_quote` - "Success quote", "Winning"
- `wisdom_quote` - "Wise words", "Sage advice"
- `friendship_quote` - "Friendship quote", "About friends"
- `happiness_quote` - "Happy quote", "Joyful words"

### Advanced
- `author_quote` - "Quote by Einstein"
- `topic_quote` - "Quote about success"
- `mood_happy` / `mood_sad` / `mood_angry` / `mood_motivated` - Mood-based quotes

### Conversation
- `thank_you` - Thanks, appreciate it
- `ask_bot` - "What can you do?"
- `more_quotes` - "Another quote", "Keep going"

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 5000 | Flask server port |
| `DEBUG` | true | Enable debug mode |
| `QUOTES_DB` | database/quotes.json | Path to quotes file

## 🎨 Customization

### Adding New Categories/Intents

1. Edit `backend/chatbot.py`: Add patterns to `self.intent_patterns`.
2. Add quotes with new category to `database/quotes.json`.
3. Restart `python backend/app.py` – instant update, no training!

### Adding New Quotes

Edit `database/quotes.json`:

```json
[
  {
    "quote": "Your inspiring quote here",
    "author": "Author Name",
    "category": "motivation"
  }
]
```

### Modifying the UI

- Edit `frontend/style.css` for styling changes
- Edit `frontend/index.html` for structural changes
- Edit `frontend/chat.js` for functionality modifications

## 🔍 Troubleshooting

### Common Issues

#### Quotes Not Loading
```bash
python -c "import json; print(len(json.load(open('database/quotes.json'))), 'quotes loaded')"
```

#### Flask Not Starting
- Check `pip install -r requirements.txt`
- Verify port 5000 free: `netstat -ano | findstr :5000`
- See logs: Run with `DEBUG=true python backend/app.py`

#### Chat Not Responding
- Backend/chatbot.py handles all keyword-based intents.
- Test API: `curl -X POST http://localhost:5000/chat -H "Content-Type: application/json" -d "{\"message\":\"motivation\"}"`

#### CORS/Frontend Errors
- Flask-CORS enabled by default.
- Open browser console (F12).

## 🏛️ Legacy RASA Support

rasa_bot/ and actions/ contain original RASA files. See [RASA_SDK_FIX.md](RASA_SDK_FIX.md) for Python/RASA compatibility issues that led to rule-based migration.

## 📄 License

This project is for educational purposes.

---

<p align="center">Made with ❤️ using Flask, rule-based Python, and vanilla JS (Glassmorphism UI)</p>

