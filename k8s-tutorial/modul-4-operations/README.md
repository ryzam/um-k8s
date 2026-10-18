# Modul 4: Fasa Operasi, Day-2 Kubernetes Operations & Reliability

**Hari 2, 2:00 petang hingga 5:00 petang**

> **Opsyen B (Rancher):** Guna context `k3d-lab` untuk Makmal 4.4 (drain); jika Rancher dipasang sekali dalam `lab` (cara 2), drain boleh mengusir pod Rancher itu sendiri; jangan pasang app Logging Rancher serentak dengan Fluent Bit makmal. Butiran: [Persediaan Opsyen B](../00-persediaan/rancher/README.md).

Dalam modul ini peserta akan:

1. Laksanakan **rolling update tanpa downtime** dan buktikannya dengan k6 (sifar request gagal), serta rollback.
2. Laksanakan **blue-green** dan **canary** deployment, dan perhati peralihan trafik di Grafana.
3. Urus **pod eviction**: `kubectl drain` dengan PodDisruptionBudget, eviction oleh kubelet, dan preemption.
4. Hantar log dari kluster ke **storan luar** (Loki + object storage S3) dengan Fluent Bit.
5. Selesaikan **7 kes kegagalan container** yang biasa berlaku di production.

> Prasyarat: Modul 1 hingga 3 selesai, stack monitoring luar (Modul 3) masih berjalan.

## Jadual

| Masa | Aktiviti |
|---|---|
| 2:00 – 2:40 | Makmal 4.1: zero-downtime rolling update & rollback |
| 2:40 – 3:15 | Makmal 4.2 & 4.3: blue-green dan canary |
| 3:15 – 3:30 | Rehat |
| 3:30 – 4:00 | Makmal 4.4: eviction, PDB, drain, preemption |
| 4:00 – 4:25 | Makmal 4.5: log shipping ke storan luar |
| 4:25 – 5:00 | Makmal 4.6: troubleshooting (7 kes) & penutup |

---

## Teori ringkas

### Strategi deployment

| Strategi | Cara | Kelebihan | Kekurangan | Rollback |
|---|---|---|---|---|
| **Rolling update** | Ganti pod sedikit demi sedikit (default K8s) | Tiada sumber tambahan besar | v1 dan v2 berjalan serentak seketika | `kubectl rollout undo` (minit) |
| **Blue-green** | Deploy v2 penuh di sebelah v1, tukar Service sekali gus | Tukar & rollback serta-merta, v2 boleh diuji dahulu | Perlu 2× sumber | Tukar selector semula (saat) |
| **Canary** | Hantar sebahagian kecil trafik ke v2, tambah berperingkat | Risiko kecil, keputusan berdasarkan metrik sebenar | Lebih kompleks, perlu monitoring baik | Buang canary (saat) |
| Recreate | Matikan semua v1, kemudian start v2 | Mudah, tiada versi bercampur | **Ada downtime** | Deploy semula v1 |

### Kitaran hayat penamatan pod (kunci zero-downtime)

```
 kubectl / rollout memadam pod
          │
          ├──▶ (serentak) Pod dibuang dari EndpointSlice ──▶ kube-proxy kemas kini iptables  (ambil masa!)
          │
          └──▶ preStop hook (sleep 5s)  ◀── beri masa langkah di atas selesai
                     │
                     ▼
                SIGTERM ke app ──▶ app gagalkan /readyz, habiskan request sedia ada (SHUTDOWN_DELAY)
                     │
                     ▼  (jika masih hidup selepas terminationGracePeriodSeconds)
                SIGKILL
```

Tanpa `preStop`, app boleh menerima SIGTERM dan berhenti **sebelum** kube-proxy berhenti menghantar trafik kepadanya, jadi beberapa request gagal. Ini punca paling biasa "rolling update tapi masih ada 502".

### Gangguan sukarela vs tidak sukarela

| Sukarela (PDB dihormati) | Tidak sukarela (PDB TIDAK membantu) |
|---|---|
| `kubectl drain`, upgrade node, Cluster Autoscaler scale-down, eviction API | Node crash, kernel panic, OOMKilled, eviction oleh kubelet kerana node-pressure |

---

## Makmal 4.1: Zero-downtime rolling update

### A. Deploy versi production-ready

