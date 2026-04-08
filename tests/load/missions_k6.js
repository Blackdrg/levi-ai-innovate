import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    missions: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || '2m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<5000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.LEVI_TEST_TOKEN || 'sovereign_test_token_v14';

export default function () {
  const payload = JSON.stringify({
    input: 'Run a deterministic mission and return a concise answer.',
    context: { tier: 'L2', load_test: true },
  });

  const headers = {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TOKEN}`,
    },
  };

  const response = http.post(`${BASE_URL}/api/v1/orchestrator/mission`, payload, headers);
  check(response, {
    'mission accepted': (r) => r.status === 202,
    'mission id returned': (r) => {
      try {
        return !!r.json().mission_id;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(1);
}
