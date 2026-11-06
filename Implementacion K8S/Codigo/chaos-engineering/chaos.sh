#!/bin/sh
# Chaos: punto de entrada para las seis fallas. Registra escenario, inicio y fin (UTC) en chaos-runs.log.
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
    network)    sh "$DIR/network-chaos.sh" cut pharmago-pharmacy-service 30 ;;
    disconnect) sh "$DIR/network-chaos.sh" disconnect pharmago-pharmacy-service pharmago-db 30 ;;
    *) return 1 ;;
  esac
}

record() {
  [ -f "$LOG" ] || echo "escenario,inicio,fin" > "$LOG"
  START=$(now)
  echo "=== $1 ($START)"
  run_scenario "$1"
  END=$(now)
  echo "$1,$START,$END" >> "$LOG"
  echo "=== $1 terminado ($END)"
}

case "$1" in
  all)
    for s in $SCENARIOS; do
      record "$s"
      [ "$s" = disconnect ] || sleep "$PAUSE"
    done
    ;;
  requests|cpu|memory|storage|network|disconnect)
    record "$1"
    ;;
  *)
    echo "Uso: $0 requests|cpu|memory|storage|network|disconnect|all"
    exit 1
    ;;
esac
