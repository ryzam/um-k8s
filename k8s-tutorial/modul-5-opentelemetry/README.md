# Modul 5 (Pilihan): OpenTelemetry, Satu Pipeline untuk Metrik dan Trace

**Modul pilihan, di luar jadual teras 2 hari.** Anggaran 3 jam sebagai makmal penuh, atau 45 minit sebagai demo fasilitator (Makmal 5.5 dan 5.6 sahaja). Sesuai untuk hari ketiga, sesi susulan, atau peserta yang selesai awal.

> **Opsyen A dan Opsyen B:** langkah sama untuk kedua-dua opsyen. Collector berjalan dalam kluster `lab` dan menghantar terus ke Prometheus dan Tempo luar, bukan melalui Rancher. Untuk Opsyen B cara sekali (Rancher dalam `lab`), DaemonSet ini menambah sekitar 3 × 128 Mi memori; tutup Rancher UI jika laptop kekurangan RAM. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Faham perbezaan antara setup bengkel sekarang (Prometheus + Fluent Bit) dengan **OpenTelemetry**, dan bila perlu memilih yang mana.
2. Pasang **OpenTelemetry Collector** sebagai DaemonSet yang menggantikan Prometheus Agent Pilihan B dalam [Modul 3](../modul-3-monitoring/README.md): metrik dihantar keluar dengan `remote_write`, dashboard dan alert Modul 3 kekal berfungsi tanpa perubahan.
3. Instrumentasi dua servis kecil (`kedai` → `inventori`) dengan **SDK OpenTelemetry** dan hantar trace ke **Grafana Tempo** di luar kluster.
4. Cari punca request lambat dengan TraceQL, service graph dan pautan trace ke log dalam Grafana.

> Prasyarat: Modul 3 selesai dan stack luar masih berjalan (`docker compose ps` dalam `modul-3-monitoring/external`). Makmal 3.1 (kube-state-metrics, node-exporter) dipasang. Modul 4 (Fluent Bit + Loki) diperlukan hanya untuk langkah pautan trace ke log dalam Makmal 5.6.

## Jadual (cadangan)

| Masa | Aktiviti |
|---|---|
| 0:00 – 0:30 | Teori: setup sekarang vs OpenTelemetry, bila pilih, bahagian OTel, konsep trace |
| 0:30 – 0:45 | Makmal 5.1: naikkan Tempo, muat semula datasource Grafana |
| 0:45 – 1:30 | Makmal 5.2 – 5.4: Prometheus luar ke Pilihan B, pasang Collector, sahkan dashboard |
| 1:30 – 1:45 | Rehat |
| 1:45 – 2:15 | Makmal 5.5: deploy `kedai` dan `inventori` yang diinstrumentasi |
| 2:15 – 3:00 | Makmal 5.6: cari request lambat; perbincangan |

---

## Teori ringkas

### Setup sekarang vs OpenTelemetry

| | Setup bengkel sekarang | Dengan OpenTelemetry (modul ini) |
|---|---|---|
| Metrik | Prometheus luar scrape terus (Pilihan A) atau Prometheus Agent + `remote_write` (Pilihan B) | Collector (DaemonSet) scrape exporter yang sama, `remote_write` ke Prometheus yang sama |
| Log | Fluent Bit DaemonSet → Loki + S3 | Kekal Fluent Bit dalam modul ini; Collector *boleh* mengambil alih (lihat Cabaran) |
| Trace | Tiada | SDK dalam aplikasi → OTLP → Collector → Tempo |
| Agent dalam kluster | Satu agent setiap jenis isyarat | Satu Collector untuk semua isyarat |
| Format | Format Prometheus, format Fluent Bit | OTLP (standard terbuka CNCF), boleh juga terima format Prometheus |
| Storan & paparan | Prometheus, Loki, Grafana | **Sama.** OTel tidak menyimpan atau memaparkan data |
| Pemprosesan sebelum keluar kluster | `relabel_configs` (metrik), penapis Fluent Bit (log) | Processor Collector: tokok atribut `k8s.*`, tapis, redact, sampling, untuk semua isyarat |
| Kematangan untuk metrik K8s | Sangat matang, contoh dan dashboard komuniti banyak | Matang, tetapi ada perbezaan kecil label (lihat Makmal 5.4) |

