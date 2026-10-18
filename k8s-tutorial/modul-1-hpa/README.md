# Modul 1: Kubernetes Workload Autoscaling & HPA Setup

**Hari 1, 9:00 pagi hingga 1:00 petang**

> **Opsyen B (Rancher):** Metrics Server dipasang seperti biasa; jangan letak namespace `demo` dalam Rancher Project yang ada Resource Quota. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Faham beza `requests` dan `limits`, dan kenapa HPA bergantung pada `requests`.
2. Pasang **Metrics Server** dan sahkan `kubectl top` berfungsi.
3. Ukur penggunaan sebenar app dan tentukan sendiri nilai `requests` dan `limits` untuk CPU dan memori.
4. Konfigur **HPA v2** berasaskan CPU, kemudian CPU + memory, dengan polisi `behavior`.
5. Lihat HPA scale-out dan scale-in dengan beban ringkas (ujian beban sebenar ada di Modul 2).

> Prasyarat: kluster `lab` dan app demo sudah sedia. Lihat [Persediaan Opsyen A](../00-persediaan/opsyen-a/README.md) atau [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

## Jadual

| Masa | Aktiviti |
|---|---|
| 9:00 – 9:30 | Teori: model resource Kubernetes, QoS class, cara HPA berfikir |
| 9:30 – 10:30 | Makmal 1.1 & 1.2: requests/limits, LimitRange, ResourceQuota |
| 10:30 – 10:45 | Rehat |
| 10:45 – 11:45 | Makmal 1.3 & 1.4: pasang Metrics Server, ukur dan tetapkan requests/limits |
| 11:45 – 12:40 | Makmal 1.5 & 1.6: HPA v2 CPU, kemudian CPU + memory + behavior |
| 12:40 – 1:00 | Makmal 1.7 (cabaran) & semakan |

---

## Teori ringkas

### Requests vs limits

| | `requests` | `limits` |
|---|---|---|
| Siapa guna | **Scheduler** (pilih node) dan **HPA** (kira %) | **Kubelet / kernel** (cgroup) |
| Maksud | "Saya perlukan sekurang-kurangnya ini" | "Jangan benarkan lebih daripada ini" |
| CPU melebihi | Boleh, jika node ada CPU lapang | **Throttled** (diperlahankan, tidak mati) |
| Memori melebihi | Boleh, tetapi pod jadi calon pertama untuk eviction | **OOMKilled** (exit code 137) |

Unit: `cpu: 100m` = 0.1 vCPU (100 millicore). `memory: 64Mi` = 64 mebibyte.

### QoS class (penting untuk eviction di Modul 4)

QoS (Quality of Service) ialah **kelas yang Kubernetes berikan secara automatik kepada setiap pod** berdasarkan cara anda menetapkan `requests` dan `limits` untuk CPU dan memori. Anda tidak menetapkan QoS secara terus; ia dikira daripada konfigurasi resource.

Tujuan utamanya: bila node kehabisan memori, Kubernetes perlu tahu **pod mana yang dibuang dahulu**.

#### Tiga kelas QoS

**1. Guaranteed** (paling dilindungi). Setiap container dalam pod mesti ada `requests` dan `limits` untuk CPU **dan** memori, dan nilainya **sama**:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

**2. Burstable** (pertengahan). Sekurang-kurangnya satu container ada `requests` atau `limits`, tetapi tidak cukup syarat untuk Guaranteed. Contohnya `requests` lebih rendah daripada `limits`:

```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "1"
    memory: "1Gi"
```

**3. BestEffort** (paling mudah dibuang). Tiada `requests` atau `limits` langsung dalam mana-mana container.

#### Kesan sebenar

| | Guaranteed | Burstable | BestEffort |
|---|---|---|---|
| Urutan eviction bila node kurang memori | Terakhir | Tengah | **Pertama** |
| Kemungkinan dibunuh oleh OOM killer | Paling rendah | Sederhana | Paling tinggi |
| Boleh guna resource lebih daripada request | Tidak | Ya, sehingga limit | Ya, sehingga node habis |

Dalam kelas Burstable, pod yang paling banyak menggunakan memori melebihi `requests`nya dibuang dahulu.

#### Salah faham yang biasa

- **QoS tidak memberi keutamaan CPU semasa berjalan.** Ia lebih kepada perlindungan bila memori tertekan. Jika container mencapai limit CPU, ia hanya kena *throttle* (diperlahankan), bukan dibunuh. Jika mencapai limit memori, ia kena **OOMKilled**.
- **Guaranteed tidak bermakna kebal.** Jika container sendiri melebihi limit memori, ia tetap OOMKilled. Guaranteed hanya melindungi daripada eviction yang disebabkan oleh pod *lain*.
- **Set limit sahaja sudah cukup untuk Guaranteed.** Jika anda menulis `limits` (CPU dan memori) tanpa `requests`, Kubernetes menyalin nilai limit ke requests, jadi pod menjadi Guaranteed.

#### Semak QoS sesuatu pod

```bash
kubectl get pod <nama-pod> -o jsonpath='{.status.qosClass}'
```

#### Panduan ringkas memilih

- **Guaranteed**: database, komponen kritikal, apa-apa yang tidak boleh tiba-tiba hilang.
- **Burstable**: kebanyakan aplikasi web/API. Set `requests` ikut penggunaan biasa, dan `limits` memori sedikit di atas puncak. Ramai juga yang tidak menetapkan limit CPU langsung untuk mengelakkan throttling yang tidak perlu.
- **BestEffort**: elakkan di production. Sesuai hanya untuk job yang memang boleh dibuang bila-bila masa.

### Cara HPA berfikir

Setiap 15 saat (default), HPA controller:

1. Ambil metrik setiap pod daripada `metrics.k8s.io` (disediakan oleh Metrics Server).
2. Kira `utilization = purata penggunaan / purata requests`.
3. Kira:

```
desiredReplicas = ceil( currentReplicas × currentUtilization / targetUtilization )
```

Contoh: 2 pod, target CPU 50%, purata sekarang 150% → `ceil(2 × 150/50) = 6` pod.

4. Ada toleransi 10%: jika nisbah antara 0.9 hingga 1.1, HPA tidak buat apa-apa (elak "flapping").
5. Untuk scale-down, HPA ambil nilai tertinggi dalam `stabilizationWindowSeconds` (default 300 saat).

#### Senario: apa yang HPA nampak, pusingan demi pusingan

Cara paling mudah memahami formula itu: **HPA mahu setiap pod berada pada target.** Jadi ia sebenarnya bertanya, "jumlah kerja sekarang perlukan berapa pod jika setiap pod hanya buat 50% daripada request-nya?"

Kita guna nilai makmal ini: `requests.cpu: 100m` setiap pod, target `averageUtilization: 50` (iaitu 50m setiap pod), `minReplicas: 1`, `maxReplicas: 10`.

| Masa | Apa berlaku | Pod | CPU setiap pod (% daripada 100m) | Pengiraan HPA | desiredReplicas |
|---|---|---|---|---|---|
| 09:00 | Tiada trafik | 1 | 10m (10%) | `ceil(1 × 10/50)` = 1 | 1, kekal (min 1) |
| 09:05 | k6 mula hantar beban; jumlah kerja kira-kira 180m | 1 | 180m (180%) | `ceil(1 × 180/50)` = `ceil(3.6)` = 4 | **4**, scale up |
| 09:06 | 3 pod baharu sedang start; belum Ready jadi belum dikira | 4 | pod lama masih tinggi | HPA tunggu pod baharu siap | 4 |
| 09:07 | Beban sama (180m) kini dikongsi 4 pod | 4 | 45m (45%) | nisbah 45/50 = 0.9, dalam toleransi | 4, tiada perubahan |
| 09:15 | Trafik naik dua kali ganda, jumlah ~400m | 4 | 100m (100%) | `ceil(4 × 100/50)` = 8 | **8**, scale up |
| 09:17 | 400m dikongsi 8 pod | 8 | 50m (50%) | nisbah 1.0 | 8, stabil |
| 09:30 | k6 berhenti | 8 | 5m (5%) | `ceil(8 × 5/50)` = 1 | cadangan 1, **tetapi tunggu** |
| 09:35 | 5 minit tiada cadangan lebih tinggi | 8 | 5m | stabilization window (300 s) tamat | **1**, scale down |

Perkara yang patut diperhatikan:

- **Ia sebenarnya "jumlah kerja ÷ kerja setiap pod".** Pada 09:05, 180m ÷ 50m = 3.6, dibundarkan ke atas jadi 4 pod. Formula `currentReplicas × currentUtilization / target` memberi jawapan yang sama.
- **Peratus dikira daripada `requests`, bukan `limits`.** Pod boleh menunjukkan 180% kerana limit CPU ialah 500m. Tanpa `requests`, HPA tidak dapat mengira peratus langsung (Makmal 1.1).
- **Scale up cepat, scale down lambat.** Naik berlaku dalam pusingan 15 saat yang seterusnya. Turun menunggu 5 minit supaya pod tidak dibuang dan dicipta semula setiap kali trafik turun sekejap.
- **Pod baharu tidak terus membantu.** Ada jarak antara HPA membuat keputusan dengan pod baharu Ready dan menerima trafik. Modul 2 (spike test) mengukur jarak ini.
- **Had tetap terpakai.** Jika pengiraan memberi 14, HPA berhenti pada `maxReplicas: 10`.

Anda akan melihat semua ini sendiri dalam Makmal 1.5 dengan `kubectl -n demo get hpa -w` (lajur `TARGETS` dan `REPLICAS`) dan `kubectl -n demo describe hpa demo-app` (bahagian `Events`).

```
 ┌──────────┐  /metrics/resource  ┌────────────────┐  metrics.k8s.io  ┌────────────────┐  scale  ┌────────────┐
 │ kubelet  │ ──────────────────▶ │ Metrics Server │ ───────────────▶ │ HPA controller │ ──────▶ │ Deployment │
 │ (cAdvisor)│                    └────────────────┘                  └────────────────┘         └────────────┘
 └──────────┘
```

> HPA juga boleh membaca metrik **External** (`external.metrics.k8s.io`), contohnya kadar request daripada Prometheus atau panjang baris gilir, tetapi Kubernetes tidak menyediakan sumbernya sendiri. **KEDA** mengisi peranan itu dan mencipta HPA untuk anda; lihat [Modul 6 (pilihan): KEDA](../modul-6-keda/README.md).

---

## Makmal 1.1: Apa jadi tanpa requests?

Semua arahan dalam modul ini dijalankan dari folder `modul-1-hpa`:

```bash
cd ~/bengkel-k8s/modul-1-hpa
kubectl apply -f ../00-persediaan/namespace.yaml
kubectl apply -f ../00-persediaan/demo-app/configmap.yaml
kubectl apply -f 01-deployment-tanpa-resources.yaml
kubectl apply -f 03-service.yaml
kubectl -n demo rollout status deploy/demo-app
```

Semak QoS class pod:

```bash
kubectl -n demo get pod -l app=demo-app -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass
```

Jangkaan: `BestEffort`.

Cuba cipta HPA sekarang (sebelum Metrics Server dan sebelum ada requests):

```bash
kubectl apply -f 06-hpa-cpu.yaml
kubectl -n demo get hpa
```

Jangkaan:

```
NAME       REFERENCE             TARGETS              MINPODS   MAXPODS   REPLICAS
demo-app   Deployment/demo-app   cpu: <unknown>/50%   1         10        1
```

```bash
kubectl -n demo describe hpa demo-app | sed -n '/Conditions/,$p'
```

Anda akan nampak `FailedGetResourceMetric`. Ada **dua** sebab di sini: Metrics Server belum dipasang, dan pod tiada `requests.cpu`. Kita betulkan kedua-duanya.

## Makmal 1.2: Tambah requests/limits, LimitRange dan ResourceQuota

```bash
kubectl apply -f 02-deployment.yaml
kubectl -n demo rollout status deploy/demo-app
kubectl -n demo get pod -l app=demo-app -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass
```

Jangkaan: `Burstable` (requests < limits).

Pasang LimitRange dan ResourceQuota. Kedua-duanya **bukan resources untuk satu app**, tetapi peraturan untuk seluruh namespace:

| | `resources` dalam Deployment | LimitRange ([`04-limitrange.yaml`](04-limitrange.yaml)) | ResourceQuota ([`05-resourcequota.yaml`](05-resourcequota.yaml)) |
|---|---|---|---|
| Ditulis oleh | Pemilik app | Admin kluster / pemilik namespace | Admin kluster / pemilik namespace |
| Terpakai kepada | Container dalam Deployment itu sahaja | **Setiap container** yang dicipta dalam namespace | **Jumlah** semua pod dalam namespace |
| Fungsi | Nyatakan keperluan app | Beri nilai default jika tiada, dan tolak nilai di luar julat `min`..`max` | Tolak pod baharu bila jumlah requests/limits namespace melebihi had |
| Analogi | Pesanan setiap pelanggan | Peraturan restoran: "jika tak pesan, dapat set biasa; maksimum 2 pinggan seorang" | Kapasiti restoran: "maksimum 20 pelanggan" |

Bila pod dicipta, API server menyemak mengikut urutan ini:

1. Container ada `resources` sendiri? Jika ya, nilai itu dikekalkan. Jika tidak, LimitRange menyuntik `defaultRequest` (requests) dan `default` (limits).
2. Nilai akhir berada dalam julat `min`..`max` LimitRange? Jika tidak, pod **ditolak**.
3. Jumlah namespace selepas pod ini masih dalam had ResourceQuota? Jika tidak, pod **ditolak**.

Jadi `demo-app` (yang ada `resources` sendiri dalam `02-deployment.yaml`) tidak berubah. LimitRange hanya menjadi "jaring keselamatan" untuk pod yang terlupa menetapkan resources, seperti pod `busybox` dalam makmal ini. Peraturan hanya terpakai pada pod **baharu**; pod yang sudah berjalan tidak terjejas.


```bash
kubectl apply -f 04-limitrange.yaml -f 05-resourcequota.yaml
kubectl -n demo describe limitrange default-resources
kubectl -n demo describe resourcequota demo-quota
```

Uji LimitRange: cipta pod tanpa resources dan lihat nilai default disuntik.

```bash
kubectl -n demo run tanpa-res --image=busybox:1.36 --restart=Never -- sleep 3600
kubectl -n demo get pod tanpa-res -o jsonpath='{.spec.containers[0].resources}' ; echo
kubectl -n demo delete pod tanpa-res
```

Jangkaan: `{"limits":{"cpu":"500m","memory":"256Mi"},"requests":{"cpu":"100m","memory":"64Mi"}}`

Uji had `max` LimitRange (sepatutnya ditolak):

```bash
kubectl -n demo run rakus --image=busybox:1.36 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"rakus","image":"busybox:1.36","command":["sleep","3600"],"resources":{"limits":{"cpu":"4"}}}]}}'
```

Jangkaan: `Error from server (Forbidden): ... maximum cpu usage per Container is 2, but limit is 4`.

> **Nota:** Bila ResourceQuota untuk `requests.cpu` wujud dalam namespace, setiap pod **mesti** ada `requests.cpu`. LimitRange membantu dengan memberi nilai default.

## Makmal 1.3: Pasang Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml

# Kluster makmal (k3d, kind, minikube): sijil kubelet tidak boleh disahkan oleh Metrics Server, perlu --kubelet-insecure-tls (lab sahaja!)
kubectl -n kube-system patch deployment metrics-server --type=json --patch-file metrics-server-patch.yaml
kubectl -n kube-system rollout status deploy/metrics-server
```

> **Nota k3d:** k3s sebenarnya membawa Metrics Server sendiri. Kita mematikannya dalam `k3d-cluster.yaml` (`--disable=metrics-server`) supaya anda memasang dan memahaminya sendiri, seperti di kluster kubeadm atau EKS. Jika `metrics-server` sudah wujud dalam `kube-system` sebelum langkah ini, kluster anda dicipta tanpa fail config tersebut; langkah di atas tetap selamat dijalankan.
>
> Pengguna minikube boleh guna `minikube addons enable metrics-server` sebagai ganti.

Sahkan API metrics berdaftar dan berfungsi (tunggu kira-kira 30–60 saat):

```bash
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl -n demo top pods
kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/demo/pods" | python3 -m json.tool | head -30
```

Jangkaan `kubectl get apiservice`: kolum `AVAILABLE` = `True`.

**Jika `AVAILABLE` = `False`:**

```bash
kubectl -n kube-system logs deploy/metrics-server | tail -20
```

| Mesej log | Punca | Penyelesaian |
|---|---|---|
| `x509: cannot validate certificate` | Sijil kubelet self-signed | Patch `--kubelet-insecure-tls` (lab) |
| `no such host` / `dial tcp ... i/o timeout` | Metrics Server tak dapat capai kubelet | Tambah `--kubelet-preferred-address-types=InternalIP` |
| `Failed to scrape node` sejurus selepas pasang | Normal, belum ada data | Tunggu 1 minit |

## Makmal 1.4: Cari nilai requests dan limits sendiri

Nilai `requests` dan `limits` tidak boleh diteka daripada kod. Caranya ialah **ukur penggunaan sebenar semasa app dibebani**, kemudian kira nilainya. Dalam makmal ini kita ukur `demo-app` pada beban normal dan beban puncak, lalu bandingkan hasilnya dengan nilai dalam `02-deployment.yaml` (`100m`/`64Mi` requests, `500m`/`256Mi` limits).

Prinsipnya:

| Nilai | Dikira daripada | Sebab |
|---|---|---|
| `requests.cpu` | Purata CPU **sepod** pada beban normal, dibundarkan ke atas | Scheduler menempah sebanyak ini, dan HPA mengira peratus daripadanya |
| `requests.memory` | Memori tertinggi **sepod** pada beban normal, dibundarkan ke atas | Memori tidak boleh "dikongsi" seperti CPU; jika node kekurangan, pod yang melebihi request diusir dahulu |
| `limits.memory` | Memori tertinggi pada beban **puncak** + 25% ruang | Melebihi had ini bermakna OOMKilled, jadi beri ruang untuk lonjakan |
| `limits.cpu` | Pilihan: CPU tertinggi pada beban puncak × 1.5, atau tidak ditetapkan | Melebihi had CPU hanya menyebabkan throttling (lambat), bukan mati |

### Langkah 1: Tetapkan bilangan pod

Kita mahu tahu berapa banyak kerja **satu pod** buat, jadi HPA tidak boleh menambah pod semasa kita mengukur. Kita andaikan rancangan kapasiti ialah **2 pod untuk trafik normal**. HPA dari Makmal 1.1 masih ada dan kini boleh membaca metrik, jadi kunci ia pada 2 pod:

```bash
cd ~/bengkel-k8s/modul-1-hpa
kubectl -n demo patch hpa demo-app --type=merge -p '{"spec":{"minReplicas":2,"maxReplicas":2}}'
kubectl -n demo get pods -l app=demo-app
```

Jangkaan: tepat 2 pod `Running`. Jika masih lebih, tunggu sehingga HPA menurunkannya.

### Langkah 2: Ukur beban normal

[`k6-ukur.js`](k6-ukur.js) menghantar **kadar request yang tetap** (bukan bilangan pengguna tetap), jadi beban boleh diramal: `RATE=5` request sesaat × 20 ms CPU setiap request ≈ 100m untuk semua pod, iaitu ≈ 50m sepod.

Arahan di bawah menjalankan k6 di latar belakang, menunggu 30 saat supaya beban stabil, kemudian merekod `kubectl top` setiap 15 saat (selang Metrics Server dalam makmal):

```bash
k6 run -q -e RATE=5 k6-ukur.js &
sleep 30
for i in $(seq 1 10); do kubectl -n demo top pods -l app=demo-app --no-headers; sleep 15; done | tee ukur-normal.txt
wait
```

Ringkaskan hasilnya (purata dan tertinggi sepod):

```bash
awk '{c=$2; m=$3; sub("m","",c); sub("Mi","",m); s+=c; n++; if(c+0>cmax)cmax=c+0; if(m+0>mmax)mmax=m+0}
     END{printf "CPU sepod: purata %dm, tertinggi %dm | Memori sepod tertinggi: %dMi\n", s/n, cmax, mmax}' ukur-normal.txt
```

Contoh output (nilai anda akan sedikit berbeza):

```
CPU sepod: purata 55m, tertinggi 63m | Memori sepod tertinggi: 24Mi
```

### Langkah 3: Ukur beban puncak

Ulang dengan tiga kali ganda trafik (`RATE=15`, ≈ 150m sepod). Pada masa yang sama, satu request `/mem` memegang 40 MB selama 60 saat, meniru lonjakan memori sebenar (contohnya satu pengguna menjana laporan besar):

```bash
k6 run -q -e RATE=15 k6-ukur.js &
sleep 30
kubectl -n demo run mem-ukur --image=busybox:1.36 --restart=Never -- \
  wget -q -O- "http://demo-app/mem?mb=40&hold=60"
for i in $(seq 1 10); do kubectl -n demo top pods -l app=demo-app --no-headers; sleep 15; done | tee ukur-puncak.txt
wait
kubectl -n demo delete pod mem-ukur
awk '{c=$2; m=$3; sub("m","",c); sub("Mi","",m); s+=c; n++; if(c+0>cmax)cmax=c+0; if(m+0>mmax)mmax=m+0}
     END{printf "CPU sepod: purata %dm, tertinggi %dm | Memori sepod tertinggi: %dMi\n", s/n, cmax, mmax}' ukur-puncak.txt
```

Contoh output:

```
CPU sepod: purata 160m, tertinggi 175m | Memori sepod tertinggi: 66Mi
```

Hanya satu pod menerima request `/mem`, jadi memori tertinggi datang daripada pod itu. Inilah yang kita mahu: had memori mesti selamat untuk pod yang paling teruk, bukan purata.

### Langkah 4: Kira nilai

Menggunakan contoh output di atas:

| Nilai | Pengiraan | Hasil |
|---|---|---|
| `requests.cpu` | purata normal 55m, bundar ke atas | **`60m`** |
| `requests.memory` | tertinggi normal 24Mi, bundar ke atas | **`32Mi`** |
| `limits.memory` | tertinggi puncak 66Mi × 1.25 = 83Mi, bundar ke atas | **`96Mi`** |
| `limits.cpu` | tertinggi puncak 175m × 1.5 = 263m, atau tidak ditetapkan | **`300m`** atau tiada |

Bandingkan dengan `02-deployment.yaml`. Nilai makmal (`100m`, `64Mi`, `500m`, `256Mi`) sengaja lebih longgar supaya makmal HPA memori, stress test dan OOMKilled dalam Modul 2 berfungsi. **Jangan apply nilai baharu ini**; makmal seterusnya dan Modul 2 bergantung pada nilai asal.

> **Kaitan dengan HPA:** `requests.cpu` ialah "unit" yang HPA guna. Dengan request `60m` dan target 50%, HPA menambah pod setiap kali purata melebihi 30m sepod. Request yang terlalu tinggi menyebabkan HPA lambat atau tidak pernah scale; terlalu rendah menyebabkan HPA scale terlalu awal dan node cepat penuh. Anda akan melihat kesan ini sendiri dalam Makmal 1.5 dan cabaran 1.7 soalan 3.

### Langkah 5: Pulihkan HPA

```bash
kubectl apply -f 06-hpa-cpu.yaml
kubectl -n demo get hpa demo-app
```

Jangkaan: `MINPODS` 1 dan `MAXPODS` 10 semula. Pod turun ke 1 selepas kira-kira 5 minit (stabilization window); anda boleh terus ke Makmal 1.5 tanpa menunggu.

### Di production: ukur lebih lama, dengan alat yang betul

`kubectl top` cukup untuk makmal, tetapi di production ukurlah **sekurang-kurangnya seminggu** supaya waktu puncak sebenar termasuk:

- **Prometheus** (Modul 3 sudah scrape cAdvisor). Contoh query:
  - CPU sepod, persentil ke-90 dalam 7 hari: `quantile_over_time(0.9, (sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="demo",container="app"}[5m])))[7d:5m])`
  - Memori tertinggi dalam 7 hari: `max_over_time(container_memory_working_set_bytes{namespace="demo",container="app"}[7d])`
- **VPA dalam mod cadangan** (`updateMode: "Off"`): Vertical Pod Autoscaler membaca penggunaan sebenar dan mencadangkan nilai requests tanpa mengubah pod. **Goldilocks** memaparkan cadangan VPA itu dalam dashboard.
- **Runtime aplikasi**: JVM, Node.js dan .NET mempunyai had heap sendiri. Selaraskan had heap dengan `limits.memory` (contohnya `-XX:MaxRAMPercentage=75`), jika tidak app boleh OOMKilled walaupun nilai nampak cukup.
- **Semak semula** selepas setiap release besar, kerana penggunaan berubah bila kod berubah.

## Makmal 1.5: HPA v2 berasaskan CPU

HPA dari Makmal 1.1 masih ada. Kini ia sepatutnya dapat membaca metrik:

```bash
kubectl -n demo get hpa demo-app
```

Jangkaan: `cpu: 2%/50%` (atau nilai kecil seumpamanya).

Buka terminal kedua dan pantau:

```bash
kubectl -n demo get hpa demo-app --watch
```

Terminal ketiga:

```bash
kubectl -n demo get pods -l app=demo-app --watch
```

Jana beban ringkas dari dalam kluster (terminal pertama):

```bash
kubectl -n demo run beban --image=busybox:1.36 --restart=Never -- /bin/sh -c \
  'while true; do wget -q -O- "http://demo-app/cpu?ms=200" >/dev/null; done'
