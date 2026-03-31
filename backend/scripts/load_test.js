import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 }, // Ramp up to 20 users
    { duration: '1m', target: 20 },  // Stay at 20 users
    { duration: '30s', target: 50 }, // Ramp up to 50 users (Real-world stress)
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },  // Scale down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1500'], // 95% of requests must complete below 1.5s
    http_req_failed: ['rate<0.01'],    // Less than 1% failure rate
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:8000/api/v1';

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': `user_${Math.floor(Math.random() * 1000)}`,
    },
  };

  // 1. Health Check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, { 'health is 200': (r) => r.status === 200 });

  sleep(1);

  // 2. Chat Simulation
  const chatPayload = JSON.stringify({
    message: 'What is the meaning of existence?',
    session_id: 'test-session',
  });
  const chatRes = http.post(`${BASE_URL}/chat`, chatPayload, params);
  check(chatRes, { 'chat is 200': (r) => r.status === 200 });

  sleep(2);

  // 3. Studio/Quote Generation
  const genPayload = JSON.stringify({
    text: 'A beautiful sunset over the digital horizon',
    mood: 'serene',
  });
  const genRes = http.post(`${BASE_URL}/generate_image`, genPayload, params);
  check(genRes, { 'image gen is 202/200': (r) => r.status === 200 || r.status === 202 });

  sleep(5);
}
