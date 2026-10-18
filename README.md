# Bengkel Kubernetes: HPA, Load Testing, Monitoring dan Operasi

Bahan bengkel Kubernetes 2 hari dalam Bahasa Melayu. Makmal menggunakan kluster k3d pada laptop atau server peserta.

Jurulatih: Irwan Azam Ahmad

## Kandungan repo

| Folder | Isi |
|---|---|
| [`k8s-tutorial/`](k8s-tutorial/) | Sumber bengkel (Markdown) dan semua fail makmal: YAML, skrip k6/Locust, konfigurasi Prometheus, Grafana dan lain-lain |
| [`k8s-tutorial-html/`](k8s-tutorial-html/) | Panduan HTML interaktif yang dibina daripada sumber Markdown (`index.html` + rajah `svg/`) |

Modul:

- `00-persediaan`: pasang alat dan pilih opsyen kluster (Opsyen A: k3d sahaja, Opsyen B: k3d + Rancher)
- `modul-1-hpa`: requests/limits dan Horizontal Pod Autoscaler
- `modul-2-load-testing`: ujian beban dengan k6 dan Locust
- `modul-3-monitoring`: Prometheus, Grafana dan Alertmanager di luar kluster
- `modul-4-operations`: rolling update, blue-green, canary, eviction, logging dan troubleshooting
- `modul-5-opentelemetry` (pilihan): OpenTelemetry Collector dan Tempo
- `modul-6-keda` (pilihan): KEDA

Mula dengan [`k8s-tutorial/README.md`](k8s-tutorial/README.md), atau buka `k8s-tutorial-html/index.html` dalam pelayar.

## Bina semula HTML

Selepas mengubah mana-mana fail Markdown dalam `k8s-tutorial/`, bina semula panduan HTML dari akar repo:

```bash
pip install markdown
python3 k8s-tutorial-html/_bina/build.py
```

Skrip membaca `k8s-tutorial/` dan menulis `k8s-tutorial-html/index.html` serta `svg/*.svg`. Untuk membina daripada salinan sumber lain atau ke folder lain:

```bash
BENGKEL_SRC=/laluan/ke/sumber python3 k8s-tutorial-html/_bina/build.py /laluan/output
```
