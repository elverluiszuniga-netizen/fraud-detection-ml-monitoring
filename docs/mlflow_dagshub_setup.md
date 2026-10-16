# MLflow local and DagsHub setup

Phase 3 is runnable locally without a remote repository or credentials. No remote was created, no push was performed and no external experiment link exists yet. DagsHub integration is prepared through MLflow environment variables; it was not connected or exercised remotely.

## Reproduce the phase in PowerShell

Run at the fraud-detection-ml-monitoring repository root:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked
uv run python -m pytest -q
uv run python scripts/run_sanity_checks.py
uv run python scripts/run_optimization.py --max-trials 20 --minimum-trials 10
uv run python scripts/build_phase3_report.py
```

The sanity script verifies every persisted Development matrix row against features reconstructed from the raw Development CSV. It does not rewrite Phase 2 matrices or outputs. Optimization requires the persisted matrices and matching sanity hashes. Missing matrices are a prerequisite failure; do not rerun the Phase 1 audit. To reproduce the full project from scratch, follow the Phase 2 preparation command separately before Phase 3.

Optuna uses sequential seeded TPE (seed 42, five startup trials), an initial baseline-like trial, exact Validation Average Precision maximization and estimator early stopping. Trials run on full Train without class resampling; row bagging parameters are algorithm-native regularization, not an artificial class-balanced dataset. A prespecified practical plateau may stop a study after at least ten completed trials when best AP >=0.9999 and best improvement over the last five trials <=0.00001. Otherwise the limit is twenty. This is a compute rule, not evidence of statistically equivalent models. Validation is reused for tuning and early stopping, so tuned scores are development-selection estimates. Production is never used.

Repeated complete executions create distinct named studies and MLflow runs. They do not silently resume an old study. Seeded single-process trials reproduce suggestions on the same locked environment; cross-version/platform timing and numerical differences remain possible. Optuna persistence supports audit, not an implicit resume command. Do not increase the search budget to chase meaningless decimals.

## Local tracking location and UI

Metadata: `mlruns/mlflow.db` (SQLite). MLflow artifacts: `mlartifacts/`. Optuna: `optuna_studies/phase3.db`. All three stores are ignored by Git. Only small result/configuration CSV and JSON files, reports, code and figures may be versioned. The native best models are stored under ignored `data/processed/phase3_models/` and as MLflow artifacts, with the ordered feature list and a model manifest. Datasets, full score arrays and credentials are never logged.

```powershell
$trackingUri = 'sqlite:///' + (Join-Path $PWD 'mlruns/mlflow.db').Replace('\', '/')
uv run mlflow ui --backend-store-uri $trackingUri --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000 in your browser and select `fraud-detection-hyperparameter-optimization`. The UI is local to this computer; it is not a public experiment link. Parent runs group each algorithm, nested child runs represent trials, best-trial runs reproduce and save the selected models, baseline reference runs import Phase 2 evidence without retraining, and a summary run contains comparison and champion rationale. `artifacts/phase3_run.json` lists the execution id, study names, run ids, count and experiment id. Reports can be regenerated without training using `build_phase3_report.py`.

## Evidencia externa: pendiente de autorización

DagsHub es una opción sugerida por la consigna, no un servicio conectado. No hay enlace externo real. Antes de publicar se requieren repositorio/endpoint verificados, acceso del usuario y autorización explícita. No guardar tokens en archivos/Git/artifacts ni imprimir variables de entorno.

Para Fase 7B, transferir los runs y artifacts **existentes**: inventariar 31 runs, verificar parámetros/métricas y modelos, exportar metadatos/artifacts sin CSV completo ni score arrays, importar al endpoint autorizado, documentar mapeo de IDs/linaje y verificar acceso del evaluador. Preservar el store local y hashes. Esa transferencia no está implementada ni ejecutada en Fase 7A; no sustituirla por `run_optimization.py --allow-remote-tracking`, porque ese comando reentrena.

Credenciales solo mediante variables de entorno de proceso con entrada segura y eliminación al terminar. La opción CLI de remote tracking protege futuros entrenamientos autorizados; no es mecanismo de publicación de resultados existentes. Si se elige otro hosting de evidencia MLflow, verificar de igual forma permisos y enlace real. No se inventan URLs.

## Model loading

XGBoost: instantiate XGBClassifier and load the best `.ubj` model. Its saved best-iteration metadata preserves early-stopping prediction behavior. LightGBM: instantiate Booster(model_file=...) using the best native `.txt` file saved at best_iteration. Construct features with the Phase 2 engineer_features function and exact MODEL_COLUMNS ordering before inference. El XGBoost congelado es el modelo académico de producción simulada entregado en models/. 0.5 continúa como threshold de evaluación. No es un servicio desplegado; ver model_recovery.md.

## Primary implementation references

- [MLflow local SQLite tracking](https://www.mlflow.org/docs/latest/ml/tracking/tutorials/local-database/)
- [MLflow Python tracking API](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.html)
- [Optuna seeded TPE sampler](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html)
- [XGBoost sklearn and early-stopping API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)
- [LightGBM metrics and parameters](https://lightgbm.readthedocs.io/en/stable/Parameters.html)
- [DagsHub MLflow integration](https://dagshub.com/docs/integration_guide/mlflow_tracking/)

MLflow includes web-serving libraries transitively; no project web application, dashboard, deployment or monitoring code is implemented in Phase 3.
