# Detección de anomalías

IsolationForest y One-Class SVM con núcleo RBF sobre datasets de métricas operacionales. Cubre el ítem "Técnicas de detección de anomalías" de la rúbrica.

## Estructura

| Carpeta | Contenido |
|---|---|
| `anomaly_detection/` | Módulo: carga de datasets, detectores, líneas base y evaluación. |
| `tests/` | Tests con pytest. |
| `notebooks/` | Un notebook por dataset, commiteado ejecutado y con sus salidas. |
| `data/` | Datasets en CSV. |

## Entorno

Requiere Python 3.10 o superior. Desde esta carpeta:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash); en Linux o macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Si pip falla con `CERTIFICATE_VERIFY_FAILED` (un proxy o antivirus que intercepta TLS), exportar los certificados raíz del sistema a un archivo PEM y pasarlo con `--cert <archivo>.pem`.

## Verificación

```bash
python -m pytest
python -m jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Para editar un notebook, abrirlo en VS Code con el kernel de `.venv`.
