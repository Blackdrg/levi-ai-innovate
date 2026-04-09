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
  const url = 'http://localhost:8000/api/v14';
  const payload = JSON.stringify({
    message: 'Hello FAST mode, what is the current protocol status?',
    session_id: `k6-session-${__VU}-${__ITER}`
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer test-token',
    },
  };

  const res = http.post(url, payload, params);

  check(res, {
    'is status 200': (r) => r.status === 200,
    'has strategy': (r) => r.json('strategy') !== undefined,
  });

  sleep(1);
}
