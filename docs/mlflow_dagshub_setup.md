# MLflow local and DagsHub setup

Los experimentos de Fase 3 y las evaluaciones posteriores se ejecutaron originalmente en el entorno local. En Fase 7B se publicó su evidencia histórica en DagsHub sin reentrenamiento ni recálculo de métricas. El repositorio GitHub y el tracking remoto ya son accesibles; los comandos de reproducción de entrenamiento que siguen son históricos y no se necesitan para revisar la entrega.

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

## Evidencia histórica publicada en DagsHub

- [Experimento: 31 runs FINISHED](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/#/experiments/0).
- [Champion XGBoost](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/#/experiments/0/runs/2adae7bc49f14c12a24fb18c2c87b60a).
- [Informe de publicación](../PHASE_7B_DAGSHUB_PUBLICATION_REPORT.md), [IDs locales/remotos](../PHASE_7B_DAGSHUB_RUN_MAPPING.json) y [hashes de artifacts](../PHASE_7B_DAGSHUB_ARTIFACT_MANIFEST.json).

Cuenta DagsHub verificada: `elverl`, distinta del propietario GitHub `elverluiszuniga-netizen`. El experimento local `1` se corresponde con el remoto `0`; los 31 IDs de runs cambiaron y las 22 relaciones padre-hijo se reconstruyeron. Se conservaron nombres, tiempos históricos, 477 parámetros y los 617 registros completos de métricas, incluidos timestamp y step.

La transferencia usó el cliente instalado MLflow 3.16.1 contra el servidor 3.5.1 mediante APIs estándar, sin actualizar dependencias. El origen SQLite se abrió en modo de solo lectura; los datos se importaron como evidencia existente. No se ejecutaron los comandos de entrenamiento o monitoring para publicar. Los tags de ID fuente y un manifiesto persistente permitieron reanudar sin duplicados.

Se publicaron los 145 artifacts históricos y dos manifiestos de procedencia en el run del champion. Diez copias se sanearon sustituyendo el prefijo del checkout privado, manteniendo los originales y ambos hashes. No se publicaron raw, DB, matrices procesadas, credenciales ni logs locales. Los modelos y valores de resultados permanecen idénticos.

Se verificó el acceso anónimo a los 31 runs, sus parámetros/métricas y la descarga de los 145 artifacts. Las páginas generales del sitio pueden redirigir al login; los enlaces directos `.mlflow` anteriores y las descargas del informe fueron comprobados sin credenciales. No se comparte ningún token con el evaluador.

El champion se recupera como archivo nativo desde su run remoto, artifact `model/XGBoost.ubj`, o desde la copia GitHub `models/XGBoost.ubj`, con el mismo SHA256 del manifiesto. No existe un flavor `MLmodel`, Model Registry ni servicio desplegado. Los artifacts que mencionan IDs locales son snapshots históricos: consultar el mapeo para resolverlos al destino.

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