### Bila pilih OpenTelemetry, bila kekal dengan cara sekarang

Pilih OpenTelemetry bila:

- **Perlu tracing.** Sistem ada banyak microservice dan dashboard hanya menunjukkan "latency p95 naik" tanpa memberitahu servis mana puncanya. Inilah sebab paling kuat.
- **Mahu satu pipeline yang tidak terikat vendor.** Aplikasi menghasilkan OTLP sekali; backend (Tempo, Jaeger, Prometheus, vendor SaaS) boleh ditukar di Collector tanpa mengubah kod aplikasi.
- **Perlu memproses data di satu tempat** sebelum keluar kluster: buang atribut sensitif, tokok label kluster, sampling trace, untuk metrik, log dan trace dengan konfigurasi yang sama.
- **Pasukan pembangun sudah menghasilkan OTLP**, atau organisasi sudah menyeragamkan OTel.

Kekal dengan cara sekarang bila:

- **Tumpuan hanya metrik dan log infrastruktur Kubernetes** (HPA, kesihatan node, alert seperti dalam Modul 1 hingga 4). Prometheus + kube-state-metrics + node-exporter lebih ringkas, dan semua dashboard serta alert bengkel dibina di atasnya.
- **Aplikasi tunggal** seperti `demo-app`. Trace satu servis hanya menunjukkan satu span; metrik sudah menjawab soalan yang sama.
- **Pasukan kecil tanpa masa** untuk mengurus satu komponen lagi. Collector perlu dipantau, dikemas kini (keluaran baharu hampir setiap 2 minggu) dan dilaraskan memorinya.

> Ini bukan pilihan "satu atau satu lagi". Pola biasa di production: Prometheus kekal sebagai storan metrik, Collector menggantikan agent dalam kluster, dan tracing ditambah untuk aplikasi yang kritikal.

### Bahagian-bahagian OpenTelemetry

| Bahagian | Fungsi | Dalam makmal ini |
|---|---|---|
| **SDK** | Pustaka dalam kod aplikasi untuk menghasilkan span (dan metrik/log) | `opentelemetry-sdk` 1.45.1 untuk Python, dalam `app/app_otel.py` |
| **OTLP** | Protokol penghantaran (gRPC port 4317, HTTP port 4318) | App → Collector (HTTP), Collector → Tempo (gRPC) |
| **Collector** | Agent yang menerima, memproses dan menghantar | `otel/opentelemetry-collector-contrib:0.163.1` sebagai DaemonSet |

Konfigurasi Collector terdiri daripada empat blok yang disambung oleh `service.pipelines`:

```
receivers ──▶ processors ──▶ exporters
  otlp          memory_limiter    prometheus_remote_write ─▶ Prometheus luar
  prometheus    k8s_attributes    otlp_grpc/tempo         ─▶ Tempo luar
                resource, batch   debug                   ─▶ log pod
```

Fail: [`k8s/01-otel-collector.yaml`](k8s/01-otel-collector.yaml). Ada dua pipeline: `metrics` (receiver `prometheus` → `prometheus_remote_write`) dan `traces` (receiver `otlp` → `k8s_attributes` → Tempo).

### Seni bina makmal

```
┌──────────────────── Kluster k3d "lab" ─────────────────────┐   ┌──── Luar kluster (docker compose) ────┐
│                                                             │   │                                       │
│  ns demo:  kedai ──traceparent──▶ inventori                 │   │  Prometheus ◀── remote_write ─────┐   │
│              │ OTLP/HTTP :4318      │                       │   │      ▲                            │   │
│              ▼                      ▼                       │   │      │ metrik span & service graph│   │
│  ns monitoring: otel-collector (DaemonSet, 1 pod/node) ─────┼──▶│  Tempo :4317 / :3200              │   │
│       ▲ scrape node sendiri: node-exporter, cAdvisor,       │   │      ▲                            │   │
│         kube-state-metrics, pod beranotasi ─────────────────┼───┼──────┼────────────────────────────┘   │
│                                                             │   │  Grafana: Prometheus, Tempo, Loki     │
└─────────────────────────────────────────────────────────────┘   └───────────────────────────────────────┘
```

