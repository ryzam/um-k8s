# Modul 2: Load & Stress Testing untuk Pengesahan HPA

**Hari 1, 2:00 petang hingga 5:00 petang**

> **Opsyen B (Rancher):** k6 dan Locust tetap menghantar trafik terus ke `localhost:30080`; agent Rancher menggunakan sedikit kapasiti worker. Jika Rancher dipasang sekali dalam `lab` (cara 2), Rancher sendiri berkongsi worker dan UI boleh perlahan semasa ujian. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Reka senario ujian beban yang betul (smoke, load, stress, spike) dengan SLO yang jelas.
2. Jalankan ujian dengan **k6** (utama) dan **Locust** (alternatif), dari laptop dan dari dalam kluster.
3. Rakam dan sahkan peristiwa **scale-out / scale-in** HPA secara real-time.
4. Kenal pasti bottleneck: CPU throttling, ResourceQuota, pod `Pending`, OOMKilled, dan had `maxReplicas`.

> Prasyarat: Modul 1 selesai. `kubectl -n demo get hpa demo-app` menunjukkan nilai CPU dan memori.
> Pasang k6: https://grafana.com/docs/k6/latest/set-up/install-k6/ (atau guna Docker: `docker run --rm -i --network host grafana/k6:1.0.0 run - < k6/smoke.js`).

## Jadual

| Masa | Aktiviti |
|---|---|
| 2:00 – 2:30 | Teori: jenis ujian, model beban, SLO, kelewatan HPA |
| 2:30 – 3:15 | Makmal 2.1 & 2.2: smoke test, load test + rakaman garis masa HPA |
| 3:15 – 3:30 | Rehat |
| 3:30 – 4:15 | Makmal 2.3 & 2.4: stress test dan spike test |
| 4:15 – 4:45 | Makmal 2.5: memburu bottleneck |
| 4:45 – 5:00 | Makmal 2.6 (Locust) & laporan ujian |

---

## Teori ringkas

### Jenis ujian

| Ujian | Soalan yang dijawab | Bentuk beban | Fail |
|---|---|---|---|
| Smoke | "Skrip dan sistem berfungsi tak?" | 1–2 VU, 1 minit | `k6/smoke.js` |
| Load | "Sistem penuhi SLO pada beban dijangka? HPA scale dengan lancar?" | Naik, tahan, turun | `k6/load.js` |
| Stress | "Di mana titik pecah? Apa yang gagal dahulu? Boleh pulih?" | Naik berperingkat melebihi kapasiti | `k6/stress.js` |
| Spike | "Berapa lama HPA ambil masa untuk kejar lonjakan mendadak?" | Lonjakan dalam beberapa saat | `k6/spike.js` |
| Soak | "Ada memory leak atau degradasi selepas berjam-jam?" | Beban sederhana, 2–8 jam | (latihan rumah) |

### Model beban: closed vs open

- **Closed model** (`vus` / `stages`): bilangan pengguna tetap. Bila sistem lambat, kadar request **turun** sendiri. Ini boleh menyembunyikan masalah.
- **Open model** (`ramping-arrival-rate`): kadar request tetap (RPS) tanpa mengira latency, macam trafik internet sebenar. `spike.js` guna model ini.

### Kenapa HPA tidak serta-merta?

Masa reaksi HPA ialah jumlah beberapa kelewatan:

```
 metric-resolution Metrics Server   ~15s
+ HPA sync period                   ~15s
+ scheduling + pull image           1–30s (image sudah ada di node = cepat)
+ container start + readinessProbe  ~3–10s
≈ 30–70 saat sebelum pod baharu terima trafik
```

Sebab itu `minReplicas` mesti cukup untuk menampung lonjakan pertama, dan sebab spike test penting.

### SLO yang kita guna dalam makmal

| Metrik | SLO | Dalam k6 |
|---|---|---|
| Kadar ralat | < 1% | `http_req_failed: ['rate<0.01']` |
| Latency p95 | < 500 ms | `http_req_duration: ['p(95)<500']` |
| Latency p99 | < 1500 ms | `http_req_duration: ['p(99)<1500']` |

k6 akan keluar dengan exit code bukan sifar jika threshold gagal, jadi skrip ini boleh terus diguna dalam pipeline CI/CD.

### Anggaran kapasiti (buat SEBELUM ujian)

App demo: `/cpu?ms=N` membakar N ms CPU setiap request. Setiap pod ada `limits.cpu: 500m`.

```
Kapasiti satu pod  ≈ 500 ms CPU sesaat / N ms     → N=20: ~25 RPS, N=100: ~5 RPS
Kapasiti maksimum  ≈ maxReplicas × kapasiti pod   → 10 pod × 5 RPS = ~50 RPS untuk /cpu?ms=100
```

Jangkakan stress test (`ms=100`, sehingga 150 VU) akan melebihi kapasiti ini. Itu memang tujuannya.

