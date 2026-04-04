import os
import json

class HNSWStore:
    def __init__(self, index_path):
        self.index_path = index_path
        self.metadata = []
        # In a real implementation, we would load the index from the path.
        # But for this "graduate" monolith, we will stub it for now.
    
    def search(self, vector, top_k, user_id):
        return [
            {"text": "Project Sovereign initialized successfully.", "user_id": user_id, "importance": 0.95},
            {"text": "User prefers deep investigative research.", "user_id": user_id, "importance": 0.92}
        ]
    
    def add(self, vector, metadata):
        self.metadata.append(metadata)
        return f"mem_{len(self.metadata)}"
