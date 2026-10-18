#!/usr/bin/env bash
# Tukar trafik live ke warna yang diberi, selepas semak warna itu sihat.
#   ./switch.sh green     |    ./switch.sh blue   (rollback)
set -euo pipefail
COLOR="${1:?guna: $0 blue|green}"
NS=demo
DEPLOY="demo-bg-${COLOR}"

echo "1) Semak ${DEPLOY} sudah siap sepenuhnya..."
kubectl -n "$NS" rollout status deploy/"$DEPLOY" --timeout=60s
READY=$(kubectl -n "$NS" get deploy "$DEPLOY" -o jsonpath='{.status.readyReplicas}')
WANT=$(kubectl -n "$NS" get deploy "$DEPLOY" -o jsonpath='{.spec.replicas}')
if [[ "${READY:-0}" != "$WANT" ]]; then
  echo "BATAL: hanya ${READY:-0}/${WANT} pod Ready" >&2; exit 1
fi

echo "2) Smoke test dalam kluster terhadap pod ${COLOR}..."
POD_IP=$(kubectl -n "$NS" get pod -l app=demo-bg,slot="$COLOR" -o jsonpath='{.items[0].status.podIP}')
kubectl -n "$NS" run "bg-smoke-$RANDOM" --rm -i --restart=Never --image=busybox:1.36 -- \
  wget -q -O- "http://${POD_IP}:8080/"
echo

echo "3) Tukar Service demo-bg -> ${COLOR}"
kubectl -n "$NS" patch svc demo-bg -p "{\"spec\":{\"selector\":{\"app\":\"demo-bg\",\"slot\":\"${COLOR}\"}}}"
kubectl -n "$NS" get endpointslices -l kubernetes.io/service-name=demo-bg -o wide
echo "Selesai. Rollback: $0 $([[ $COLOR == green ]] && echo blue || echo green)"