---

## Persediaan terminal

Buka 4 terminal dan dalam setiap satu jalankan `cd ~/bengkel-k8s/modul-2-load-testing` dahulu. Ini susun atur yang kita guna sepanjang modul:

| Terminal | Arahan |
|---|---|
| T1: k6 | (arahan ujian) |
| T2: HPA | `kubectl -n demo get hpa demo-app --watch` |
| T3: Pod | `kubectl -n demo get pods -l app=demo-app -o wide --watch` |
| T4: Rakaman | `bash watch-hpa.sh demo demo-app 5 \| tee hpa-timeline.csv` |

Tambahan berguna (jalankan sekali-sekala):

```bash
kubectl -n demo top pods
kubectl -n demo get events --sort-by=.lastTimestamp | tail -20
```

Pastikan HPA dalam keadaan asas (dari Makmal 1.6):

```bash
cd ~/bengkel-k8s/modul-2-load-testing
kubectl apply -f ../modul-1-hpa/07-hpa-cpu-memory.yaml
kubectl -n demo get hpa demo-app
```

## Makmal 2.1: Smoke test

```bash
k6 run k6/smoke.js
```

Jangkaan ringkasan:

```
  ✓ GET / 200
  ✓ GET /cpu 200
  http_req_duration ✓ 'p(95)<300'
  http_req_failed   ✓ 'rate<0.01'
```

Jika gagal di sini, **jangan** teruskan ke ujian besar. Semak `curl http://localhost:30080/` dahulu.

> Pengguna minikube: NodePort tidak dipetakan ke localhost. Guna `export BASE_URL=$(minikube service demo-app -n demo --url)` dan `k6 run -e BASE_URL=$BASE_URL k6/smoke.js`.

## Makmal 2.2: Load test dan rakaman garis masa HPA

T4 sudah merakam. Di T1:

```bash
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT=load-report.html k6 run k6/load.js
```

Buka http://localhost:5665 untuk dashboard k6 secara langsung. Fail `load-report.html` dijana di hujung ujian.