Modul ini bermula dari folder `modul-4-operations`; setiap makmal masuk ke subfolder masing-masing:

```bash
cd ~/bengkel-k8s/modul-4-operations/rolling-update
kubectl apply -f deployment-production.yaml -f pdb.yaml
kubectl -n demo rollout status deploy/demo-app
kubectl annotate -n demo deploy/demo-app kubernetes.io/change-cause="v1: baseline production" --overwrite
```

Bandingkan dengan `../modul-1-hpa/02-deployment.yaml`. Semua perubahan ditanda `[BARU]` dalam fail.

### B. Rollout v2 di bawah beban

Terminal 1 (beban berterusan 20 RPS, threshold sifar ralat):

```bash
k6 run -e DURATION=3m zero-downtime.js
```

Terminal 2, mulakan rollout dalam masa 20 saat:

```bash
sed -E 's/(version|value): v1/\1: v2/' deployment-production.yaml | kubectl apply -f -
kubectl annotate -n demo deploy/demo-app kubernetes.io/change-cause="v2: ciri baharu" --overwrite
kubectl -n demo rollout status deploy/demo-app
```

Terminal 3, perhati penggantian pod:

```bash
kubectl -n demo get pods -l app=demo-app -L version --watch
```

Jangkaan output k6:

```
http_req_failed ✓ 'rate==0' rate=0.00%
requests_by_version{version:v1} ... count=xxxx
requests_by_version{version:v2} ... count=xxxx
```

Di Grafana, panel **"Request sesaat mengikut versi"** menunjukkan v1 menurun dan v2 meningkat.

### C. Eksperimen: pecahkan zero-downtime

Buang `preStop` dan graceful shutdown, kemudian ulang Langkah B (rollout balik ke v1):

```bash
kubectl -n demo patch deploy demo-app --type=json -p '[
  {"op":"remove","path":"/spec/template/spec/containers/0/lifecycle"},
  {"op":"replace","path":"/spec/template/spec/containers/0/env/1/value","value":"0"},
  {"op":"replace","path":"/spec/strategy/rollingUpdate/maxUnavailable","value":"50%"}
]'
# tunggu rollout ini selesai, kemudian jalankan k6 dan rollout lagi:
k6 run -e DURATION=2m zero-downtime.js &
sleep 15; kubectl -n demo set env deploy/demo-app VERSION=v3
wait
```

Jangkaan: `http_req_failed ✗ 'rate==0'`, dengan beberapa `connection refused` / `EOF`. Bincang sebab setiap perubahan menyumbang kepada ralat. Pulihkan:

```bash
kubectl apply -f deployment-production.yaml
```

### D. Rollout gagal dan rollback

```bash
kubectl -n demo set image deploy/demo-app app=python:3.12-tiada-wujud
kubectl -n demo rollout status deploy/demo-app --timeout=150s   # gagal selepas progressDeadlineSeconds (120s)
kubectl -n demo get pods -l app=demo-app
```

Perhatikan: pod lama **masih berjalan dan melayan trafik** kerana `maxUnavailable: 0`. Pod baharu tersekat dalam `ImagePullBackOff`.

```bash
kubectl -n demo get deploy demo-app -o jsonpath='{.status.conditions[?(@.type=="Progressing")].reason}'; echo   # ProgressDeadlineExceeded
kubectl -n demo rollout history deploy/demo-app
kubectl -n demo rollout undo deploy/demo-app
kubectl -n demo rollout status deploy/demo-app
```

Rollback ke revision tertentu: `kubectl -n demo rollout undo deploy/demo-app --to-revision=2`

> **Pause/resume:** `kubectl rollout pause` membolehkan beberapa perubahan dikumpul dan dilancar sebagai satu rollout dengan `kubectl rollout resume`.

> **GitOps:** di production, `rollout undo` mencipta drift daripada Git. Rollback sebenar ialah `git revert` dan biar Argo CD / Flux apply. `rollout undo` ialah butang kecemasan.

## Makmal 4.2: Blue-green deployment

```bash
cd ../blue-green
kubectl apply -f 01-blue.yaml -f 03-service.yaml
kubectl -n demo rollout status deploy/demo-bg-blue
curl -s localhost:30082/ ; echo        # "version": "v1"
```

