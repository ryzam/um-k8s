# Persediaan Opsyen B: k3d dengan Rancher management server

Opsyen ini untuk peserta yang mengurus kluster melalui **Rancher** di tempat kerja. Rancher dipasang dengan Helm, seperti cara pemasangan production (Rancher atas kluster Kubernetes sendiri, bukan `docker run`). Semua modul tetap berjalan pada kluster `lab`. Halaman ini lengkap dari mencipta kluster `lab` hingga semakan siap; anda tidak perlu mengikut Persediaan Opsyen A.

> **Prasyarat:** semua alat dalam [Persediaan: Pasang semua alat](../README.md#pasang-semua-alat), **termasuk Helm**, sudah dipasang dan [Semak pemasangan](../README.md#semak-pemasangan) lulus. Untuk Docker Desktop, peruntukkan memori seperti dalam [Keperluan tambahan](#keperluan-tambahan).

## Dua cara pasang Rancher

Rancher boleh dipasang dalam kluster **berasingan** daripada kluster beban kerja, atau **sekali** dalam kluster yang sama:

- **Cara 1: berasingan (cadangan).** Dua kluster k3d pada laptop. Kluster `rancher` ialah kluster pengurusan; Rancher dipasang di sini. Kluster `lab` (sama seperti Opsyen A) **didaftarkan (import)** ke Rancher sebagai *downstream cluster*.
- **Cara 2: sekali dengan kluster `lab`.** Satu kluster k3d sahaja. Rancher dipasang terus dalam kluster `lab`, dan Rancher memaparkannya sebagai kluster **`local`**. Tiada import. Sesuai untuk laptop dengan RAM terhad.

| | Cara 1: berasingan | Cara 2: sekali dengan `lab` |
|---|---|---|
| Kluster k3d | Dua: `rancher` dan `lab` | Satu: `lab` (dalam Rancher bernama `local`) |
| RAM laptop / memori Docker | 16 GB / 10 GB | 12 GB / 8 GB (anggaran, belum diukur) |
| Kesan ujian beban Modul 2 | Rancher tidak terjejas. Hanya `cattle-cluster-agent` dan `fleet-agent` yang kecil berjalan pada worker `lab` | Rancher berkongsi CPU dan memori worker dengan app demo. UI Rancher boleh menjadi perlahan semasa ujian stress dan spike, tepat bila peserta mahu melihatnya, dan nombor makmal "node penuh" berubah |
| Kitar semula kluster `lab` | Padam dan cipta semula `lab` (Langkah B2 dan B3) tanpa kehilangan Rancher; kemudian import semula sahaja (Langkah B7) | Padam `lab` bermakna Rancher hilang bersama. Ulang Langkah S2 hingga S6 (kluster dan pemasangan Rancher semula) |
| Realistik berbanding production | Sama seperti amalan biasa: management server berasingan, kluster beban kerja didaftarkan dan diurus melalui tunnel agent | Kurang realistik. Dalam production, kluster `local` dikhaskan untuk Rancher sahaja dan tidak menjalankan beban kerja aplikasi |
| Bilangan langkah | 8: B1 hingga B8 (termasuk cipta `lab` dan import) | 6: B1, S2 hingga S6 (tiada import, tetapi kluster `lab` dicipta dengan config lain) |
| Konsep Rancher yang dipelajari | Import kluster, agent dan tunnel keluar, kubeconfig Rancher, Projects, UI | Kubeconfig Rancher, Projects, UI |

**Pilihan lalai bengkel ialah cara 1.** Guna cara 2 hanya jika laptop tidak cukup RAM untuk dua kluster. Kedua-dua cara bermula dengan **Langkah B1**, kemudian ikut **satu** bahagian sahaja: [Cara 1](#cara-1-rancher-dalam-kluster-berasingan) (B2 hingga B8) atau [Cara 2](#cara-2-rancher-sekali-dalam-kluster-lab) (S2 hingga S6; S = sekali). Setiap bahagian mencipta kluster `lab` sendiri dan berakhir dengan semakan siap.

## Seni bina

Cara 1 (berasingan):

```
 Laptop (Docker)
 ┌─ Kluster k3d "rancher" ───────────────┐          ┌─ Kluster k3d "lab" ──────────────────────────┐
 │  Traefik :443 ── Rancher (cattle-system)│◀──wss────│  cattle-cluster-agent (cattle-system)        │
 │  cert-manager                           │  tunnel  │  fleet-agent (cattle-fleet-system)           │
 └─────────────▲───────────────────────────┘ (keluar) │  demo, monitoring, logging (semua modul)     │
               │ https://rancher.<IP>.sslip.io        └──────────────▲───────────────────────────────┘
   browser + kubectl --context lab ── melalui Rancher ─┘             │ kubectl --context k3d-lab (terus)
```

Perkara penting: agent dalam kluster `lab` membuka sambungan **keluar** ke Rancher dan mengekalkan tunnel. Rancher tidak perlu boleh mencapai API server `lab` secara terus. Itulah sebabnya Rancher boleh mengurus kluster di belakang NAT atau firewall.

Cara 2 (sekali):

```
 Laptop (Docker)
 ┌─ Kluster k3d "lab" (Rancher di dalam; dalam Rancher bernama "local") ───────────────┐
 │  Traefik :443 ── Rancher (cattle-system) ── API server (dalam kluster yang sama)     │
 │  cert-manager · fleet (cattle-fleet-system, cattle-fleet-local-system)               │
 │  demo, monitoring, logging (semua modul)  ◀── berkongsi worker agent-0 dan agent-1   │
 └──────────▲──────────────────────────────────────────────────────▲──────────────────┘
            │ https://rancher.<IP>.sslip.io                          │ kubectl --context k3d-lab (terus)
   browser + kubectl --context local ── melalui Rancher
```

Dalam cara 2 tiada tunnel: Rancher bercakap dengan API server kluster yang menempatkannya. Pod Rancher berjalan pada worker yang sama dengan app demo, kerana control-plane mempunyai taint `NoSchedule`.

## Keperluan tambahan

| Item | Cara 1 | Cara 2 |
|---|---|---|
| RAM laptop | 16 GB minimum (Docker Desktop: peruntukkan 10 GB) | 12 GB minimum, 16 GB disyorkan (Docker Desktop: 8 GB) |
| Port 443 laptop | Mesti kosong (Rancher didedahkan di sini) | Sama |
| Internet | Perlu untuk DNS `sslip.io` dan repo Helm | Sama |
| Helm | v3.18 atau lebih baharu | Sama |

| Komponen | Versi rujukan |
|---|---|
| Rancher | v2.13.10 (Helm chart `rancher-stable/rancher`) |
| cert-manager | v1.19.6 |
| k3s (semua kluster) | v1.33.1+k3s1 |

> Versi Rancher yang lebih baharu biasanya boleh digunakan. Semak [support matrix Rancher](https://www.suse.com/suse-rancher/support-matrix/) untuk versi Kubernetes yang disokong, dan senarai versi chart dengan `helm search repo rancher-stable/rancher --versions`.

## Langkah B1: Tentukan hostname Rancher

*Kedua-dua cara.*

Rancher memerlukan satu URL yang boleh dicapai dari **browser anda** dan dari **pod dalam kluster**. `localhost` tidak sesuai: dalam pod, `localhost` ialah pod itu sendiri. Kita guna IP laptop dengan DNS wildcard [sslip.io](https://sslip.io) (`rancher.192-168-1-10.sslip.io` → `192.168.1.10`), jadi tiada fail `/etc/hosts` perlu diubah.

```bash
# Folder bengkel: lihat Dapatkan bahan bengkel dalam halaman Persediaan
cd ~/bengkel-k8s/00-persediaan/rancher
eval "$(bash hostname-rancher.sh)"
echo "$LAPTOP_IP  $RANCHER_HOST"
nslookup "$RANCHER_HOST"            # mesti memulangkan $LAPTOP_IP
```

> **IP laptop berubah** bila anda bertukar rangkaian Wi-Fi, dan URL Rancher akan putus. Buat persediaan ini pada rangkaian yang akan digunakan semasa bengkel. WSL2: jalankan skrip dalam WSL; browser Windows boleh mencapai IP WSL tersebut.

Cara 1: teruskan ke [Langkah B2](#langkah-b2-cipta-kluster-lab). Cara 2: lompat ke [Langkah S2](#langkah-s2-cipta-kluster-lab-dengan-traefik-dan-port-443).

Semua arahan seterusnya dijalankan dari folder `00-persediaan/rancher`.

---

## Cara 1: Rancher dalam kluster berasingan

### Langkah B2: Cipta kluster `lab`

Kluster `lab` cara 1 sama dengan kluster Opsyen A: fail [`../k3d-cluster.yaml`](../k3d-cluster.yaml) (1 server, 2 agent, k3s v1.33.1, API `127.0.0.1:6550`, NodePort 30080 hingga 30082).

```bash
k3d cluster create --config ../k3d-cluster.yaml
kubectl config current-context        # k3d-lab
kubectl get nodes                     # k3d-lab-server-0, k3d-lab-agent-0, k3d-lab-agent-1: Ready
```

Sahkan kluster berfungsi seperti yang diandaikan oleh modul. Jadual ini menerangkan apa yang k3d sediakan dan cara menyemaknya:

| Perkara | Nilai dalam makmal | Cara semak | Digunakan dalam |
|---|---|---|---|
| Nama node (sama dengan nama container Docker) | `k3d-lab-server-0`, `k3d-lab-agent-0`, `k3d-lab-agent-1` | `kubectl get nodes` | Modul 3 (Prometheus), Modul 4 (drain) |
| Context kubectl | `k3d-lab` | `kubectl config current-context` | Semua modul |
| Rangkaian Docker | `k3d-lab` | `docker network ls` | Stack luar Modul 3 & 4 disambung ke sini |
| Taint control-plane | `node-role.kubernetes.io/control-plane:NoSchedule` | `kubectl describe node k3d-lab-server-0` | Pod aplikasi hanya pada 2 agent, seperti kluster sebenar |
| Dimatikan | Traefik, Metrics Server terbina dalam k3s | `kubectl -n kube-system get pods` | Metrics Server dipasang sendiri dalam Modul 1 |

```bash
kubectl --context k3d-lab get nodes -o wide
kubectl --context k3d-lab describe node k3d-lab-server-0 | grep Taints
docker network ls --filter name=k3d-lab
kubectl --context k3d-lab -n kube-system get pods
```

Jangkaan:

- 3 node `Ready`; `server-0` berperanan `control-plane,master`, dua agent `<none>`
- `Taints: node-role.kubernetes.io/control-plane:NoSchedule`
- Satu rangkaian bernama `k3d-lab`
- `coredns` dan `local-path-provisioner` `Running`; **tiada** `traefik` atau `metrics-server`

### Langkah B3: Pra-muat image dan uji app demo

`k3d image import` menyalin image dari Docker laptop ke dalam setiap node, jadi pod tidak perlu menarik dari internet semasa bengkel.

```bash
IMAGES="python:3.12-slim busybox:1.36 nginx:1.27-alpine grafana/k6:1.0.0 \
  registry.k8s.io/metrics-server/metrics-server:v0.7.2 \
  registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.15.0 \
  quay.io/prometheus/node-exporter:v1.9.1 fluent/fluent-bit:4.0.3"
for img in $IMAGES; do docker pull "$img"; done
k3d image import $IMAGES -c lab

# Image stack luar (Modul 3 & 4)
for img in prom/prometheus:v3.4.0 prom/alertmanager:v0.28.1 grafana/grafana:12.0.0 axllent/mailpit:v1.25 \
           grafana/loki:3.5.0 chrislusf/seaweedfs:3.85 amazon/aws-cli:2.27.0 locustio/locust:2.37.0 \
           curlimages/curl:8.13.0; do
  docker pull "$img"
done
```

Uji app demo (deploy yang sebenar dalam Modul 1, Makmal 1.1):

```bash
kubectl --context k3d-lab apply -f ../namespace.yaml -f ../demo-app/configmap.yaml
kubectl --context k3d-lab apply -f ../../modul-1-hpa/02-deployment.yaml -f ../../modul-1-hpa/03-service.yaml
kubectl --context k3d-lab -n demo rollout status deploy/demo-app
curl -s localhost:30080/ ; echo        # {"pod": "demo-app-xxxxx", "version": "v1", "uptime_s": 5}
```

App demo ialah satu app Python kecil ([`demo-app/app.py`](../demo-app/app.py)) yang dimuatkan melalui ConfigMap ke dalam image `python:3.12-slim`, jadi tiada image perlu dibina. App ini ada endpoint khas untuk makmal:

| Endpoint | Kegunaan dalam bengkel |
|---|---|
| `/` | Pulangkan nama pod dan versi (rolling update, canary) |
| `/cpu?ms=100` | Bakar CPU selama N ms (HPA CPU, ujian beban) |
| `/mem?mb=50&hold=60` | Pegang N MB memori selama `hold` saat (HPA memori, OOMKilled) |
| `/healthz`, `/readyz` | Liveness & readiness probe |
| `/metrics` | Metrik Prometheus `demo_http_requests_total` (Modul 3) |
| `/crash` | Tamatkan proses dengan exit 1 (troubleshooting) |

Uji endpoint yang digunakan dalam modul, dan sahkan pod berjalan pada agent (bukan server, kerana taint):

```bash
curl -s "localhost:30080/cpu?ms=50" ; echo
curl -s localhost:30080/readyz ; echo
curl -s localhost:30080/metrics | grep demo_http_requests_total
kubectl --context k3d-lab -n demo get pods -o wide
```

Jangkaan:

```
{"pod": "demo-app-xxxxx", "version": "v1", "cpu_ms": 50}
{"ready": true}
demo_http_requests_total{path="/",code="200",version="v1"} 1
demo_http_requests_total{path="/cpu",code="200",version="v1"} 1
...
```

Lajur `NODE` menunjukkan `k3d-lab-agent-0` atau `k3d-lab-agent-1`. Kiraan metrik mungkin berbeza kerana probe dan request anda boleh sampai ke pod yang berlainan.

Env: `VERSION`, `STARTUP_DELAY`, `SHUTDOWN_DELAY`, `FAIL_RATE` (lihat docstring dalam `app.py`). Jika anda mengubah `app.py`, jana semula ConfigMap (masih dari folder `rancher`, supaya langkah seterusnya tidak terjejas):

```bash
kubectl --context k3d-lab create configmap demo-app-code -n demo --from-file=../demo-app/app.py --dry-run=client -o yaml > ../demo-app/configmap.yaml
kubectl --context k3d-lab apply -f ../demo-app/configmap.yaml && kubectl --context k3d-lab -n demo rollout restart deploy/demo-app
```

### Langkah B4: Cipta kluster `rancher`

```bash
k3d cluster create --config k3d-rancher.yaml
kubectl --context k3d-rancher get nodes
kubectl config current-context          # masih k3d-lab
```

Jangkaan: node `k3d-rancher-server-0` `Ready`. Traefik dibiarkan aktif dalam kluster ini kerana ia menjadi ingress untuk Rancher. Fail: [`k3d-rancher.yaml`](k3d-rancher.yaml).

### Langkah B5: Pasang cert-manager dan Rancher dengan Helm

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update

helm --kube-context k3d-rancher install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace --version v1.19.6 --set crds.enabled=true
kubectl --context k3d-rancher -n cert-manager rollout status deploy/cert-manager-webhook

helm --kube-context k3d-rancher install rancher rancher-stable/rancher \
  -n cattle-system --create-namespace --version 2.13.10 \
  -f rancher-values.yaml --set hostname="$RANCHER_HOST"
kubectl --context k3d-rancher -n cattle-system rollout status deploy/rancher --timeout=15m
```

Rancher mengambil 3 hingga 8 minit untuk bermula kali pertama. Fail nilai: [`rancher-values.yaml`](rancher-values.yaml) (1 replica, sijil self-signed, kata laluan bootstrap).

Semak:

```bash
kubectl --context k3d-rancher -n cattle-system get pods
kubectl --context k3d-rancher -n cattle-system get ingress rancher
curl -sk "https://$RANCHER_HOST/ping" ; echo     # pong
```

### Langkah B6: Log masuk

1. Buka `https://$RANCHER_HOST` dalam browser. Terima amaran sijil (sijil self-signed makmal).
2. Kata laluan bootstrap: `bengkel-rancher-123`. Tetapkan kata laluan baharu.
3. Pastikan **Server URL** ialah `https://rancher.<IP-anda>.sslip.io`. Agent kluster `lab` akan menyambung ke URL ini.

Anda akan melihat satu kluster bernama **local**: itulah kluster `rancher` sendiri.

### Langkah B7: Import kluster `lab` ke Rancher

1. ☰ → **Cluster Management** → **Import Existing** → **Generic**.
2. **Cluster Name**: `lab` → **Create**.
3. Rancher memaparkan beberapa arahan. Kerana sijil Rancher self-signed, salin arahan yang menggunakan `curl --insecure`, dan jalankan terhadap context `k3d-lab`:

```bash
curl --insecure -sfL https://$RANCHER_HOST/v3/import/<token-anda>.yaml | kubectl --context k3d-lab apply -f -
kubectl --context k3d-lab -n cattle-system get pods -w
```

Jangkaan: pod `cattle-cluster-agent-...` `Running`, dan dalam 2 hingga 5 minit kluster `lab` berstatus **Active** di Cluster Management. Rancher juga memasang `fleet-agent` dalam namespace `cattle-fleet-system`.

```bash
kubectl --context k3d-lab get ns | grep cattle
```

### Langkah B8: kubectl melalui Rancher

Di Rancher, buka kluster **lab** → ikon **Download KubeConfig** (penjuru kanan atas). Simpan sebagai `~/.kube/rancher-lab.yaml`.

```bash
export KUBECONFIG=$HOME/.kube/config:$HOME/.kube/rancher-lab.yaml
kubectl config get-contexts
kubectl --context lab get nodes
kubectl --context lab -n demo get pods
```

Kini ada dua laluan ke kluster yang sama:

| Context | Laluan | Pengesahan |
|---|---|---|
| `k3d-lab` | kubectl → API server k3d (`127.0.0.1:6550`) | Sijil admin k3s (akses penuh) |
| `lab` | kubectl → Rancher → tunnel agent → API server | Token pengguna Rancher; RBAC Rancher dan audit log Rancher berkuat kuasa |

Untuk bengkel, guna context **`lab`** secara lalai (`kubectl config use-context lab`), kecuali di tempat yang dinyatakan dalam [jadual perubahan modul](#perubahan-dalam-modul).

### Semakan siap: Opsyen B cara 1

- [ ] `kubectl --context k3d-lab get nodes` menunjukkan 3 node `Ready`, dan `curl -s localhost:30080/` memulangkan app demo
- [ ] `kubectl --context k3d-rancher -n cattle-system get pods` menunjukkan `rancher` `Running`
- [ ] UI Rancher boleh dibuka di `https://rancher.<IP>.sslip.io`
- [ ] Kluster `lab` berstatus **Active** di Cluster Management
- [ ] `kubectl --context lab -n demo get pods` berfungsi melalui Rancher

Semua lulus? Persediaan anda siap. Baca [Perubahan dalam modul](#perubahan-dalam-modul) sekali, kemudian **seterusnya: [Modul 1: Workload Autoscaling & HPA](../../modul-1-hpa/README.md).**

---

## Cara 2: Rancher sekali dalam kluster `lab`

### Langkah S2: Cipta kluster `lab` dengan Traefik dan port 443

Kluster `lab` Opsyen A mematikan Traefik dan tidak mendedahkan port 443, kerana makmal tidak memerlukan ingress. Rancher pula memerlukan ingress. Fail [`k3d-lab-rancher.yaml`](k3d-lab-rancher.yaml) sama dengan [`../k3d-cluster.yaml`](../k3d-cluster.yaml) kecuali dua perkara:

| Tetapan | `k3d-cluster.yaml` (Opsyen A, cara 1) | `k3d-lab-rancher.yaml` (cara 2) |
|---|---|---|
| Traefik | Dimatikan (`--disable=traefik`) | Aktif, menjadi ingress untuk Rancher |
| Port 443 laptop | Tidak dipetakan | `443:443` ke loadbalancer k3d (`k3d-lab-serverlb`) |
| Nama kluster, node, rangkaian Docker, context, API `127.0.0.1:6550`, NodePort 30080 hingga 30082, taint control-plane, Metrics Server dimatikan | Sama | Sama |

Kerana nama dan port tidak berubah, semua fail YAML, skrip dan `prometheus.yml` dalam modul boleh digunakan tanpa diubah.

Jika kluster `lab` sudah wujud (contohnya dicipta dengan `k3d-cluster.yaml`), padam dahulu dengan `k3d cluster delete lab`. Kemudian:

```bash
k3d cluster create --config k3d-lab-rancher.yaml
kubectl config current-context                        # k3d-lab
kubectl get nodes                                     # 3 node Ready, nama sama seperti Opsyen A
docker ps --filter name=k3d-lab-serverlb --format '{{.Ports}}'   # mesti ada 0.0.0.0:443->443/tcp
kubectl -n kube-system rollout status deploy/traefik
kubectl -n kube-system get svc traefik                # TYPE LoadBalancer, EXTERNAL-IP = IP node
```

Sahkan kluster berfungsi seperti yang diandaikan oleh modul. Jadual ini menerangkan apa yang k3d sediakan dan cara menyemaknya:

| Perkara | Nilai dalam makmal | Cara semak | Digunakan dalam |
|---|---|---|---|
| Nama node (sama dengan nama container Docker) | `k3d-lab-server-0`, `k3d-lab-agent-0`, `k3d-lab-agent-1` | `kubectl get nodes` | Modul 3 (Prometheus), Modul 4 (drain) |
| Context kubectl | `k3d-lab` | `kubectl config current-context` | Semua modul |
| Rangkaian Docker | `k3d-lab` | `docker network ls` | Stack luar Modul 3 & 4 disambung ke sini |
| Taint control-plane | `node-role.kubernetes.io/control-plane:NoSchedule` | `kubectl describe node k3d-lab-server-0` | Pod aplikasi hanya pada 2 agent, seperti kluster sebenar |
| Traefik | Aktif (ingress untuk Rancher) | `kubectl -n kube-system get deploy traefik` | Rancher |
| Metrics Server terbina dalam k3s | Dimatikan | `kubectl -n kube-system get pods` | Dipasang sendiri dalam Modul 1 |

```bash
kubectl --context k3d-lab get nodes -o wide
kubectl --context k3d-lab describe node k3d-lab-server-0 | grep Taints
docker network ls --filter name=k3d-lab
kubectl --context k3d-lab -n kube-system get pods
```

Jangkaan:

- 3 node `Ready`; `server-0` berperanan `control-plane,master`, dua agent `<none>`
- `Taints: node-role.kubernetes.io/control-plane:NoSchedule`
- Satu rangkaian bernama `k3d-lab`
- `coredns`, `local-path-provisioner` dan `traefik` `Running`; pod `helm-install-traefik*` `Completed`; **tiada** `metrics-server`

### Langkah S3: Pra-muat image dan uji app demo

`k3d image import` menyalin image dari Docker laptop ke dalam setiap node, jadi pod tidak perlu menarik dari internet semasa bengkel.

```bash
IMAGES="python:3.12-slim busybox:1.36 nginx:1.27-alpine grafana/k6:1.0.0 \
  registry.k8s.io/metrics-server/metrics-server:v0.7.2 \
  registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.15.0 \
  quay.io/prometheus/node-exporter:v1.9.1 fluent/fluent-bit:4.0.3"
for img in $IMAGES; do docker pull "$img"; done
k3d image import $IMAGES -c lab

# Image stack luar (Modul 3 & 4)
for img in prom/prometheus:v3.4.0 prom/alertmanager:v0.28.1 grafana/grafana:12.0.0 axllent/mailpit:v1.25 \
           grafana/loki:3.5.0 chrislusf/seaweedfs:3.85 amazon/aws-cli:2.27.0 locustio/locust:2.37.0 \
           curlimages/curl:8.13.0; do
  docker pull "$img"
done
```

Uji app demo (deploy yang sebenar dalam Modul 1, Makmal 1.1):

```bash
kubectl --context k3d-lab apply -f ../namespace.yaml -f ../demo-app/configmap.yaml
kubectl --context k3d-lab apply -f ../../modul-1-hpa/02-deployment.yaml -f ../../modul-1-hpa/03-service.yaml
kubectl --context k3d-lab -n demo rollout status deploy/demo-app
curl -s localhost:30080/ ; echo        # {"pod": "demo-app-xxxxx", "version": "v1", "uptime_s": 5}
```

App demo ialah satu app Python kecil ([`demo-app/app.py`](../demo-app/app.py)) yang dimuatkan melalui ConfigMap ke dalam image `python:3.12-slim`, jadi tiada image perlu dibina. App ini ada endpoint khas untuk makmal:

| Endpoint | Kegunaan dalam bengkel |
|---|---|
| `/` | Pulangkan nama pod dan versi (rolling update, canary) |
| `/cpu?ms=100` | Bakar CPU selama N ms (HPA CPU, ujian beban) |
| `/mem?mb=50&hold=60` | Pegang N MB memori selama `hold` saat (HPA memori, OOMKilled) |
| `/healthz`, `/readyz` | Liveness & readiness probe |
| `/metrics` | Metrik Prometheus `demo_http_requests_total` (Modul 3) |
| `/crash` | Tamatkan proses dengan exit 1 (troubleshooting) |

Uji endpoint yang digunakan dalam modul, dan sahkan pod berjalan pada agent (bukan server, kerana taint):

```bash
curl -s "localhost:30080/cpu?ms=50" ; echo
curl -s localhost:30080/readyz ; echo
curl -s localhost:30080/metrics | grep demo_http_requests_total
kubectl --context k3d-lab -n demo get pods -o wide
```

Jangkaan:

```
{"pod": "demo-app-xxxxx", "version": "v1", "cpu_ms": 50}
{"ready": true}
demo_http_requests_total{path="/",code="200",version="v1"} 1
demo_http_requests_total{path="/cpu",code="200",version="v1"} 1
...
```

Lajur `NODE` menunjukkan `k3d-lab-agent-0` atau `k3d-lab-agent-1`. Kiraan metrik mungkin berbeza kerana probe dan request anda boleh sampai ke pod yang berlainan.

Env: `VERSION`, `STARTUP_DELAY`, `SHUTDOWN_DELAY`, `FAIL_RATE` (lihat docstring dalam `app.py`). Jika anda mengubah `app.py`, jana semula ConfigMap (masih dari folder `rancher`, supaya langkah seterusnya tidak terjejas):

```bash
kubectl --context k3d-lab create configmap demo-app-code -n demo --from-file=../demo-app/app.py --dry-run=client -o yaml > ../demo-app/configmap.yaml
kubectl --context k3d-lab apply -f ../demo-app/configmap.yaml && kubectl --context k3d-lab -n demo rollout restart deploy/demo-app
```

### Langkah S4: Pasang cert-manager dan Rancher dalam kluster `lab`

Arahan sama seperti Langkah B5 cara 1, tetapi sasarannya `k3d-lab`:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update

helm --kube-context k3d-lab install cert-manager jetstack/cert-manager \
  -n cert-manager --create-namespace --version v1.19.6 --set crds.enabled=true
kubectl --context k3d-lab -n cert-manager rollout status deploy/cert-manager-webhook

helm --kube-context k3d-lab install rancher rancher-stable/rancher \
  -n cattle-system --create-namespace --version 2.13.10 \
  -f rancher-values.yaml --set hostname="$RANCHER_HOST"
kubectl --context k3d-lab -n cattle-system rollout status deploy/rancher --timeout=15m
```

Semak:

```bash
kubectl --context k3d-lab -n cattle-system get pods -o wide   # pod rancher pada k3d-lab-agent-0 atau agent-1
kubectl --context k3d-lab -n cattle-system get ingress rancher
curl -sk "https://$RANCHER_HOST/ping" ; echo                  # pong
```

Perhatikan kolum `NODE`: pod Rancher berjalan pada worker yang sama dengan app demo. Selepas Rancher bermula, ia juga memasang komponen lain (fleet, rancher-webhook) dalam kluster ini; `kubectl --context k3d-lab get ns` menunjukkan beberapa namespace `cattle-*` dan `fleet-*`.

### Langkah S5: Log masuk

1. Buka `https://$RANCHER_HOST`, terima amaran sijil.
2. Kata laluan bootstrap: `bengkel-rancher-123`. Tetapkan kata laluan baharu.
3. Server URL: `https://rancher.<IP-anda>.sslip.io`.

Anda akan melihat satu kluster bernama **local**: dalam cara 2, itulah kluster `lab` sendiri. Tiada langkah import. Buka **local** → **Workloads**, pilih namespace `demo`, dan anda akan melihat `demo-app`.

### Langkah S6: kubectl melalui Rancher

Di Rancher, buka kluster **local** → ikon **Download KubeConfig**. Simpan sebagai `~/.kube/rancher-local.yaml`.

```bash
export KUBECONFIG=$HOME/.kube/config:$HOME/.kube/rancher-local.yaml
kubectl config get-contexts
kubectl --context local get nodes          # node k3d-lab-*
kubectl --context local -n demo get pods
```

| Context | Laluan | Pengesahan |
|---|---|---|
| `k3d-lab` | kubectl → API server k3d (`127.0.0.1:6550`) | Sijil admin k3s (akses penuh) |
| `local` | kubectl → Rancher (dalam kluster `lab`) → API server | Token pengguna Rancher; RBAC Rancher dan audit log Rancher berkuat kuasa |

Untuk bengkel, guna context **`local`** secara lalai (`kubectl config use-context local`). Di mana-mana jadual dan nota modul menyebut context `lab`, cara 2 menggunakan `local`.

### Semakan siap: Opsyen B cara 2

- [ ] `kubectl --context k3d-lab -n cattle-system get pods` menunjukkan `rancher` `Running`
- [ ] UI Rancher boleh dibuka di `https://rancher.<IP>.sslip.io`, dan kluster **local** menunjukkan node `k3d-lab-*`
- [ ] `kubectl --context local -n demo get pods` berfungsi melalui Rancher
- [ ] `curl -s localhost:30080/` masih memulangkan app demo

Semua lulus? Persediaan anda siap. Baca [Perubahan dalam modul](#perubahan-dalam-modul) sekali, kemudian **seterusnya: [Modul 1: Workload Autoscaling & HPA](../../modul-1-hpa/README.md).**

---

## Perubahan dalam modul

Semua fail YAML dan skrip sama untuk kedua-dua opsyen dan kedua-dua cara. Hanya perkara berikut berbeza untuk Opsyen B. "Context Rancher" bermaksud `lab` (cara 1) atau `local` (cara 2).

| Modul | Apa yang berubah (kedua-dua cara) | Tambahan untuk cara 2 |
|---|---|---|
| Persediaan | Kluster `lab` dicipta dengan `k3d-cluster.yaml` yang sama seperti Opsyen A (Langkah B2) | Kluster `lab` dicipta dengan `rancher/k3d-lab-rancher.yaml`, bukan `k3d-cluster.yaml` (Langkah S2: Traefik aktif, port 443). Nama node, rangkaian Docker `k3d-lab`, context `k3d-lab` dan port lain tidak berubah |
| Semua | Arahan `kubectl` dijalankan dengan context Rancher. Hasil arahan sama. `kubectl port-forward` dan `exec` berfungsi melalui Rancher tetapi lebih perlahan; untuk port-forward yang lama, guna `k3d-lab`. | Context Rancher bernama `local`, bukan `lab`. `kubectl get pods -A` dan `kubectl get ns` menunjukkan lebih banyak namespace (`cattle-*`, `fleet-*`, `cert-manager`) |
| Modul 1: HPA | Metrics Server tetap dipasang seperti biasa (Rancher tidak memasangnya). Selepas itu, dashboard kluster di Rancher menunjukkan graf CPU dan memori, dan HPA boleh dilihat di **Service Discovery → HorizontalPodAutoscalers**. **Jangan** masukkan namespace `demo` ke dalam Rancher Project yang mempunyai Resource Quota: Rancher akan mencipta ResourceQuota dan LimitRange tambahan yang bercanggah dengan Makmal 1.2. | `kubectl top pods -A` menunjukkan pod Rancher sebagai antara pengguna memori terbesar pada worker. Ini contoh yang baik untuk perbincangan: beban kerja lain berkongsi node dengan app anda |
| Modul 2: Load testing | k6 dan Locust tetap menghantar trafik terus ke `localhost:30080`, bukan melalui Rancher. Agent Rancher (cara 1) atau Rancher sendiri (cara 2) menggunakan kapasiti worker, jadi nombor dalam makmal "node penuh" mungkin berbeza. Semak dengan `kubectl describe node k3d-lab-agent-0` → *Allocated resources*. | Kesan lebih besar: Rancher, cert-manager dan fleet berjalan pada worker yang sama dengan app demo. Semasa ujian stress dan spike, UI Rancher boleh menjadi perlahan atau tidak responsif; perhatikan HPA dengan `watch-hpa.sh` (context `k3d-lab`), bukan UI. Kurangkan `maxReplicas` atau VU jika laptop terhimpit |
| Modul 3: Monitoring | Prometheus luar bercakap **terus** dengan API server k3d (`k3d-lab-server-0:6443`) menggunakan token ServiceAccount, bukan melalui Rancher. Jalankan `get-k8s-credentials.sh` dengan context `k3d-lab`. **Jangan** pasang app **Monitoring** Rancher semasa bengkel: ia memasang Prometheus, Grafana dan node-exporter kedua dalam kluster (kira-kira 2 GB RAM) dan mengelirukan perbandingan. Ia sesuai sebagai demo selepas bengkel: monitoring dalam kluster yang diurus Rancher berbanding monitoring luar. | kube-state-metrics dan cAdvisor juga melaporkan pod Rancher. Alert seluruh kluster (contohnya pod tidak Running) boleh menyala untuk namespace `cattle-*` semasa Rancher bermula atau dinaik taraf; tapis dengan label `namespace` jika mengganggu |
| Modul 4: Day-2 Ops | Rolling update dan rollback juga boleh dibuat dari UI (**Workloads** → ⋮ → **Redeploy** / **Rollback**), dan drain dari **Nodes** → ⋮ → **Drain**. Buat dengan kubectl dahulu, kemudian bandingkan dengan UI. Untuk Makmal 4.4 (drain), guna context `k3d-lab` supaya akses kubectl tidak bergantung pada Rancher atau agent yang mungkin turut diusir dari node. **Jangan** pasang app **Logging** Rancher serentak dengan Fluent Bit makmal: ia memasang pengumpul log kedua yang membaca fail log yang sama. | Drain worker yang menempatkan pod Rancher (semak dengan `kubectl -n cattle-system get pods -o wide`) mengusir Rancher itu sendiri: UI dan context `local` putus sehingga pod bermula semula pada worker lain. Jangan drain dari UI Rancher dalam cara 2. `kubectl get priorityclass` juga menunjukkan PriorityClass milik Rancher di samping yang dicipta dalam makmal eviction |
| Troubleshooting | UI Rancher memudahkan melihat events dan log pod, tetapi selesaikan setiap kes dengan kubectl dahulu; itulah alat yang ada bila Rancher sendiri bermasalah. | Sama |

## Masalah lazim

| Gejala | Punca | Penyelesaian |
|---|---|---|
| Browser tidak dapat membuka Rancher | Port 443 digunakan aplikasi lain, atau IP laptop berubah | `docker ps` (semak `k3d-rancher-serverlb` untuk cara 1 atau `k3d-lab-serverlb` untuk cara 2 → `0.0.0.0:443`); jalankan semula Langkah B1. Jika IP berubah: cara 1, padam kluster `rancher` dan ulang B1, B4 hingga B7; cara 2, cipta semula `lab` dan ulang B1, S2 hingga S6 |
| Cara 2: ingress `rancher` tiada ADDRESS, atau `curl` ke port 443 ditolak | Kluster `lab` dicipta dengan `k3d-cluster.yaml` (Traefik dimatikan, port 443 tidak dipetakan) | `kubectl -n kube-system get deploy traefik`. Jika tiada, cipta semula `lab` dengan `k3d-lab-rancher.yaml` (Langkah S2) |
| Cara 1: kluster `lab` kekal *Pending* / *Waiting for API* | Agent tidak dapat mencapai Rancher | `kubectl --context k3d-lab -n cattle-system logs deploy/cattle-cluster-agent --tail=20` |
| Cara 1: log agent `no such host` | DNS dalam kluster tidak dapat menyelesaikan `sslip.io` (rangkaian syarikat menyekat DNS luar) | Tambah entri DNS untuk Rancher dalam CoreDNS kluster `lab` (lihat di bawah) |
| Cara 1: log agent `x509: certificate signed by unknown authority` | Kluster diimport dengan arahan tanpa `--insecure` atau tanpa checksum CA | Padam kluster `lab` di Rancher, import semula dengan arahan `curl --insecure` |
| Pod `rancher` `CrashLoopBackOff` / `OOMKilled` | Memori Docker tidak cukup | Naikkan memori Docker Desktop; tutup aplikasi lain. Cara 2: kurangkan beban dalam Modul 2, atau tukar ke cara 1 jika RAM mencukupi |
| Cara 2: UI Rancher perlahan semasa Modul 2 | Rancher berkongsi worker dengan pod yang sedang diuji | Dijangka. Guna kubectl dengan context `k3d-lab` untuk memerhati; UI pulih selepas beban berhenti |

Entri DNS manual (hanya jika `sslip.io` tidak dapat diselesaikan dari pod):

```bash
kubectl --context k3d-lab -n kube-system create configmap coredns-custom \
  --from-literal=rancher.server="$RANCHER_HOST:53 {
    hosts {
      $LAPTOP_IP $RANCHER_HOST
    }
}"
kubectl --context k3d-lab -n kube-system rollout restart deploy/coredns
```

Untuk browser, tambah `$LAPTOP_IP $RANCHER_HOST` ke `/etc/hosts` laptop.

## Reset & buang

Cara 1:

```bash
k3d cluster delete rancher
```

Kluster `lab` masih mengandungi agent Rancher (`cattle-system`, `cattle-fleet-system`). Cara paling bersih ialah mencipta semula kluster `lab` (Langkah B2 dan B3).

Cara 2: `helm uninstall rancher` tidak membuang semua sumber yang Rancher cipta (CRD, namespace `cattle-*` dan `fleet-*`). Cara paling bersih ialah mencipta semula `lab`: dengan `k3d-cluster.yaml` untuk kembali ke Opsyen A, atau dengan `k3d-lab-rancher.yaml` dan ulang Langkah S3 hingga S6 untuk kekal dengan cara 2.

```bash
k3d cluster delete lab
k3d cluster create --config ../k3d-cluster.yaml          # atau: --config k3d-lab-rancher.yaml
```

Buang semuanya selepas bengkel:

```bash
kubectl --context k3d-lab delete namespace demo   # reset namespace demo sahaja, jika perlu
k3d cluster delete lab
k3d cluster delete rancher                         # cara 1 sahaja
(cd ~/bengkel-k8s/modul-3-monitoring/external && docker compose down -v)
(cd ~/bengkel-k8s/modul-4-operations/logging/external && docker compose down -v)
```