Perhatikan dan catat (isi jadual dalam [templat laporan](#templat-laporan-ujian)):

1. Bila (saat ke berapa) HPA mula scale-out? Berapa `REPLICAS` maksimum?
2. Semasa scale-out, adakah p95 latency melonjak? Berapa lama sebelum kembali normal?
3. Selepas beban turun ke 0, berapa lama sebelum replicas mula turun? Padankan dengan `behavior.scaleDown.stabilizationWindowSeconds` (120s).
4. Adakah `REPLICAS` "naik-turun" (flapping) semasa fasa tahan?

Jejak peristiwa HPA selepas ujian:

```bash
kubectl -n demo describe hpa demo-app | sed -n '/Events/,$p'
kubectl -n demo get events --field-selector involvedObject.kind=HorizontalPodAutoscaler --sort-by=.lastTimestamp
```

Hentikan T4 (Ctrl+C). Lihat ringkasan garis masa:

```bash
column -s, -t hpa-timeline.csv | less
```

## Makmal 2.3: Stress test, melebihi kapasiti

Mulakan semula rakaman di T4 (`bash watch-hpa.sh | tee stress-timeline.csv`), kemudian di T1:

```bash
k6 run --summary-trend-stats="avg,p(90),p(95),p(99),max" k6/stress.js
```

Apa yang patut berlaku:

| Fasa | VU | Jangkaan |
|---|---|---|
| 0–2 min | 0→20 | HPA scale-out, latency stabil |
| 2–4 min | 20→50 | HPA capai `maxReplicas: 10`. `TARGETS` terus naik melebihi 50% |
| 4–8 min | 50→150 | Latency melonjak, mungkin timeout/ralat. HPA **tidak boleh** bantu lagi |
| 8–11 min | 150→0 | Pemulihan: latency kembali normal, kemudian scale-in |

Soalan perbincangan:

- Di VU berapa p95 melebihi 500 ms? Itu **kapasiti berkesan** sistem anda dengan konfigurasi sekarang.
- Adakah sistem pulih sepenuhnya tanpa campur tangan? (Sepatutnya ya. Jika tidak, ada masalah lebih besar.)
- Adakah ada pod restart (lajur `restarts` dalam CSV)? Kenapa? (Petunjuk: liveness probe gagal bila pod terlalu sibuk. Lihat Makmal 2.5.)

## Makmal 2.4: Spike test, mengukur kelewatan HPA

Reset ke keadaan asas: tunggu sehingga replicas kembali ke `minReplicas` (2).

```bash
kubectl -n demo get hpa demo-app   # REPLICAS = 2
k6 run k6/spike.js
```

Dari CSV dan output k6, kira:

```
Masa reaksi HPA = (masa ready_pods mula naik) − (masa lonjakan bermula, saat ke-60)
```

Eksperimen (pilih satu, ulang spike test, bandingkan):

1. Naikkan `minReplicas` ke 4. Kesan pada latency awal lonjakan?
2. Kurangkan masa start-up app dari 3 saat ke 0 (sync period HPA sendiri ialah flag kube-controller-manager dan biasanya tidak diubah):
   `kubectl -n demo set env deploy/demo-app STARTUP_DELAY=0`
3. Ubah `behavior.scaleUp.policies` kepada `Pods: 1 setiap 60s`. Lihat betapa teruk kesannya.

## Makmal 2.5: Memburu bottleneck

Empat bottleneck biasa. Untuk setiap satu, kenal pasti **gejala** dan **bukti**.

### A. CPU throttling (pod "hidup" tetapi lambat)

Jalankan load test (T1: `k6 run k6/stress.js`), kemudian semasa beban tinggi:

```bash
NODE=$(kubectl -n demo get pod -l app=demo-app -o jsonpath='{.items[0].spec.nodeName}')
kubectl get --raw "/api/v1/nodes/$NODE/proxy/metrics/cadvisor" \
  | grep -E 'container_cpu_cfs_(throttled_)?periods_total' | grep 'namespace="demo"' | grep 'container="app"'
```

Nisbah `throttled_periods / periods` yang tinggi (> 25%) bermaksud container kerap mencecah `limits.cpu`. Gejala: p99 latency tinggi walaupun `kubectl top` nampak "cuma" 500m.

Kita akan visualkan metrik ini di Grafana dalam Modul 3.

### B. ResourceQuota (HPA mahu scale, tetapi ditolak)

```bash
kubectl apply -f quota-ketat.yaml          # requests.cpu: 500m -> maksimum 5 pod
k6 run k6/load.js
```

Gejala: `DESIRED` HPA > bilangan pod sebenar. Bukti:

```bash
kubectl -n demo describe resourcequota demo-quota
kubectl -n demo get events --sort-by=.lastTimestamp | grep -i quota
kubectl -n demo describe rs -l app=demo-app | grep -A2 FailedCreate
```

Jangkaan: `Error creating: pods "demo-app-..." is forbidden: exceeded quota: demo-quota, requested: requests.cpu=100m, used: requests.cpu=500m, limited: requests.cpu=500m`

Pulihkan:

```bash
kubectl apply -f ../modul-1-hpa/05-resourcequota.yaml
```

### C. Node penuh (pod `Pending`)

Semua node k3d berkongsi CPU laptop (setiap node melaporkan semua core laptop sebagai `allocatable`), jadi kita perlu kira berapa besar requests supaya node "penuh":

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu
```

Andaikan setiap worker ada 4 CPU. Requests `1500m` bermaksud 2 pod sahaja muat setiap worker (4 pod untuk 2 worker). Jika laptop anda ada lebih CPU, besarkan nilai dalam `deployment-requests-besar.yaml` (dan naikkan `max` dalam LimitRange serta quota mengikut keperluan).

```bash
kubectl -n demo delete resourcequota demo-quota      # sementara, supaya quota tidak menghalang dahulu
kubectl -n demo patch deploy demo-app --patch-file deployment-requests-besar.yaml
k6 run k6/load.js
```

Gejala: pod `Pending`. Bukti:

```bash
kubectl -n demo get pods --field-selector=status.phase=Pending
kubectl -n demo describe pod <pod-pending> | sed -n '/Events/,$p'
```

Jangkaan: `0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 2 Insufficient cpu.`

> Di cloud, ini ialah tempat **Cluster Autoscaler** atau **Karpenter** menambah node. HPA menambah pod; Cluster Autoscaler menambah node untuk pod yang `Pending`.

Pulihkan:

```bash
kubectl apply -f ../modul-1-hpa/02-deployment.yaml
kubectl apply -f ../modul-1-hpa/05-resourcequota.yaml
```

### D. OOMKilled (memori melebihi limit)

```bash
curl "http://localhost:30080/mem?mb=300&hold=60"     # 300 MB > limits.memory 256Mi
kubectl -n demo get pods -l app=demo-app
```

Bukti:

```bash
POD=$(kubectl -n demo get pods -l app=demo-app -o jsonpath='{range .items[?(@.status.containerStatuses[0].restartCount>0)]}{.metadata.name}{"\n"}{end}' | head -1)
kubectl -n demo get pod "$POD" -o jsonpath='{.status.containerStatuses[0].lastState.terminated}' ; echo
```

Jangkaan: `{"exitCode":137,"reason":"OOMKilled",...}`

> HPA memori **tidak** menyelamatkan pod daripada OOMKilled. HPA bertindak pada **purata** semua pod setiap 15 saat; OOM berlaku pada **satu** pod dalam milisaat. Penyelesaian: limits memori yang betul + had saiz request di aplikasi.

### Ringkasan bottleneck

| Bottleneck | Gejala dalam ujian | Di mana bukti |
|---|---|---|
| CPU throttling | p99 tinggi, CPU nampak "tidak penuh" | cAdvisor `container_cpu_cfs_throttled_periods_total` |
| `maxReplicas` dicapai | `REPLICAS = MAXPODS`, `TARGETS` jauh melebihi sasaran | `kubectl get hpa`, condition `ScalingLimited` |
| ResourceQuota | `DESIRED` > pod sebenar, tiada pod Pending | Events `FailedCreate ... exceeded quota` |
| Node penuh | Pod `Pending` | Events `FailedScheduling ... Insufficient cpu` |
| OOMKilled | Restart, ralat 502/connection reset | `lastState.terminated.reason` |
| Liveness probe gagal di bawah beban | Restart walaupun tiada OOM | Events `Liveness probe failed`, `Killing` |

## Makmal 2.6: Locust (alternatif) dan k6 dalam kluster

### Locust dengan UI web

```bash
cd locust
pip install locust          # atau guna Docker di bawah
locust -f locustfile.py -H http://localhost:30080
# Docker (Linux):
docker run --rm --network host -v $PWD:/mnt/locust -w /mnt/locust locustio/locust:2.37.0 -f locustfile.py -H http://localhost:30080
```

Buka http://localhost:8089, set 50 users, spawn rate 5. Perhatikan graf RPS dan response time sambil memantau T2.

Step load automatik (tanpa UI), dengan hasil ke CSV:

```bash
locust -f stepload.py -H http://localhost:30080 --headless --csv hasil-step
```

### k6 di dalam kluster

Beban dari laptop melalui NodePort boleh jadi bottleneck sendiri (rangkaian Docker, CPU laptop). Untuk ujian lebih besar, jalankan k6 sebagai Job (dari folder `modul-2-load-testing`):

```bash
cd ~/bengkel-k8s/modul-2-load-testing
kubectl create namespace loadtest
kubectl -n loadtest create configmap k6-scripts --from-file=k6/ --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k6/k6-job.yaml
kubectl -n loadtest logs -f job/k6-load
```

Untuk ujian berskala besar (k6 teragih), lihat **k6-operator**: https://github.com/grafana/k6-operator

### Bagaimana dengan JMeter?

JMeter masih biasa di organisasi enterprise. Konsepnya sama: Thread Group = VU, Ramp-up = stages, Assertions = checks, dan mod non-GUI untuk ujian sebenar:

```bash
jmeter -n -t pelan.jmx -l hasil.jtl -e -o laporan/
```

Kita guna k6 dalam bengkel kerana skrip berupa kod (mudah diversion dalam Git) dan ringan.

## Templat laporan ujian

Salin ke dokumen anda dan isi untuk setiap ujian:

```
Ujian: ____________   Tarikh: ________   Versi app: ____
Konfigurasi HPA: min=__ max=__ target CPU=__% mem=__%   requests cpu=__ mem=__

| Metrik                                   | Nilai |
|------------------------------------------|-------|
| RPS puncak                               |       |
| p95 / p99 latency (keseluruhan)          |       |
| Kadar ralat                              |       |
| Replicas: mula -> puncak -> akhir        |       |
| Masa reaksi scale-out pertama (s)        |       |
| Masa sehingga scale-in bermula (s)       |       |
| Pod restart / OOMKilled                  |       |
| Threshold k6 lulus? (ya/tidak)           |       |

Bottleneck yang ditemui:
Cadangan perubahan (requests/limits, min/maxReplicas, behavior, kod app):
```

## Semakan akhir modul

- [ ] Peserta ada `hpa-timeline.csv` untuk load test dan stress test
- [ ] Peserta boleh nyatakan kapasiti berkesan sistem (VU/RPS sebelum SLO dilanggar)
- [ ] Peserta boleh tunjuk bukti untuk sekurang-kurangnya 3 jenis bottleneck
- [ ] Semua sumber dipulihkan ke keadaan Modul 1 (`02-deployment.yaml`, `05-resourcequota.yaml`, `07-hpa-cpu-memory.yaml`)

```bash
cd ~/bengkel-k8s/modul-2-load-testing
kubectl apply -f ../modul-1-hpa/02-deployment.yaml -f ../modul-1-hpa/05-resourcequota.yaml -f ../modul-1-hpa/07-hpa-cpu-memory.yaml
```

## Rujukan

- k6 test types: https://grafana.com/docs/k6/latest/testing-guides/test-types/
- k6 executors: https://grafana.com/docs/k6/latest/using-k6/scenarios/executors/
- k6 web dashboard: https://grafana.com/docs/k6/latest/results-output/web-dashboard/
- Locust: https://docs.locust.io/
- HPA behavior: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior
