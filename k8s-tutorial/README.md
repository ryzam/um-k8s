# Bengkel Hands-on: Kubernetes Autoscaling, Monitoring & Day-2 Operations (2 Hari)

Tutorial makmal untuk bengkel 2 hari. Setiap modul ada nota teori ringkas, makmal langkah demi langkah dengan output jangkaan, cabaran, dan senarai semak. Semua makmal berjalan pada laptop (kluster **k3d**, iaitu k3s dalam Docker); Prometheus, Grafana dan storan log berjalan **di luar kluster** dengan Docker Compose, meniru pelayan monitoring sebenar.

## Trainer

**Irwan Azam Ahmad** mempunyai 8 tahun pengalaman dalam DevOps dan Kubernetes. Beliau juga berpengalaman dalam pembangunan perisian sebagai solution architect, dan terkini membangunkan tools AI collaborative framework.

## Silibus

| Hari | Sesi | Modul | Topik |
|---|---|---|---|
| 1 | 9:00 – 1:00 | [Modul 1: Workload Autoscaling & HPA](modul-1-hpa/README.md) | requests/limits, QoS, LimitRange, ResourceQuota, Metrics Server, HPA v2 CPU + memori, `behavior` |
| 1 | 2:00 – 5:00 | [Modul 2: Load & Stress Testing](modul-2-load-testing/README.md) | k6 (smoke, load, stress, spike), Locust, rakaman garis masa HPA, memburu bottleneck |
| 2 | 9:00 – 1:00 | [Modul 3: Monitoring luaran](modul-3-monitoring/README.md) | kube-state-metrics, node-exporter, Prometheus & Grafana luar kluster, dashboard, alert ke Email/Slack/Teams |
| 2 | 2:00 – 5:00 | [Modul 4: Day-2 Operations](modul-4-operations/README.md) | Rolling update tanpa downtime, blue-green, canary, eviction & PDB, log shipping, troubleshooting |
| Pilihan | ~3 jam | [Modul 5 (pilihan): OpenTelemetry](modul-5-opentelemetry/README.md) | Di luar jadual 2 hari. Collector DaemonSet menggantikan Prometheus Agent (Pilihan B), tracing dua servis ke Tempo, bila pilih OTel berbanding setup sekarang |
| Pilihan | ~2.5 jam | [Modul 6 (pilihan): KEDA](modul-6-keda/README.md) | Di luar jadual 2 hari. KEDA mencipta HPA di belakang tabir: skala berdasarkan RPS daripada Prometheus luar, perbandingan dengan HPA CPU, `fallback`, cron dan scale-to-zero, bila pilih KEDA |

Mula di sini: **[00-persediaan/README.md](00-persediaan/README.md)** (pasang alat untuk semua peserta). Baru pertama kali guna Docker? Bahagian **Pasang semua alat** di halaman itu memberi langkah untuk Windows (WSL2), macOS dan Linux. Kemudian ikut halaman persediaan **satu** opsyen sahaja.

Dua opsyen persediaan disediakan, dan kedua-duanya menggunakan modul yang sama:

- **Opsyen A: k3d sahaja.** Satu kluster k3d `lab`, kubectl terus ke API server. Lihat **[Persediaan Opsyen A](00-persediaan/opsyen-a/README.md)**.
- **Opsyen B: k3d + Rancher.** Kluster `lab` yang sama diurus oleh Rancher management server yang dipasang dengan Helm, sama ada pada kluster k3d kedua (berasingan, cadangan) atau terus dalam kluster `lab` (sekali, untuk laptop dengan RAM terhad). kubectl boleh melalui Rancher. Lihat **[Persediaan Opsyen B](00-persediaan/rancher/README.md)**.

## Seni bina makmal

