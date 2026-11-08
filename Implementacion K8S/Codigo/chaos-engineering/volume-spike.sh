#!/bin/sh
# Chaos: llenar disco/ephemeral en pod. Uso: ./volume-spike.sh [deployment] [MB] [segundos]
. "$(dirname "$0")/lib.sh"
DEPLOY="${1:-pharmago-api-gateway}"
MB="${2:-300}"
SECS="${3:-60}"
POD=$(require_pod "$DEPLOY") || exit 1
echo "Volume spike: $POD (${MB}MB durante ${SECS}s)"
# El trap borra el archivo aunque se corte la sesión de kubectl exec.
kubectl exec -n $NS "$POD" -- sh -c "trap 'rm -f /tmp/chaos_fill' EXIT HUP INT TERM; dd if=/dev/zero of=/tmp/chaos_fill bs=1M count=$MB; sleep $SECS"
