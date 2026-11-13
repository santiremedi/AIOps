#!/bin/sh
# Funciones comunes de los scripts de caos. Se cargan con: . "$(dirname "$0")/lib.sh"
NS=pharmago

first_pod() {
  kubectl get pod -n $NS -l app="$1" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

require_pod() {
  POD=$(first_pod "$1")
  if [ -z "$POD" ]; then
    echo "Error: no hay pods con app=$1 en el namespace $NS." >&2
    exit 1
  fi
  echo "$POD"
}
