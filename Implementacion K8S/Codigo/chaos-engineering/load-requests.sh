#!/bin/sh
# Chaos: muchas requests a login. Uso: ./load-requests.sh [cantidad] [url]
# Requiere port-forward activo.
URL="${2:-http://127.0.0.1:5000/api/login}"
N="${1:-500}"
login() {
  curl -s -o /dev/null -X POST "$URL" -H "Content-Type: application/json" -d '{"userName":"x","password":"y"}'
}
if ! login; then
  echo "Error: no se pudo conectar a $URL. ¿Está activo el port-forward?"
  exit 1
fi
echo "Load: $N requests a $URL"
i=0
while [ $i -lt $N ]; do
  login &
  i=$((i+1))
done
wait
echo "Done"
