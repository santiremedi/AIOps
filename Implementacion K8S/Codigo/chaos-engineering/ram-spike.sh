#!/bin/sh
# Chaos: RAM spike en pod. Uso: ./ram-spike.sh [deployment] [MB] [segundos]
. "$(dirname "$0")/lib.sh"
DEPLOY="${1:-pharmago-api-gateway}"
MB="${2:-200}"
SECS="${3:-60}"
POD=$(require_pod "$DEPLOY") || exit 1
echo "RAM spike: $POD (${MB}MB durante ${SECS}s)"
# tail guarda en memoria la última "línea" de su entrada; /dev/zero no tiene saltos de línea,
# así que retiene los MB completos hasta que el sleep cierra el pipe.
kubectl exec -n $NS "$POD" -- sh -c "(head -c ${MB}m /dev/zero; sleep $SECS) | tail > /dev/null"
