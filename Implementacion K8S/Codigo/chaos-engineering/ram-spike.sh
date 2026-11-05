#!/bin/sh
# Chaos: RAM spike en pod. Uso: ./ram-spike.sh [deployment] [MB] [segundos]
DEPLOY="${1:-pharmago-api-gateway}"
MB="${2:-200}"
SECS="${3:-60}"
POD=$(kubectl get pod -n pharmago -l app="$DEPLOY" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$POD" ]; then
  echo "Error: no hay pods con app=$DEPLOY en el namespace pharmago."
  exit 1
fi
echo "RAM spike: $POD (${MB}MB durante ${SECS}s)"
# tail guarda en memoria la última "línea" de su entrada; /dev/zero no tiene saltos de línea,
# así que retiene los MB completos hasta que el sleep cierra el pipe.
kubectl exec -n pharmago "$POD" -- sh -c "(head -c ${MB}m /dev/zero; sleep $SECS) | tail > /dev/null"
