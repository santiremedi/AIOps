#!/bin/sh
# Chaos: punto de entrada para las seis fallas. Registra escenario, inicio, fin (UTC) y resultado en chaos-runs.log.
# Uso: ./chaos.sh requests|cpu|memory|storage|network|disconnect|all
#      PAUSE=60 ./chaos.sh all     segundos de pausa entre escenarios
# Requiere port-forward activo para requests.
DIR=$(cd "$(dirname "$0")" && pwd)
LOG="$DIR/chaos-runs.log"
PAUSE="${PAUSE:-60}"
SCENARIOS="requests cpu memory storage network disconnect"

now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

run_scenario() {
  case "$1" in
    requests)   sh "$DIR/load-requests.sh" 500 ;;
    cpu)        sh "$DIR/cpu-spike.sh" pharmago-api-gateway 60 ;;
    memory)     sh "$DIR/ram-spike.sh" pharmago-api-gateway 200 60 ;;
    storage)    sh "$DIR/volume-spike.sh" pharmago-api-gateway 300 60 ;;
    network)    sh "$DIR/network-chaos.sh" cut pharmago-pharmacy-service 20 ;;
    disconnect) sh "$DIR/network-chaos.sh" disconnect pharmago-pharmacy-service pharmago-db 30 ;;
  esac
}

record() {
  [ -f "$LOG" ] || echo "escenario,inicio,fin,resultado" > "$LOG"
  START=$(now)
  echo "=== $1 ($START)"
  if run_scenario "$1"; then RESULT=ok; else RESULT=error; fi
  END=$(now)
  echo "$1,$START,$END,$RESULT" >> "$LOG"
  echo "=== $1 terminado: $RESULT ($END)"
  [ "$RESULT" = ok ]
}

case "$1" in
  all)
    FAILED=""
    for s in $SCENARIOS; do
      record "$s" || FAILED="$FAILED $s"
      [ "$s" = disconnect ] || sleep "$PAUSE"
    done
    if [ -n "$FAILED" ]; then
      echo "Escenarios con error:$FAILED"
      exit 1
    fi
    ;;
  requests|cpu|memory|storage|network|disconnect)
    record "$1"
    ;;
  *)
    echo "Uso: $0 requests|cpu|memory|storage|network|disconnect|all"
    exit 1
    ;;
esac
