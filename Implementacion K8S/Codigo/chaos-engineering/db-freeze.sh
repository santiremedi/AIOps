#!/bin/sh
# Chaos: congela SQL Server (SIGSTOP) para simular una base degradada. Uso: ./db-freeze.sh [segundos]
. "$(dirname "$0")/lib.sh"
SECS="${1:-60}"
POD=$(require_pod pharmago-db) || exit 1
echo "DB freeze: $POD (${SECS}s)"
# El trap reanuda la base aunque se corte la sesión de kubectl exec.
kubectl exec -n $NS "$POD" -- sh -c "
  pids=''
  for p in /proc/[0-9]*; do [ \"\$(cat \$p/comm 2>/dev/null)\" = sqlservr ] && pids=\"\$pids \${p#/proc/}\"; done
  trap 'kill -CONT \$pids' EXIT HUP INT TERM
  kill -STOP \$pids
  sleep $SECS"
