// SPIKE TEST: lonjakan mendadak (cth: flash sale, push notification).
// HPA ada kelewatan semula jadi: scrape metrik (15s) + sync HPA (15s) + pod start + readiness.
// Ujian ini mengukur "jurang" tersebut, dan berapa banyak request terjejas.
//   k6 run spike.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';

export const options = {
  scenarios: {
    spike: {
      executor: 'ramping-arrival-rate',   // kadar request tetap, tidak bergantung pada latency
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { duration: '1m', target: 5 },     // baseline 5 RPS
        // 60 RPS x 50ms = ~3 core CPU. 2 pod (2 x 500m limit) jauh tidak cukup,
        // jadi latency melonjak sehingga HPA sempat menambah pod.
        { duration: '10s', target: 60 },   // lonjakan ke 60 RPS dalam 10 saat
        { duration: '3m', target: 60 },    // tahan
        { duration: '10s', target: 5 },    // jatuh mendadak
        { duration: '3m', target: 5 },     // perhatikan scale-in
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    dropped_iterations: ['count<100'],   // iteration yang k6 tak sempat hantar (tiada VU lapang)
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/cpu?ms=50`, { tags: { name: 'cpu' }, timeout: '10s' });
  check(res, { 'status 200': (r) => r.status === 200 });
}
