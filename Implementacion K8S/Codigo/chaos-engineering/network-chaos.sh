#!/bin/sh
# Chaos: fallas de red con iptables desde un contenedor efímero que comparte la red del pod.
# Uso: ./network-chaos.sh cut        [deploy] [seg]           corta todo el tráfico de un pod
#      ./network-chaos.sh disconnect [deploy] [target] [seg]  corta el tráfico de un pod hacia otro componente
NS=pharmago
IMAGE=nicolaka/netshoot:v0.13
MODE="$1"

first_pod() {
  kubectl get pod -n $NS -l app="$1" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

target_ips() {
  SERVICE_IP=$(kubectl get service -n $NS "$1" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
  POD_IPS=$(kubectl get pod -n $NS -l app="$1" -o jsonpath='{.items[*].status.podIP}' 2>/dev/null)
  echo "$SERVICE_IP $POD_IPS"
}

# Las reglas se quitan dentro del contenedor efímero: así se restaura la red aunque se corte este script.
run_in_pod_network() {
  POD="$1"; SECS="$2"; RULES="$3"
  NAME="chaos-net-$(date +%s)"
  kubectl debug -n $NS "$POD" --image=$IMAGE --profile=netadmin --container="$NAME" --quiet -- sh -c "
    trap 'iptables -F INPUT; iptables -F OUTPUT; echo Red restaurada' EXIT
    set -e
    $RULES
    echo Red cortada; iptables -S
    sleep $SECS" >/dev/null || exit 1
  wait_terminated "$POD" "$NAME" $((SECS + 120))
  kubectl logs -n $NS "$POD" -c "$NAME"
}

wait_terminated() {
  DEADLINE=$(( $(date +%s) + $3 ))
  until [ -n "$(kubectl get pod -n $NS "$1" -o jsonpath="{.status.ephemeralContainerStatuses[?(@.name==\"$2\")].state.terminated}")" ]; do
    if [ "$(date +%s)" -ge "$DEADLINE" ]; then
      echo "Error: el contenedor $2 no terminó a tiempo."
      exit 1
    fi
    sleep 2
  done
}

wait_ready() {
  kubectl wait -n $NS --for=condition=Ready pod/"$1" --timeout=180s >/dev/null
}

case "$MODE" in
  cut)
    DEPLOY="${2:-pharmago-pharmacy-service}"
    SECS="${3:-30}"
    RULES="iptables -I INPUT -j DROP; iptables -I OUTPUT -j DROP"
    ;;
  disconnect)
    DEPLOY="${2:-pharmago-pharmacy-service}"
    TARGET="${3:-pharmago-db}"
    SECS="${4:-30}"
    IPS=$(target_ips "$TARGET")
    if [ -z "$(echo $IPS)" ]; then
      echo "Error: no se encontró el servicio ni pods de $TARGET en el namespace $NS."
      exit 1
    fi
    RULES=""
    for ip in $IPS; do RULES="$RULES iptables -I OUTPUT -d $ip -j DROP;"; done
    ;;
  *)
    echo "Uso: $0 cut [deploy] [seg]  |  $0 disconnect [deploy] [target] [seg]"
    exit 1
    ;;
esac

POD=$(first_pod "$DEPLOY")
if [ -z "$POD" ]; then
  echo "Error: no hay pods con app=$DEPLOY en el namespace $NS."
  exit 1
fi
echo "Network $MODE: $POD ${TARGET:+-> $TARGET }(${SECS}s)"
run_in_pod_network "$POD" "$SECS" "$RULES"
START=$(date +%s)
wait_ready "$POD"
echo "READY de nuevo $(( $(date +%s) - START ))s después de restaurar la red"
kubectl get pods -n $NS -l app="$DEPLOY"
