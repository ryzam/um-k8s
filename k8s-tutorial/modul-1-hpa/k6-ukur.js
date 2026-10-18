// UKUR: kadar request tetap (bukan bilangan VU tetap) supaya penggunaan CPU boleh diramal
// dan diukur. Digunakan dalam Makmal 1.4 untuk mencari nilai requests/limits.
//   k6 run -e RATE=5 k6-ukur.js     # beban normal
//   k6 run -e RATE=15 k6-ukur.js    # beban puncak
// Anggaran CPU: RATE x CPU_MS. Contoh RATE=5, CPU_MS=20 -> ~100m untuk semua pod.
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';
const CPU_MS = __ENV.CPU_MS || '20';

export const options = {
  scenarios: {
    ukur: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 5),   // request sesaat
      timeUnit: '1s',
      duration: __ENV.DURATION || '3m',
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/cpu?ms=${CPU_MS}`);
  check(res, { 'status 200': (r) => r.status === 200 });
}