Arah rangkaian sama seperti Pilihan B: **semua sambungan dari kluster keluar**. Prometheus luar tidak lagi perlu token ServiceAccount atau akses ke API server.

**Kenapa DaemonSet, bukan Deployment seperti Prometheus Agent?** Setiap pod Collector hanya scrape sasaran pada node ia berjalan (`selectors` dengan `spec.nodeName`), jadi beban scrape tersebar dan trace dari aplikasi pergi ke Collector pada node yang sama (Service dengan `internalTrafficPolicy: Local`). Tanpa selector itu, 3 pod akan scrape sasaran yang sama 3 kali.

### Konsep trace dalam 2 minit

| Istilah | Maksud | Contoh dalam makmal |
|---|---|---|
| **Trace** | Perjalanan satu request merentas semua servis, dikenal pasti oleh `trace_id` | Satu `GET /beli` |
| **Span** | Satu langkah dalam trace, dengan masa mula, tempoh dan atribut | `GET /beli`, `GET /stok`, `semak-pangkalan-data`, `kira-harga` |
| **Span kind** | Peranan span: `SERVER` (terima request), `CLIENT` (panggil servis lain), `INTERNAL` | `kedai` mencipta span CLIENT `GET /stok`; `inventori` mencipta span SERVER `GET /stok` |
| **Propagasi konteks** | `trace_id` dihantar ke servis seterusnya dalam header HTTP `traceparent` (W3C) | `inject(headers)` dalam `kedai`, `extract(self.headers)` dalam `inventori` |
| **Resource** | Siapa yang menghasilkan span | `service.name=kedai`, ditambah `k8s.pod.name`, `k8s.deployment.name` oleh Collector |

---

## Makmal 5.1: Naikkan Tempo di luar kluster

```bash
cd ~/bengkel-k8s/modul-5-opentelemetry/external
docker compose up -d
curl -s localhost:3200/ready
```

Jangkaan: `ready` (mungkin `Ingester check failed` selama 15 hingga 30 saat pertama; cuba semula). Mesej `error calling scheduler ... no jobs found` dalam `docker compose logs tempo` adalah normal bila belum ada data.