```

Dalam 1–2 minit, `TARGETS` akan naik melebihi 50% dan `REPLICAS` bertambah. Lihat sebab keputusan HPA:

```bash
kubectl -n demo describe hpa demo-app | sed -n '/Events/,$p'
```

Jangkaan, sesuatu seperti:

```
Normal  SuccessfulRescale  New size: 4; reason: cpu resource utilization (percentage of request) above target
```

Hentikan beban dan lihat scale-in:

```bash
kubectl -n demo delete pod beban
```

**Soalan:** Kenapa replicas tidak terus turun? (Jawapan: `stabilizationWindowSeconds` scale-down default ialah 300 saat.)

## Makmal 1.6: HPA v2 CPU + memory dengan behavior

```bash
kubectl apply -f 07-hpa-cpu-memory.yaml
kubectl -n demo get hpa demo-app
```

Jangkaan: `cpu: x%/50%, memory: y%/70%`, dan `MINPODS` = 2, jadi replicas naik ke 2 serta-merta.

Picu scale-out melalui **memori** (setiap panggilan memegang 50 MB selama 120 saat):

```bash
for i in 1 2 3 4; do
  kubectl -n demo run mem-$i --image=busybox:1.36 --restart=Never --rm -i -- \
    wget -q -O- "http://demo-app/mem?mb=50&hold=120"; echo
