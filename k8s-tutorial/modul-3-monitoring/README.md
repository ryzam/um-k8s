# Modul 3: Fasa Monitoring, Integrasi Prometheus & Grafana Luaran

**Hari 2, 9:00 pagi hingga 1:00 petang**

> **Opsyen B (Rancher):** Prometheus luar bercakap terus dengan API server k3d, bukan melalui Rancher; jangan pasang app Monitoring Rancher semasa bengkel. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Pasang exporter dalam kluster: **kube-state-metrics** dan **node-exporter**.
2. Sambungkan kluster ke **Prometheus dan Grafana yang berada di LUAR kluster**, dengan cara yang selamat (ServiceAccount + RBAC + API server proxy).
3. Bina dashboard Grafana untuk kesihatan kluster, prestasi pod dan metrik HPA.
4. Konfigur peraturan alert dan hantar notifikasi ke **Email, Slack dan Microsoft Teams**.

> Prasyarat: Modul 1 dan 2 selesai. Docker Compose v2 dipasang (`docker compose version`).

## Jadual

| Masa | Aktiviti |
|---|---|
| 9:00 – 9:30 | Teori: jenis metrik K8s, Prometheus vs Grafana, cara mereka bentuk dashboard, seni bina monitoring luaran, Pilihan A vs B |
| 9:30 – 10:00 | Makmal 3.1 & 3.2: pasang exporter, RBAC untuk Prometheus luar |
| 10:00 – 10:30 | Makmal 3.3: naikkan stack luar (Pilihan A), sahkan semua target `UP` |
| 10:30 – 10:45 | Makmal 3.3B: tukar ke Pilihan B, bandingkan, kembali ke Pilihan A |
| 10:45 – 11:00 | Rehat |
| 11:00 – 11:45 | Makmal 3.4: dashboard Grafana (yang disediakan + bina panel sendiri) |
| 11:45 – 12:40 | Makmal 3.5 & 3.6: alert rules, Alertmanager, Email/Slack/Teams, Grafana alerting |
| 12:40 – 1:00 | Makmal 3.7: cetuskan alert sebenar dengan ujian beban Modul 2 |

---

## Teori ringkas

### Tiga sumber metrik utama

| Sumber | Jawab soalan | Contoh metrik |
|---|---|---|
| **cAdvisor** (dalam kubelet) | Berapa banyak resource container **guna**? | `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes`, `container_cpu_cfs_throttled_periods_total` |
| **kube-state-metrics** | Apa **keadaan** objek K8s? | `kube_pod_status_phase`, `kube_deployment_status_replicas_available`, `kube_horizontalpodautoscaler_status_current_replicas`, `kube_pod_container_resource_requests` |
| **node-exporter** | Bagaimana keadaan **OS node**? | `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `node_filesystem_avail_bytes` |

> **Metrics Server ≠ Prometheus.** Metrics Server (Modul 1) hanya simpan nilai terkini dalam memori untuk HPA dan `kubectl top`. Ia tiada sejarah dan tidak boleh di-query dengan PromQL.

### Prometheus vs Grafana: siapa buat apa

Ramai pemula keliru kerana kedua-duanya "ada graf". Pembahagian kerjanya mudah:

| | Prometheus | Grafana |
|---|---|---|
| Peranan | **Kumpul dan simpan** metrik | **Paparkan** metrik |
| Cara kerja | Setiap 15 saat, *scrape* (tarik) `/metrics` dari setiap target (exporter, pod), simpan sebagai siri masa | Hantar query PromQL kepada Prometheus, terima nombor, lukis graf |
| Bahasa | PromQL (Prometheus yang menjalankan query) | Tiada bahasa sendiri untuk metrik; ia hanya menghantar PromQL anda |
| Simpan data? | Ya (TSDB, contoh 15 hari) | Tidak. Grafana hanya simpan definisi dashboard |
| Tanpa yang satu lagi | Masih berfungsi: query di http://localhost:9090, alert tetap jalan | Kosong. Tiada datasource, tiada graf |

Aliran satu panel: **exporter → Prometheus scrape dan simpan → Grafana hantar PromQL → Prometheus jawab → Grafana lukis**. Maka setiap panel Grafana sebenarnya ialah **satu atau lebih query PromQL + tetapan paparan** (jenis graf, unit, warna, threshold). Jika query betul di Prometheus (`localhost:9090/query`), ia akan betul di Grafana. Uji query di Prometheus dahulu, kemudian salin ke panel.

Tiga corak PromQL yang meliputi hampir semua panel dalam bengkel ini:

| Jenis metrik | Contoh | Cara guna |
|---|---|---|
| **Counter** (sentiasa naik, `_total`) | `demo_http_requests_total` | Jangan plot terus. Guna `rate(...[1m])` untuk dapat "per saat" |
| **Gauge** (naik turun) | `container_memory_working_set_bytes`, `kube_..._current_replicas` | Plot terus, atau `sum by (pod)` |
| **Nisbah** | penggunaan / requests | `100 * A / B` untuk peratus, seperti cara HPA mengira |

### Cara mereka bentuk dashboard

Jangan mula dengan "metrik apa yang ada". Mula dengan **soalan yang mahu dijawab semasa insiden**, kemudian cari metrik yang menjawabnya. Dua senarai semak yang biasa digunakan:

- **USE** untuk *resource* (node, CPU, memori): **U**tilization (berapa % digunakan), **S**aturation (ada yang beratur atau dihadkan?), **E**rrors.
- **RED** untuk *servis* (aplikasi): **R**ate (request sesaat), **E**rrors (kadar ralat), **D**uration (latensi). Google SRE memanggil gabungannya *four golden signals*: latency, traffic, errors, saturation.

Susun dashboard dari atas ke bawah, daripada gambaran besar ke butiran, supaya mata bergerak seperti proses diagnosis. Dashboard bengkel ([`bengkel-k8s-hpa.json`](external/grafana/dashboards/bengkel-k8s-hpa.json)) mengikut corak ini:

| Soalan | Panel dalam dashboard bengkel | Kaedah |
|---|---|---|
| Adakah kluster sihat sekarang? | Node Ready / NotReady, Pod tidak sihat, Alert firing (stat, satu nombor besar) | E |
| Adakah node penuh? | CPU node (%), Memori node (%) | USE: U |
| Berapa CPU pod guna berbanding apa yang ia minta? | CPU pod vs requests & limits (garis putus-putus = requests/limits) | USE: U |
| Adakah pod hampir OOMKilled? | Memori pod (working set) vs limits | USE: S |
| Adakah pod dihadkan oleh limits CPU? | CPU throttling (%), lebih 25% = latency terjejas | USE: S |
| Adakah pod crash berulang kali? | Restart container (1 jam), Pod mengikut fasa | USE: E |
| Adakah HPA bertindak, dan adakah ia tersekat? | Replicas semasa / dikehendaki / min / max | Khusus HPA |
| Kenapa HPA scale (atau tidak)? | Utilization CPU & memori vs sasaran HPA | Khusus HPA |
| Berapa banyak trafik, dan berapa yang gagal? | Request sesaat mengikut kod HTTP | RED: R, E |
| Trafik pergi ke versi mana? | Request sesaat mengikut versi | RED: R (Modul 4) |

Perhatikan satu corak penting: **letak nilai sebenar dan had/sasaran dalam panel yang sama**. CPU sahaja tidak bermakna; CPU berbanding requests memberitahu HPA, dan berbanding limits memberitahu throttling. Replicas sahaja tidak bermakna; semasa berbanding dikehendaki memberitahu sama ada quota atau node menyekat scale.

Yang **tiada** dalam dashboard bengkel: **latensi (D dalam RED)**. demo-app hanya mengeluarkan counter `demo_http_requests_total`, tiada histogram masa respons, jadi latensi diukur dari sisi klien oleh k6 di Modul 2. Dalam aplikasi sebenar, tambah histogram (contoh `http_request_duration_seconds_bucket`) dan plot p95 dengan `histogram_quantile(0.95, sum by (le) (rate(..._bucket[5m])))`.

Tips paparan ringkas:

- **Stat** untuk "berapa sekarang" (Node Ready, alert firing); **Time series** untuk "bagaimana ia berubah" (hampir semua yang lain).
- Sentiasa tetapkan **unit** (percent, bytes, cores, req/s) dan **threshold warna** yang sama dengan threshold alert, supaya merah di dashboard bermaksud perkara yang sama dengan alert.
- Guna **pembolehubah** (`$namespace`, `$deployment`) supaya satu dashboard boleh digunakan untuk banyak aplikasi.
- Hadkan setiap dashboard kepada satu tujuan. Kalau lebih kurang 15 panel tidak cukup, pecahkan kepada dashboard baharu dan pautkan.

### Seni bina makmal (Pilihan A: Prometheus luar scrape terus)

```
                         ┌──────────────────────── Kluster k3d "lab" ─────────────────────────┐
                         │                                                                    │
                         │  API server :6443 ──proxy──▶ kubelet/cAdvisor (setiap node)        │
 ┌───── Luar kluster ────┤               └──proxy──▶ pod demo-app :8080/metrics              │
 │  (docker compose)     │                                                                    │
 │                       │  node-exporter (DaemonSet, hostNetwork) ── <IP-node>:9100          │
 │  Prometheus ──────────┼─▶ kube-state-metrics (NodePort) ───────── <node>:30081             │
 │     │      ───────────┼─▶ API server (token ServiceAccount prometheus-external)            │
 │     ▼                 └────────────────────────────────────────────────────────────────────┘
 │  Alertmanager ──▶ Email (Mailpit) / Slack / Teams
 │     ▲
 │  Grafana ──▶ dashboard + Grafana-managed alerts
 └───────────────────────