```
┌──────────────────────────── Laptop peserta ─────────────────────────────────────────────┐
│                                                                                          │
│  ┌──────────── Kluster k3d "lab" (Docker) ──────────────┐   ┌──── Luar kluster ────────┐ │
│  │  server-0        agent-0   agent-1                    │   │  (docker compose)        │ │
│  │                                                       │   │                          │ │
│  │  ns demo:       demo-app + HPA + PDB  ◀── k6 / Locust │   │  Prometheus ── Grafana   │ │
│  │  ns kube-system: Metrics Server                       │──▶│  Alertmanager ─▶ Email/  │ │
│  │  ns monitoring: kube-state-metrics, node-exporter     │   │     Slack/Teams          │ │
│  │  ns logging:    Fluent Bit ───────────────────────────┼──▶│  Loki, S3 (SeaweedFS)    │ │
│  └───────────────────────────────────────────────────────┘   └──────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Struktur folder

```
bengkel-k8s/
├── 00-persediaan/            Pasang alat; k3d-cluster.yaml, namespace, app demo (app.py + ConfigMap)
│   ├── opsyen-a/             Opsyen A: langkah persediaan k3d sahaja
│   └── rancher/              Opsyen B: k3d-rancher.yaml, k3d-lab-rancher.yaml, rancher-values.yaml, hostname-rancher.sh
├── modul-1-hpa/              Deployment, Service, LimitRange, ResourceQuota, HPA CPU & CPU+memori, patch Metrics Server
├── modul-2-load-testing/
│   ├── k6/                   smoke.js, load.js, stress.js, spike.js, k6-job.yaml (k6 dalam kluster)
│   ├── locust/               locustfile.py, stepload.py
│   ├── watch-hpa.sh          rakam garis masa HPA ke CSV
│   └── quota-ketat.yaml, deployment-requests-besar.yaml   (makmal bottleneck)
├── modul-3-monitoring/
│   ├── k8s/                  kube-state-metrics, node-exporter, RBAC Prometheus luar, (Pilihan B) Prometheus Agent
│   └── external/             docker-compose.yml, prometheus.yml, alert rules + unit test, alertmanager.yml,
│                             Grafana provisioning (datasource, dashboard JSON, contact points, alert rules)
├── modul-4-operations/
│   ├── rolling-update/       Deployment production-ready, PDB, zero-downtime.js
│   ├── blue-green/           blue, green, Service, switch.sh
│   ├── canary/               stable, canary, Service, canary-traffic.sh, rujukan Gateway API
│   ├── eviction/             ephemeral-storage eviction, PriorityClass, demo preemption
│   ├── logging/              Fluent Bit DaemonSet (k8s/), Loki + S3 luar (external/)
│   └── troubleshooting/      7 kes kegagalan + jawapan dalam README
├── modul-5-opentelemetry/    (pilihan)
│   ├── app/                  app_otel.py (kedai + inventori, SDK OTel), ConfigMap, Dockerfile
│   ├── k8s/                  OpenTelemetry Collector DaemonSet + RBAC, Deployment kedai & inventori
│   └── external/             Tempo (docker compose)
└── modul-6-keda/             (pilihan)
    ├── helm/                 keda-values.yaml (nilai Helm untuk makmal)
    └── k8s/                  ScaledObject Prometheus (RPS) untuk demo-app, Deployment laporan + ScaledObject cron