> Pengguna minikube: `minikube service demo-bg -n demo --url`. Jika kluster k3d anda dicipta sebelum port 30082 ditambah dalam `k3d-cluster.yaml`, guna `kubectl -n demo port-forward svc/demo-bg 30082:80`.

Deploy GREEN (belum terima trafik live):

```bash
kubectl apply -f 02-green.yaml
kubectl -n demo rollout status deploy/demo-bg-green
kubectl -n demo run preview --rm -i --restart=Never --image=busybox:1.36 -- wget -q -O- http://demo-bg-preview/
```

Tukar trafik, sambil k6 berjalan supaya kita lihat peralihan:

```bash
k6 run -e BASE_URL=http://localhost:30082 -e DURATION=1m ../rolling-update/zero-downtime.js &
sleep 20; ./switch.sh green
wait
```

Rollback serta-merta:

```bash
./switch.sh blue
```

Selepas yakin dengan GREEN, BLUE boleh di-scale ke 0 (simpan untuk rollback pantas) atau dipadam:

```bash
kubectl -n demo scale deploy demo-bg-blue --replicas=0
```

Bersihkan sebelum makmal seterusnya (ResourceQuota namespace demo hanya 2 CPU requests):

```bash
kubectl delete -f .
```

Soalan perbincangan: Apa yang berlaku kepada sambungan sedia ada (keep-alive) semasa selector ditukar? Bagaimana dengan perubahan skema pangkalan data yang tidak serasi ke belakang?

## Makmal 4.3: Canary deployment

Canary di sini guna **nisbah pod**: satu Service memilih label `app=demo-canary`, dan kedua-dua Deployment `stable` (4 pod, v1) dan `canary` (1 pod, v2) mempunyai label itu, jadi kira-kira 20% trafik ke canary.

### A. Canary sihat, promosi berperingkat

```bash
cd ../canary
kubectl apply -f 01-stable.yaml -f 02-canary.yaml -f 03-service.yaml
kubectl -n demo rollout status deploy/demo-canary-stable
kubectl -n demo rollout status deploy/demo-canary-canary
./canary-traffic.sh 200
```

Jangkaan, lebih kurang:

```
    160 "version": "v1"
     40 "version": "v2"
```

Promosi berperingkat (semak metrik di Grafana selepas setiap langkah):

```bash
kubectl -n demo scale deploy demo-canary-canary --replicas=2   # ~33%
kubectl -n demo scale deploy demo-canary-canary --replicas=4   # ~50%
./canary-traffic.sh 200
```

Promosi penuh: kemas kini stable ke v2, kemudian buang canary.

```bash
kubectl -n demo set env deploy/demo-canary-stable VERSION=v2
kubectl -n demo patch deploy demo-canary-stable -p '{"spec":{"template":{"metadata":{"labels":{"version":"v2"}}}}}'
kubectl -n demo rollout status deploy/demo-canary-stable
kubectl -n demo scale deploy demo-canary-canary --replicas=0
```

### B. Canary rosak, kesan dan batalkan

Reset ke v1 dan lancarkan canary yang memulangkan HTTP 500 untuk 30% request:

```bash
kubectl apply -f 01-stable.yaml
kubectl -n demo set env deploy/demo-canary-canary FAIL_RATE=0.3
kubectl -n demo scale deploy demo-canary-canary --replicas=1
./canary-traffic.sh 200
```

Jangkaan: kira-kira 6% `GAGAL (5xx)` (20% trafik × 30% gagal).

Jana trafik berterusan supaya Prometheus nampak corak ralat:

```bash
kubectl -n demo run canary-load --image=busybox:1.36 --restart=Never -- sh -c \
  'while true; do wget -q -O- http://demo-canary/ >/dev/null 2>&1; sleep 0.05; done'
```

Dalam Grafana, tambah query ini di **Explore** untuk bandingkan kadar ralat setiap versi:

```promql
sum by (version) (rate(demo_http_requests_total{namespace="demo", app="demo-canary", code=~"5.."}[1m]))
  / sum by (version) (rate(demo_http_requests_total{namespace="demo", app="demo-canary"}[1m]))
```

Alert `DemoAppHighErrorRate` (Modul 3) akan firing dalam ~2 minit jika kadar ralat keseluruhan namespace > 5%. Batalkan canary:

