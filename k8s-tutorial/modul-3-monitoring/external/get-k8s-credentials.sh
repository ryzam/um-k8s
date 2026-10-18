#!/usr/bin/env bash
# Salin token ServiceAccount prometheus-external dan CA kluster ke ./prometheus/k8s/
# supaya Prometheus luar boleh bercakap dengan API server.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p prometheus/k8s
kubectl -n monitoring get secret prometheus-external-token -o jsonpath='{.data.token}' | base64 -d > prometheus/k8s/token
kubectl -n monitoring get secret prometheus-external-token -o jsonpath='{.data.ca\.crt}' | base64 -d > prometheus/k8s/ca.crt
chmod 644 prometheus/k8s/token prometheus/k8s/ca.crt   # container Prometheus berjalan sebagai user nobody
echo "Token dan CA disimpan dalam $(pwd)/prometheus/k8s/"
echo "API server (dalam rangkaian Docker k3d-lab): https://k3d-lab-server-0:6443"
