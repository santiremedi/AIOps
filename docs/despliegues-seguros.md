# Despliegues seguros

Cómo cumple PharmaGo el ítem "Despliegues seguros" de la rúbrica: los microservicios se reemplazan por una versión nueva garantizando 100% de disponibilidad.

## Técnica elegida: rolling update sin pods no disponibles

Es la estrategia nativa de los Deployments de Kubernetes: reemplaza los pods de a uno, levantando el nuevo antes de bajar el viejo. Se aplica a `pharmago-api-gateway`, `pharmago-users-service`, `pharmago-pharmacy-service` y `pharmago-ui`, en sus manifiestos de [`k8s/deployments/`](../Implementacion%20K8S/Codigo/k8s/deployments).

Sola, la estrategia no alcanza para el 100%. Lo garantizan cuatro piezas juntas:

| Pieza | Configuración | Qué evita |
|---|---|---|
| `maxUnavailable: 0` | `spec.strategy.rollingUpdate` | Que Kubernetes baje un pod viejo antes de tener uno nuevo listo. Nunca hay menos pods sirviendo que réplicas deseadas. |
| `maxSurge: 1` | `spec.strategy.rollingUpdate` | Que el rollout se trabe: permite un pod extra temporal para que el nuevo conviva con el viejo. |
| `readinessProbe` | En cada contenedor (`/health` en users y pharmacy, puerto 80 en el gateway, `/` en la UI) | Que el Service mande tráfico a un pod que todavía está arrancando. El pod nuevo recién recibe requests cuando el probe pasa. |
| `preStop: sleep 10` | `lifecycle` de cada contenedor | Que se corten requests al bajar el pod viejo. Kubernetes saca el pod del Service y le manda la señal de apagado al mismo tiempo; los 10 segundos de espera dan tiempo a que el resto del cluster deje de enviarle tráfico antes de que el proceso termine. |

### Secuencia de un rollout

1. Se crea el pod nuevo (`maxSurge: 1`). El viejo sigue atendiendo todo el tráfico.
2. El pod nuevo arranca; cuando pasa el `readinessProbe` entra al Service y empieza a recibir requests.
3. Recién entonces Kubernetes termina el pod viejo (`maxUnavailable: 0`): lo saca del Service y ejecuta el `preStop`.
4. Durante los 10 segundos del `preStop` el pod viejo termina los requests en curso y deja de recibir nuevos. Después se apaga.

En ningún momento hay cero pods listos detrás del Service, así que ningún request falla.

## Por qué rolling update y no canary o blue-green

| Técnica | Cómo funciona | Por qué no la elegimos |
|---|---|---|
| **Rolling update** | Reemplaza pods de a uno dentro del mismo Deployment. | Elegida: es nativa, no agrega manifiestos ni herramientas, y con las cuatro piezas de arriba cumple el 100% de disponibilidad. |
| **Canary** | Manda una parte del tráfico a la versión nueva y la promueve si las métricas están bien. | Reduce el **riesgo de una versión mala**, no mejora la disponibilidad del reemplazo: al promover igual hay que reemplazar los pods sin cortes, que es lo que ya resuelve el rolling update. En Kubernetes sin herramientas extra requiere dos Deployments por servicio y repartir tráfico por cantidad de réplicas. |
| **Blue-green** | Levanta una copia completa de la versión nueva y cambia el Service de golpe. | Duplica los recursos de cada microservicio durante el despliegue, y con un nodo por microservicio el cluster no tiene margen para eso. |

## Componentes con estado

La base de datos, Elasticsearch y Prometheus usan `strategy: Recreate`: tienen un único volumen de datos y dos instancias no pueden escribir sobre el mismo directorio. Kibana también usa `Recreate` para no tener dos instancias de 2Gi en el nodo `ops` a la vez. Su reemplazo implica unos segundos sin servicio. El ítem de la rúbrica apunta a los microservicios de la aplicación, que son stateless.

## Desplegar una versión nueva

Los comandos se ejecutan desde `Implementacion K8S/Codigo/k8s`. Las imágenes usan el tag `latest` con `imagePullPolicy: Never`, así que volver a aplicar el manifiesto no dispara un rollout: hay que reiniciar el Deployment después de reconstruir la imagen.

```bash
./build-images.sh
kubectl rollout restart deployment/pharmago-users-service -n pharmago
kubectl rollout status deployment/pharmago-users-service -n pharmago
```

### Rollback

Si la versión nueva no queda lista, el rollout se detiene solo y el pod viejo sigue atendiendo, porque `maxUnavailable: 0` impide bajarlo. Para volver a la versión anterior:

```bash
kubectl rollout undo deployment/pharmago-users-service -n pharmago
```

## Demostrar que no hay cortes

El tráfico de prueba tiene que salir desde adentro del cluster: `kubectl port-forward` se conecta a un único pod y se corta cuando ese pod se reemplaza, aunque el Service siga disponible.

En una terminal, 300 requests al gateway (unos 60 segundos) que pasan por users-service:

```bash
kubectl run trafico -n pharmago --rm -i --restart=Never --image=curlimages/curl --command -- sh -c 'for i in $(seq 1 300); do curl -s -o /dev/null -w "%{http_code}\n" --max-time 2 http://pharmago-api-gateway/api/roles/ping; sleep 0.2; done | sort | uniq -c'
```

Mientras corre, en otra terminal reemplazar users-service y el gateway:

```bash
kubectl rollout restart deployment/pharmago-users-service deployment/pharmago-api-gateway -n pharmago
kubectl rollout status deployment/pharmago-users-service -n pharmago
kubectl rollout status deployment/pharmago-api-gateway -n pharmago
```

El resultado esperado es `300 200`: todos los requests respondieron bien. Cualquier otro código (`000` es timeout o conexión rechazada, `502`/`503` es el gateway sin destino) indica un corte.