```bash
kubectl -n demo scale deploy demo-canary-canary --replicas=0
kubectl -n demo delete pod canary-load
```

> **Automasi:** Argo Rollouts dan Flagger melaksanakan langkah di atas secara automatik: tambah berat, query Prometheus, dan rollback sendiri jika metrik teruk. Untuk pembahagian trafik mengikut peratus tepat (bukan nisbah pod), lihat [`rujukan-gateway-api-httproute.yaml`](canary/rujukan-gateway-api-httproute.yaml).

Bersihkan:

```bash
kubectl delete -f 01-stable.yaml -f 02-canary.yaml -f 03-service.yaml
```

## Makmal 4.4: Pod eviction

### A. `kubectl drain` dan PodDisruptionBudget

```bash
kubectl -n demo get pods -l app=demo-app -o wide      # pod tersebar di k3d-lab-agent-0 & k3d-lab-agent-1
kubectl -n demo get pdb demo-app                      # ALLOWED DISRUPTIONS = replicas - 1
```

Drain satu node (simulasi penyelenggaraan / upgrade):

```bash
kubectl drain k3d-lab-agent-0 --ignore-daemonsets --delete-emptydir-data
kubectl -n demo get pods -l app=demo-app -o wide
kubectl get nodes                                     # k3d-lab-agent-0: SchedulingDisabled
kubectl uncordon k3d-lab-agent-0
```

Sekarang buat PDB terlalu ketat dan cuba lagi:

```bash
REPLICAS=$(kubectl -n demo get deploy demo-app -o jsonpath='{.spec.replicas}')
kubectl -n demo patch pdb demo-app -p "{\"spec\":{\"minAvailable\":$REPLICAS}}"
kubectl -n demo get pdb demo-app                      # ALLOWED DISRUPTIONS = 0
kubectl drain k3d-lab-agent-0 --ignore-daemonsets --delete-emptydir-data --timeout=60s
```

Jangkaan, berulang kali:

```
error when evicting pods/"demo-app-..." -n "demo" (will retry after 5s): Cannot evict pod as it would violate the pod's disruption budget.
```

Pengajaran: PDB yang tidak membenarkan sebarang gangguan akan **menyekat** upgrade node dan Cluster Autoscaler. Guna `maxUnavailable: 1` atau `minAvailable` < replicas. Pulihkan:

```bash
kubectl apply -f ../rolling-update/pdb.yaml
kubectl uncordon k3d-lab-agent-0
```

### B. Eviction oleh kubelet (had ephemeral storage)

```bash
cd ../eviction
kubectl apply -f 01-ephemeral-storage-eviction.yaml
kubectl -n demo get pod disk-hog --watch               # Running -> Error/Evicted dalam ~10-30s
kubectl -n demo describe pod disk-hog | grep -A3 -E 'Status:|Reason:|Message:'
```

Jangkaan: `Reason: Evicted`, `Message: Pod ephemeral local storage usage exceeds the total limit of containers 50Mi.`

Mekanisme yang sama berlaku pada skala node bila `DiskPressure` atau `MemoryPressure`. Susunan kubelet mengusir pod: pod yang menggunakan melebihi `requests` dahulu, kemudian mengikut **priority**, kemudian penggunaan relatif. Itulah sebab `BestEffort` diusir paling awal (Modul 1).

```bash
kubectl describe node k3d-lab-agent-0 | grep -A8 Conditions     # MemoryPressure / DiskPressure / PIDPressure
```

Pod yang diusir **kekal** dalam status `Failed` sebagai rekod. Bersihkan secara berkala:

```bash
kubectl get pods -A --field-selector=status.phase=Failed
kubectl -n demo delete pods --field-selector=status.phase=Failed
```

### C. Priority dan preemption

```bash
kubectl apply -f 02-priorityclass.yaml
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu
```

Laraskan `replicas` dalam `03-batch-keutamaan-rendah.yaml` supaya pod batch (1 CPU setiap satu) memenuhi CPU worker. Contoh: 2 worker × 4 CPU = set `replicas: 7` (ruang untuk pod sistem).

