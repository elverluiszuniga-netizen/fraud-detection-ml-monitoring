# fraud-detection-ml-monitoring
Proyecto académico de Machine Learning Engineering III: clasificación de fraude transaccional con target `isFraud`.

Estado actual: **Data audit / project initialization**.

Restricción temporal: `step <= 400` corresponde a reference/development y `step >= 401` a production simulada. No se permite un split aleatorio que mezcle ambos periodos.

## Estructura inicial
- `data/raw/`, `data/processed/`: datos excluidos de Git.
- `src/fraud_detection/`: funciones de validación.
- `scripts/`: auditoría reproducible.
- `tests/`: pruebas sintéticas.
- `reports/figures/`, `reports/monitoring/`, `artifacts/`, `notebooks/`, `app/`, `docs/`: reservados, sin implementación posterior.
- `INITIAL_DATA_AUDIT.md`: reporte de esta fase.

## Reproducción en PowerShell
```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".uv-cache"
uv sync --offline
uv run python -m unittest discover -s tests -v
uv run python scripts/audit_data.py --input PS_20174392719_1491204439457_log.csv
```
La fase utiliza solo la biblioteca estándar de Python. La auditoría recorre el CSV sin cargarlo completo y utiliza SQLite temporal en disco para conteos exactos. Requiere espacio temporal libre (varios GB) y elimina su base temporal al terminar. Genera `reports/audit_results.json` e `INITIAL_DATA_AUDIT.md`.

El dataset raw no se versiona por tamaño; se conserva el original en la raíz sin modificaciones. No se han entrenado modelos ni implementado monitoreo, aplicaciones o integraciones externas.
