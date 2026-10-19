#!/usr/bin/env bash
# Rakam garis masa HPA ke CSV semasa ujian beban, untuk dianalisis selepas ujian.
#   ./watch-hpa.sh                      -> namespace demo, hpa demo-app, setiap 5s
#   ./watch-hpa.sh demo demo-app 5 > hpa-timeline.csv
# Lajur: masa, replicas semasa, replicas dikehendaki, CPU%, memori%, pod Ready, pod Pending, pod restart
set -euo pipefail
NS="${1:-demo}"
HPA="${2:-demo-app}"
INTERVAL="${3:-5}"
SELECTOR="$(kubectl -n "$NS" get hpa "$HPA" -o jsonpath='{.spec.scaleTargetRef.name}')"
SELECTOR="app=${SELECTOR}"

echo "time,current_replicas,desired_replicas,cpu_pct,mem_pct,ready_pods,pending_pods,restarts"
while true; do
  read -r cur des cpu mem < <(kubectl -n "$NS" get hpa "$HPA" -o jsonpath='{.status.currentReplicas} {.status.desiredReplicas} {.status.currentMetrics[?(@.resource.name=="cpu")].resource.current.averageUtilization} {.status.currentMetrics[?(@.resource.name=="memory")].resource.current.averageUtilization}' 2>/dev/null; echo)
  pods="$(kubectl -n "$NS" get pods -l "$SELECTOR" --no-headers -o custom-columns=PHASE:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount 2>/dev/null || true)"
  ready="$(awk '$2=="true"{n++} END{print n+0}' <<<"$pods")"
  pending="$(awk '$1=="Pending"{n++} END{print n+0}' <<<"$pods")"
  restarts="$(awk '$3 ~ /^[0-9]+$/ {n+=$3} END{print n+0}' <<<"$pods")"
  echo "$(date +%H:%M:%S),${cur:-},${des:-},${cpu:-},${mem:-},${ready},${pending},${restarts}"
  sleep "$INTERVAL"
done
