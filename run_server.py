
try:
    from waitress import serve
except ImportError:
    print("Waitress not found. Please install it with 'pip install waitress'.")
    exit(1)

from backend.main import app

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8000)
