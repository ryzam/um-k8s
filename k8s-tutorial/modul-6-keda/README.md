# Modul 6 (Pilihan): KEDA, Autoscaling Berasaskan Event di Atas HPA

**Modul pilihan, di luar jadual teras 2 hari.** Anggaran 2.5 jam sebagai makmal penuh, atau 45 minit sebagai demo fasilitator (Makmal 6.3 dan 6.5 sahaja). Sesuai untuk hari ketiga, sesi susulan, atau peserta yang selesai awal.

> **Opsyen A dan Opsyen B:** langkah sama untuk kedua-dua opsyen. KEDA dipasang terus dalam kluster `lab` dengan Helm, menggunakan context kubectl yang sama seperti modul lain, dan bertanya terus kepada Prometheus luar (bukan melalui Rancher). Untuk Opsyen B cara sekali (Rancher dalam `lab`), KEDA menambah 3 pod kecil (sekitar 160 Mi memori `requests` semuanya); tutup Rancher UI jika laptop kekurangan RAM. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Faham bahawa **KEDA tidak menggantikan HPA**: ia mencipta HPA di belakang tabir dan menyuapnya dengan metrik luar, menyambung terus dengan [Modul 1](../modul-1-hpa/README.md).
2. Pasang **KEDA** dengan Helm.
3. Skala `demo-app` berdasarkan **kadar request daripada Prometheus luar** [Modul 3](../modul-3-monitoring/README.md), ulang ujian k6 [Modul 2](../modul-2-load-testing/README.md), dan bandingkan dengan HPA CPU.
4. Lihat apa yang berlaku bila Prometheus mati (`fallback`).
5. Gunakan trigger **cron** untuk **scale-to-zero**, dan faham kenapa scale-to-zero tidak sesuai untuk setiap aplikasi.
6. Tahu bila memilih KEDA dan bila HPA biasa sudah memadai.