```bash
kubectl apply -f 03-batch-keutamaan-rendah.yaml
kubectl -n ops-lab get pods -o wide                   # sesetengah mungkin Pending: kluster penuh
kubectl apply -f 04-kritikal.yaml
kubectl -n ops-lab get pods -o wide --watch
kubectl -n ops-lab get events --sort-by=.lastTimestamp | grep -i preempt
```

Jangkaan: pod `batch` di-preempt (`Preempted by pod ...`) dan pod `kritikal` dijadualkan.

```bash
kubectl delete namespace ops-lab
kubectl delete -f 02-priorityclass.yaml
```

## Makmal 4.5: Log shipping ke storan luar

Seni bina:

```
 Setiap node: /var/log/containers/*.log
        │
        ▼
 Fluent Bit (DaemonSet) ── tambah metadata K8s, buang log /healthz, penimbal di disk
        │                         │
        ▼                         ▼
 Loki (luar kluster)        Object storage S3 (luar kluster, SeaweedFS dalam makmal)
 cari log di Grafana        arkib .gz: cluster=lab/YYYY/MM/DD/HH/<pod>_<ns>_<container>-....gz
```

### A. Naikkan storan log luar

```bash
cd ../logging/external
docker compose up -d
docker compose logs create-bucket     # "bucket k8s-logs dicipta"
curl -s localhost:3100/ready          # ready (selepas ~30s)
```

### B. Pasang Fluent Bit

```bash
cd ..
kubectl apply -f k8s/fluent-bit.yaml
kubectl -n logging rollout status ds/fluent-bit
kubectl -n logging logs ds/fluent-bit | grep -iE 'error|upload' | tail
```

Selepas ~1 minit, jangkaan dalam log: `[output:s3:s3.1] Successfully uploaded object /cluster=lab/...`

> Fluent Bit dalam pod mencapai `loki` dan `s3` melalui DNS Docker rangkaian `k3d-lab` (k3d menghala DNS node ke resolver Docker). Jika log menunjukkan `getaddrinfo` / `no such host`, gantikan `Host loki` dan `endpoint http://s3:8333` dalam ConfigMap dengan IP container:
> `docker inspect logging-luar-loki-1 -f '{{(index .NetworkSettings.Networks "k3d-lab").IPAddress}}'`

### C. Cari log di Grafana

