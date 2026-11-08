#!/bin/sh
# Chaos: CPU spike en pod. Uso: ./cpu-spike.sh [deployment] [segundos]
. "$(dirname "$0")/lib.sh"
DEPLOY="${1:-pharmago-api-gateway}"
SECS="${2:-30}"
POD=$(require_pod "$DEPLOY") || exit 1
echo "CPU spike: $POD (${SECS}s)"
kubectl exec -n $NS "$POD" -- sh -c "pids=''; for i in 1 2 3 4; do (while :; do :; done) & pids=\"\$pids \$!\"; done; sleep $SECS; kill \$pids"