```

Langkah untuk Pilihan A ialah Makmal 3.1 (exporter), 3.2 (RBAC + token) dan [Makmal 3.3](#makmal-3-3-naikkan-stack-monitoring-luar) (naikkan Prometheus, Alertmanager dan Grafana dengan `docker compose`). Dalam bengkel, semua peserta buat Pilihan A dahulu, kemudian tukar ke Pilihan B dalam [Makmal 3.3B](#makmal-3-3b-tukar-kepada-pilihan-b-dan-bandingkan) supaya dapat merasai kelebihan dan kekurangan kedua-dua cara.

Kenapa melalui **API server proxy** untuk cAdvisor dan pod? Kerana IP pod (`10.42.x.x` dalam k3s) tidak boleh dicapai dari luar kluster, dan port kubelet 10250 biasanya ditutup. API server biasanya sudah boleh dicapai, dan akses dikawal oleh RBAC.

### Pilihan B: Prometheus Agent dalam kluster + remote_write

Bila Prometheus luar **tidak boleh** capai kluster langsung (firewall hanya benarkan trafik keluar), jalankan Prometheus dalam *agent mode* di dalam kluster dan `remote_write` ke Prometheus luar. Manifest: [`k8s/04-pilihan-b-prometheus-agent.yaml`](k8s/04-pilihan-b-prometheus-agent.yaml). Grafana Alloy dan OpenTelemetry Collector ialah alternatif lain untuk peranan yang sama; [Modul 5 (pilihan)](../modul-5-opentelemetry/README.md) menunjukkan Pilihan B dengan OpenTelemetry Collector.

| | Pilihan A: scrape dari luar | Pilihan B: agent + remote_write |
|---|---|---|
| Arah rangkaian | Luar → kluster | Kluster → luar |
| Komponen dalam kluster | Exporter sahaja | Exporter + agent |
| Jika rangkaian putus | Data hilang semasa putus | Agent simpan WAL dan hantar semula |
| Sesuai untuk | Makmal, rangkaian dalaman rata | Banyak kluster, cloud, kluster di belakang NAT |
| Prometheus, Alertmanager, Grafana luar | `docker compose` | `docker compose` yang **sama** (Prometheus jadi penerima `remote_write`) |
| Prometheus luar scrape | Semua job kluster | Job `prometheus` sahaja |
| Token ServiceAccount di luar | Perlu (`get-k8s-credentials.sh`) | Tidak perlu |

**Pilihan B tidak menggantikan stack `docker compose`.** Agent dalam kluster hanya mengumpul dan menghantar metrik; ia tidak menyimpan data untuk query, tidak menilai peraturan alert dan tiada UI. Prometheus luar masih diperlukan untuk menyimpan data, menilai alert dan menjadi datasource Grafana, jadi Prometheus, Alertmanager, Grafana dan Mailpit tetap dinaikkan dengan `docker compose up -d` seperti Makmal 3.3. Yang berubah hanya konfigurasi Prometheus luar (berhenti scrape kluster) dan satu manifest tambahan dalam kluster. Langkah penuh: [Makmal 3.3B](#makmal-3-3b-tukar-kepada-pilihan-b-dan-bandingkan).

### Nota: Apa itu OpenTelemetry dan bila perlu

**OpenTelemetry (OTel)** ialah standard terbuka (projek CNCF) untuk mengumpul tiga jenis isyarat *observability*:

| Isyarat | Menjawab soalan | Dalam bengkel ini |
|---|---|---|
| Metrik | Berapa banyak / berapa laju? (CPU, RPS, replicas) | Prometheus + exporter |
| Log | Apa yang berlaku? (mesej ralat, akses) | Fluent Bit + Loki (Modul 4) |
| Trace | Di mana masa dihabiskan dalam satu permintaan merentas banyak servis? | Tiada |

OTel terdiri daripada tiga bahagian: **SDK** (pustaka dalam kod aplikasi untuk menghasilkan trace dan metrik), protokol **OTLP** (format penghantaran), dan **OpenTelemetry Collector** (agent yang menerima, memproses dan menghantar data ke mana-mana backend). OTel tidak menyimpan atau memaparkan data; ia masih perlukan backend seperti Prometheus, Loki, Tempo atau Jaeger.

**Jadual teras bengkel tidak menggunakan OTel**, kerana semua objektif (HPA, ujian beban, alert, operasi) bergantung pada metrik dan log sahaja, dan demo-app hanyalah satu servis. Untuk mencubanya, lihat **[Modul 5 (pilihan): OpenTelemetry](../modul-5-opentelemetry/README.md)**: Collector DaemonSet sebagai Pilihan B, tracing dua servis ke Tempo, dan perbandingan penuh bila memilih OTel.

Bila OTel patut dipertimbangkan:

- **Collector sebagai agent tunggal.** Satu DaemonSet Collector boleh menggantikan Prometheus agent (Pilihan B) dan Fluent Bit sekali gus, dan menghantar metrik serta log ke luar kluster melalui OTLP atau `prometheusremotewrite`. Sesuai bila organisasi mahu satu pipeline yang tidak terikat pada vendor.
- **Tracing aplikasi.** Bila sistem ada banyak microservice dan dashboard hanya menunjukkan "latency p95 naik" tanpa tahu servis mana puncanya. Aplikasi diinstrumentasi dengan SDK OTel (atau auto-instrumentation melalui OpenTelemetry Operator), dan trace dihantar ke Tempo atau Jaeger.
- **Pasukan pembangun sudah menghasilkan OTLP.** Jika aplikasi sudah mengeluarkan OTLP, Collector ialah cara paling mudah untuk menerimanya.

Jika tiada keperluan di atas, stack Prometheus + Loki yang digunakan di sini sudah memadai.

---

## Makmal 3.1: Pasang kube-state-metrics dan node-exporter

Semua arahan dalam modul ini dijalankan dari folder `modul-3-monitoring` kecuali dinyatakan:

```bash
cd ~/bengkel-k8s/modul-3-monitoring
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-kube-state-metrics.yaml
kubectl apply -f k8s/02-node-exporter.yaml
kubectl -n monitoring rollout status deploy/kube-state-metrics
kubectl -n monitoring rollout status ds/node-exporter
kubectl -n monitoring get pods -o wide
```

Jangkaan: 1 pod kube-state-metrics, dan 3 pod node-exporter (satu setiap node, termasuk control-plane kerana `tolerations: operator: Exists`).

Sahkan dari laptop (NodePort 30081 dipetakan ke localhost oleh `k3d-cluster.yaml`):

```bash
curl -s localhost:30081/metrics | grep -E '^kube_horizontalpodautoscaler_status_(current|desired)_replicas'
```

Jangkaan:

```
kube_horizontalpodautoscaler_status_current_replicas{namespace="demo",horizontalpodautoscaler="demo-app"} 2
kube_horizontalpodautoscaler_status_desired_replicas{namespace="demo",horizontalpodautoscaler="demo-app"} 2
```

Sahkan node-exporter dari dalam rangkaian Docker `k3d-lab` (nama container node = nama node):

```bash
docker run --rm --network k3d-lab curlimages/curl:8.13.0 -s k3d-lab-agent-0:9100/metrics | grep -m3 '^node_load'
```

## Makmal 3.2: ServiceAccount dan RBAC untuk Prometheus luar

```bash
kubectl apply -f k8s/03-prometheus-external-rbac.yaml
```

Uji kebenaran (tanpa token sebenar, guna impersonation):

```bash
SA=system:serviceaccount:monitoring:prometheus-external
kubectl auth can-i get nodes/proxy --as=$SA          # yes
kubectl auth can-i get pods/proxy  --as=$SA -n demo  # yes
kubectl auth can-i delete pods     --as=$SA -n demo  # no  <- prinsip least privilege
kubectl auth can-i get secrets     --as=$SA -n demo  # no
```

Salin token dan CA untuk Prometheus luar:

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
bash get-k8s-credentials.sh
ls -l prometheus/k8s/        # mesti ada: ca.crt dan token
```