Grafana (http://localhost:3000) → **Explore** → datasource **Loki**. Cuba LogQL:

```logql
{namespace="demo", container="app"}

# Hanya log daripada pod v2 (Merge_Log menjadikan JSON app sebagai medan)
{namespace="demo"} | json | version="v2"

# Mesej fatal (cth: /crash dari Modul 3)
{namespace="demo"} | json | level="fatal"

# Kadar log setiap pod, berguna untuk kesan pod "bising"
sum by (pod) (rate({namespace="demo"}[1m]))
```

Picu beberapa log menarik dan cari mereka:

```bash
curl -s localhost:30080/crash; curl -s "localhost:30080/cpu?ms=10"
```

### D. Sahkan arkib di S3

```bash
docker run --rm --network k3d-lab -e AWS_ACCESS_KEY_ID=fluentbit -e AWS_SECRET_ACCESS_KEY=fluentbit-rahsia-123 \
  -e AWS_DEFAULT_REGION=us-east-1 amazon/aws-cli:2.27.0 --endpoint-url http://s3:8333 \
  s3 ls s3://k8s-logs/ --recursive | tail -5
```

### E. Ketahanan: apa jadi bila storan luar mati?

```bash
cd external && docker compose stop loki && cd ..
for i in $(seq 1 20); do curl -s "localhost:30080/?ujian=loki-mati-$i" >/dev/null; done
kubectl -n logging logs ds/fluent-bit --tail=5            # retry ...
sleep 60; cd external && docker compose start loki && cd ..
```

Selepas Loki kembali, cari `{namespace="demo"} |= "loki-mati"` di Grafana. Log semasa Loki mati sepatutnya muncul, kerana Fluent Bit menyimpannya dalam penimbal disk (`storage.type filesystem`) dan menghantar semula.

> **Production:** gantikan kelayakan dalam Secret `s3-credentials` (atau guna IRSA / Workload Identity di cloud), dayakan TLS, dan tetapkan lifecycle policy pada bucket (cth: pindah ke Glacier selepas 30 hari, padam selepas 1 tahun) mengikut keperluan audit.

## Makmal 4.6: Troubleshooting kegagalan container

### Aliran diagnosis

```
kubectl get pods            ─▶ Apa STATUS dan RESTARTS?
     │
     ├─ Pending              ─▶ kubectl describe pod  → Events: FailedScheduling (resource, nodeSelector, taint, PVC)
     ├─ ImagePullBackOff     ─▶ kubectl describe pod  → Events: nama image/tag, registry, imagePullSecrets
     ├─ CreateContainerConfigError ─▶ describe → ConfigMap/Secret/key yang hilang
     ├─ CrashLoopBackOff     ─▶ kubectl logs --previous → ralat app;  describe → Last State: exit code
     │                          exit 1 = ralat app | 137 = SIGKILL (OOMKilled / liveness) | 143 = SIGTERM
     ├─ Running tapi 0/1     ─▶ readinessProbe gagal → describe → Events: Readiness probe failed
     └─ Running 1/1 tapi Service tak jalan ─▶ kubectl get endpointslices → selector & targetPort
```

### Kotak alat

```bash
kubectl get pods -o wide
kubectl describe pod <pod>                         # Events di bahagian bawah: paling penting
kubectl logs <pod> [-c container] --previous       # log container SEBELUM restart
kubectl get events --sort-by=.lastTimestamp
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[0].lastState}'
kubectl top pod <pod>
kubectl exec -it <pod> -- sh
kubectl debug -it <pod> --image=busybox:1.36 --target=<container>   # ephemeral container untuk image tanpa shell
kubectl debug node/<node> -it --image=busybox:1.36                  # shell pada node
kubectl get endpointslices -l kubernetes.io/service-name=<svc>
kubectl run tmp --rm -it --image=busybox:1.36 --restart=Never -- wget -qO- http://<svc>.<ns>
```

### Kes

Deploy semua kes sekali gus:

```bash
cd ../troubleshooting
kubectl apply -f .
kubectl -n troubleshoot get pods
```

Untuk setiap kes: (1) kenal pasti gejala, (2) cari bukti dengan kotak alat, (3) betulkan YAML dan apply semula. Jangan buka jawapan sebelum mencuba.

| Kes | Aduan pengguna |
|---|---|
| 1 | "Pod saya tak start langsung" |
| 2 | "Pod asyik restart" |
| 3 | "Pod mati bila trafik tinggi, tiada error dalam log aplikasi" |
| 4 | "Pod Running, tetapi Service tidak dapat dicapai" (ada **3** masalah) |
| 5 | "Pod Pending selama-lamanya" |
| 6 | "Container tak boleh dicipta" |
| 7 | "App start perlahan, kemudian di-restart berulang kali walaupun app OK" |

<details>
<summary>Jawapan Kes 1</summary>

**Gejala:** `ErrImagePull` → `ImagePullBackOff`.
**Bukti:** `kubectl -n troubleshoot describe pod -l app=kes-1-web` → `manifest for nginx:1.27.99-alpine not found`.
**Betulkan:** `kubectl -n troubleshoot set image deploy/kes-1-web web=nginx:1.27-alpine`. Punca lain yang biasa: registry peribadi tanpa `imagePullSecrets`, rate limit Docker Hub, seni bina image (arm64 vs amd64).
</details>

<details>
<summary>Jawapan Kes 2</summary>

**Gejala:** `CrashLoopBackOff`, RESTARTS bertambah.
**Bukti:** `kubectl -n troubleshoot logs deploy/kes-2-worker --previous` → `FATAL: DB_PORT tidak ditetapkan`. Exit code 1.
**Betulkan:** tambah `DB_PORT: "5432"` dalam ConfigMap `kes-2-config`, kemudian `kubectl -n troubleshoot rollout restart deploy/kes-2-worker` (pod tidak membaca semula `envFrom` tanpa restart).
</details>

<details>
<summary>Jawapan Kes 3</summary>

**Gejala:** restart berkala, log berhenti mengejut pada `cache: 90 MB` tanpa mesej ralat.
**Bukti:** `kubectl -n troubleshoot get pod -l app=kes-3-cache -o jsonpath='{.items[0].status.containerStatuses[0].lastState.terminated}'` → `reason: OOMKilled, exitCode: 137`. Kernel membunuh proses, jadi app tiada peluang menulis log.
**Betulkan:** dua pilihan: naikkan `limits.memory` jika penggunaan itu sah, atau (lebih betul) hadkan saiz cache dalam app. Di Grafana, panel "Memori pod vs limits" menunjukkan garis memori mencecah limit sebelum setiap restart.
</details>

<details>
<summary>Jawapan Kes 4</summary>

1. **Readiness gagal:** pod `0/1 Running`. `describe` → `Readiness probe failed: HTTP probe failed with statuscode: 404`. nginx tiada `/health`. Tukar `path: /`.
2. **Selector salah:** `kubectl -n troubleshoot get endpointslices -l kubernetes.io/service-name=kes-4-api` → tiada endpoint. Selector `kes4-api` vs label `kes-4-api`.
3. **targetPort salah:** Service hantar ke 8080, nginx dengar pada 80. Tukar `targetPort: 80`.

Uji: `kubectl -n troubleshoot run t --rm -i --restart=Never --image=busybox:1.36 -- wget -qO- http://kes-4-api`
</details>

<details>
<summary>Jawapan Kes 5</summary>

**Gejala:** `Pending`.
**Bukti:** `describe` → `0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 2 node(s) didn't match Pod's node affinity/selector`. Selepas buang `nodeSelector`, mesej bertukar ke `Insufficient cpu, Insufficient memory`.
**Betulkan:** buang `nodeSelector` (atau label node yang betul), dan kurangkan `requests` ke nilai realistik (cth: `cpu: 100m, memory: 128Mi`). Requests ialah tempahan, bukan anggaran puncak.
</details>

<details>
<summary>Jawapan Kes 6</summary>

**Gejala:** `CreateContainerConfigError`.
**Bukti:** `describe` → `Error: secret "payment-gateway" not found`.
**Betulkan:** `kubectl -n troubleshoot create secret generic payment-gateway --from-literal=token=rahsia123`. Pod akan cuba semula sendiri. Jika rujukan ConfigMap/Secret itu sepatutnya pilihan, tambah `optional: true`.
</details>

<details>
<summary>Jawapan Kes 7</summary>

**Gejala:** `CrashLoopBackOff` walaupun log hanya menunjukkan `warming up...`.
**Bukti:** `describe` → `Liveness probe failed: ... connection refused` diikuti `Container app failed liveness probe, will be restarted`. Liveness bermula selepas 5s dan membunuh container selepas 3 × 5s = 20s, sedangkan app perlukan 40s.
**Betulkan:** tambah `startupProbe` (cth: `periodSeconds: 5, failureThreshold: 12` = 60s), yang menangguhkan liveness sehingga app pertama kali sihat. Jangan sekadar menaikkan `initialDelaySeconds` liveness kerana itu juga melambatkan pengesanan bila app benar-benar tergantung kemudian.
</details>

Bersihkan:

```bash
kubectl delete namespace troubleshoot
```

## Penutup: senarai semak Day-2

| Bidang | Amalan | Modul |
|---|---|---|
| Kapasiti | requests/limits berdasarkan data ujian beban, HPA dengan `behavior`, ResourceQuota | 1, 2 |
| Pengesahan | Ujian beban dalam pipeline (threshold k6), spike test sebelum musim puncak | 2 |
| Observability | Metrik (Prometheus), dashboard sebagai kod, alert dengan unit test, log berpusat | 3, 4 |
| Deployment | `maxUnavailable: 0`, readiness + startup probe, `preStop`, graceful SIGTERM, canary untuk perubahan berisiko | 4 |
| Gangguan | PDB yang membenarkan sekurang-kurangnya 1 gangguan, topologySpreadConstraints, PriorityClass | 4 |
| Insiden | Aliran diagnosis, `kubectl logs --previous`, `kubectl debug`, rollback sebagai butang kecemasan | 4 |

## Rujukan

- Deployments & rolling update: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Pod termination: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination
- Disruptions & PDB: https://kubernetes.io/docs/concepts/workloads/pods/disruptions/
- Node-pressure eviction: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
- Priority & preemption: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/
- Fluent Bit Kubernetes: https://docs.fluentbit.io/manual/installation/kubernetes
- Debug running pods: https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/
- Argo Rollouts: https://argo-rollouts.readthedocs.io/