```

## Versi komponen

| Komponen | Versi |
|---|---|
| Kubernetes (k3s dalam k3d) | v1.33.1+k3s1 (k3d v5.8.3) |
| Metrics Server | v0.7.2 |
| kube-state-metrics | v2.15.0 |
| node-exporter | v1.9.1 |
| Prometheus / Alertmanager | v3.4.0 / v0.28.1 |
| Grafana | 12.0.0 |
| k6 / Locust | v1.0.0 / 2.37.0 |
| Fluent Bit / Loki | 4.0.3 / 3.5.0 |
| Rancher / cert-manager (Opsyen B) | v2.13.10 / v1.19.6 |
| OpenTelemetry Collector contrib / Tempo (Modul 5, pilihan) | 0.163.1 / 3.1.0 |
| KEDA (Modul 6, pilihan) | 2.20.2 |

## Apa yang telah diuji

Semua manifest Kubernetes disahkan dengan `kubeconform` terhadap skema Kubernetes 1.33. Selain itu, perkara berikut telah dijalankan dan disahkan berfungsi dalam Docker:

- App demo: semua endpoint, graceful shutdown SIGTERM, OOMKilled (exit 137) untuk Kes 3 troubleshooting
- Skrip k6 (smoke, load) dan Locust (biasa + step load) terhadap app demo
- `promtool check config`, `promtool check rules`, dan unit test alert (`promtool test rules`): lulus
- `amtool check-config` dan ujian penghalaan (critical → Slack + Teams + Email)
- Stack luar Modul 3: Grafana memprovision datasource, dashboard, contact points dan alert rules tanpa ralat; alert ujian sampai ke peti email Mailpit
- Fluent Bit: konfigurasi lulus `--dry-run`; log berjaya dihantar ke Loki (boleh di-query) dan dimuat naik ke bucket S3; penapis log `/healthz` berfungsi

Ujian dengan kluster k3d sebenar (k3d v5.8.3, k3s v1.33.1) dalam persekitaran penyediaan:

- `k3d cluster create --config k3d-cluster.yaml` berjaya: 3 node `Ready`, taint control-plane pada `k3d-lab-server-0`, context `k3d-lab`, API server pada `127.0.0.1:6550`, NodePort 30080 hingga 30082 dipetakan
- Semua manifest modul diterima oleh API server k3s (`kubectl apply --dry-run=server`), patch Metrics Server dan RBAC Prometheus (`kubectl auth can-i`) berfungsi
- Sijil API server sah untuk nama `k3d-lab-server-0` dari rangkaian Docker `k3d-lab`; token ServiceAccount boleh membaca cAdvisor melalui proxy API server
- Prometheus luar (docker compose, rangkaian `k3d-lab`) menemui 3 node melalui `kubernetes_sd_configs`; job `kubelet` dan `kubernetes-cadvisor` `UP`
- Nama container Docker pada rangkaian `k3d-lab` (cth: `loki`, `s3`) boleh diselesaikan dari node k3d melalui resolver yang juga digunakan oleh CoreDNS, jadi Fluent Bit sepatutnya boleh mencapainya (resolusi dari dalam pod belum diuji)
- `k3d image import` dan `k3d-rancher.yaml` (kluster kedua, port 443) berjaya
- `k3d-lab-rancher.yaml` (Opsyen B cara sekali) berjaya: 3 node `Ready` dengan nama yang sama, `0.0.0.0:443` pada `k3d-lab-serverlb`, Metrics Server terbina dalam tidak dipasang, dan job `helm-install-traefik` dicipta (Traefik sendiri tidak dapat berjalan di sini, lihat di bawah)

Yang **belum** dapat diuji: persekitaran penyediaan tidak membenarkan container bersarang berjalan di dalam node k3d, jadi tiada pod yang benar-benar berjalan. Ini bermakna HPA scaling, drain, eviction, rolling update hidup, kube-state-metrics, node-exporter, Fluent Bit dalam kluster, dan **keseluruhan Opsyen B, kedua-dua cara (pemasangan Rancher, import kluster, kubeconfig Rancher, dan Traefik berjalan sebagai ingress dalam `lab`)** belum dicuba sebenar. Langkah-langkah ini mengikut tingkah laku yang didokumenkan; jalankan sekali secara penuh sebelum bengkel (dry-run oleh fasilitator) untuk melaraskan nombor seperti bilangan replicas mengikut CPU laptop.

Modul 5 dan Modul 6 (pilihan) mempunyai senarai ujian masing-masing di bahagian **Apa yang telah diuji** dalam README [Modul 5](modul-5-opentelemetry/README.md) dan [Modul 6](modul-6-keda/README.md).

## Nota untuk fasilitator

- Masa makmal dianggarkan untuk 15–25 peserta dengan seorang pembantu. Bahagian "cabaran" dan "eksperimen" boleh dilangkau jika kelas ketinggalan.
- Nombor dalam output jangkaan (bilangan replicas, masa reaksi HPA, latency) bergantung pada CPU laptop. Tekankan **corak**, bukan nilai tepat.
- Laptop dengan 4 core mungkin perlu kurangkan beban: `k6 run -e CPU_MS=10 load.js` atau kurangkan `target` VU dalam `stages`.
- Pra-muat image (Persediaan Opsyen A Langkah A2, atau Opsyen B Langkah B3/S3) menjimatkan banyak masa jika Wi-Fi tempat bengkel perlahan.
