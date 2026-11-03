#!/bin/sh
# Sesión de caos para el dataset de detección de anomalías. Uso: ./run-chaos-session.sh [log.csv] [ciclos]
# Requiere app en K8s + port-forward activo. Dura unos 10 minutos de línea base más 30 por ciclo.
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
CHAOS_DIR="$SCRIPT_DIR/../../chaos-engineering"
LOG="${1:-$SCRIPT_DIR/../data/chaos-log.csv}"
CYCLES="${2:-2}"
TRAFFIC_URL="${TRAFFIC_URL:-http://127.0.0.1:5001/api/roles}"
BASELINE_SECS="${BASELINE_SECS:-600}"
PAUSE_SECS="${PAUSE_SECS:-240}"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

background_traffic() {
  while :; do
    curl -s -o /dev/null "$TRAFFIC_URL"
    sleep 0.5
  done
}

run_scenario() {
  name="$1"
  shift
  start=$(now)
  echo "[$start] $name"
  "$@" || echo "  $name terminó con error"
  echo "$name,$start,$(now)" >> "$LOG"
  sleep "$PAUSE_SECS"
}

mkdir -p "$(dirname "$LOG")"
echo "scenario,start,end" > "$LOG"
background_traffic &
TRAFFIC_PID=$!
trap 'kill $TRAFFIC_PID 2>/dev/null' EXIT INT TERM

echo "Tráfico de fondo contra $TRAFFIC_URL. Línea base de ${BASELINE_SECS}s"
sleep "$BASELINE_SECS"
cycle=1
while [ "$cycle" -le "$CYCLES" ]; do
  echo "=== Ciclo $cycle de $CYCLES"
  run_scenario cpu_users sh "$CHAOS_DIR/cpu-spike.sh" pharmago-users-service 60
  run_scenario ram_users sh "$CHAOS_DIR/ram-spike.sh" pharmago-users-service 250 60
  run_scenario disk_users sh "$CHAOS_DIR/volume-spike.sh" pharmago-users-service 300
  run_scenario db_freeze sh "$CHAOS_DIR/db-freeze.sh" 60
  run_scenario load_gateway sh "$CHAOS_DIR/load-requests.sh" 500
  run_scenario cpu_gateway sh "$CHAOS_DIR/cpu-spike.sh" pharmago-api-gateway 60
  cycle=$((cycle + 1))
done
echo "Listo. Registro en $LOG"
