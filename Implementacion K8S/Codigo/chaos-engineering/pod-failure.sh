#!/bin/sh
# Chaos: fallas de pods para ver self-healing y circuit breaker.
# Uso: ./pod-failure.sh kill    [deploy]       mata el proceso de un pod (el kubelet reinicia el contenedor)
#      ./pod-failure.sh delete  [deploy]       borra un pod (el ReplicaSet crea otro)
#      ./pod-failure.sh db-down [N] [url]      baja la DB, manda N requests y la restaura
# Requiere port-forward activo para db-down.
NS=pharmago
MODE="$1"

first_pod() {
  kubectl get pod -n $NS -l app="$1" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

wait_available() {
  sleep 3
  kubectl wait -n $NS --for=condition=Available deployment/"$1" --timeout=300s >/dev/null
}

case "$MODE" in
  kill|delete)
    DEPLOY="${2:-pharmago-pharmacy-service}"
    POD=$(first_pod "$DEPLOY")
    if [ -z "$POD" ]; then
      echo "Error: no hay pods con app=$DEPLOY en el namespace $NS."
      exit 1
    fi
    START=$(date +%s)
    if [ "$MODE" = kill ]; then
      echo "Matando el proceso principal de $POD"
      kubectl exec -n $NS "$POD" -- sh -c 'kill 1'
      sleep 3
      kubectl wait -n $NS --for=condition=Ready pod/"$POD" --timeout=180s >/dev/null
    else
      echo "Borrando $POD"
      kubectl delete pod -n $NS "$POD" --wait=false
      wait_available "$DEPLOY"
    fi
    echo "Recuperado en $(( $(date +%s) - START ))s"
    kubectl get pods -n $NS -l app="$DEPLOY"
    ;;
  db-down)
    N="${2:-30}"
    URL="${3:-http://127.0.0.1:5000/api/drug}"
    echo "Bajando pharmago-db"
    kubectl scale deployment/pharmago-db -n $NS --replicas=0
    kubectl wait -n $NS --for=delete pod -l app=pharmago-db --timeout=120s >/dev/null
    sleep 15
    kubectl get pods -n $NS -l 'app in (pharmago-pharmacy-service,pharmago-users-service)'
    echo "Enviando $N requests a $URL (codigo HTTP, header X-Circuit-Breaker)"
    i=0
    while [ $i -lt "$N" ]; do
      curl -s -o /dev/null -D - "$URL" | tr -d '\r' | awk '/^HTTP/{code=$2} tolower($1)=="x-circuit-breaker:"{cb=$2} END{print code, cb}'
      i=$((i+1))
    done | sort | uniq -c
    echo "Restaurando pharmago-db"
    START=$(date +%s)
    kubectl scale deployment/pharmago-db -n $NS --replicas=1
    wait_available pharmago-db
    wait_available pharmago-pharmacy-service
    wait_available pharmago-users-service
    echo "Servicios READY de nuevo en $(( $(date +%s) - START ))s"
    kubectl get pods -n $NS
    ;;
  *)
    echo "Uso: $0 kill|delete [deploy]  |  $0 db-down [N] [url]"
    exit 1
    ;;
esac
