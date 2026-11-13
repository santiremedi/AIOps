#!/bin/sh
# Chaos: fallas de red con iptables desde un contenedor efímero que comparte la red del pod.
# Uso: ./network-chaos.sh cut        [deploy] [seg]           corta todo el tráfico de un pod
#      ./network-chaos.sh disconnect [deploy] [target] [seg]  corta el tráfico de un pod hacia otro componente
. "$(dirname "$0")/lib.sh"
IMAGE=nicolaka/netshoot:v0.13
PULL_TIMEOUT=300
MODE="$1"

target_ips() {
  SERVICE_IP=$(kubectl get service -n $NS "$1" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
  POD_IPS=$(kubectl get pod -n $NS -l app="$1" -o jsonpath='{.items[*].status.podIP}' 2>/dev/null)
  echo "$SERVICE_IP $POD_IPS" | tr ' ' '\n' | grep -E '^[0-9]+(\.[0-9]+){3}$'
}

iptables_commands() {
  ACTION="$1"; SPECS="$2"; ON_ERROR="$3"
  echo "$SPECS" | while read -r spec; do
    [ -n "$spec" ] && printf 'iptables %s %s %s; ' "$ACTION" "$spec" "$ON_ERROR"
  done
}

ephemeral_state() {
  kubectl get pod -n $NS "$1" -o jsonpath="{.status.ephemeralContainerStatuses[?(@.name==\"$2\")].state}"
}

wait_ephemeral() {
  POD="$1"; NAME="$2"; STATE="$3"; TIMEOUT="$4"
  DEADLINE=$(( $(date +%s) + TIMEOUT ))
  until ephemeral_state "$POD" "$NAME" | grep -qE "\"($STATE)\""; do
    if [ "$(date +%s)" -ge "$DEADLINE" ]; then
      echo "Error: el contenedor $NAME no llegó a $STATE en ${TIMEOUT}s."
      exit 1
    fi
    sleep 2
  done
}

exit_code() {
  kubectl get pod -n $NS "$1" -o jsonpath="{.status.ephemeralContainerStatuses[?(@.name==\"$2\")].state.terminated.exitCode}"
}

# Las reglas se quitan dentro del contenedor efímero: así se restaura la red aunque se corte este script.
run_in_pod_network() {
  POD="$1"; SECS="$2"; SPECS="$3"
  NAME="chaos-net-$(date +%s)"
  kubectl debug -n $NS "$POD" --image=$IMAGE --profile=netadmin --container="$NAME" --quiet -- sh -c "
    trap '$(iptables_commands -D "$SPECS" "2>/dev/null || true") echo Red restaurada' EXIT
    trap 'exit 1' HUP INT TERM
    set -e
    $(iptables_commands -I "$SPECS")
    echo Red cortada
    sleep $SECS" >/dev/null || exit 1
  wait_ephemeral "$POD" "$NAME" "running|terminated" $PULL_TIMEOUT
  wait_ephemeral "$POD" "$NAME" "terminated" $((SECS + 60))
  kubectl logs -n $NS "$POD" -c "$NAME"
  if [ "$(exit_code "$POD" "$NAME")" != 0 ]; then
    echo "Error: no se pudieron aplicar las reglas de iptables en $POD."
    exit 1
  fi
}

case "$MODE" in
  cut)
    DEPLOY="${2:-pharmago-pharmacy-service}"
    SECS="${3:-20}"
    SPECS="INPUT -j DROP
OUTPUT -j DROP"
    ;;
  disconnect)
    DEPLOY="${2:-pharmago-pharmacy-service}"
    TARGET="${3:-pharmago-db}"
    SECS="${4:-30}"
    IPS=$(target_ips "$TARGET")
    if [ -z "$IPS" ]; then
      echo "Error: no se encontró el servicio ni pods de $TARGET en el namespace $NS."
      exit 1
    fi
    SPECS=$(echo "$IPS" | sed 's/^/OUTPUT -d /; s/$/ -j DROP/')
    ;;
  *)
    echo "Uso: $0 cut [deploy] [seg]  |  $0 disconnect [deploy] [target] [seg]"
    exit 1
    ;;
esac

POD=$(require_pod "$DEPLOY") || exit 1
echo "Network $MODE: $POD ${TARGET:+-> $TARGET }(${SECS}s)"
run_in_pod_network "$POD" "$SECS" "$SPECS"
START=$(date +%s)
if ! kubectl wait -n $NS --for=condition=Ready pod/"$POD" --timeout=180s >/dev/null; then
  echo "Error: $POD no volvió a READY en 180s."
  exit 1
fi
echo "READY de nuevo $(( $(date +%s) - START ))s después de restaurar la red"
kubectl get pods -n $NS -l app="$DEPLOY"
