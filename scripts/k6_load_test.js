import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 }, // Ramp up
    { duration: '1m', target: 200 }, // Sustained load
    { duration: '30s', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests must complete below 3s
  },
};

export default function () {
  const url = 'http://localhost:8000/api/v1/orchestrator/mission';
  const payload = JSON.stringify({
    input: 'Autonomous mission: Stress-test the cognitive resonance of the swarm.',
    user_id: `k6-vu-${__VU}`,
    settings: { mode: "FAST" }
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-Sovereign-Request': 'true'
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'mission accepted (200)': (r) => r.status === 200,
    'has confidence score': (r) => r.json('confidence') !== undefined,
    'latency < 4s': (r) => r.timings.duration < 4000,
  });

  sleep(0.5); // 500ms between cognitive waves
}
