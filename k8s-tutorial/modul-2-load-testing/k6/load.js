// LOAD TEST: beban "normal hingga sibuk" yang dijangka. Tujuan: sahkan HPA scale-out
// dengan lancar dan SLO (p95, error rate) kekal dipenuhi sepanjang scaling.
//   k6 run load.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';
const CPU_MS = __ENV.CPU_MS || '20';   // kos CPU setiap request (ms)
const podLatency = new Trend('cpu_endpoint_latency', true);

export const options = {
  stages: [
    // Anggaran: 10 VU x ~1.9 req/s x 20ms CPU = ~380m CPU. Dengan target 50% daripada
    // requests 100m (= 50m sepod), HPA patut stabil sekitar 7-8 pod.
    { duration: '1m', target: 3 },    // warm-up
    { duration: '3m', target: 10 },   // naik ke beban sibuk -> HPA patut scale-out
    { duration: '5m', target: 10 },   // tahan: replicas patut stabil, latency kembali normal
    { duration: '1m', target: 0 },    // turun -> perhatikan scale-in selepas stabilization window
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/cpu?ms=${CPU_MS}`, { tags: { name: 'cpu' } });
  podLatency.add(res.timings.duration);
  check(res, {
    'status 200': (r) => r.status === 200,
    'ada nama pod': (r) => r.status === 200 && r.json('pod') !== undefined,
  });
  sleep(0.5);
}
