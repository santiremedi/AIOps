#!/bin/sh
# Chaos: congela SQL Server (SIGSTOP) para simular una base degradada. Uso: ./db-freeze.sh [segundos]
SECS="${1:-60}"
POD=$(kubectl get pod -n pharmago -l app=pharmago-db -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$POD" ]; then
  echo "Error: no hay pods con app=pharmago-db en el namespace pharmago."
  exit 1
fi
echo "DB freeze: $POD (${SECS}s)"
# El trap reanuda la base aunque se corte la sesión de kubectl exec.
kubectl exec -n pharmago "$POD" -- sh -c "
  pids=''
  for p in /proc/[0-9]*; do [ \"\$(cat \$p/comm 2>/dev/null)\" = sqlservr ] && pids=\"\$pids \${p#/proc/}\"; done
  trap 'kill -CONT \$pids' EXIT HUP INT TERM
  kill -STOP \$pids
  sleep $SECS"