Datasource **Tempo** sudah ditambah dalam provisioning Modul 3 ([`prometheus.yml`](../modul-3-monitoring/external/grafana/provisioning/datasources/prometheus.yml)). Mulakan semula Grafana supaya ia dibaca:

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
docker compose restart grafana
```

Sahkan di Grafana → **Connections → Data sources → Tempo → Save & test**. Jangkaan: hijau, walaupun belum ada trace.

## Makmal 5.2: Tukar Prometheus luar ke Pilihan B

Dalam Pilihan B, kluster yang menghantar metrik. Jika Prometheus luar terus scrape kluster (Pilihan A) pada masa yang sama, setiap siri akan muncul dua kali dan dashboard menjumlahkan nilai berganda. Jadi buang job scrape kluster daripada Prometheus luar (masih dalam `modul-3-monitoring/external`):

```bash
cp prometheus/prometheus.yml prometheus/prometheus.yml.asal
cp ../../modul-5-opentelemetry/external/prometheus-pilihan-b.yml prometheus/prometheus.yml
curl -X POST localhost:9090/-/reload
```

Buka http://localhost:9090/targets. Jangkaan: hanya job `prometheus` tinggal. Jika anda pernah memasang Prometheus Agent Pilihan B dari Modul 3, buang dahulu supaya tiada dua agent:

```bash
kubectl delete -f ../k8s/04-pilihan-b-prometheus-agent.yaml --ignore-not-found
```

## Makmal 5.3: Pasang OpenTelemetry Collector

```bash
cd ~/bengkel-k8s/modul-5-opentelemetry
kubectl apply -f k8s/01-otel-collector.yaml
kubectl -n monitoring rollout status ds/otel-collector
kubectl -n monitoring get pods -l app=otel-collector -o wide
```

Jangkaan: 3 pod `Running`, satu pada setiap node (termasuk `k3d-lab-server-0` kerana `tolerations: operator: Exists`).

Baca konfigurasi sambil melihat fail. Perkara penting:

- `${env:K8S_NODE_NAME}` dikembangkan oleh Collector daripada env pod (Downward API). Tanda `$` yang perlu sampai kepada Prometheus, seperti `$1` dalam relabel, ditulis `$$1`.
- Job `kube-state-metrics` menemui pod KSM melalui `role: pod` dengan selector node, jadi hanya pod Collector pada node yang sama dengan KSM akan scrape (tiada data berganda).
- `memory_limiter` menolak data baharu sebelum pod mencapai `limits.memory`, supaya Collector tidak OOMKilled ketika beban tinggi.

Semak log satu pod:

```bash
kubectl -n monitoring logs ds/otel-collector | grep -iE 'error|warn|Everything is ready'
```

Jangkaan: `Everything is ready. Begin running and processing data.` Ralat biasa:

| Ralat dalam log | Punca | Pembetulan |
|---|---|---|
| `dial tcp: lookup prometheus ... no such host` | Pod tidak dapat menyelesaikan nama container Docker | Gantikan `prometheus` dan `tempo` dalam ConfigMap dengan IP daripada `docker inspect` (arahan di kepala fail) |
| `connection refused` ke `:9090/api/v1/write` | Prometheus luar tanpa `--web.enable-remote-write-receiver` | Sudah ada dalam `docker-compose.yml` Modul 3; semak anda menggunakan fail itu |
| `403 Forbidden` dalam scrape cAdvisor | RBAC | `kubectl auth can-i get nodes/metrics --as=system:serviceaccount:monitoring:otel-collector` |
| `data refused due to high memory usage` | `memory_limiter` aktif | Normal sekali-sekala; jika berterusan, naikkan `limits.memory` dan `GOMEMLIMIT` bersama |

## Makmal 5.4: Sahkan metrik dan dashboard Modul 3

Dalam http://localhost:9090/query:

```promql
# Setiap target yang di-scrape oleh Collector menghantar "up" seperti Prometheus biasa
count by (job) (up{cluster="lab"})

