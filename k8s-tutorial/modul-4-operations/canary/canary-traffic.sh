#!/usr/bin/env bash
# Hantar N request ke Service demo-canary dari dalam kluster dan kira agihan mengikut versi & status.
#   ./canary-traffic.sh 200
N="${1:-200}"
kubectl -n demo run "canary-check-$RANDOM" --rm -i --restart=Never --image=busybox:1.36 -- sh -c "
  i=0; while [ \$i -lt $N ]; do
    wget -q -O- http://demo-canary/ 2>/dev/null | grep -o '\"version\": \"v[0-9]*\"' || echo 'GAGAL (5xx)'
    i=\$((i+1))
  done" | sort | uniq -c
