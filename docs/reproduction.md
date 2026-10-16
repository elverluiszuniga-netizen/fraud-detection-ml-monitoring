# Instalación, revisión y reproducción

Entorno validado: Windows, PowerShell, Python 3.14.5 (`.python-version`), uv y `uv.lock`. El rango del pyproject no es certificación de todos los Python posibles. Desde la raíz:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
$env:DO_NOT_TRACK = '1'
$env:MLFLOW_DISABLE_TELEMETRY = 'true'
New-Item -ItemType Directory -Force tmp | Out-Null
$env:TEMP = Join-Path $PWD 'tmp'
$env:TMP = $env:TEMP
uv sync --locked
uv run python -m pytest -q -p no:cacheprovider
uv run python scripts/verify_delivery.py --notebooks
# Después de obtener el CSV según data/README.md:
uv run python scripts/verify_delivery.py --raw
```

La primera instalación requiere internet si faltan paquetes. No se necesita el CSV, matrices o MLflow para consultar notebooks/HTML/dashboard y validar la entrega con `verify_delivery` sin `--raw`. El test de MLflow crea un store sintético temporal, no usa el historial real. Los tests entrenan fixtures diminutas únicamente; no regeneran el champion. Los cinco notebooks presentan artifacts y reutilizan funciones. Abrir desde raíz o carpeta notebooks; el verificador establece raíz desde `__file__`, por lo que admite una invocación desde otro directorio. No guarda outputs de notebooks históricos.

La validación en sandbox puede fallar con permisos al consultar el intérprete o canonicalizar archivos XGBoost; usar un terminal local con permisos normales y TEMP accesible. No modificar resultados para ocultar estos errores.

## Rutas

Scripts/app toman raíz desde su archivo. Raw: argumento `--input` (audit/baselines) o `FRAUD_DATA_PATH`, relativo a raíz o absoluto, luego `data/raw/<nombre>`, luego ubicación legacy en raíz. Un override inexistente falla, no se ignora. Modelos: ver `model_recovery.md`. Tracking de scripts de presentación/interpretabilidad/monitoring resuelve SQLite bajo la raíz actual; URIs históricas permanecen como metadatos. Optimization permite endpoint remoto solo con flag explícito y autorización; no invocarlo para transferir evidencia.

## Producción histórica de resultados (no ejecutar para revisar entrega)

Esta secuencia documenta cómo se produjeron las fases, no es una instrucción para reentrenar en Fase 7A/7B. Los comandos pueden sobrescribir resultados o añadir runs:

| Fase | Productor |
|---|---|
| 1 | `scripts/audit_data.py` (recorre raw y reemplaza auditoría) |
| 2 | `scripts/run_baselines.py --prepare-only` (matrices) o sin flag (entrena); `build_phase2_report.py` |
| 3 | `run_sanity_checks.py`, `run_optimization.py`, `build_phase3_report.py` |
| 4 | `run_interpretability.py`, `build_phase4_report.py` |
| 5 | `freeze_monitoring_model.py`, `run_monitoring.py`, `build_phase5_report.py` |
| 6 | `streamlit run app/main.py` (solo lectura de artifacts) |

Reproducción pesada exige raw verificado, varios GB RAM/disco, matrices Development y acceso al store histórico para scripts que preservan linaje. Los modelos no requieren reentrenamiento para entrega. No se certificó un entrenamiento nuevo desde cero. Las rutas absolutas dentro de reportes/JSON históricos son procedencia, no dependencias activas del dashboard/verificador. No editarlos: su identidad está autenticada por el freeze.

## Limitaciones conocidas

PaySim tiene relaciones casi deterministas; métricas no extrapolables a banca real. Validation fue reutilizada por tuning/early stopping; Production es retrospectiva con etiquetas asumidas disponibles. No calibración ni costo/threshold operativo seleccionado. Balances y prefijo M requieren verificación fuera del simulador. Dependencia temporal limita tests iid; PSI muestral no es KS/TV full-data. Concept drift no establecido. No scores individuales persistidos para AP/ROC arbitrarias multiventana, ni SHAP Production. No streaming, servicio online, cloud o alertas en vivo.