Uji token secara manual (dari laptop, melalui port API server yang k3d dedahkan, `https://127.0.0.1:6550`):

```bash
TOKEN=$(cat prometheus/k8s/token)
APISERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
curl -s --cacert prometheus/k8s/ca.crt -H "Authorization: Bearer $TOKEN" \
  "$APISERVER/api/v1/nodes/k3d-lab-agent-0/proxy/metrics/cadvisor" | grep -m3 container_cpu_usage_seconds_total
```

> **Keselamatan:** `prometheus/k8s/token` ialah kelayakan. Ia sudah dalam `.gitignore`. Jangan commit ke Git.

## Makmal 3.3: Naikkan stack monitoring luar

Prometheus, Alertmanager dan Grafana dinaikkan **sekali gus** dengan satu fail Docker Compose: [`external/docker-compose.yml`](external/docker-compose.yml). Fail ini menjalankan 4 container di laptop anda, di luar kluster:

| Servis | Image | Port | Konfigurasi dibaca dari |
|---|---|---|---|
| `prometheus` | `prom/prometheus:v3.4.0` | 9090 | `external/prometheus/prometheus.yml` + `prometheus/rules/` + `prometheus/k8s/` (token & CA) |
| `alertmanager` | `prom/alertmanager:v0.28.1` | 9093 | `external/alertmanager/alertmanager.yml` |
| `grafana` | `grafana/grafana:12.0.0` | 3000 | `external/grafana/provisioning/` (datasource, dashboard, alert) + `grafana/dashboards/` |
| `mailpit` | `axllent/mailpit:v1.25` | 8025 | Tiada (pelayan SMTP ujian untuk email alert) |

Prasyarat sebelum `up` (semuanya dari Makmal 3.1 dan 3.2):

