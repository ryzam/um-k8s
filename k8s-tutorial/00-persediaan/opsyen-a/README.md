# Persediaan Opsyen A: k3d sahaja

Satu kluster k3d `lab` pada laptop, dan kubectl bercakap terus dengan API server k3d. Halaman ini lengkap dari mencipta kluster hingga semakan siap (~15 minit).

> **Prasyarat:** semua alat dalam [Persediaan: Pasang semua alat](../README.md#pasang-semua-alat) sudah dipasang dan [Semak pemasangan](../README.md#semak-pemasangan) lulus. Helm tidak diperlukan untuk Opsyen A.

Folder bengkel (`~/bengkel-k8s`) mesti sudah ada: lihat [Dapatkan bahan bengkel](../README.md#dapatkan-bahan-bengkel). Semua arahan di halaman ini dijalankan dari `~/bengkel-k8s/00-persediaan`.

## Langkah A1: Cipta kluster `lab`

Fail [`k3d-cluster.yaml`](../k3d-cluster.yaml) mencipta 1 server (control-plane) dan 2 agent (worker) dengan k3s v1.33.1, memetakan NodePort 30080 hingga 30082 ke `localhost`, dan mendedahkan API server pada `127.0.0.1:6550`.

```bash
cd ~/bengkel-k8s/00-persediaan
k3d cluster create --config k3d-cluster.yaml
kubectl config current-context        # k3d-lab
kubectl get nodes
```

Jangkaan:

```
NAME               STATUS   ROLES                  AGE   VERSION
k3d-lab-agent-0    Ready    <none>                 1m    v1.33.1+k3s1
k3d-lab-agent-1    Ready    <none>                 1m    v1.33.1+k3s1
k3d-lab-server-0   Ready    control-plane,master   1m    v1.33.1+k3s1
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
kubectl get nodes -o wide
kubectl describe node k3d-lab-server-0 | grep Taints
docker network ls --filter name=k3d-lab
kubectl -n kube-system get pods
```

Jangkaan:

- 3 node `Ready`; `server-0` berperanan `control-plane,master`, dua agent `<none>`
- `Taints: node-role.kubernetes.io/control-plane:NoSchedule`
- Satu rangkaian bernama `k3d-lab`
- `coredns` dan `local-path-provisioner` `Running`; **tiada** `traefik` atau `metrics-server`

> **Mengguna minikube?** `minikube start --nodes 3 --cpus 2 --memory 4096 -p lab`. Perbezaan utama: NodePort tidak dipetakan ke `localhost`, jadi guna `minikube service <svc> -n <ns> --url -p lab` untuk dapatkan URL. Metrics Server: `minikube addons enable metrics-server -p lab`. Untuk Modul 3, gantikan `k3d-lab-server-0:6443` dan `k3d-lab-agent-0` dalam `prometheus.yml` dengan IP dari `minikube ip -p lab`.

## Langkah A2: Pra-muat image (jimat masa & bandwidth semasa bengkel)

`k3d image import` menyalin image dari Docker laptop ke dalam containerd setiap node, jadi pod tidak perlu menarik dari internet.

```bash
IMAGES="python:3.12-slim busybox:1.36 nginx:1.27-alpine grafana/k6:1.0.0 \
  registry.k8s.io/metrics-server/metrics-server:v0.7.2 \
  registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.15.0 \
  quay.io/prometheus/node-exporter:v1.9.1 fluent/fluent-bit:4.0.3"
for img in $IMAGES; do docker pull "$img"; done
k3d image import $IMAGES -c lab
```

Image untuk stack luar (Modul 3 & 4) juga patut ditarik awal:

```bash
for img in prom/prometheus:v3.4.0 prom/alertmanager:v0.28.1 grafana/grafana:12.0.0 axllent/mailpit:v1.25 \
           grafana/loki:3.5.0 chrislusf/seaweedfs:3.85 amazon/aws-cli:2.27.0 locustio/locust:2.37.0 \
           curlimages/curl:8.13.0; do
  docker pull "$img"
done
```

## Langkah A3: Uji app demo

Deploy app yang sebenar dilakukan dalam Modul 1, Makmal 1.1. Untuk menguji persediaan sekarang (masih dalam folder `00-persediaan`):

```bash
kubectl apply -f namespace.yaml -f demo-app/configmap.yaml
kubectl apply -f ../modul-1-hpa/02-deployment.yaml -f ../modul-1-hpa/03-service.yaml
kubectl -n demo rollout status deploy/demo-app
curl -s localhost:30080/ ; echo
```

Jangkaan: `{"pod": "demo-app-xxxxx", "version": "v1", "uptime_s": 5}`

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
kubectl -n demo get pods -o wide
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

Env: `VERSION`, `STARTUP_DELAY`, `SHUTDOWN_DELAY`, `FAIL_RATE` (lihat docstring dalam `app.py`). Jika anda mengubah `app.py`, jana semula ConfigMap:

```bash
cd ~/bengkel-k8s/00-persediaan
kubectl create configmap demo-app-code -n demo --from-file=demo-app/app.py --dry-run=client -o yaml > demo-app/configmap.yaml
kubectl apply -f demo-app/configmap.yaml && kubectl -n demo rollout restart deploy/demo-app
```

## Semakan siap: Opsyen A

- [ ] `kubectl config current-context` memulangkan `k3d-lab`, dan `kubectl get nodes` menunjukkan 3 node `Ready`
- [ ] `k3d-lab-server-0` ada taint `NoSchedule`, dan `kube-system` tiada `traefik` atau `metrics-server`
- [ ] `k3d image import ... -c lab` selesai tanpa ralat
- [ ] `curl -s localhost:30080/` memulangkan JSON app demo, dan pod `demo-app` berjalan pada agent

Semua lulus? Persediaan anda siap. **Seterusnya: [Modul 1: Workload Autoscaling & HPA](../../modul-1-hpa/README.md).**

---

## Reset & buang

```bash
# Reset namespace demo sahaja
kubectl delete namespace demo

# Buang semuanya selepas bengkel (dari folder 00-persediaan)
k3d cluster delete lab
(cd ~/bengkel-k8s/modul-3-monitoring/external && docker compose down -v)
(cd ~/bengkel-k8s/modul-4-operations/logging/external && docker compose down -v)
```
