// SMOKE TEST: 1-2 VU, 1 minit. Sahkan skrip & sistem berfungsi sebelum ujian besar.
//   k6 run smoke.js                       (default BASE_URL=http://localhost:30080)
//   k6 run -e BASE_URL=http://demo-app.demo smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';

export const options = {
  vus: 2,
  duration: '1m',
  thresholds: {
    http_req_failed: ['rate<0.01'],     // < 1% gagal
    http_req_duration: ['p(95)<300'],   // 95% request < 300ms
  },
};

export default function () {
  const r1 = http.get(`${BASE_URL}/`);
  check(r1, { 'GET / 200': (r) => r.status === 200 });
  const r2 = http.get(`${BASE_URL}/cpu?ms=20`, { tags: { name: 'cpu' } });
  check(r2, { 'GET /cpu 200': (r) => r.status === 200 });
  sleep(1);
}
