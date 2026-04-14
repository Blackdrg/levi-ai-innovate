from locust import HttpUser, task, between
import uuid
import json

class LeviUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Perform login and set user context"""
        self.user_id = f"load_test_user_{uuid.uuid4().hex[:8]}"
        self.headers = {
            "Content-Type": "application/json",
            "X-User-ID": self.user_id
        }

    @task(3)
    def mission_chat(self):
        """Simulate concurrent chat missions"""
        payload = {
            "objective": "Tell me about the history of artificial intelligence in 3 paragraphs.",
            "mode": "AUTONOMOUS",
            "user_id": self.user_id
        }
        with self.client.post("/api/v1/mission", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "request_id" in data:
                    response.success()
                else:
                    response.failure(f"Missing request_id in response: {data}")
            else:
                response.failure(f"Failed with status code: {response.status_code}")

    @task(1)
    def get_user_missions(self):
        """Simulate dashboard mission retrieval"""
        self.client.get(f"/api/v1/missions/{self.user_id}", headers=self.headers)

    @task(1)
    def check_health(self):
        """Verify DCN cluster health"""
        self.client.get("/api/v1/health", headers=self.headers)
