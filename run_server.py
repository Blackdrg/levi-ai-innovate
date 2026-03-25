
try:
    import uvicorn
except ImportError:
    print("Uvicorn not found. Please install it with 'pip install uvicorn'.")
    exit(1)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=False)
