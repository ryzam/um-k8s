// Ujian zero-downtime: kadar request tetap sepanjang rollout. Threshold: SIFAR ralat.
// Juga mengira request mengikut versi supaya anda nampak peralihan v1 -> v2.
//   k6 run zero-downtime.js            (jalankan, KEMUDIAN mulakan rollout di terminal lain)
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';
const byVersion = new Counter('requests_by_version');

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: 20, timeUnit: '1s',
      duration: __ENV.DURATION || '3m',
      preAllocatedVUs: 20, maxVUs: 100,
    },
  },
  thresholds: {
    http_req_failed: ['rate==0'],      // zero-downtime = tiada satu pun request gagal
    'requests_by_version{version:v1}': ['count>=0'],
    'requests_by_version{version:v2}': ['count>=0'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/`, { timeout: '5s' });
  const ok = check(res, { 'status 200': (r) => r.status === 200 });
  if (ok) byVersion.add(1, { version: res.json('version') });
}
