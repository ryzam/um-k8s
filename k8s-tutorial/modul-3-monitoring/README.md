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
| 9:00 – 9:30 | Teori: jenis metrik K8s, seni bina monitoring luaran, Pilihan A vs B |
| 9:30 – 10:15 | Makmal 3.1 & 3.2: pasang exporter, RBAC untuk Prometheus luar |
| 10:15 – 10:45 | Makmal 3.3: naikkan stack luar, sahkan semua target `UP` |
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

Kenapa melalui **API server proxy** untuk cAdvisor dan pod? Kerana IP pod (`10.42.x.x` dalam k3s) tidak boleh dicapai dari luar kluster, dan port kubelet 10250 biasanya ditutup. API server biasanya sudah boleh dicapai, dan akses dikawal oleh RBAC.

### Pilihan B: Prometheus Agent dalam kluster + remote_write

Bila Prometheus luar **tidak boleh** capai kluster langsung (firewall hanya benarkan trafik keluar), jalankan Prometheus dalam *agent mode* di dalam kluster dan `remote_write` ke Prometheus luar. Manifest: [`k8s/04-pilihan-b-prometheus-agent.yaml`](k8s/04-pilihan-b-prometheus-agent.yaml). Grafana Alloy dan OpenTelemetry Collector ialah alternatif lain untuk peranan yang sama; [Modul 5 (pilihan)](../modul-5-opentelemetry/README.md) menunjukkan Pilihan B dengan OpenTelemetry Collector.

| | Pilihan A: scrape dari luar | Pilihan B: agent + remote_write |
|---|---|---|
| Arah rangkaian | Luar → kluster | Kluster → luar |
| Komponen dalam kluster | Exporter sahaja | Exporter + agent |
| Jika rangkaian putus | Data hilang semasa putus | Agent simpan WAL dan hantar semula |
| Sesuai untuk | Makmal, rangkaian dalaman rata | Banyak kluster, cloud, kluster di belakang NAT |

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
cd external
./get-k8s-credentials.sh
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

```bash
docker compose up -d
docker compose ps
```

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

Cuba beberapa query di http://localhost:9090/query:

```promql
# CPU setiap pod demo-app (cores)
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="demo", container="app"}[1m]))

# Utilization yang HPA "nampak": penggunaan / requests
100 * sum(rate(container_cpu_usage_seconds_total{namespace="demo", container="app"}[1m]))
    / sum(kube_pod_container_resource_requests{namespace="demo", resource="cpu"})

# Replicas HPA
kube_horizontalpodautoscaler_status_current_replicas{namespace="demo"}

# Memori tersedia setiap node (%)
100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes

# RPS demo-app mengikut kod HTTP
sum by (code) (rate(demo_http_requests_total{path!~"/healthz|/readyz|/metrics"}[1m]))
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

## Semakan akhir modul

- [ ] Semua target di http://localhost:9090/targets `UP`
- [ ] Dashboard Bengkel K8s memaparkan data untuk semua baris
- [ ] Peserta menambah sekurang-kurangnya satu panel sendiri dan mengeksport JSON
- [ ] Email ujian diterima di Mailpit; laluan critical diuji dengan `amtool config routes test`
- [ ] Sekurang-kurangnya 2 alert sebenar dicetuskan dan diterima

Biarkan stack monitoring berjalan. Modul 4 menggunakannya untuk memerhati rolling update dan canary.

## Rujukan

- kube-state-metrics: https://github.com/kubernetes/kube-state-metrics/tree/main/docs
- node-exporter: https://github.com/prometheus/node_exporter
- Prometheus kubernetes_sd_config: https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config
- Alertmanager configuration: https://prometheus.io/docs/alerting/latest/configuration/
- Prometheus agent mode: https://prometheus.io/docs/prometheus/latest/feature_flags/#prometheus-agent
- OpenTelemetry: https://opentelemetry.io/docs/what-is-opentelemetry/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- Grafana alerting provisioning: https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/