# Metrik Collector sendiri: berapa banyak titik metrik dihantar sesaat
sum(rate(otelcol_exporter_sent_metric_points_total[1m]))
```

Jangkaan untuk query pertama: `node-exporter` 3, `kubernetes-cadvisor` 3, `kube-state-metrics` 1, `kubernetes-pods` = bilangan pod beranotasi `prometheus.io/scrape` (demo-app, ditambah 3 pod Collector pada port 8888).

Buka dashboard **Bengkel K8s: Kluster, Pod & HPA** dan jalankan `k6 run ../modul-2-load-testing/k6/load.js`. Semua panel sepatutnya berfungsi seperti Modul 3, kerana nama metrik dan label `job` dikekalkan. Alert `HPAMaxedOut` dan lain-lain juga tidak perlu diubah.

Perbezaan yang akan anda nampak pada setiap siri:

| Label | Asal | Kesan |
|---|---|---|
| `otel_scope_name`, `otel_scope_version` | Ditambah oleh receiver `prometheus` Collector | Tiada kesan pada `sum by (...)`; boleh mengganggu padanan vektor tanpa `on(...)` |
| `cluster="lab"` | `external_labels` pada exporter | Sama seperti Prometheus Agent Pilihan B |
| `instance` bagi metrik `otelcol_*` | UUID Collector, bukan IP pod | Guna label `pod` untuk membezakan pod Collector |
| Tiada job `kubelet` | Tidak dikonfigurasi, sama seperti Prometheus Agent | Panel yang hanya menggunakan job `kubelet` akan kosong |

**Perbincangan: pull vs push.** Dalam Pilihan A, jika kluster tidak dapat dicapai, Prometheus mencatat `up == 0` dan alert `TargetDown` berbunyi. Dalam Pilihan B, jika Collector mati, tiada data langsung dan `up == 0` tidak pernah dihantar. Alert perlu mengesan *ketiadaan* data (lihat Cabaran 2).

## Makmal 5.5: Instrumentasi aplikasi dengan SDK OpenTelemetry

Dua servis daripada satu fail [`app/app_otel.py`](app/app_otel.py), dipilih oleh env `ROLE`:

| Servis | Endpoint | Apa yang dilakukan | Span yang dicipta |
|---|---|---|---|
| `kedai` | `/beli?item=buku` | Panggil `inventori`, kemudian kira harga | SERVER `GET /beli`, CLIENT `GET /stok`, `kira-harga` |
| `inventori` | `/stok?item=buku` | "Semak pangkalan data": 20 ms biasanya, 800 ms bagi 10% request, gagal bagi 2% | SERVER `GET /stok`, `semak-pangkalan-data` |

Baca bahagian penting kod sebelum deploy: `TracerProvider` dan `BatchSpanProcessor` (bahagian atas), `inject(headers)` dalam `panggil_inventori`, dan `extract(self.headers)` dalam `do_GET`. SDK membaca `OTEL_SERVICE_NAME` dan `OTEL_EXPORTER_OTLP_ENDPOINT` daripada env, jadi kod tidak tahu ke mana trace dihantar.

```bash
kubectl apply -f app/configmap.yaml
kubectl apply -f k8s/02-app-otel.yaml
kubectl -n demo rollout status deploy/inventori
kubectl -n demo rollout status deploy/kedai
```

Pod akan berada dalam `Init:0/1` selama 10 hingga 60 saat semasa initContainer `pasang-otel-sdk` memasang SDK dengan pip (sekitar 14 MB dari pypi.org). Jika Wi-Fi bengkel perlahan, bina image sekali dengan [`app/Dockerfile`](app/Dockerfile) dan `k3d image import`.

Hantar trafik (terminal berasingan untuk port-forward):

```bash
kubectl -n demo port-forward svc/kedai 8085:8080
```

```bash
curl -s "localhost:8085/beli?item=buku"
for i in $(seq 1 200); do curl -s -o /dev/null "localhost:8085/beli?item=buku"; done
```

Jangkaan output `curl` pertama:

```json
{"item": "buku", "stok": 42, "harga": 27.31, "pod": "kedai-6d8f7c9b5-x2k4p"}
```

Sahkan trace sampai ke Collector:

```bash
kubectl -n monitoring logs -l app=otel-collector --tail=20 | grep '"spans"'
```

## Makmal 5.6: Cari request lambat dalam Grafana

### A. Cari trace dengan TraceQL

Grafana → **Explore → Tempo → Query type: Search** atau **TraceQL**:

```
{ resource.service.name = "kedai" && duration > 500ms }
```

Buka satu trace. Paparan waterfall menunjukkan:

```
kedai      GET /beli                 ████████████████████████████████  ~808 ms
kedai        GET /stok (CLIENT)      ██████████████████████████████▌
inventori      GET /stok (SERVER)    ██████████████████████████████
inventori        semak-pangkalan-data ████████████████████████████▉     ~800 ms
kedai        kira-harga                                            ▌   ~5 ms
```

Jawapannya jelas tanpa membaca log: masa dihabiskan dalam `semak-pangkalan-data` di servis `inventori`. Klik span itu dan lihat atribut `bengkel.lambat = true`, serta atribut resource `k8s.pod.name` dan `k8s.deployment.name` yang ditambah oleh processor `k8s_attributes` (aplikasi tidak menghantarnya).

Query lain untuk dicuba:

```
{ span.bengkel.lambat = true }
{ status = error }
{ resource.service.name = "inventori" } | rate()
```

### B. Service graph

Grafana → **Explore → Tempo → Service Graph**. Jangkaan: `user → kedai → inventori`, dengan kadar request dan ralat pada setiap anak panah. Data ini datang daripada metrik `traces_service_graph_*` yang dijana oleh Tempo dan di-`remote_write` ke Prometheus. Cuba di Prometheus:

```promql
sum by (client, server) (rate(traces_service_graph_request_total[5m]))

