import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

// Custom metrics for Sovereign characterization
export const vramPressure = new Counter('vram_pressure_alerts');
export const semaphoreWait = new Counter('semaphore_wait_seconds');

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Baseline
    { duration: '3m', target: 50 },   // Transition
    { duration: '5m', target: 100 },  // v14.0 Goal: 100 CCU
    { duration: '5m', target: 500 },  // Stress Test
    { duration: '5m', target: 1000 }, // Absolute Saturation (1000 CCU)
    { duration: '2m', target: 0 },    // Cool down
  ],
  thresholds: {
    // 🛡️ v14.0 Sovereign Gate: p95 < 15s (Hybrid), p99 tracked
    http_req_duration: ['p(95)<15000', 'p(99)<25000'], 
    http_req_failed: ['rate<0.05'], // 5% tolerance for cloud burst edge cases
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 1. Dispatch Mission (Complex Reasoning Chain)
  const payload = JSON.stringify({
    objective: "Execute a cross-agent cognitive audit of the DCN architecture.",
    context: { "priority": "high", "concurrency_test": true }
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${__ENV.TEST_JWT || 'test_token'}`
    },
  };

  const res = http.post(`${BASE_URL}/api/v1/mission/dispatch`, payload, params);

  check(res, {
    'mission_dispatched': (r) => r.status === 200,
    'has_mission_id': (r) => r.json().mission_id !== undefined,
  });

  // 2. Poll for Metrics (VRAM/Semaphore Simulation)
  const metricsRes = http.get(`${BASE_URL}/metrics`, params);
  
  if (metricsRes.status === 200) {
    const output = metricsRes.body;
    if (output.includes('vram_pressure_alert_total 1')) {
        vramPressure.add(1);
    }
  }

  sleep(Math.random() * 5 + 5); // Realistic user wait time between cognitive missions
}