- Kluster `lab` sedang berjalan, jadi rangkaian Docker `k3d-lab` wujud. Prometheus disambung ke rangkaian ini supaya boleh capai `k3d-lab-server-0:6443` dan node.
- `external/prometheus/k8s/token` dan `ca.crt` sudah dijana oleh `bash get-k8s-credentials.sh`.

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
docker network ls | grep k3d-lab          # mesti ada satu baris
docker compose up -d                      # kali pertama: tarik 4 image, ambil masa beberapa minit
docker compose ps                         # 4 servis, STATUS "Up"
```

Jangkaan `docker compose ps` (ringkas):

```
NAME                             SERVICE        STATUS    PORTS
monitoring-luar-alertmanager-1   alertmanager   Up        0.0.0.0:9093->9093/tcp
monitoring-luar-grafana-1        grafana        Up        0.0.0.0:3000->3000/tcp
monitoring-luar-mailpit-1        mailpit        Up        0.0.0.0:8025->8025/tcp
monitoring-luar-prometheus-1     prometheus     Up        0.0.0.0:9090->9090/tcp
```

Semak kesihatan setiap servis dari terminal:

```bash
curl -s localhost:9090/-/ready        # Prometheus Server is Ready.
curl -s localhost:9093/-/ready        # OK
curl -s localhost:3000/api/health     # "database": "ok"
```

Jika satu servis tiada atau asyik restart, lihat lognya:

```bash
docker compose logs prometheus --tail=30
```

| Masalah | Punca lazim | Penyelesaian |
|---|---|---|
| `network k3d-lab declared as external, but could not be found` | Kluster `lab` tidak berjalan | `k3d cluster start lab`, kemudian `docker compose up -d` semula |
| `./get-k8s-credentials.sh: Permission denied` | Bit executable hilang (salinan zip atau git lama) | Jalankan dengan `bash get-k8s-credentials.sh`, atau `chmod +x *.sh` dahulu |
| Prometheus log `open /etc/prometheus/k8s/token: no such file` | Langkau `get-k8s-credentials.sh` | Jalankan `bash get-k8s-credentials.sh`, kemudian `docker compose restart prometheus` |
| `port is already allocated` (9090/3000/9093/8025) | Port digunakan program lain | Hentikan program itu, atau tukar port kiri dalam `ports:` (cth `"3001:3000"`) |
| `no configuration file provided: not found` | Bukan dalam folder `external` | `cd ~/bengkel-k8s/modul-3-monitoring/external` |

Kemudian buka di pelayar:

| Perkhidmatan | URL | Log masuk |
|---|---|---|
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Grafana | http://localhost:3000 | `admin` / `admin123` |
| Mailpit (peti email ujian) | http://localhost:8025 | - |

Buka **Prometheus → Status → Targets** (http://localhost:9090/targets). Semua job mesti `UP`:

| Job | Bilangan target | Jika DOWN |
|---|---|---|
| `kube-state-metrics` | 1 | Semak `kubectl -n monitoring get svc kube-state-metrics` (NodePort 30081) |
| `node-exporter` | 3 | Semak pod DaemonSet. `context deadline exceeded` = firewall/port 9100 |
| `kubernetes-cadvisor` | 3 | `401` = token salah; `403` = RBAC; `x509` = CA salah |
| `kubelet` | 3 | Sama seperti cadvisor |
| `kubernetes-pods` | = bilangan pod demo-app | Pod tiada anotasi `prometheus.io/scrape: "true"` |

Nama job dalam jadual ini bukan lalai Prometheus; semuanya ditulis sendiri dalam `prometheus.yml`. Penerangan lanjut dan cara menambah job anda sendiri: [Cara menulis scrape job sendiri](#cara-menulis-scrape-job-sendiri).

Cuba beberapa query di http://localhost:9090/query. Kotak ekspresi Prometheus menerima **satu query pada satu masa**. Salin dan jalankan setiap blok di bawah satu demi satu; jika beberapa query ditampal sekali gus, Prometheus memberi ralat seperti `parse error: unexpected number`.

**CPU setiap pod demo-app (cores)**

```promql
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="demo", container="app"}[1m]))
```

**Utilization yang HPA "nampak" (% penggunaan / requests)**

```promql
100 * sum(rate(container_cpu_usage_seconds_total{namespace="demo", container="app"}[1m]))
    / sum(kube_pod_container_resource_requests{namespace="demo", container="app", resource="cpu"})
```

**Replicas HPA**

```promql
kube_horizontalpodautoscaler_status_current_replicas{namespace="demo"}
```

**Memori tersedia setiap node (%)**

```promql
100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
```

**RPS demo-app mengikut kod HTTP**

```promql
sum by (code) (rate(demo_http_requests_total{path!~"/healthz|/readyz|/metrics"}[1m]))
```

## Makmal 3.3B: Tukar kepada Pilihan B dan bandingkan

Dalam bengkel, makmal ini dibuat selepas Pilihan A berjalan (Makmal 3.1 hingga 3.3), supaya anda boleh membandingkan kedua-dua cara pada kluster yang sama. Di hujung makmal, anda kembali ke Pilihan A kerana makmal seterusnya (dan Modul 5) bermula dari Pilihan A.

> **Terus guna Pilihan B (di luar bengkel)?** Boleh. Langkahnya hampir sama dengan Pilihan A: Makmal 3.1 (exporter) dan `kubectl apply -f k8s/03-prometheus-external-rbac.yaml` daripada Makmal 3.2 tetap dibuat, `get-k8s-credentials.sh` dilangkau, `docker compose up -d` dalam Makmal 3.3 tetap dibuat, kemudian terus ke Langkah 1 hingga 4 di bawah. Dalam Makmal 3.3, jadual target `UP` hanya untuk Pilihan A; untuk Pilihan B guna semakan dalam Langkah 4.

Ringkasan apa yang dijalankan di mana:

| Komponen | Pilihan A | Pilihan B |
|---|---|---|
| kube-state-metrics, node-exporter (Makmal 3.1) | Dalam kluster | Sama |
| ClusterRole `prometheus-external` (`k8s/03-prometheus-external-rbac.yaml`, Makmal 3.2) | Untuk token Prometheus luar | Masih di-`apply`, kerana Prometheus Agent guna semula ClusterRole ini |
| `get-k8s-credentials.sh` (token & CA) | Perlu | Tidak perlu |
| Prometheus Agent (`k8s/04-pilihan-b-prometheus-agent.yaml`) | Tiada | Dalam kluster, scrape dan `remote_write` |
| Prometheus, Alertmanager, Grafana, Mailpit | `docker compose up -d` | `docker compose up -d` yang sama |
| `external/prometheus/prometheus.yml` | 6 job scrape | Diganti dengan `prometheus-pilihan-b.yml` (job `prometheus` sahaja) |
| Peraturan alert, Alertmanager, dashboard Grafana | Tiada perubahan | Tiada perubahan (nama metrik dan label `job` sama) |

Penerima `remote_write` sudah dihidupkan dalam [`external/docker-compose.yml`](external/docker-compose.yml) melalui flag `--web.enable-remote-write-receiver`, jadi fail Compose tidak perlu diubah.

**Langkah 1: Hentikan Prometheus luar daripada scrape kluster.** Jika kedua-dua Prometheus luar dan agent mengumpul sasaran yang sama, setiap siri muncul dua kali dan dashboard menjumlahkan nilai berganda.

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
cp prometheus/prometheus.yml prometheus/prometheus.yml.asal
cp prometheus/prometheus-pilihan-b.yml prometheus/prometheus.yml
curl -X POST localhost:9090/-/reload
```