> Prasyarat: Modul 1 dan 2 selesai. Stack luar Modul 3 berjalan dalam **Pilihan A** (`docker compose ps` dalam `modul-3-monitoring/external`, dan job `kubernetes-pods` `UP` di http://localhost:9090/targets). Jika anda baru selesai Modul 5, pulihkan Pilihan A dahulu (bahagian Pembersihan Modul 5). Helm v3.18.6 dipasang (lihat [Pasang semua alat](../00-persediaan/README.md); Helm ditanda "B sahaja" di situ, tetapi modul ini memerlukannya untuk kedua-dua opsyen).

## Jadual (cadangan)

| Masa | Aktiviti |
|---|---|
| 0:00 – 0:25 | Teori: KEDA di atas HPA, komponen, ScaledObject, bila pilih KEDA |
| 0:25 – 0:45 | Makmal 6.1 & 6.2: pasang KEDA, sahkan query di Prometheus |
| 0:45 – 1:30 | Makmal 6.3: ganti HPA CPU dengan ScaledObject, ulang load test k6, bandingkan |
| 1:30 – 1:40 | Rehat |
| 1:40 – 1:55 | Makmal 6.4: Prometheus mati, `fallback` |
| 1:55 – 2:30 | Makmal 6.5: cron dan scale-to-zero; perbincangan |

---

## Teori ringkas

### KEDA dibina di atas HPA

Dalam Modul 1, HPA membaca CPU dan memori daripada **Metrics Server** (`metrics.k8s.io`). HPA juga boleh membaca metrik **External** (`external.metrics.k8s.io`), tetapi Kubernetes tidak menyediakan sumber metrik itu sendiri. **KEDA** (Kubernetes Event-driven Autoscaling, projek CNCF *graduated*) mengisi jurang itu:

```
                      ┌────────────────────────── Kluster k3d "lab" ──────────────────────────┐
                      │                                                                        │
 ┌─ Luar kluster ─┐   │  ns keda:                                    ns demo:                  │
 │                │   │  ┌───────────────┐  cipta/urus  ┌───────────────────┐  scale 1..N      │
 │  Prometheus ◀──┼───┼──│ keda-operator │ ───────────▶ │ HPA               │ ──────────┐      │
 │  (Modul 3)     │   │  └───────┬───────┘              │ keda-hpa-demo-app │           ▼      │
 │                │   │          │ scale 0 <-> 1        └─────────┬─────────┘   ┌────────────┐ │
 └────────────────┘   │          └──────────────────────────────────────────▶ │ demo-app   │ │
                      │  ┌──────────────────────┐ external.metrics │         └────────────┘ │
                      │  │ keda-operator-       │ ◀────────────────┘                        │
                      │  │ metrics-apiserver    │  (HPA tanya nilai "s0-prometheus")        │
                      │  └──────────────────────┘                                            │
                      └────────────────────────────────────────────────────────────────────┘
```

Jadi apa yang anda pelajari dalam Modul 1 masih berlaku sepenuhnya: formula `desiredReplicas`, toleransi 10%, `behavior`, `stabilizationWindowSeconds`. KEDA hanya menukar **dari mana metrik datang**, dan menambah satu keupayaan yang HPA tiada: **turun ke 0 dan naik semula dari 0**.

| Komponen KEDA | Fungsi |
|---|---|
| `keda-operator` | Memantau `ScaledObject`, mencipta HPA `keda-hpa-<nama>`, bertanya kepada sumber event (Prometheus, cron, baris gilir, ...) setiap `pollingInterval`, dan melakukan sendiri langkah **0 ↔ 1** |
| `keda-operator-metrics-apiserver` | Mendaftar `v1beta1.external.metrics.k8s.io`. HPA bertanya kepadanya setiap 15 saat untuk nilai metrik bagi langkah **1 ↔ N** |
| `keda-admission-webhooks` | Menolak konfigurasi salah, contohnya `ScaledObject` untuk Deployment yang sudah ada HPA lain |

### Dari HPA ke ScaledObject

| HPA (Modul 1) | ScaledObject (modul ini) | Nota |
|---|---|---|
| `scaleTargetRef` | `scaleTargetRef` | Sama |
| `minReplicas` (≥ 1) | `minReplicaCount` (boleh 0) | 0 = scale-to-zero |
| `maxReplicas` | `maxReplicaCount` | Sama |
| `metrics:` (Resource cpu/memory) | `triggers:` (lebih 70 jenis scaler) | `cpu` dan `memory` juga ada sebagai trigger KEDA |
| `behavior` | `advanced.horizontalPodAutoscalerConfig.behavior` | Disalin terus ke HPA yang dicipta |
| (tiada) | `pollingInterval`, `cooldownPeriod` | Untuk langkah 0 ↔ 1 sahaja |
| (tiada) | `fallback` | Bilangan replicas bila sumber metrik gagal |

Fail: [`k8s/01-scaledobject-prometheus.yaml`](k8s/01-scaledobject-prometheus.yaml). Untuk trigger `prometheus` dengan `metricType: AverageValue` (default):

```
desiredReplicas = ceil( nilai query / threshold )
contoh: sum(rate(...)) = 19 RPS, threshold 5  ->  ceil(19 / 5) = 4 pod
```

Query **mesti** mengembalikan satu nilai sahaja (guna `sum(...)`). Jika ia mengembalikan beberapa siri, KEDA menganggapnya ralat.

### Dua gelung masa

| Langkah | Siapa | Kekerapan |
|---|---|---|
| 0 → 1 dan 1 → 0 | `keda-operator` | `pollingInterval` (15 s); turun ke 0 hanya selepas `cooldownPeriod` tidak aktif |
| 1 → N dan N → 1 | HPA controller Kubernetes | Setiap 15 s, mengikut `behavior` |

Kelewatan sebenar untuk trigger Prometheus: `scrape_interval` Prometheus (15 s) + tetingkap `rate(...[1m])` + sync HPA (15 s) + permulaan pod. Bandingkan dengan Modul 2: Metrics Server juga mengambil ~15 s, tetapi `rate[1m]` melicinkan lonjakan, jadi KEDA dengan Prometheus biasanya **lebih perlahan sedikit** bertindak pada lonjakan mendadak, dan lebih stabil.

### Bila pilih KEDA, bila kekal dengan HPA biasa

Pilih KEDA bila:

- **Skala berdasarkan beban kerja sebenar, bukan CPU.** RPS, latency, bilangan mesej dalam baris gilir (RabbitMQ, Kafka, SQS, Redis), lag consumer. CPU hanyalah anggaran tidak langsung kepada beban, dan bergantung pada `requests.cpu` yang betul (ingat Makmal 1.1).
- **Perlu scale-to-zero.** Worker baris gilir, kerja berjadual, persekitaran dev/test di luar waktu pejabat. Pod 0 = tiada CPU dan memori ditempah.
- **Jadual yang diketahui.** Trigger `cron` menaikkan kapasiti sebelum waktu puncak (cth: jam 8 pagi), bukan selepas pengguna merasai kelambatan.
- **Gabungan beberapa isyarat.** Satu ScaledObject dengan trigger cron + Prometheus + CPU; HPA mengambil nilai tertinggi, sama seperti Makmal 1.6.

Kekal dengan HPA biasa bila:

- **CPU atau memori memang mewakili beban** (app stateless yang CPU-bound seperti `demo-app`). HPA + Metrics Server sudah terbina dalam, tiada komponen tambahan untuk diurus.
- **Tiada sumber metrik yang boleh dipercayai.** Trigger Prometheus menjadikan Prometheus sebahagian daripada laluan autoscaling: jika Prometheus mati, scaling terjejas (Makmal 6.4). HPA CPU hanya bergantung pada komponen dalam kluster.
- **Aplikasi menerima trafik HTTP terus dan mesti sentiasa menjawab.** Scale-to-zero memerlukan sesuatu untuk memegang request semasa pod pertama dimulakan (Makmal 6.5 B).

> Alternatif lain untuk metrik tersuai ialah **Prometheus Adapter** (`custom.metrics.k8s.io`). Ia hanya menyokong Prometheus dan tiada scale-to-zero. Hanya satu komponen boleh mendaftar `external.metrics.k8s.io` dalam satu kluster, jadi jangan pasang dua adapter external.

---

## Makmal 6.1: Pasang KEDA dengan Helm

Pra-muat image (pilihan, jimat masa jika Wi-Fi perlahan; image datang dari `ghcr.io`):

```bash
cd ~/bengkel-k8s/modul-6-keda
IMAGES="ghcr.io/kedacore/keda:2.20.2 ghcr.io/kedacore/keda-metrics-apiserver:2.20.2 \
  ghcr.io/kedacore/keda-admission-webhooks:2.20.2"
for img in $IMAGES; do docker pull "$img"; done
k3d image import $IMAGES -c lab
```

Pastikan kubectl (dan Helm, yang menggunakan context yang sama) menunjuk ke kluster `lab`:

```bash
kubectl config current-context
kubectl get nodes
```

Jangkaan: `k3d-lab` (atau context Rancher untuk `lab` dalam Opsyen B) dan 3 node `Ready`.

Pasang KEDA. Baca dahulu [`helm/keda-values.yaml`](helm/keda-values.yaml): `pullPolicy: IfNotPresent` (supaya image yang dipra-muat digunakan), `resources` yang lebih kecil untuk laptop, dan anotasi `prometheus.io/scrape` supaya Prometheus luar scrape operator KEDA.

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update kedacore
helm install keda kedacore/keda --version 2.20.2 -n keda --create-namespace -f helm/keda-values.yaml
kubectl -n keda rollout status deploy/keda-operator
kubectl -n keda rollout status deploy/keda-operator-metrics-apiserver
kubectl -n keda get pods
```

Jangkaan: 3 pod `Running` (`keda-admission-webhooks-...`, `keda-operator-...`, `keda-operator-metrics-apiserver-...`).

> **Normal selepas pasang:** `keda-operator` restart sekali dalam kira-kira 20 saat pertama (`RESTARTS 1`, log terakhir sebelum restart: `Secrets have been updated; exiting so pod can be restarted`). Operator menjana sijil TLS dalaman sendiri, kemudian bermula semula untuk menggunakannya. `keda-admission-webhooks` pula mengambil kira-kira 30 saat untuk menjadi `1/1`. Tiada tindakan diperlukan.

Sahkan KEDA mendaftar API metrik external (bandingkan dengan `v1beta1.metrics.k8s.io` daripada Metrics Server dalam Makmal 1.3):

```bash
kubectl get apiservice v1beta1.external.metrics.k8s.io v1beta1.metrics.k8s.io
kubectl get crd | grep keda.sh
```

Jangkaan: kedua-dua APIService `AVAILABLE` = `True` (mungkin `False (MissingEndpoints)` selama 30 saat pertama), dan 6 CRD termasuk `scaledobjects.keda.sh` dan `scaledjobs.keda.sh`.

> **Tanpa Helm?** KEDA juga menerbitkan satu fail manifest: `kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.20.2/keda-2.20.2.yaml`. Nama Deployment metrics server dalam fail itu ialah `keda-metrics-apiserver` (bukan `keda-operator-metrics-apiserver`), dan nilai `helm/keda-values.yaml` tidak digunakan.

## Makmal 6.2: Sahkan query di Prometheus dahulu

KEDA hanya menjalankan query PromQL; jika query salah di Prometheus, ia salah dalam KEDA juga. Uji dahulu di http://localhost:9090/query sambil menghantar sedikit trafik:

```bash
for i in $(seq 1 300); do curl -s -o /dev/null "localhost:30080/cpu?ms=20"; sleep 0.1; done
```

```promql
# Query yang akan digunakan oleh ScaledObject: jumlah RPS /cpu untuk SEMUA pod demo-app
sum(rate(demo_http_requests_total{namespace="demo", app="demo-app", path="/cpu"}[1m]))

# Tanpa sum(): satu siri setiap pod. KEDA akan menolak ini ("returned multiple elements")
rate(demo_http_requests_total{namespace="demo", app="demo-app", path="/cpu"}[1m])
```

Jangkaan: query pertama memberi satu nilai, sekitar 5 hingga 8 (RPS) semasa gelung berjalan, dan turun ke 0 kira-kira 1 minit selepas gelung tamat.

Sahkan juga operator KEDA di-scrape (anotasi dari `keda-values.yaml`). Di http://localhost:9090/targets, job `kubernetes-pods` kini termasuk satu target dalam namespace `keda`:

```promql
up{job="kubernetes-pods", namespace="keda"}
```

Jangkaan: `1`. Jika tiada, tunggu 30 saat (penemuan pod) dan muat semula.

## Makmal 6.3: Ganti HPA CPU dengan ScaledObject

### A. Buang HPA Modul 1 dan cipta ScaledObject

Satu Deployment hanya boleh dikawal oleh **satu** HPA. Jika HPA `demo-app` masih wujud, webhook KEDA menolak ScaledObject dengan mesej bahawa workload itu sudah diurus oleh HPA lain.

```bash
cd ~/bengkel-k8s/modul-6-keda
kubectl -n demo delete hpa demo-app --ignore-not-found
kubectl apply -f k8s/01-scaledobject-prometheus.yaml
kubectl -n demo get scaledobject demo-app
```

Jangkaan (selepas 15 hingga 30 saat):

```
NAME       SCALETARGETKIND      SCALETARGETNAME   MIN   MAX   READY   ACTIVE   FALLBACK   PAUSED   TRIGGERS     AUTHENTICATIONS   AGE
demo-app   apps/v1.Deployment   demo-app          1     10    True    False    False      False    prometheus                     30s
```

`READY True` bermaksud KEDA berjaya bertanya kepada Prometheus. `ACTIVE False` bermaksud nilai query ≤ `activationThreshold` (tiada trafik sekarang); dengan `minReplicaCount: 1` ini tidak menurunkan pod ke 0.

Jika `READY` kekal `False` atau kosong:

```bash
kubectl -n keda logs deploy/keda-operator | grep -iE 'error|prometheus' | tail -5
```

| Ralat dalam log | Punca | Pembetulan |
|---|---|---|
| `dial tcp: lookup prometheus ... no such host` | Pod operator tidak dapat menyelesaikan nama container Docker | Gantikan `prometheus` dalam `serverAddress` dengan IP daripada `docker inspect` (arahan di kepala fail) |
| `connection refused` | Stack Modul 3 tidak berjalan, atau Prometheus tidak disambung ke rangkaian `k3d-lab` | `docker compose ps` dalam `modul-3-monitoring/external` |
| `returned multiple elements` | Query tanpa `sum(...)` | Betulkan query (Makmal 6.2) |
| `bad_data` / `parse error` | Sintaks PromQL | Uji di http://localhost:9090 dahulu |

### B. HPA yang dicipta oleh KEDA

```bash
kubectl -n demo get hpa
kubectl -n demo get hpa keda-hpa-demo-app -o yaml | sed -n '/^spec:/,/^status:/p'
```

Jangkaan: HPA `keda-hpa-demo-app` dengan `TARGETS` seperti `0/5 (avg)`, `MINPODS 1`, `MAXPODS 10`. Dalam `spec` anda akan nampak `type: External`, `metric.name: s0-prometheus` dengan `selector` `scaledobject.keda.sh/name: demo-app`, `target.type: AverageValue`, `averageValue: "5"`, dan blok `behavior` yang sama seperti Makmal 1.6. **Ini HPA biasa**; KEDA hanya menulisnya untuk anda.

Lihat nilai yang HPA terima, terus dari API external metrics:

```bash
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/demo/s0-prometheus?labelSelector=scaledobject.keda.sh%2Fname%3Ddemo-app" | python3 -m json.tool
```

Jangkaan: satu item dengan `"value": "0"` tanpa trafik. Nilai dalam unit mili, jadi 4.5 RPS dipaparkan sebagai `"4500m"`.

> Jangan edit `keda-hpa-demo-app` terus; KEDA akan menulis semula. Ubah `ScaledObject`.

### C. Ulang load test Modul 2

Gunakan susun atur terminal Modul 2 (setiap terminal bermula dengan `cd ~/bengkel-k8s/modul-2-load-testing`), dengan nama HPA yang baharu:

| Terminal | Arahan |
|---|---|
| T1: k6 | `k6 run k6/load.js` |
| T2: HPA | `kubectl -n demo get hpa keda-hpa-demo-app --watch` |
| T3: Pod | `kubectl -n demo get pods -l app=demo-app --watch` |
| T4: Rakaman | `./watch-hpa.sh demo keda-hpa-demo-app 5 \| tee keda-timeline.csv` |

Lajur `cpu_pct` dan `mem_pct` dalam CSV akan kosong (HPA ini tiada metrik Resource); lajur replicas dan pod tetap direkod.

Jangkaan: `load.js` menghasilkan sekitar 19 RPS pada 10 VU (`10 VU × ~1.9 iterasi/saat`). HPA naik ke **4 pod** (`ceil(19 / 5)`) dan kekal di situ semasa fasa tahan, berbanding **7 hingga 8 pod** dengan HPA CPU dalam Modul 2. `TARGETS` dalam T2 menunjukkan sekitar `4750m/5 (avg)`.

Isi jadual perbandingan (gunakan `hpa-timeline.csv` dari Makmal 2.2 jika masih ada):

| | HPA CPU (Modul 2) | KEDA Prometheus RPS |
|---|---|---|
| Saat pertama replicas naik | | |
| Replicas maksimum semasa tahan | | |
| p95 latency (ringkasan k6) | | |
| Flapping semasa tahan? | | |
| Masa sebelum scale-in bermula | | |

Perbincangan:

1. Kenapa bilangan pod berbeza? HPA CPU menyasarkan 50% daripada `requests.cpu` 100m (50m sepod). KEDA menyasarkan 5 RPS sepod tanpa mengira CPU. Mana satu "betul" bergantung pada **kapasiti sebenar** satu pod yang anda ukur dalam Modul 2 (`/cpu?ms=20`: ~25 RPS sepod pada limit 500m). Threshold 5 memberi ruang yang besar; production biasanya menetapkan 60% hingga 70% daripada kapasiti yang diukur.
2. Jika seseorang menukar `requests.cpu` kepada 50m, apa jadi pada HPA CPU? Pada ScaledObject? (HPA CPU menggandakan pod; KEDA tidak berubah.)
3. Bila k6 berhenti, scale-in bermula selepas `rate[1m]` turun **dan** `stabilizationWindowSeconds: 120` tamat. Padankan dengan CSV.

## Makmal 6.4: Apa jadi bila Prometheus mati?

Trigger Prometheus menjadikan Prometheus sebahagian daripada laluan autoscaling. ScaledObject ini ada blok `fallback`: selepas 3 kegagalan berturut-turut, KEDA memberi HPA nilai yang menghasilkan **3 replicas**.

Pastikan tiada ujian beban berjalan, jadi `demo-app` berada pada 1 pod (`minReplicaCount`). Hentikan Prometheus:

```bash
cd ~/bengkel-k8s/modul-3-monitoring/external
docker compose stop prometheus
kubectl -n demo get scaledobject demo-app --watch
```

Terminal lain:

```bash
kubectl -n demo get pods -l app=demo-app --watch
```

Jangkaan: dalam sekitar 1 minit (lebih daripada 3 kegagalan query berturut-turut), `FALLBACK` menjadi `True` dan `demo-app` **naik dari 1 ke 3 pod** walaupun tiada trafik langsung. `READY` mungkin juga menjadi `False`. Log operator:

```bash
kubectl -n keda logs deploy/keda-operator | grep -i 'error executing prometheus query' | tail -2
kubectl -n demo describe scaledobject demo-app | sed -n '/Events/,$p'
```

Hidupkan semula:

```bash
docker compose start prometheus
```

Jangkaan: `FALLBACK False` dan `READY True` dalam 30 saat. Pod turun semula dari 3 ke 1, perlahan-lahan mengikut `behavior.scaleDown` (tunggu 120 saat, kemudian 1 pod setiap 30 saat).

Perbincangan: tanpa `fallback`, HPA mengekalkan bilangan replicas terakhir (tidak naik walaupun beban naik). Berapakah nilai `fallback.replicas` yang selamat untuk sistem anda: purata, atau kapasiti puncak? Bandingkan dengan Pilihan A vs B dalam Modul 3: apakah yang perlu dipantau supaya anda tahu autoscaling sedang "buta"? (Petunjuk: `keda_scaler_detail_errors_total` dan `keda_scaled_object_errors_total` daripada operator KEDA yang di-scrape dalam Makmal 6.2.)

## Makmal 6.5: Cron dan scale-to-zero

### A. Kerja berjadual yang turun ke 0

[`k8s/02-kerja-berjadual.yaml`](k8s/02-kerja-berjadual.yaml) mencipta Deployment `laporan` (proses ringkas yang mencetak log setiap 10 saat) dan ScaledObject dengan trigger `cron`: 2 replicas pada minit 0 hingga 5, 10 hingga 15, 20 hingga 25, dan seterusnya (zon `Asia/Kuala_Lumpur`), dan **0** di luar tetingkap itu.

```bash
cd ~/bengkel-k8s/modul-6-keda
kubectl apply -f k8s/02-kerja-berjadual.yaml
date +%H:%M
kubectl -n demo get scaledobject laporan
kubectl -n demo get deploy laporan --watch
```

Jangkaan:

- Jika minit sekarang berakhir dengan 0 hingga 4: `ACTIVE True`, `READY` Deployment naik `0/0` → `1/1` → `2/2` dalam ~30 saat (operator KEDA melakukan 0 → 1, HPA melakukan 1 → 2).
- Pada minit ke-5 (cth: 10:15): `ACTIVE False` dan Deployment terus turun ke `0/0` pada minit itu. Dalam ujian sebenar, `cooldownPeriod` tidak menambah kelewatan bila tetingkap cron tamat.
- Jika minit sekarang 5 hingga 9: kekal `0/0` sehingga minit 0 seterusnya.

Lihat log semasa aktif:

```bash
kubectl -n demo logs deploy/laporan -f
```

```
10:10:24 laporan-5d9c8b7f4-q7wzx memproses laporan...
```

Cap masa dalam log ialah waktu Malaysia kerana Deployment menetapkan `TZ=Asia/Kuala_Lumpur`. Tanpa env itu, container menggunakan UTC (8 jam di belakang), walaupun jadual cron KEDA tetap mengikut `timezone` dalam ScaledObject. Zon masa jadual (KEDA) dan zon masa container adalah dua tetapan berasingan.

HPA `keda-hpa-laporan` juga wujud, dengan `MINPODS 1`: HPA tidak boleh 0, jadi langkah ke 0 dan dari 0 sentiasa dilakukan oleh operator KEDA. Semak:

```bash
kubectl -n demo get hpa keda-hpa-laporan
kubectl -n demo get events --field-selector involvedObject.name=laporan --sort-by=.lastTimestamp | tail -5
```

Untuk production, tukar kepada waktu pejabat: `start: "0 8 * * 1-5"` dan `end: "0 18 * * 1-5"`.

### B. Eksperimen: kenapa bukan scale-to-zero untuk `demo-app`?

Tukar ScaledObject `demo-app` supaya boleh turun ke 0, dengan cooldown pendek:

```bash
kubectl -n demo patch scaledobject demo-app --type merge -p '{"spec":{"minReplicaCount":0,"cooldownPeriod":60}}'
kubectl -n demo get deploy demo-app --watch
```

Tanpa trafik, selepas `rate[1m]` turun ke 0 dan `cooldownPeriod` 60 saat, Deployment menjadi `0/0`. Sekarang cuba:

```bash
curl -s -m 5 localhost:30080/ || echo "GAGAL: tiada pod"
k6 run ../modul-2-load-testing/k6/smoke.js
```

Jangkaan: `curl` gagal (`Connection refused` atau tamat masa), k6 smoke gagal, dan **Deployment kekal 0/0 selama-lamanya**. Kenapa? Metrik `demo_http_requests_total` datang daripada pod itu sendiri. Tiada pod, tiada metrik, query kosong, KEDA menganggap nilai 0 (`ignoreNullValues: true` secara default), jadi tidak pernah aktif semula. `fallback` juga tidak membantu kerana query kosong bukan ralat. (Operator mengira kejadian ini dalam metrik `keda_scaler_empty_upstream_responses_total`.)

Pulihkan:

```bash
kubectl -n demo patch scaledobject demo-app --type merge -p '{"spec":{"minReplicaCount":1,"cooldownPeriod":300}}'
kubectl -n demo rollout status deploy/demo-app
```

Pengajaran untuk scale-to-zero:

| Jenis workload | Sumber isyarat untuk bangun dari 0 | Sesuai? |
|---|---|---|
| Worker baris gilir (RabbitMQ, Kafka, SQS) | Panjang baris gilir, di luar pod | Ya, kes paling biasa |
| Kerja berjadual | Jam (`cron`) | Ya (Makmal 6.5 A) |
| API HTTP dengan metrik dari pod sendiri | Tiada | Tidak |
| API HTTP dengan metrik dari ingress/gateway | Metrik ingress, tetapi request pertama gagal atau menunggu | Hanya dengan komponen yang memegang request, cth: **KEDA HTTP Add-on** |

## Cabaran

1. **Dua trigger.** Tambah trigger `cpu` pada ScaledObject `demo-app` (perlukan Metrics Server dari Modul 1, dan hanya berfungsi bila `minReplicaCount` ≥ 1):

   ```yaml
       - type: cpu
         metricType: Utilization
         metadata:
           value: "50"
   ```

   Jalankan `k6 run -e CPU_MS=100 k6/load.js`. Lajur `TARGETS` HPA kini menunjukkan dua nilai. Metrik mana yang menentukan replicas, dan kenapa? (Sama seperti Makmal 1.6: nilai tertinggi menang.)
2. **Gabung cron dan RPS.** Tambah trigger `cron` pada `demo-app` dengan `desiredReplicas: "6"` untuk tetingkap 10 minit akan datang. Ini meniru "pre-scale sebelum flash sale". Jalankan `k6 run k6/spike.js` dalam tetingkap itu dan di luarnya. Bandingkan bilangan permintaan gagal dengan Makmal 2.4.
3. **Jeda autoscaling.** Semasa penyelenggaraan, bekukan replicas pada 2: `kubectl -n demo annotate scaledobject demo-app autoscaling.keda.sh/paused-replicas="2"`. Apakah lajur `PAUSED` sekarang? Buang anotasi dengan `autoscaling.keda.sh/paused-replicas-`.
4. **Alert untuk KEDA.** Tulis peraturan Prometheus (gaya `kubernetes-alerts.yml` Modul 3) yang berbunyi bila `increase(keda_scaler_detail_errors_total[5m]) > 0`, dan uji dengan Makmal 6.4.
5. **ScaledJob.** Baca tentang `ScaledJob`: setiap mesej dalam baris gilir menjadi satu Job, bukan satu replica Deployment yang berjalan lama. Bila ini lebih baik daripada ScaledObject?

## Pembersihan

```bash
cd ~/bengkel-k8s/modul-6-keda
kubectl delete -f k8s/02-kerja-berjadual.yaml
kubectl delete -f k8s/01-scaledobject-prometheus.yaml
# pulihkan HPA Makmal 1.6 (Modul 1) untuk modul lain
kubectl apply -f ../modul-1-hpa/07-hpa-cpu-memory.yaml
helm uninstall keda -n keda
kubectl delete namespace keda
```

Bila ScaledObject dipadam, KEDA memadam HPA `keda-hpa-demo-app` juga, dan Deployment kekal pada bilangan replicas terakhir sehingga HPA Makmal 1.6 (Modul 1) mengambil alih. Chart KEDA memasang CRD sebagai sebahagian daripada release, jadi `helm uninstall` juga membuang keenam-enam CRD `*.keda.sh`. Padam ScaledObject **sebelum** `helm uninstall`, seperti di atas, supaya HPA yang dicipta oleh KEDA dibersihkan dengan betul.

## Semakan akhir modul

- [ ] Peserta boleh menerangkan bahawa KEDA mencipta HPA, dan langkah mana yang dilakukan oleh KEDA (0 ↔ 1) serta oleh HPA (1 ↔ N)
- [ ] 3 pod KEDA `Running` dan `v1beta1.external.metrics.k8s.io` `AVAILABLE True`
- [ ] ScaledObject `demo-app` `READY True`, dan HPA `keda-hpa-demo-app` naik ke ~4 pod semasa `load.js`
- [ ] Jadual perbandingan HPA CPU vs KEDA RPS diisi
- [ ] `FALLBACK True` dan `demo-app` naik ke 3 pod semasa Prometheus dihentikan
- [ ] Deployment `laporan` naik ke 2 dan turun ke 0 mengikut jadual cron
- [ ] Peserta boleh menerangkan kenapa `demo-app` tidak bangun semula dari 0
- [ ] HPA Makmal 1.6 (Modul 1) dipulihkan selepas makmal

## Apa yang telah diuji

Dalam kluster k3d sebenar (k3d v5.8.3, k3s v1.33.1) dalam persekitaran penyediaan:

- Chart `kedacore/keda` 2.20.2 dimuat turun daripada repositori chart rasmi (digest sha256 sepadan dengan `index.yaml`); `helm lint` dan `helm template` dengan `helm/keda-values.yaml` lulus; `helm install` berjaya: 6 CRD, 3 Deployment (`keda-operator`, `keda-operator-metrics-apiserver`, `keda-admission-webhooks`) dengan `imagePullPolicy: IfNotPresent`, `resources` dan anotasi `prometheus.io/*` yang betul, dan APIService `v1beta1.external.metrics.k8s.io`
- Kedua-dua ScaledObject dan Deployment `laporan` diterima oleh API server (`kubectl apply --dry-run=server` dan `apply` sebenar) dengan skema CRD KEDA 2.20.2, termasuk `fallback`, `advanced.horizontalPodAutoscalerConfig.behavior` dan trigger `cron`
- Nama parameter trigger `prometheus` dan `cron`, nama metrik `s0-prometheus`, dan tingkah laku query kosong (dianggap 0) disemak terhadap kod sumber KEDA v2.20.2
- Query PromQL ScaledObject diuji dengan `promtool test rules` (Prometheus v3.4.0): 3 pod × 6.67 RPS memberi 20, mengabaikan `/healthz` dan app lain, `ceil(20 / 5) = 4`, dan tiada pod memberi hasil kosong
- Nama container `prometheus` pada rangkaian `k3d-lab` boleh diselesaikan dan API query Prometheus boleh dicapai dari node k3d (resolver yang sama digunakan oleh CoreDNS)

Pada server ujian Linode (Ubuntu 24.04, kluster k3d `lab`, Rancher 2.13.3 sekali dalam `lab`), 2026-10-18:

- Makmal 6.1: `helm install` KEDA 2.20.2 dengan `helm/keda-values.yaml` berjaya; 3 pod `Running` (operator restart sekali selepas menjana sijil, webhook `1/1` selepas ~30 saat); APIService `v1beta1.external.metrics.k8s.io` dan `v1beta1.metrics.k8s.io` `True`; 6 CRD
- Makmal 6.5 A: trigger cron menaikkan `laporan` 0 → 2 pada minit x0 dan menurunkannya ke 0 tepat pada minit x5; HPA `keda-hpa-laporan` dicipta
- Pembersihan: `helm uninstall` membuang KEDA dan keenam-enam CRD

Yang **belum** diuji dengan pod berjalan: Makmal 6.2 hingga 6.4, Makmal 6.5 B dan Cabaran (query Prometheus, operator di-scrape, webhook menolak HPA berganda, ScaledObject `demo-app` `READY` dengan nama `prometheus` dari dalam pod, HPA `keda-hpa-demo-app` dan nilai External metric, scaling semasa k6, `fallback`, eksperimen scale-to-zero `demo-app`, anotasi jeda), kerana fail Modul 1 hingga 3 belum ada di server ujian. `env TZ` pada `laporan` ditambah selepas ujian itu. Jalankan modul ini sekali secara penuh sebelum menggunakannya dalam kelas.

## Versi komponen modul ini

| Komponen | Versi |
|---|---|
| KEDA (chart `kedacore/keda` dan image) | 2.20.2 |
| Kubernetes yang disokong oleh KEDA 2.20 | 1.33 hingga 1.35 (makmal: v1.33.1) |

KEDA 2.21 (September 2026) menyokong Kubernetes 1.34 hingga 1.36 sahaja, jadi tidak digunakan dengan k3s v1.33 dalam bengkel ini.

## Rujukan

- KEDA: https://keda.sh/docs/latest/concepts/
- ScaledObject: https://keda.sh/docs/latest/reference/scaledobject-spec/
- Scaler Prometheus: https://keda.sh/docs/latest/scalers/prometheus/
- Scaler Cron: https://keda.sh/docs/latest/scalers/cron/
- Pemasangan Helm: https://keda.sh/docs/latest/deploy/
- Keserasian versi Kubernetes: https://keda.sh/docs/latest/operate/cluster/
- KEDA HTTP Add-on: https://github.com/kedacore/http-add-on
- HPA metrik External: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#scaling-on-metrics-not-related-to-kubernetes-objects
