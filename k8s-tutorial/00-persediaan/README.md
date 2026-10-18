# Persediaan Makmal

Lakukan persediaan ini **sebelum** Hari 1 (atau dalam 30 minit pertama). Semua makmal berjalan pada laptop dengan kluster tempatan **k3d** (k3s dalam Docker); tiada akaun cloud diperlukan.

## Pilih opsyen

| | Opsyen A: k3d sahaja | Opsyen B: k3d + Rancher |
|---|---|---|
| Apa yang dipasang | Satu kluster k3d `lab` | Kluster `lab` yang sama ditambah Rancher management server, dengan dua cara: **berasingan** (kluster k3d kedua `rancher`, `lab` didaftarkan ke Rancher; cadangan) atau **sekali** (Rancher dipasang terus dalam `lab`) |
| Akses kubectl | Terus ke API server k3d | Terus, **atau** melalui Rancher (kubeconfig dari UI Rancher) |
| RAM laptop | 8 GB minimum, 16 GB disyorkan | 16 GB minimum (cara sekali: 12 GB) |
| Masa persediaan | ~15 minit | ~35 minit |
| Sesuai untuk | Fokus pada Kubernetes asas | Organisasi yang mengurus kluster melalui Rancher |

Persediaan ada dua bahagian:

1. **Halaman ini (semua peserta):** keperluan laptop dan [pasang semua alat](#pasang-semua-alat).
2. **Halaman opsyen anda (pilih satu):** [Persediaan Opsyen A: k3d sahaja](opsyen-a/README.md) atau [Persediaan Opsyen B: k3d + Rancher](rancher/README.md). Setiap halaman lengkap dari mencipta kluster hingga semakan siap; anda tidak perlu membaca halaman opsyen yang lain.

Semua modul berjalan pada kluster `lab` yang sama untuk kedua-dua opsyen.

## Keperluan laptop

| Item | Minimum | Disyorkan |
|---|---|---|
| CPU | 4 core, dengan virtualisasi (VT-x/AMD-V) aktif dalam BIOS/UEFI | 8 core |
| RAM | 8 GB (Opsyen B: 16 GB, atau 12 GB untuk cara sekali) | 16 GB |
| Disk kosong | 20 GB | 40 GB |
| OS | Windows 10 22H2 / Windows 11 23H2 ke atas dengan WSL2, macOS (3 versi utama terkini), atau Linux 64-bit (arahan di bawah untuk Ubuntu/Debian) | |
| Akses | Hak admin (`sudo` / "Run as administrator") dan internet untuk memuat turun alat & image | |

## Pasang semua alat

Bahagian ini untuk peserta yang belum pernah memasang Docker. Ikut **satu** platform di bawah, kemudian jalankan [Semak pemasangan](#semak-pemasangan).

| Alat | Versi bengkel | Untuk apa | Opsyen |
|---|---|---|---|
| Docker (Desktop atau Engine) + Compose v2 | 27+ | Menjalankan node k3d dan stack luar Modul 3 & 4 | A, B |
| kubectl | v1.33.13 | Arahan ke kluster (sama minor dengan k3s v1.33.1) | A, B |
| k3d | v5.8.3 | Mencipta kluster k3s dalam Docker | A, B |
| k6 | v1.0.0 | Ujian beban Modul 2 dan 4 | A, B |
| curl, bash, python3 | mana-mana | Arahan & skrip makmal (`python3 -m json.tool` dalam Modul 1) | A, B |
| Locust | 2.37.0 | Ujian beban alternatif Modul 2 (pilihan; boleh guna Docker) | A, B |
| Helm | v3.18.6 | Memasang cert-manager dan Rancher | B sahaja |

jq dan git tidak diperlukan. Bahan bengkel diberi oleh fasilitator sebagai zip: lihat [Dapatkan bahan bengkel](#dapatkan-bahan-bengkel).

> **Kenapa versi tetap?** Pengurus pakej seperti Homebrew memasang versi terkini (cth: k6 v2.x, Helm v4, kubectl yang jauh lebih baharu daripada kluster). Skrip makmal ditulis dan diuji dengan versi di atas, jadi arahan di bawah memasang versi tersebut terus dari laman keluaran rasmi.

> **Lesen Docker Desktop:** percuma untuk kegunaan peribadi, pendidikan dan syarikat kecil. Organisasi lebih 250 pekerja **atau** hasil tahunan lebih USD 10 juta perlu langganan berbayar ([harga Docker](https://www.docker.com/pricing/)). Pada Linux, Docker Engine percuma untuk semua.

### Windows (WSL2 + Docker Desktop)

Semua arahan makmal dijalankan dalam terminal **Ubuntu (WSL2)**, bukan PowerShell. Docker Desktop menyediakan `docker` ke dalam Ubuntu.

**1. Pasang WSL2 dan Ubuntu.** Buka PowerShell sebagai admin (klik kanan → *Run as administrator*):

```powershell
wsl --install
```

Restart laptop. Selepas restart, buka **Ubuntu** dari menu Start dan cipta nama pengguna serta kata laluan Linux. Semak dalam PowerShell:

```powershell
wsl --version            # WSL version: 2.1.5 atau lebih baharu
wsl --list --verbose     # Ubuntu ... VERSION 2
```

Jika `wsl --version` tidak dikenali atau versi lama: `wsl --update`.

**2. Hadkan memori WSL2 (penting).** Dengan backend WSL2, memori Docker **tidak** ditetapkan dalam Docker Desktop tetapi oleh fail `%UserProfile%\.wslconfig`. Cipta fail itu (cth: `notepad $env:USERPROFILE\.wslconfig` dalam PowerShell):

```ini
[wsl2]
memory=6GB       # Opsyen B: 10GB (cara sekali: 8GB)
processors=4
```

Kemudian `wsl --shutdown` dalam PowerShell supaya tetapan baharu digunakan.

**3. Pasang Docker Desktop.** Muat turun dari [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/), jalankan installer dan pastikan **Use WSL 2** dipilih. Buka Docker Desktop, terima terma, dan tunggu sehingga status *Engine running*. Kemudian **Settings → Resources → WSL Integration**: hidupkan untuk **Ubuntu**, klik *Apply & restart*.

**4. Pasang alat lain dalam Ubuntu.** Buka terminal Ubuntu dan ikut [Linux langkah 2 dan 3](#linux-langkah-2-kubectl-k3d-k6-dan-helm). **Langkau** Linux langkah 1 (jangan pasang Docker Engine dalam Ubuntu kerana Docker Desktop sudah menyediakannya).

> Simpan folder bengkel dalam home Ubuntu (`~/bengkel-k8s`), bukan di `/mnt/c/...`; akses fail Windows dari WSL jauh lebih perlahan. Dari Windows Explorer, folder ini boleh dibuka di `\\wsl$\Ubuntu\home\<nama>`.

### macOS

**1. Pasang Docker Desktop.** Muat turun dari [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/) (pilih *Apple silicon* untuk M1/M2/M3/M4 atau *Intel chip*), seret ke Applications dan buka. Atau dengan Homebrew: `brew install --cask docker-desktop`.

Tunggu ikon ikan paus di menu bar berhenti beranimasi. Kemudian **Settings → Resources → Advanced**: Memory limit **6 GB** (Opsyen B: 10 GB, cara sekali: 8 GB), CPU 4 atau lebih, klik *Apply & restart*.

**2. Pasang kubectl, k3d, k6 dan Helm.** Buka Terminal:

```bash
ARCH=$(uname -m | sed 's/x86_64/amd64/')   # arm64 (Apple silicon) atau amd64 (Intel)

# kubectl v1.33.13
curl -LO "https://dl.k8s.io/release/v1.33.13/bin/darwin/${ARCH}/kubectl"
sudo mkdir -p /usr/local/bin
chmod +x kubectl && sudo mv kubectl /usr/local/bin/kubectl

# k3d v5.8.3
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=v5.8.3 bash

# k6 v1.0.0
curl -LO "https://github.com/grafana/k6/releases/download/v1.0.0/k6-v1.0.0-macos-${ARCH}.zip"
unzip -q k6-v1.0.0-macos-${ARCH}.zip && sudo mv k6-v1.0.0-macos-${ARCH}/k6 /usr/local/bin/k6
rm -r k6-v1.0.0-macos-${ARCH} k6-v1.0.0-macos-${ARCH}.zip

# Helm v3.18.6 (Opsyen B sahaja)
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh && ./get_helm.sh --version v3.18.6 && rm get_helm.sh
```

Jika macOS memaparkan amaran keselamatan semasa menjalankan `k6` atau `kubectl` kali pertama, benarkan dalam **System Settings → Privacy & Security**. `curl` dan `python3` sudah ada (jika diminta, pasang *Command Line Tools*).

**3. Locust (pilihan):** sama seperti [Linux langkah 3](#linux-langkah-3-locust-pilihan).

### Linux (Ubuntu/Debian, juga dalam WSL2)

#### Linux langkah 1: Docker Engine

Langkau langkah ini jika anda guna WSL2 dengan Docker Desktop. Ini arahan rasmi untuk Ubuntu; untuk Debian, gantikan `ubuntu` dengan `debian` dalam dua URL. Distro lain: [Install Docker Engine](https://docs.docker.com/engine/install/).

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources <<EOT
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOT
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Guna docker tanpa sudo, kemudian log keluar dan masuk semula (atau: newgrp docker)
sudo usermod -aG docker $USER
```

Docker Engine pada Linux menggunakan semua RAM laptop; tiada tetapan memori diperlukan.

#### Linux langkah 2: kubectl, k3d, k6 dan Helm

```bash
ARCH=$(dpkg --print-architecture)   # amd64 atau arm64

# kubectl v1.33.13
curl -LO "https://dl.k8s.io/release/v1.33.13/bin/linux/${ARCH}/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# k3d v5.8.3
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=v5.8.3 bash

# k6 v1.0.0
curl -L "https://github.com/grafana/k6/releases/download/v1.0.0/k6-v1.0.0-linux-${ARCH}.tar.gz" | tar xz
sudo install -m 0755 k6-v1.0.0-linux-${ARCH}/k6 /usr/local/bin/k6 && rm -r k6-v1.0.0-linux-${ARCH}

# Helm v3.18.6 (Opsyen B sahaja)
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh && ./get_helm.sh --version v3.18.6 && rm get_helm.sh
```

#### Linux langkah 3: Locust (pilihan)

Ubuntu 23.04 ke atas dan macOS (Homebrew) menolak `pip install` terus ke Python sistem (`externally-managed-environment`), jadi pasang dalam virtualenv:

```bash
sudo apt install -y python3-venv          # Linux/WSL sahaja
python3 -m venv ~/.venv/bengkel
source ~/.venv/bengkel/bin/activate       # ulang dalam setiap terminal baharu yang guna Locust
pip install locust==2.37.0
```

Tanpa Locust, gunakan image Docker `locustio/locust:2.37.0` seperti dalam Modul 2.

### Semak pemasangan

Jalankan dalam terminal yang akan digunakan semasa bengkel (Ubuntu untuk Windows):

```bash
docker version --format '{{.Server.Version}}'
docker compose version
docker run --rm hello-world
kubectl version --client
k3d version
k6 version
helm version --short          # Opsyen B
locust --version              # pilihan
python3 --version && curl --version | head -1
```

Jangkaan (nombor patch Docker dan Python boleh berbeza):

```
28.x.x                        <- 27 atau lebih baharu
Docker Compose version v2.x.x
Hello from Docker!
...
Client Version: v1.33.13
Kustomize Version: v5.6.0
k3d version v5.8.3
k3s version v1.31.5-k3s1 (default)    <- normal; k3d-cluster.yaml menetapkan v1.33.1
k6 v1.0.0 (commit/41b4984b75, go1.24.2, linux/amd64)
v3.18.6+g...
locust 2.37.0 from ...
Python 3.x.x
curl 8.x.x ...
```

Jika `docker version` hanya memaparkan bahagian *Client* dan ralat, Docker daemon belum berjalan; lihat ralat biasa di bawah.

### Ralat biasa pemula

| Ralat | Punca | Penyelesaian |
|---|---|---|
| `Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?` | Docker belum berjalan | Windows/macOS: buka Docker Desktop dan tunggu *Engine running*. Linux: `sudo systemctl start docker` (dan `sudo systemctl enable docker` supaya bermula semasa boot) |
| `permission denied while trying to connect to the Docker daemon socket` | Pengguna Linux belum dalam kumpulan `docker` | `sudo usermod -aG docker $USER`, kemudian log keluar dan masuk semula (atau `newgrp docker`). Jangan jalankan makmal dengan `sudo` |
| `docker: command not found` dalam Ubuntu (WSL2) | WSL Integration belum dihidupkan | Docker Desktop → **Settings → Resources → WSL Integration** → hidupkan Ubuntu → *Apply & restart*. Tutup dan buka semula terminal Ubuntu |
| `WSL 2 requires an update to its kernel component` atau Docker Desktop gagal bermula pada Windows | WSL2 belum lengkap | PowerShell (admin): `wsl --install`, kemudian `wsl --update`, restart. `wsl --list --verbose` mesti menunjukkan VERSION 2 |
| `Please enable the Virtual Machine Platform Windows feature and ensure virtualization is enabled in the BIOS` | Virtualisasi dimatikan | Hidupkan Intel VT-x / AMD-V (SVM) dalam BIOS/UEFI. Semak: Task Manager → Performance → CPU → *Virtualization: Enabled* |
| Node k3d `NotReady`, pod `Pending` atau `OOMKilled` tanpa sebab, laptop sangat perlahan | Memori Docker terlalu kecil | Semak `docker info --format '{{.MemTotal}}'` (bait). macOS: naikkan Memory limit dalam Docker Desktop. Windows: naikkan `memory=` dalam `.wslconfig`, kemudian `wsl --shutdown` |
| `Bind for 0.0.0.0:443 failed: port is already allocated` atau `address already in use` | Port sudah dipakai program lain (web server, Skype, VPN, kluster lama) | Cari pemiliknya: `sudo lsof -i :443` (macOS/Linux) atau `Get-NetTCPConnection -LocalPort 443` (PowerShell; lajur `OwningProcess` ialah PID dalam Task Manager). Hentikan program itu, atau buang kluster lama: `k3d cluster list` dan `k3d cluster delete <nama>` |
| `docker-credential-secretservice: error while loading shared libraries: libsecret-1.so.0` atau `error getting credentials` semasa `docker pull`/`docker run` (Linux/WSL2 tanpa desktop) | Docker cuba menyimpan kelayakan dalam keyring desktop (`secretservice`). Ia berlaku jika `~/.docker/config.json` ada `"credsStore": "secretservice"`, **atau** jika program `docker-credential-secretservice` wujud dalam PATH (Docker memilihnya secara automatik walaupun tiada config) | Semak `cat ~/.docker/config.json`: jika ada `credsStore`, buang baris itu (jaga koma JSON). Jika tiada config, lumpuhkan helper: `H=$(command -v docker-credential-secretservice); sudo mv "$H" "$H.disabled"`. Kemudian `docker run --rm hello-world`. Image awam tidak perlukan kelayakan |
| `k3d: command not found` selepas pasang | `/usr/local/bin` tiada dalam PATH, atau terminal lama | Buka terminal baharu; semak `echo $PATH` |
| `error: externally-managed-environment` semasa `pip install` | Python sistem dilindungi | Guna virtualenv seperti [Locust (pilihan)](#linux-langkah-3-locust-pilihan) |
| `too many open files`, atau pod Fluent Bit/node-exporter gagal bermula (Linux) | Had inotify terlalu rendah | `sudo sysctl fs.inotify.max_user_instances=512 fs.inotify.max_user_watches=524288` |

Port yang digunakan bengkel (pastikan kosong):

| Port | Digunakan oleh |
|---|---|
| 6550 | API server kluster `lab` |
| 30080, 30081, 30082 | NodePort app demo, kube-state-metrics, blue-green |
| 9090, 9093, 3000, 8025 | Prometheus, Alertmanager, Grafana, Mailpit (Modul 3) |
| 3100, 8333 | Loki, S3 SeaweedFS (Modul 4) |
| 8089 | UI Locust (Modul 2) |
| 443, 6551 | Rancher dan API server kluster `rancher` (Opsyen B) |

## Dapatkan bahan bengkel

Semua fail makmal (YAML, skrip k6/Locust, konfigurasi Prometheus, Grafana, Loki dan lain-lain) sudah disediakan. Anda **tidak perlu mencipta folder atau menaip fail sendiri**. Fasilitator akan memberi satu fail zip (contoh: `bengkel-k8s-peserta.zip`).

Unzip ke folder rumah anda supaya folder kerja ialah `~/bengkel-k8s`:

```bash
# Windows: jalankan dalam terminal Ubuntu (WSL2), bukan PowerShell.
# Salin zip dari folder Downloads Windows dahulu (tukar <nama> kepada nama pengguna Windows anda):
#   cp /mnt/c/Users/<nama>/Downloads/bengkel-k8s-peserta.zip ~/
# Ubuntu/WSL2 tanpa unzip: sudo apt install -y unzip
cd ~
unzip bengkel-k8s-peserta.zip        # mencipta folder ~/bengkel-k8s
cd ~/bengkel-k8s
ls
```

Jangkaan:

```
00-persediaan  modul-1-hpa  modul-2-load-testing  modul-3-monitoring  modul-4-operations  modul-5-opentelemetry  modul-6-keda  panduan  README.md
```

| Folder | Isi |
|---|---|
| `00-persediaan/` | Fail kluster k3d, namespace, app demo; `opsyen-a/` dan `rancher/` (Opsyen B) |
| `modul-1-hpa/` hingga `modul-6-keda/` | Manifest, skrip dan konfigurasi setiap modul |
| `panduan/` | Panduan ini dalam bentuk HTML (buka `panduan/index.html` dalam browser) |

> **Penting:** setiap modul bermula dengan `cd ~/bengkel-k8s/<folder-modul>`. Arahan dalam modul menggunakan laluan relatif (contoh: `../00-persediaan/namespace.yaml`), jadi ia hanya berfungsi jika dijalankan dari folder modul itu. 

Jika anda unzip di tempat lain (contoh `~/latihan-k8s/bengkel-k8s`), jangan ubah setiap arahan. Cipta pautan `~/bengkel-k8s` sekali sahaja dari dalam folder itu, dan semua `cd ~/bengkel-k8s/...` akan berfungsi:

```bash
cd <folder-tempat-anda-unzip>/bengkel-k8s
ln -sfn "$PWD" ~/bengkel-k8s
ls ~/bengkel-k8s/modul-1-hpa      # mesti menyenaraikan fail modul
```

## Seterusnya: pilih opsyen

Halaman opsyen mencipta kluster `lab`, menerangkan apa yang disediakan, dan menguji app demo untuk memastikan semuanya berfungsi.


- **[Persediaan Opsyen A: k3d sahaja](opsyen-a/README.md)**: satu kluster `lab`, kubectl terus ke API server (~15 minit).
- **[Persediaan Opsyen B: k3d + Rancher](rancher/README.md)**: kluster `lab` diurus oleh Rancher, cara berasingan atau sekali (~35 minit).
