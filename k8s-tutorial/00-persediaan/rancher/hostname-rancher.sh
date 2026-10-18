#!/usr/bin/env bash
# Cetak IP laptop dan hostname Rancher (sslip.io) yang boleh dicapai dari browser DAN dari pod dalam kluster lab.
# Guna:  eval "$(bash hostname-rancher.sh)"   -> menetapkan LAPTOP_IP dan RANCHER_HOST
set -euo pipefail
case "$(uname -s)" in
  Darwin) IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1) ;;
  *)      IP=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}' || true)
          [ -n "$IP" ] || IP=$(hostname -I 2>/dev/null | awk '{print $1}') ;;
esac
if [ -z "${IP:-}" ] || [[ "$IP" == 127.* ]]; then
  echo "echo 'Tidak dapat mengesan IP laptop. Tetapkan LAPTOP_IP secara manual.' >&2" ; exit 1
fi
echo "export LAPTOP_IP=$IP"
echo "export RANCHER_HOST=rancher.${IP//./-}.sslip.io"