done
kubectl -n demo top pods
kubectl -n demo get hpa demo-app --watch
```

Perhatikan:

- Memori pod naik melebihi 70% daripada `requests.memory` (64Mi), lalu HPA scale-out walaupun CPU rendah. HPA ambil keputusan **tertinggi** antara metrik.
- Selepas 120 saat memori dilepaskan. Scale-in berlaku **1 pod setiap 30 saat** selepas tetingkap 120 saat, mengikut `behavior.scaleDown`.

> **Awas dengan HPA memori:** banyak runtime (JVM, Node.js, Go) tidak memulangkan memori kepada OS selepas beban turun. HPA memori boleh "tersekat" pada replicas tinggi. Gunakan memori sebagai metrik sekunder, dan CPU atau metrik aplikasi (RPS, queue length) sebagai metrik utama.

Lihat `behavior` yang sedang berkuat kuasa:

```bash
kubectl -n demo get hpa demo-app -o yaml | sed -n '/behavior:/,/metrics:/p'
```

## Makmal 1.7 (cabaran): Kawal kadar scale

1. Ubah `07-hpa-cpu-memory.yaml` supaya scale-up dihadkan kepada **2 pod setiap 60 saat**. Jalankan semula beban CPU dari Makmal 1.5 dan bandingkan kelajuan scale-out.
2. Set `scaleDown.selectPolicy: Disabled`. Apa yang berlaku bila beban berhenti? Bila ini berguna? (Contoh: semasa insiden, untuk "bekukan" kapasiti.)
3. Ubah `requests.cpu` kepada `50m` dalam `02-deployment.yaml` dan apply. Dengan beban yang sama, adakah HPA mencipta lebih atau kurang pod? Kenapa?

<details>
<summary>Jawapan cabaran 3</summary>

Lebih banyak pod. Utilization = penggunaan / requests. Bila requests separuh, peratus yang sama penggunaan menjadi dua kali ganda, jadi HPA cipta kira-kira dua kali ganda pod. Requests yang terlalu rendah = over-scaling; terlalu tinggi = pod membazir dan HPA lambat bertindak.
</details>

## Semakan akhir modul

```bash
kubectl -n demo get deploy,hpa,pods,limitrange,resourcequota
```

Senarai semak:

- [ ] `kubectl top pods` berfungsi
- [ ] HPA `demo-app` menunjukkan nilai CPU dan memori (bukan `<unknown>`)
- [ ] Peserta boleh terangkan formula `desiredReplicas`
- [ ] Peserta boleh terangkan beza CPU throttling dan OOMKilled
- [ ] Peserta boleh terangkan cara mendapatkan nilai requests dan limits daripada pengukuran

Biarkan semua sumber ini. Modul 2 bermula dari keadaan ini.

## Rujukan

- HPA walkthrough: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/
- HPA algorithm details: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#algorithm-details
- Metrics Server: https://github.com/kubernetes-sigs/metrics-server
- Resource management: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