Buka http://localhost:9090/targets. Jangkaan: hanya job `prometheus`.

**Langkah 2: Cari alamat Prometheus luar yang boleh dicapai dari pod.** Container Prometheus disambung ke rangkaian Docker `k3d-lab`, sama seperti node k3d, jadi pod boleh capai IP container itu terus:

```bash
PROM_IP=$(docker inspect monitoring-luar-prometheus-1 -f '{{(index .NetworkSettings.Networks "k3d-lab").IPAddress}}')
echo $PROM_IP        # cth 172.18.0.6
```

**Langkah 3: Pasang Prometheus Agent** dengan `PROMETHEUS_LUAR` dalam manifest diganti oleh IP tadi:

```bash
cd ~/bengkel-k8s/modul-3-monitoring
kubectl apply -f k8s/03-prometheus-external-rbac.yaml      # jika Makmal 3.2 dilangkau
sed "s/PROMETHEUS_LUAR/$PROM_IP/" k8s/04-pilihan-b-prometheus-agent.yaml | kubectl apply -f -
kubectl -n monitoring rollout status deploy/prometheus-agent
kubectl -n monitoring logs deploy/prometheus-agent | grep -iE 'remote|error' | tail -5
```

**Langkah 4: Sahkan data tiba.** Halaman Targets Prometheus luar tidak menunjukkan sasaran agent, kerana Prometheus luar tidak scrape mereka. Semak dengan query di http://localhost:9090/query:

```promql
count by (job) (up{cluster="lab"})
```

Jangkaan: `kube-state-metrics` 1, `node-exporter` 3, `kubernetes-cadvisor` 3, `kubernetes-pods` = bilangan pod demo-app. Label `cluster="lab"` datang daripada `external_labels` agent. Dashboard Bengkel K8s di Grafana terus berfungsi tanpa perubahan. Untuk melihat sasaran dari sisi agent:

```bash
kubectl -n monitoring port-forward deploy/prometheus-agent 9091:9090
# buka http://localhost:9091/targets
```

| Masalah | Punca lazim | Penyelesaian |
|---|---|---|
| Log agent `connection refused` atau `context deadline exceeded` ke `/api/v1/write` | IP salah, atau container Prometheus dicipta semula dan IP berubah | Ulang Langkah 2 dan 3 |
| Log agent `404` ke `/api/v1/write` | Prometheus luar tanpa `--web.enable-remote-write-receiver` | Guna `docker-compose.yml` modul ini, kemudian `docker compose up -d` |
| Query memulangkan nilai berganda | Prometheus luar masih scrape kluster | Ulang Langkah 1, semak hanya job `prometheus` di Targets |
| Tiada `kubernetes-cadvisor` | RBAC `nodes/metrics` | `kubectl auth can-i get nodes/metrics --as=system:serviceaccount:monitoring:prometheus-agent` |

**Bandingkan (perbincangan 5 minit):** dari sisi rangkaian, Pilihan A perlukan Prometheus luar boleh capai API server dan node, manakala Pilihan B hanya perlukan kluster boleh capai Prometheus luar. Dari sisi operasi, Pilihan A tiada komponen tambahan dalam kluster dan halaman Targets terus menunjukkan kesihatan setiap sasaran, manakala Pilihan B menambah satu pod agent tetapi menahan data dalam WAL jika rangkaian putus.

Perbezaan tingkah laku alert: jika exporter mati, agent masih menghantar `up == 0` dan alert seperti Pilihan A berbunyi. Tetapi jika **agent sendiri** mati, tiada data langsung sampai, jadi alert perlu mengesan ketiadaan data, contohnya `absent(up{job="node-exporter", cluster="lab"})`. Di persekitaran sebenar, port `remote_write` Prometheus luar menerima trafik masuk dari kluster, jadi lindungi dengan TLS dan pengesahan (`basic_auth` atau token dalam blok `remote_write`).

Kembali ke Pilihan A sebelum Makmal 3.4:

```bash
kubectl delete -f k8s/04-pilihan-b-prometheus-agent.yaml
cd external
cp prometheus/prometheus.yml.asal prometheus/prometheus.yml
curl -X POST localhost:9090/-/reload
```

## Makmal 3.4: Dashboard Grafana

### A. Dashboard yang disediakan

Buka Grafana → **Dashboards → Bengkel K8s → Bengkel K8s: Kluster, Pod & HPA**. Dashboard ini diprovision dari [`external/grafana/dashboards/bengkel-k8s-hpa.json`](external/grafana/dashboards/bengkel-k8s-hpa.json) dan mengandungi:

| Baris | Panel |
|---|---|
| Kesihatan kluster | Node Ready / NotReady, pod tidak sihat, alert firing, CPU & memori node |
| Prestasi pod | CPU vs requests/limits, memori vs limits, CPU throttling %, restart, pod mengikut fasa |
| HPA | Replicas semasa/dikehendaki/min/max, utilization sebenar vs sasaran HPA |
| Aplikasi | RPS mengikut kod HTTP, RPS mengikut versi (untuk canary di Modul 4) |

Jalankan load test dari Modul 2 dan tonton dashboard:

```bash
k6 run ~/bengkel-k8s/modul-2-load-testing/k6/load.js
```

Perhatikan bagaimana garisan **CPU sebenar** melintasi **sasaran CPU**, kemudian **dikehendaki** naik, diikuti **semasa** beberapa saat kemudian. Itulah kelewatan HPA yang kita ukur di Modul 2, kini dalam bentuk visual.

### B. Bina panel sendiri

