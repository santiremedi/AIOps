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

`requirements.txt` instala también este módulo en modo editable (`-e .`), así los notebooks y los tests lo importan sin tocar el `PYTHONPATH`.

Si pip falla con `CERTIFICATE_VERIFY_FAILED` (un proxy o antivirus que intercepta TLS), exportar los certificados raíz del sistema a un archivo PEM y apuntar `PIP_CERT` a ese archivo antes de instalar. La opción `--cert` no alcanza: no llega al subproceso que instala `setuptools` para el modo editable.

## Verificación

Con el entorno activado (el kernel de los notebooks arranca el `python` del `PATH`):

```bash
python -m pytest
python -m nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

Para editar un notebook, abrirlo en VS Code con el kernel de `.venv`.