# p95 setiap servis, dikira daripada span (tanpa sebarang metrik dalam kod aplikasi)
histogram_quantile(0.95, sum by (le, service) (rate(traces_spanmetrics_latency_bucket{span_kind="SPAN_KIND_SERVER"}[5m])))
```

### C. Daripada trace ke log (perlukan Modul 4)

`app_otel.py` menulis `trace_id` dalam setiap baris log JSON. Jika Fluent Bit dan Loki dari Modul 4 masih berjalan, klik **Logs for this span** pada span dalam Tempo. Grafana membuka Loki dengan `{namespace="demo"} |= "<trace_id>"`. Atau terus di Explore → Loki:

```
{namespace="demo", container="app"} | json | trace_id != ""
```

Inilah nilai sebenar tiga isyarat yang disambung: metrik memberitahu *ada masalah*, trace memberitahu *di mana*, log memberitahu *kenapa*.

## Cabaran

1. **Collector menggantikan Fluent Bit juga.** Tambah pipeline `logs` pada ConfigMap Collector: receiver `filelog` (baca `/var/log/pods/*/*/*.log`, operator `container`) dan exporter `otlp_http/loki` ke `http://loki:3100/otlp` (Loki 3 menerima OTLP secara asli). DaemonSet perlu `hostPath` `/var/log/pods` (readOnly). Bandingkan label log dalam Loki: Fluent Bit memberi `namespace`, `pod`; OTLP memberi `service_name`, `k8s_namespace_name` dan atribut lain sebagai *structured metadata*.

   ```yaml
   receivers:
     filelog:
       include: [/var/log/pods/*/*/*.log]
       exclude: [/var/log/pods/monitoring_otel-collector-*/*/*.log]   # jangan baca log sendiri
       include_file_path: true
       operators:
         - type: container
   exporters:
     otlp_http/loki:
       endpoint: http://loki:3100/otlp
   service:
     pipelines:
       logs:
         receivers: [filelog]
         processors: [memory_limiter, k8s_attributes, resource, batch]
         exporters: [otlp_http/loki]
   ```

2. **Alert bila agent senyap.** Tulis peraturan yang berbunyi jika tiada data cAdvisor dari mana-mana node selama 5 minit: `absent_over_time(up{job="kubernetes-cadvisor"}[5m])` atau `count(up{job="kubernetes-cadvisor"}) < 3`. Uji dengan `kubectl -n monitoring delete ds otel-collector`, kemudian pasang semula.
3. **Ralat dalam trace.** Set `GAGAL_RATE` kepada `0.3` pada `inventori` (`kubectl -n demo set env deploy/inventori GAGAL_RATE=0.3`). Cari `{ status = error }`. Apakah status span `GET /beli` di `kedai`, dan kenapa?
4. **Sampling.** Pada trafik tinggi, menyimpan setiap trace mahal. Baca tentang processor `tail_sampling` (contoh: simpan semua trace dengan ralat atau > 500 ms, dan 10% yang lain). Kenapa *tail* sampling tidak berfungsi dengan betul pada DaemonSet jika span satu trace sampai ke pod Collector yang berlainan?

## Pembersihan

```bash
kubectl delete -f k8s/02-app-otel.yaml -f app/configmap.yaml
kubectl delete -f k8s/01-otel-collector.yaml
cd external && docker compose down -v && cd ..
# pulihkan Pilihan A
cd ~/bengkel-k8s/modul-3-monitoring/external
cp prometheus/prometheus.yml.asal prometheus/prometheus.yml && curl -X POST localhost:9090/-/reload
```

## Semakan akhir modul