Sebelum mula, ingat semula [Cara mereka bentuk dashboard](#cara-mereka-bentuk-dashboard): panel ini menjawab soalan "berapa peratus request gagal?" (E dalam RED).

Latihan: tambah panel baharu **"Kadar ralat 5xx (%)"** pada baris Aplikasi.

1. Klik **Edit → Add → Visualization**.
2. Query:
   ```promql
   100 * sum(rate(demo_http_requests_total{namespace="$namespace", code=~"5.."}[$__rate_interval]))
       / sum(rate(demo_http_requests_total{namespace="$namespace"}[$__rate_interval]))
   ```
3. Unit: **Percent (0-100)**. Thresholds: hijau < 1, oren < 5, merah ≥ 5.
4. Simpan. Kemudian **Export → Export as JSON** dan simpan ke `grafana/dashboards/` supaya ia jadi kod (dashboard-as-code).

Latihan tambahan: panel **"Pod Pending vs desired HPA"** untuk mengesan bottleneck node penuh dari Modul 2.

### C. Dashboard komuniti (import)

**Dashboards → New → Import**, masukkan ID dari grafana.com dan pilih datasource `Prometheus`:

| ID | Dashboard |
|---|---|
| 1860 | Node Exporter Full |
| 15757 | Kubernetes / Views / Global |
| 15760 | Kubernetes / Views / Pods |

> Dashboard komuniti mungkin mengandaikan nama job atau label yang berbeza. Ia permulaan yang baik, tetapi dashboard sendiri yang menjawab soalan operasi **anda** lebih berguna.

## Makmal 3.5: Peraturan alert Prometheus + Alertmanager

Peraturan dalam [`external/prometheus/rules/kubernetes-alerts.yml`](external/prometheus/rules/kubernetes-alerts.yml):

| Alert | Severity | Syarat |
|---|---|---|
| `PodCrashLooping` | critical | > 3 restart dalam 10 minit |
| `PodNotReady` | warning | Pod Pending/Failed/Unknown > 5 minit |
| `ContainerOOMKilled` | warning | Restart terbaru disebabkan OOMKilled |
| `ContainerMemoryNearLimit` | warning | Memori > 90% limits selama 5 minit |
| `CPUThrottlingHigh` | warning | Throttled > 25% selama 10 minit |
| `DeploymentReplicasMismatch` | warning | Replicas available ≠ spec selama 10 minit |
| `HPAMaxedOut` | warning | HPA pada `maxReplicas` selama 5 minit |
| `HPAReplicasMismatch` | warning | Desired ≠ current selama 10 minit (quota / node penuh) |
| `NodeNotReady` | critical | Node tidak Ready > 2 minit |
| `NodeHighCPU`, `NodeMemoryHigh`, `NodeDiskAlmostFull` | warning/critical | Ambang sumber node |
| `TargetDown` | critical | Prometheus tidak dapat scrape sasaran |
| `DemoAppHighErrorRate` | critical | 5xx > 5% selama 2 minit |

Sahkan peraturan (sebelum deploy, sesuai untuk CI):

```bash
docker run --rm -v $PWD/prometheus:/p -w /p --entrypoint promtool prom/prometheus:v3.4.0 check rules rules/kubernetes-alerts.yml
docker run --rm -v $PWD/prometheus:/p -w /p --entrypoint promtool prom/prometheus:v3.4.0 test rules tests/alerts-test.yml
```

`tests/alerts-test.yml` ialah **unit test** untuk alert: ia memberi siri masa palsu dan menyemak alert firing pada masa yang betul. Latihan: tambah test untuk `NodeNotReady`.

Lihat alert di http://localhost:9090/alerts (keadaan: inactive → pending → firing).

### Penghalaan Alertmanager

[`external/alertmanager/alertmanager.yml`](external/alertmanager/alertmanager.yml):

```
semua alert          ─▶ email-pasukan (Mailpit)
severity="critical"  ─▶ slack-oncall + teams-oncall + email-pasukan
```

Uji tanpa menunggu alert sebenar:

```bash
docker compose exec alertmanager amtool alert add UjianAlert severity=warning namespace=demo \
  --annotation='summary="Ujian alert dari bengkel"' --alertmanager.url=http://localhost:9093
```

Dalam ~30 saat (`group_wait`), email `[FIRING:1] UjianAlert demo (warning)` muncul di http://localhost:8025.

Lihat laluan penghalaan bagi set label tertentu:

```bash
docker compose exec alertmanager amtool config routes test --config.file=/etc/alertmanager/alertmanager.yml severity=critical
```

Jangkaan: `slack-oncall,teams-oncall,email-pasukan`

## Makmal 3.6: Sambung Slack, Teams dan Email sebenar

### Slack

1. https://api.slack.com/apps → **Create New App → From scratch**.
2. **Incoming Webhooks → On → Add New Webhook to Workspace**, pilih channel.
3. Salin URL `https://hooks.slack.com/services/T000/B000/XXXX` dan gantikan `api_url` dalam `alertmanager.yml`.

### Microsoft Teams

Connector "Incoming Webhook" Office 365 yang lama sedang ditamatkan oleh Microsoft. Guna **Workflows**:

1. Dalam channel Teams: **⋯ → Workflows → "Post to a channel when a webhook request is received"**.
2. Salin URL workflow, gantikan `webhook_url` di bawah `msteamsv2_configs`.

### Email sebenar (contoh Office 365 / Gmail)

```yaml
global:
  smtp_smarthost: smtp.office365.com:587
  smtp_from: alerts@syarikat.com
  smtp_auth_username: alerts@syarikat.com
  smtp_auth_password_file: /etc/alertmanager/smtp-password   # jangan letak kata laluan terus dalam fail
  smtp_require_tls: true
```

Muat semula konfigurasi tanpa restart:

```bash
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
curl -X POST localhost:9093/-/reload
curl -X POST localhost:9090/-/reload     # untuk perubahan prometheus.yml / rules
```

### Alternatif: Grafana-managed alerting

Sesetengah pasukan lebih suka mengurus alert dalam Grafana. Stack ini sudah memprovision:

- Contact points: `email-pasukan`, `slack-oncall`, `teams-oncall` ([`contact-points.yml`](external/grafana/provisioning/alerting/contact-points.yml))
- Dua contoh alert rule ([`rules.yml`](external/grafana/provisioning/alerting/rules.yml)): `[Grafana] HPA pada maxReplicas` dan `[Grafana] Container restart berulang`

Lihat di Grafana → **Alerting → Alert rules**. Latihan: cipta alert rule baharu dari panel "CPU throttling (%)" (**panel menu → More → New alert rule**), ambang > 25 selama 5 minit, label `severity=warning`.

| | Prometheus + Alertmanager | Grafana alerting |
|---|---|---|
| Konfigurasi | Fail YAML (GitOps) | UI atau fail provisioning |
| Sumber data | Prometheus sahaja | Mana-mana datasource Grafana |
| Unit test | `promtool test rules` | Tiada setara |
| Pilih jika | Pasukan platform, banyak kluster | Pasukan kecil, perlu alert dari pelbagai sumber |

> Pilih **satu** sebagai sumber utama untuk setiap alert. Alert yang sama dari dua sistem = notifikasi berganda.

## Makmal 3.7: Cetuskan alert sebenar

| Alert sasaran | Cara cetuskan |
|---|---|
| `HPAMaxedOut` | `k6 run ~/bengkel-k8s/modul-2-load-testing/k6/stress.js` (tunggu 5 minit pada max) |
| `CPUThrottlingHigh` | Stress test yang sama, tunggu 10 minit |
| `ContainerOOMKilled` | `curl "localhost:30080/mem?mb=300&hold=60"` |
| `PodCrashLooping` | `for i in 1 2 3 4 5; do curl -s localhost:30080/crash; sleep 20; done` |
| `HPAReplicasMismatch` | `kubectl apply -f ~/bengkel-k8s/modul-2-load-testing/quota-ketat.yaml` + load test |
| `TargetDown` | `kubectl -n monitoring scale deploy kube-state-metrics --replicas=0` |

Untuk setiap satu, catat: masa kejadian, masa alert `pending`, masa `firing`, masa notifikasi tiba. Bincang: adakah `for:` terlalu pendek (bising) atau terlalu panjang (lambat)?

Pulihkan selepas makmal:

```bash
kubectl -n monitoring scale deploy kube-state-metrics --replicas=1
kubectl apply -f ~/bengkel-k8s/modul-1-hpa/05-resourcequota.yaml
```

## Cara menulis scrape job sendiri

> Bacaan rujukan, di luar jadual teras. Sesuai dibaca selepas Makmal 3.3 atau selepas bengkel, apabila anda mahu Prometheus mengumpul metrik daripada aplikasi atau servis baharu.

### Nama job ialah label yang kita tulis sendiri

Prometheus tidak datang dengan job `kube-state-metrics`, `node-exporter` atau `kubelet`. Selepas dipasang, Prometheus tidak tahu apa-apa tentang kluster anda. Setiap nama dalam jadual Targets di Makmal 3.3 datang daripada baris `job_name:` yang ditulis dalam [`external/prometheus/prometheus.yml`](external/prometheus/prometheus.yml), dan nama itu menjadi label `job` pada setiap siri metrik (`up{job="node-exporter"}`). Anda boleh menamakannya apa sahaja, asalkan unik dalam fail.

Job dan exporter ialah dua perkara berbeza:

| Job dalam `prometheus.yml` | Siapa yang mendedahkan metrik | Dipasang oleh |
|---|---|---|
| `prometheus` | Prometheus sendiri, `localhost:9090/metrics` | `docker compose` (Makmal 3.3) |
| `kube-state-metrics` | Pod kube-state-metrics, NodePort 30081 | [`k8s/01-kube-state-metrics.yaml`](k8s/01-kube-state-metrics.yaml) (Makmal 3.1) |
| `node-exporter` | DaemonSet node-exporter, `<IP-node>:9100` | [`k8s/02-node-exporter.yaml`](k8s/02-node-exporter.yaml) (Makmal 3.1) |
| `kubernetes-cadvisor`, `kubelet` | kubelet pada setiap node (terbina dalam k3s), melalui API server proxy | Sudah ada dalam kluster |
| `kubernetes-pods` | Pod aplikasi yang ada anotasi `prometheus.io/scrape: "true"` (demo-app) | Deployment aplikasi anda (Modul 1) |

Jika exporter tidak dipasang, job tetap wujud tetapi targetnya `DOWN`. Jika exporter dipasang tetapi tiada job, metriknya tidak pernah dikumpul.

### Tiga perkara yang perlu tahu sebelum menulis job

1. **Di mana target mendedahkan metrik.** Alamat (hostname atau IP), port, dan path, biasanya `/metrics`. Uji dahulu dari tempat Prometheus berjalan: `curl http://<alamat>:<port>/metrics` mesti memulangkan teks seperti `nama_metrik{label="x"} 123`. Jika curl gagal, Prometheus juga akan gagal.
2. **Sintaks `scrape_configs`.** Setiap job ialah satu item senarai di bawah `scrape_configs:`, sekurang-kurangnya dengan `job_name` dan satu cara mencari target. Medan pilihan yang lazim: `metrics_path` (lalai `/metrics`), `scheme` (lalai `http`), `scrape_interval` (lalai ikut `global`), `authorization` dan `tls_config`.
3. **Cara mencari target.** `static_configs` untuk senarai alamat tetap, atau service discovery seperti `kubernetes_sd_configs` untuk target yang berubah (pod datang dan pergi). Service discovery hampir selalu digandingkan dengan `relabel_configs`.

### Contoh: job kecil dengan `static_configs`

Alertmanager dan Grafana dalam stack Makmal 3.3 juga mendedahkan `/metrics`, tetapi `prometheus.yml` belum scrape kedua-duanya. Tambah job ini di hujung `scrape_configs:` (perhatikan inden dua ruang, sama dengan job lain):

```yaml
  # Job sendiri: metrik Alertmanager (bilangan notifikasi dihantar, gagal, dll.)
  - job_name: alertmanager
    static_configs:
      - targets: ["alertmanager:9093"]
        labels:
          peranan: monitoring       # label tambahan pada setiap siri daripada target ini
```

`alertmanager:9093` ialah nama servis dalam `docker-compose.yml`; Prometheus dan Alertmanager berkongsi rangkaian Docker `monitoring`, jadi nama itu boleh diselesaikan. Dari laptop anda, alamat yang sama ialah `localhost:9093`.

### Semak sebelum dan selepas reload

Semak sintaks dengan `promtool`, yang sudah ada dalam image `prom/prometheus`:

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

Jangkaan:

```
Checking /etc/prometheus/prometheus.yml
  SUCCESS: 1 rule files found
 SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

Jalankan `promtool` di dalam container, bukan pada fail di laptop: `prometheus.yml` merujuk laluan dalam container seperti `/etc/prometheus/k8s/token`, dan `promtool` gagal jika fail itu tiada pada laluan tersebut. Contoh ralat yang lazim:

| Mesej `promtool` | Punca |
|---|---|
| `cannot unmarshal !!str ... into []string` | `targets: alertmanager:9093` tanpa kurungan `[...]`; `targets` mesti senarai |
| `found multiple scrape configs with job name "alertmanager"` | Dua job dengan `job_name` yang sama |
| `error checking authorization credentials ... no such file or directory` | `promtool` dijalankan di luar container, atau token belum dijana |
| `yaml: line N: did not find expected key` | Inden salah (tab, atau bilangan ruang tidak sepadan) |

Jika lulus, muat semula konfigurasi tanpa restart (flag `--web.enable-lifecycle` sudah ada dalam `docker-compose.yml`):

```bash
curl -X POST localhost:9090/-/reload
docker compose logs prometheus --tail=5     # cari "Completed loading of configuration file"
```

Kemudian sahkan di UI Prometheus:

- **Status → Targets** (http://localhost:9090/targets): job `alertmanager` muncul dengan 1 target `UP`. Jika `DOWN`, lajur Error menunjukkan sebabnya (`connection refused`, `404`, `context deadline exceeded`).
- **Status → Service Discovery** (http://localhost:9090/service-discovery): untuk job yang guna service discovery, halaman ini menunjukkan label asal setiap target sebelum relabel (`__meta_kubernetes_*`) dan target yang dibuang oleh `relabel_configs`. Inilah tempat pertama untuk dilihat apabila job Kubernetes "hilang" target.
- Query `up{job="alertmanager"}` memulangkan `1`, dan `alertmanager_notifications_total` memaparkan data.

Latihan: tambah job `grafana` untuk `grafana:3000` dengan cara yang sama, kemudian semak di Targets.

### Pengenalan `kubernetes_sd_configs` dan `relabel_configs`

`static_configs` tidak sesuai untuk pod kerana IP dan bilangannya berubah setiap kali scale atau rolling update. `kubernetes_sd_configs` bertanya kepada API server senarai objek (`role: node`, `pod`, `service`, `endpoints`, `ingress`) dan menjadikan setiap satu target. Setiap target membawa label meta seperti `__meta_kubernetes_namespace`, `__meta_kubernetes_pod_name` dan setiap anotasi pod (`__meta_kubernetes_pod_annotation_prometheus_io_scrape`).

`relabel_configs` dijalankan pada setiap target **sebelum** scrape, mengikut susunan. Tindakan yang paling kerap:

| `action` | Kegunaan | Contoh dalam `prometheus.yml` |
|---|---|---|
| `keep` | Simpan target yang label sumbernya padan dengan `regex`, buang yang lain | Job `kubernetes-pods`: hanya pod dengan anotasi `prometheus.io/scrape: "true"` dan fasa `Running` |
| `drop` | Sebaliknya: buang target yang padan | |
| `replace` (lalai) | Tulis nilai baharu ke `target_label` | Job `node-exporter`: tukar port alamat kepada `9100`; salin `__meta_kubernetes_node_name` ke label `node` |

Label yang bermula dengan `__` dibuang selepas relabel, jadi apa-apa yang mahu dikekalkan (namespace, nama pod) mesti disalin ke label biasa, seperti yang dibuat oleh job `kubernetes-pods`. Tiga label khas mengawal scrape itu sendiri: `__address__` (host:port), `__metrics_path__` dan `__scheme__`.

Untuk aplikasi baharu dalam kluster, anda biasanya **tidak perlu menulis job baharu**: tambah anotasi `prometheus.io/scrape`, `prometheus.io/port` dan `prometheus.io/path` pada template pod (lihat [`02-deployment.yaml`](../modul-1-hpa/02-deployment.yaml) Modul 1), dan job `kubernetes-pods` yang sedia ada akan menjumpainya. Anotasi ini hanya konvensyen yang dibaca oleh `relabel_configs` kita, bukan ciri terbina dalam Prometheus.

### Adakah ada alat web untuk menjana `prometheus.yml`?

Setahu kami tiada penjana web rasmi daripada projek Prometheus. Rujukan utama ialah [halaman konfigurasi](https://prometheus.io/docs/prometheus/latest/configuration/configuration/), yang menyenaraikan setiap medan dan nilai lalainya. Dalam amalan, yang paling membantu ialah:

- `promtool check config` untuk sintaks, sebelum setiap reload.
- Halaman **Targets** dan **Service Discovery** untuk melihat hasil sebenar.
- Contoh dalam dokumentasi setiap exporter, yang biasanya menyertakan job sedia guna.

Di produksi, ramai pasukan tidak menulis `prometheus.yml` dengan tangan langsung. Carta Helm **kube-prometheus-stack** memasang Prometheus Operator dalam kluster, dan target ditakrifkan sebagai objek Kubernetes `ServiceMonitor` (pilih Service dengan label) atau `PodMonitor` (pilih pod terus). Operator menjana konfigurasi scrape dan `relabel_configs` daripada objek itu. Bengkel ini kekal dengan fail tangan kerana Prometheus kita berada di luar kluster dan kerana fail tangan menunjukkan apa yang sebenarnya berlaku di bawah objek-objek tersebut.

## Semakan akhir modul

- [ ] Semua target di http://localhost:9090/targets `UP` (Pilihan B: `count by (job) (up{cluster="lab"})` memaparkan 4 job)
- [ ] Dashboard Bengkel K8s memaparkan data untuk semua baris
- [ ] Peserta menambah sekurang-kurangnya satu panel sendiri dan mengeksport JSON
- [ ] Email ujian diterima di Mailpit; laluan critical diuji dengan `amtool config routes test`
- [ ] Sekurang-kurangnya 2 alert sebenar dicetuskan dan diterima

Biarkan stack monitoring berjalan. Modul 4 menggunakannya untuk memerhati rolling update dan canary.

### Hentikan dan hidupkan semula stack monitoring

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
docker compose stop          # hentikan sementara (data kekal)
docker compose start         # hidupkan semula
docker compose down          # buang container, volume data Prometheus/Grafana kekal
docker compose down -v       # buang semua termasuk data (selepas bengkel tamat)
```

Jika kluster `lab` dicipta semula, jalankan `bash get-k8s-credentials.sh` sekali lagi (token dan CA baharu), kemudian `docker compose restart prometheus`.

## Rujukan

- kube-state-metrics: https://github.com/kubernetes/kube-state-metrics/tree/main/docs
- node-exporter: https://github.com/prometheus/node_exporter
- Prometheus kubernetes_sd_config: https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config
- Alertmanager configuration: https://prometheus.io/docs/alerting/latest/configuration/
- Prometheus agent mode: https://prometheus.io/docs/prometheus/latest/feature_flags/#prometheus-agent
- OpenTelemetry: https://opentelemetry.io/docs/what-is-opentelemetry/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- Grafana alerting provisioning: https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/
