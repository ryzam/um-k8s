// STRESS TEST: tolak MELEBIHI kapasiti maxReplicas. Tujuan: cari titik pecah,
// lihat apa yang gagal dahulu (CPU throttling? quota? node penuh? latency?)
// dan sahkan sistem pulih selepas beban turun.
//   k6 run stress.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:30080';
const CPU_MS = __ENV.CPU_MS || '100';
const errors = new Counter('errors_by_status');

export const options = {
  stages: [
    { duration: '2m', target: 20 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 100 },   // biasanya melebihi kapasiti 10 pod x 500m
    { duration: '2m', target: 150 },
    { duration: '3m', target: 0 },     // fasa pemulihan
  ],
  thresholds: {
    // Threshold longgar: ujian stress dijangka "gagal" di hujung. abortOnFail tidak di-set
    // supaya kita dapat data penuh.
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<2000'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/cpu?ms=${CPU_MS}`, { tags: { name: 'cpu' }, timeout: '10s' });
  if (!check(res, { 'status 200': (r) => r.status === 200 })) {
    errors.add(1, { status: String(res.status) });
  }
  sleep(0.2);
}