- [ ] Peserta boleh menerangkan sekurang-kurangnya dua situasi untuk memilih OpenTelemetry, dan satu situasi untuk kekal dengan Prometheus + Fluent Bit
- [ ] 3 pod `otel-collector` `Running`, dan `count by (job) (up{cluster="lab"})` menunjukkan semua job
- [ ] Dashboard Bengkel K8s memaparkan data melalui Pilihan B tanpa perubahan pada dashboard
- [ ] Trace `kedai → inventori` kelihatan dalam Tempo, dan span lambat ditemui dengan TraceQL
- [ ] Service graph memaparkan `kedai → inventori`
- [ ] Prometheus luar dipulihkan ke Pilihan A selepas makmal

## Apa yang telah diuji

Dijalankan dan disahkan dalam Docker (versi yang sama seperti di bawah):

- `otelcol-contrib validate` lulus untuk konfigurasi Collector, termasuk pipeline `logs` dalam Cabaran 1
- `kedai` dan `inventori` (SDK Python 1.45.1) → Collector → Tempo 3.1.0: trace lengkap dengan 5 span merentas dua servis, propagasi `traceparent` berfungsi, carian TraceQL (`duration > 500ms`, `span.bengkel.lambat = true`) menemui trace ~808 ms
- Receiver `prometheus` → `prometheus_remote_write` → Prometheus v3.4.0: `up`, `node_*` (node-exporter v1.9.1), `demo_http_requests_total` dan `otelcol_*` tiba dengan nama dan label `job` yang sama seperti Pilihan A
- Metrics-generator Tempo menghasilkan `traces_service_graph_*` (`kedai → inventori`) dan `traces_spanmetrics_*` dalam Prometheus
- Grafana 12.0.0 memprovision datasource Tempo dan boleh mengambil trace serta carian melalui proxy datasource
- `promtool check config` lulus untuk `prometheus-pilihan-b.yml` bersama peraturan alert Modul 3; `app/Dockerfile` berjaya dibina

Dengan kluster k3d sebenar (k3s v1.33.1):

- Semua manifest diterima oleh API server (`kubectl apply --dry-run=server`); DaemonSet dijadualkan pada ketiga-tiga node termasuk control-plane
- RBAC `otel-collector` disahkan dengan `kubectl auth can-i`; processor `k8s_attributes` boleh memantau pod tanpa ralat kebenaran
- Collector yang sama (dengan token ServiceAccount `otel-collector`) menemui **hanya node sendiri** melalui `selectors`, dan scrape cAdvisor terus ke kubelet port 10250 berjaya (`up == 1`)

Yang **belum** dapat diuji, kerana tiada pod yang benar-benar berjalan dalam persekitaran penyediaan: Collector berjalan sebagai pod, penemuan `role: pod` (pod KSM dan pod beranotasi perlukan IP pod), `internalTrafficPolicy: Local`, penyelesaian nama `prometheus` dan `tempo` dari dalam pod, initContainer pip, atribut `k8s.*` pada span sebenar, pautan trace ke log dengan Loki, dan pipeline `logs` Cabaran 1. Jalankan modul ini sekali secara penuh sebelum menggunakannya dalam kelas.

## Versi komponen modul ini

| Komponen | Versi |
|---|---|
| OpenTelemetry Collector (contrib) | 0.163.1 |
| Grafana Tempo | 3.1.0 |
| `opentelemetry-sdk` / `opentelemetry-exporter-otlp-proto-http` (Python) | 1.45.1 / 1.45.1 |

## Rujukan

- OpenTelemetry: https://opentelemetry.io/docs/what-is-opentelemetry/
- OpenTelemetry Collector, konfigurasi: https://opentelemetry.io/docs/collector/configuration/
- Collector pada Kubernetes (pola DaemonSet): https://opentelemetry.io/docs/platforms/kubernetes/collector/
- Receiver `prometheus`: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/prometheusreceiver
- Processor `k8s_attributes`: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/k8sattributesprocessor
- SDK Python: https://opentelemetry.io/docs/languages/python/
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- Grafana Tempo: https://grafana.com/docs/tempo/latest/
- TraceQL: https://grafana.com/docs/tempo/latest/traceql/
- Loki OTLP ingestion: https://grafana.com/docs/loki/latest/send-data/otel/
