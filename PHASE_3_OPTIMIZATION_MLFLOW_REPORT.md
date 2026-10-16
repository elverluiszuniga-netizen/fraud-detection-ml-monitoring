# Phase 3 Optimization and MLflow Report

## 1 Executive summary
Sanity checks completed before tuning: all 5,787,030 Development feature/label rows exactly reconstructed from raw Development, no prohibited predictor or implementation leakage detected. Strong simulator shortcuts explain near-perfect separability. XGBoost and LightGBM optimized with finite seeded Optuna searches and local nested MLflow tracking. The selected XGBoost is a PROVISIONAL CHAMPION, not a final production champion. Production remained completely reserved. Validation is now reused for selection and early stopping, so tuned scores are development estimates rather than independent test evidence.

## 2 Received state and scope
Reviewed the Phase 1 audit, Phase 2 report, feature catalog, README, pyproject, src, scripts, tests, baseline comparison, executed Phase 2 notebook and current Git. Branch development throughout. Existing uncommitted Phase 2 work was preserved; no prior phase rerun, no baseline model retraining, no remote, push, merge, tag or release. Fingerprints confirm Phase 2 features.py, modeling.py, run_baselines.py and report remained unchanged. Phase 2 matrices were verified, not rewritten.

Train: steps 1–320, 4,388,788 rows, 3,609 frauds. Validation: steps 321–400, 1,398,242 rows, 868 frauds. No resampling; original Validation prevalence. Production is excluded from sanity checks, optimization, early stopping, class-weight decisions, candidate selection and calibration.

## 3 Sanity check evidence and conclusion
See docs/perfect_performance_sanity_check.md and artifacts/phase3_sanity.json. Exact raw reconstruction, strict nonoverlapping temporal ranges, schema checks and prohibited-column mutation invariance passed. isFraud, isFlaggedFraud, raw IDs, new balances and their derivatives are absent. Fixed row-local features require no fitted preprocessing. Phase 2 logistic scaler fit only on Train.

The fixed rule TRANSFER/CASH_OUT plus requested balance emptying captures 3,533/3,609 Train frauds (97.8942%) and 852/868 Validation frauds (98.1567%), with zero false positives in each segment. The emptied feature has Validation univariate AP approximately 0.981578. Univariate high/low directions for all fourteen columns and seven fixed simple rules are persisted. Development has 137 all-fraud low-volume steps containing 1524 transactions, indicating a simulation scheduling pattern. No predictors were removed or modified to reduce scores artificially.

A: no implementation evidence of leakage detected. B: near-deterministic simulator relationships present. C: pre-execution balance availability, prefix semantics, generator shortcuts and external generalization remain uncertain. Absence of detected implementation leakage is not proof that simulation label-generation shortcuts are absent.

## 4 Algorithms and optimization rationale
Tune XGBoost and LightGBM: Phase 2 AP is already high, training takes seconds, histogram boosting scales to full Train, and constrained complexity/regularization spaces enable efficient experiments. Compact tree models are suitable for later explanation workflows, including possible SHAP, without implementing explanations here. Logistic regression remains an interpretable baseline and Random Forest a strong benchmark; costly RF search offers little clear value under saturation.

## 5 Objective and search spaces
Direction maximize, objective exact sklearn Average Precision on Validation. Accuracy not optimized or used for selection. Additional ROC-AUC, threshold-0.5 precision/recall/F1/F2/confusion counts, operational Top-K and timing are logged for every trial. No final production threshold selected.

| algorithm | parameter | range | scale | rationale |
| --- | --- | --- | --- | --- |
| XGBoost | n_estimators | 80 to 200 | int | Upper bound on boosting rounds; early stopping may use fewer |
| XGBoost | max_depth | 3 to 7 | int | Bound tree complexity |
| XGBoost | learning_rate | 0.03 to 0.15 | log | Moderate shrinkage |
| XGBoost | min_child_weight | 0.5 to 10.0 | log | Leaf Hessian regularization |
| XGBoost | subsample | 0.8 to 1.0 | float | Controlled row sampling inside Train |
| XGBoost | colsample_bytree | 0.8 to 1.0 | float | Controlled feature sampling |
| XGBoost | reg_alpha | 0.0001 to 1.0 | log | L1 regularization |
| XGBoost | reg_lambda | 0.5 to 5.0 | log | L2 regularization |
| XGBoost | gamma | 0.0 to 1.0 | float | Split gain requirement |
| XGBoost | scale_pos_weight | 1, 10, 100 | categorical | Controlled native weights, no full inverse-prevalence assumption |
| LightGBM | n_estimators | 80 to 200 | int | Upper bound on boosting rounds |
| LightGBM | learning_rate | 0.03 to 0.15 | log | Moderate shrinkage |
| LightGBM | num_leaves | 15 to 31 | int | Bound leaf count; capped by selected depth |
| LightGBM | max_depth | 4 to 7 | int | Bound tree complexity |
| LightGBM | min_child_samples | 20 to 100 | int | Minimum leaf observations |
| LightGBM | subsample | 0.8 to 1.0 | float | Train bagging; subsample_freq fixed to 1 |
| LightGBM | colsample_bytree | 0.8 to 1.0 | float | Feature sampling |
| LightGBM | reg_alpha | 0.0001 to 1.0 | log | L1 regularization |
| LightGBM | reg_lambda | 0.5 to 5.0 | log | L2 regularization |
| LightGBM | scale_pos_weight | 1, 10, 100 | categorical | Controlled native weights, no full inverse-prevalence assumption |

LightGBM num_leaves upper bound is additionally capped at 2**max_depth. Fixed: four workers, random_state 42, XGBoost histogram method, LightGBM deterministic/force_col_wise, max_delta_step 1.0 inherited from the stability correction, subsample_freq 1 to activate bagging. Native scale_pos_weight alternatives are 1, 10, 100; full inverse prevalence is not assumed optimal. There is no artificial class-balanced dataset or balanced Validation.

## 6 Optuna configuration and actual trials
TPESampler(seed=42,n_startup_trials=5,multivariate=False); sequential study.optimize n_jobs=1; seed 42; five startup trials; one enqueued baseline-like candidate under the Phase 3 early-stopping protocol. NopPruner; estimator early stopping provides computational control. Upper budget 20 trials per algorithm. At least 10 completed trials before the prespecified plateau can stop: best AP >=0.9999 and maximum improvement relative to the best before the last five trials <=0.00001. Fewer trials demonstrate saturation, not global-optimum discovery or statistical equivalence.

| algorithm | trials | ap_min | ap_max | ap_median | fit_seconds |
| --- | --- | --- | --- | --- | --- |
| LightGBM | 10 | 0.02345220 | 1.00000000 | 0.99966666 | 122.94676480 |
| XGBoost | 10 | 0.99884908 | 0.99991859 | 0.99982341 | 167.64146250 |

Study completion details:
```json
{
  "XGBoost": {
    "study_name": "20261004T152211371659Z_XGBoost",
    "trials": 10,
    "best_trial": 7,
    "best_parameters": {
      "n_estimators": 148,
      "max_depth": 6,
      "learning_rate": 0.1469541059356907,
      "min_child_weight": 3.532871354926938,
      "subsample": 0.9942734367531818,
      "colsample_bytree": 0.8825728131957696,
      "reg_alpha": 0.02165779390916417,
      "reg_lambda": 0.5395608952674368,
      "gamma": 0.9674364834653933,
      "scale_pos_weight": 10.0
    },
    "best_trial_value": 0.9999185900788442,
    "best_trial_run_id": "1fbb627a70de438b8aefa60154a1f57d",
    "stop_reason": "prespecified_practical_saturation",
    "trial_pr_auc_min": 0.998849082523785,
    "trial_pr_auc_max": 0.9999185900788442,
    "best_run_id": "1d353308f1e3427094a221667f3da9de",
    "refit_matches_best_trial": true
  },
  "LightGBM": {
    "study_name": "20261004T152211371659Z_LightGBM",
    "trials": 10,
    "best_trial": 0,
    "best_parameters": {
      "n_estimators": 100,
      "learning_rate": 0.1,
      "max_depth": 5,
      "num_leaves": 31,
      "min_child_samples": 20,
      "subsample": 1.0,
      "colsample_bytree": 1.0,
      "reg_alpha": 0.0001,
      "reg_lambda": 0.5,
      "scale_pos_weight": 1.0
    },
    "best_trial_value": 1.0,
    "best_trial_run_id": "17155e8a4c2449c9a8930b67e397e336",
    "stop_reason": "prespecified_practical_saturation",
    "trial_pr_auc_min": 0.023452198744142182,
    "trial_pr_auc_max": 1.0,
    "best_run_id": "0b450b60eded4bdab40160bd9d4ce3b1",
    "refit_matches_best_trial": true
  }
}
```

Persistent Optuna storage: `sqlite:///./optuna_studies/phase3.db`. Repeated executions create new uniquely named studies; no silent resume. Exact AP ties choose earliest completed trial reproducibly. Selected models were refit using identical Train/Validation protocol and their AP reproduced to tolerance 1e-10. Trial dispersion is hyperparameter sensitivity on one reused holdout, not independent temporal stability. The minimum/median/maximum table deliberately retains poor trials, including any degenerate ranking or threshold behavior. Saturation of the best observed value does not imply that all configurations are stable or that native weighting is always helpful.

## 7 Early stopping
Patience 20, Development Validation only. XGBoost eval_metric aucpr is its native interpolated PR-area metric, which differs from exact Average Precision; the final trial objective always computes exact AP after prediction. LightGBM monitors native average_precision with first_metric_only=True. Selected effective iterations appear in the comparison. No Production early stopping or training on Train+Validation.

## 8 MLflow configuration and experiment evidence
Local metadata URI: `sqlite:///./mlruns/mlflow.db`. Artifacts: `mlartifacts/`; experiment `fraud-detection-hyperparameter-optimization` id `1`. Execution `20261004T152211371659Z` has 29 FINISHED runs: four imported baseline reference runs, two algorithm parents, 20 child trials, two best-trial refits/native model runs and one comparison summary. Baseline references log saved Phase 2 evidence and are not newly trained models.

```json
[
  {
    "role": "baseline_reference",
    "algorithm": "LogisticRegression",
    "run_id": "7fa24d6ea79f4b6d8f62a07236a351f9"
  },
  {
    "role": "baseline_reference",
    "algorithm": "RandomForest",
    "run_id": "33845df18b4a48288e116b0027e6b946"
  },
  {
    "role": "baseline_reference",
    "algorithm": "XGBoost",
    "run_id": "ac0682a9e54a4f75a3b63cd052a1fdc6"
  },
  {
    "role": "baseline_reference",
    "algorithm": "LightGBM",
    "run_id": "e5b6ee1abaca488095f18010663e5166"
  },
  {
    "role": "algorithm_parent",
    "algorithm": "XGBoost",
    "run_id": "d18fbdce26b74ebf97073b110eca54c2"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 0,
    "run_id": "c59c39c3a2c94ac09c84ab4910a6971b"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 1,
    "run_id": "e2ed011b3ba047e7bded7d278c8b0115"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 2,
    "run_id": "ec2c94b13a2f4c8b9d28731222d400a7"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 3,
    "run_id": "dfeb3a494f8d46a184212798089f23ec"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 4,
    "run_id": "023cd1c3521a4affbf7912a1ce58fe09"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 5,
    "run_id": "cdeaeffbe978456a93bbf642eeb10b8d"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 6,
    "run_id": "41f73af9dba14a7d97371b548fa1e4b8"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 7,
    "run_id": "1fbb627a70de438b8aefa60154a1f57d"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 8,
    "run_id": "c11529857b7c4030b5589c588f94008a"
  },
  {
    "role": "trial",
    "algorithm": "XGBoost",
    "trial": 9,
    "run_id": "3ee468511a6c4f6fb78bfa8693c82928"
  },
  {
    "role": "best_trial_refit",
    "algorithm": "XGBoost",
    "run_id": "1d353308f1e3427094a221667f3da9de"
  },
  {
    "role": "algorithm_parent",
    "algorithm": "LightGBM",
    "run_id": "4e71a938811f4a86a71292cb6adeb669"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 0,
    "run_id": "17155e8a4c2449c9a8930b67e397e336"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 1,
    "run_id": "54ea51eb9ac44e85af481111bd904cdd"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 2,
    "run_id": "3f5e3df5e3fe418ebff49133ceb1d51d"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 3,
    "run_id": "78eabe4bbf1048c482a7cafd7508b3e9"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 4,
    "run_id": "e936815afc094268bf71234ef023100c"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 5,
    "run_id": "d742fd989af24bf3a71a4c0c60b8bba7"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 6,
    "run_id": "dbaf47c49bb54324b1028450609ce4d8"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 7,
    "run_id": "92a5ca187d1b4fcf92d9c89ffbaa72ad"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 8,
    "run_id": "b4afceed25ca464e9ef3c828cc9baf9a"
  },
  {
    "role": "trial",
    "algorithm": "LightGBM",
    "trial": 9,
    "run_id": "c17e19d3d4904ab38316ac9e21395984"
  },
  {
    "role": "best_trial_refit",
    "algorithm": "LightGBM",
    "run_id": "0b450b60eded4bdab40160bd9d4ce3b1"
  },
  {
    "role": "comparison_summary",
    "run_id": "8102e98114514566a47f68945f260aa4"
  }
]
```

Each trial logs algorithm, sampled parameters, seed, feature count, Train/Validation step ranges, threshold convention, exact AP, ROC-AUC, P/R/F1/F2, TP/FP/TN/FN, Top0.1%/0.5%/1%, effective iterations and fit/prediction time. Artifacts include metrics and feature list per trial; selected models additionally have native model manifest, PR/ROC curves and confusion matrix. Parents include search summaries, summary run includes comparison, sanity evidence, source, pyproject and lockfile. No dataset, full score arrays, credentials or environment-variable dumps are logged. In-progress/failed fits enter a run before fitting, preserving failure visibility.

## 9 Best parameters
```json
{
  "XGBoost": {
    "n_estimators": 148,
    "max_depth": 6,
    "learning_rate": 0.1469541059356907,
    "min_child_weight": 3.532871354926938,
    "subsample": 0.9942734367531818,
    "colsample_bytree": 0.8825728131957696,
    "reg_alpha": 0.02165779390916417,
    "reg_lambda": 0.5395608952674368,
    "gamma": 0.9674364834653933,
    "scale_pos_weight": 10.0
  },
  "LightGBM": {
    "n_estimators": 100,
    "learning_rate": 0.1,
    "max_depth": 5,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_alpha": 0.0001,
    "reg_lambda": 0.5,
    "scale_pos_weight": 1.0
  }
}
```

Best search trial ids and MLflow run ids are included above. Native models are saved locally under ignored data/processed/phase3_models and logged as compact MLflow artifacts. Their ordered features and effective iterations are explicit. Serialization is tested on small synthetic data.

## 10 Baseline versus tuned results
| model | variant | pr_auc | roc_auc | precision_05 | recall_05 | f1_05 | f2_05 | tp | fp | tn | fn | training_seconds | prediction_seconds | effective_iterations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | baseline | 0.99884966 | 0.99952544 | 0.99769850 | 0.99884793 | 0.99827288 | 0.99861783 | 867 | 2 | 1397372 | 1 | 10.11606340 | 0.18949810 | nan |
| RandomForest | baseline | 0.99999735 | 1.00000000 | 0.99655568 | 1.00000000 | 0.99827487 | 0.99930923 | 868 | 3 | 1397371 | 0 | 77.54232330 | 0.61039140 | 40.00000000 |
| XGBoost | baseline | 0.99975950 | 0.99999982 | 1.00000000 | 0.99884793 | 0.99942363 | 0.99907813 | 867 | 0 | 1397374 | 1 | 13.52448850 | 0.55808210 | 100.00000000 |
| LightGBM | baseline | 0.99999340 | 1.00000000 | 1.00000000 | 0.99769585 | 0.99884660 | 0.99815583 | 866 | 0 | 1397374 | 2 | 11.97191610 | 1.42161740 | 100.00000000 |
| XGBoost | tuned | 0.99991859 | 0.99999997 | 1.00000000 | 0.99884793 | 0.99942363 | 0.99907813 | 867 | 0 | 1397374 | 1 | 16.28608990 | 0.18658530 | 24.00000000 |
| LightGBM | tuned | 1.00000000 | 1.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0 | 0 | 1397374 | 868 | 5.80575850 | 0.34441730 | 20.00000000 |

Exact saved values, including best_parameters, are in artifacts/tuned_model_comparison.csv. Imported baseline times were measured during Phase 2; tuned times come from Phase 3 best refits. Protocol differs: Phase 2 baselines had no early stopping while tuned models do. Timing is a single-run observation under local resource conditions and is not a controlled latency benchmark. ROC-AUC values displayed near one do not imply zero errors; inspect FP/FN explicitly.

## 11 Operational Top-K
| model | variant | k_0.1pct | precision_top_0.1pct | recall_top_0.1pct | k_0.5pct | precision_top_0.5pct | recall_top_0.5pct | k_1pct | precision_top_1pct | recall_top_1pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | baseline | 1399 | 0.61972838 | 0.99884793 | 6992 | 0.12399886 | 0.99884793 | 13983 | 0.06200386 | 0.99884793 |
| RandomForest | baseline | 1399 | 0.62044317 | 1.00000000 | 6992 | 0.12414188 | 1.00000000 | 13983 | 0.06207538 | 1.00000000 |
| XGBoost | baseline | 1399 | 0.62044317 | 1.00000000 | 6992 | 0.12414188 | 1.00000000 | 13983 | 0.06207538 | 1.00000000 |
| LightGBM | baseline | 1399 | 0.62044317 | 1.00000000 | 6992 | 0.12414188 | 1.00000000 | 13983 | 0.06207538 | 1.00000000 |
| XGBoost | tuned | 1399 | 0.62044317 | 1.00000000 | 6992 | 0.12414188 | 1.00000000 | 13983 | 0.06207538 | 1.00000000 |
| LightGBM | tuned | 1399 | 0.62044317 | 1.00000000 | 6992 | 0.12414188 | 1.00000000 | 13983 | 0.06207538 | 1.00000000 |

Top0.1% = 1,399 transactions; Top0.5% = 6,992; Top1% = 13,983. Recall is fraction of all 868 Validation frauds captured; precision is fraud share of reviewed transactions. This is retrospective ranking at unchanged prevalence, not a demonstrated real-time operational policy. Stable input row order breaks ties, as in Phase 2.

## 12 Timing and saturation analysis
Sanity verification and descriptive analysis: 61.6 seconds. Optimization including tracking, best refits and figures: 578.8 seconds. Combined compute: 640.4 seconds (10.67 minutes), excluding dependency installation, report construction and human-readable implementation work. Per-trial and per-model timing are recorded separately.

Near-ceiling AP differences do not establish meaningful superiority or statistical significance with 868 positives on one reused holdout. Models in the predeclared practical band of 0.0001 AP are treated as approximately similar for candidate decision-making, not statistically proven equivalent. Compare operational capture, false negatives/positives at the fixed threshold, measured inference time, fitted iterations, training time, complexity and later maintainability. Logistic regression offers interpretability; RF remains a strong reference. Tuning is not presumed to improve every baseline. Some boosting trials achieve high ranking AP while all scores remain below 0.5 and threshold recall is zero; optimizing ranking does not optimize calibration or threshold-specific recall. These results are retained transparently rather than hidden or corrected by selecting a new threshold.

## 13 Provisional champion
XGBoost in practical AP band, Top0.1% recall=1.000000; threshold 0.5 FN=1, FP=0; prediction=0.187s; effective iterations=24. No statistically proven superiority; times are one-run measurements.

Prespecified selection policy: Tuned candidates within 0.0001 AP of best; full Top0.1% capture preferred; then FN, FP, measured prediction latency, effective iterations, training time and name. Selection is restricted to tuned candidates for a compact, tracked boosting artifact. The strong RF baseline remains a benchmark and is not declared inferior. Both tuned algorithms support later tree explanation workflows; no SHAP is implemented. Hyperparameter-search saturation and best-trial reproduction offer implementation evidence, not proof of future stability. This provisional decision must be revisited on genuinely independent evidence in a separately authorized phase.

## 14 DagsHub status
Prepared only: docs/mlflow_dagshub_setup.md documents MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD using process environment variables. Remote URI requires explicit --allow-remote-tracking; credential-containing URLs are rejected. No repository or remote experiment created, no token invented, no secrets written, no push. An external academic experiment link is pending real remote access and later authorization; this does not block the independently completed local tracking phase. Local UI instructions use localhost and the actual SQLite store.

## 15 Tests notebook and verification
Full suite:
```
...............................                                          [100%]
============================== warnings summary ===============================
tests/test_optimization.py::TrackingTests::test_local_nested_logging
  .\.venv\Lib\site-packages\mlflow\store\tracking\utils\sql_trace_metrics_utils.py:155: SADeprecationWarning: The ``noload`` loader strategy is deprecated and will be removed in a future release.  This option produces incorrect results by returning ``None`` for related items. (deprecated since: 2.1) (This warning originated from the `configure_mappers()` process, which was invoked automatically in response to a user-initiated operation.)
    _SESSION_TRACE_METADATA = aliased(SqlTraceMetadata)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
31 passed, 1 warning in 8.12s
```

6 notebook code cells executed successfully from artifacts; no heavy logic duplicated. Tests use small synthetic arrays and CSVs only, cover valid bounded search spaces, depth/leaves consistency, objective AP/run linkage, deterministic best ties, saturation, metrics, model early stopping and native serialization, local nested MLflow logging and artifacts, exact provenance, and rejection of Production or invalid schema. The initial test cleanup encountered a Windows pooled SQLite lock; disposing the test engine fixed it. MLflow emits a dependency SQLAlchemy noload deprecation warning; it does not prevent logging or pass/fail validation. LightGBM uses its current eval_X/eval_y API.

Phase 2 feature/model/source/report fingerprints verified unchanged. Git tracked-path check found no .env, dataset, processed matrices, MLflow or Optuna stores. Ignore rules exclude large/local artifacts. No real credentials were introduced; remote auth is documented using secure input rather than literals. All MLflow runs for this execution are finished and can be queried locally.

## 16 Files dependencies and Git
New files: docs/perfect_performance_sanity_check.md, docs/mlflow_dagshub_setup.md, src/fraud_detection/optimization.py, src/fraud_detection/tracking.py, scripts/run_sanity_checks.py, scripts/run_optimization.py, scripts/build_phase3_report.py, tests/test_optimization.py, notebooks/03_hyperparameter_optimization.ipynb, PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md, artifacts/phase3_sanity.json, artifacts/sanity_univariate_features.csv, artifacts/sanity_simple_rules.csv, artifacts/hyperparameter_search_space.json, artifacts/optimization_trials.csv, artifacts/tuned_model_comparison.csv, artifacts/phase3_run.json, reports/figures/phase3_*.png.
Updated: README.md, pyproject.toml, uv.lock and .gitignore. Added direct dependencies: Optuna and MLflow, with pinned resolution in uv.lock. MLflow brings web-serving libraries transitively; no project web app, service, monitoring or deployment was implemented.

Current branch `development`; existing Phase 2 changes and academic PDF preserved. No commit, push, remote or history modification.
```
M .gitignore
 M README.md
 M pyproject.toml
 M uv.lock
?? PHASE_2_MODELING_REPORT.md
?? "Proyecto Final - Curso MLE3.pdf"
?? artifacts/baseline_model_comparison.csv
?? artifacts/development_temporal_profile.csv
?? artifacts/hyperparameter_search_space.json
?? artifacts/optimization_trials.csv
?? artifacts/phase2_run.json
?? artifacts/phase3_run.json
?? artifacts/phase3_sanity.json
?? artifacts/sanity_simple_rules.csv
?? artifacts/sanity_univariate_features.csv
?? artifacts/tuned_model_comparison.csv
?? docs/feature_catalog.md
?? docs/mlflow_dagshub_setup.md
?? docs/perfect_performance_sanity_check.md
?? notebooks/02_ml_training.ipynb
?? reports/figures/average_precision_comparison.png
?? reports/figures/confusion_Dummy.png
?? reports/figures/confusion_LightGBM.png
?? reports/figures/confusion_LogisticRegression.png
?? reports/figures/confusion_RandomForest.png
?? reports/figures/confusion_XGBoost.png
?? reports/figures/development_temporal.png
?? reports/figures/phase3_confusion_LightGBM.png
?? reports/figures/phase3_confusion_XGBoost.png
?? reports/figures/phase3_optimization_history.png
?? reports/figures/phase3_pr_LightGBM.png
?? reports/figures/phase3_pr_XGBoost.png
?? reports/figures/phase3_roc_LightGBM.png
?? reports/figures/phase3_roc_XGBoost.png
?? reports/figures/precision_recall.png
?? reports/figures/roc.png
?? scripts/build_phase2_report.py
?? scripts/build_phase3_report.py
?? scripts/execute_phase2_notebook.py
?? scripts/run_baselines.py
?? scripts/run_optimization.py
?? scripts/run_sanity_checks.py
?? src/fraud_detection/features.py
?? src/fraud_detection/metrics.py
?? src/fraud_detection/modeling.py
?? src/fraud_detection/optimization.py
?? src/fraud_detection/splitting.py
?? src/fraud_detection/tracking.py
?? tests/test_modeling.py
?? tests/test_optimization.py
```

## 17 Limitations pending decisions and next phase
The simulator contains highly discriminating structural rules; metrics cannot be extrapolated to live banking fraud. Operational prior-balance availability and prefix semantics require confirmation. Reused Validation induces selection optimism; no independent final evaluation was performed. Search is intentionally small, does not establish global optimum, and does not justify sixth-decimal superiority. Weighting can affect calibration; no calibration or threshold optimization performed. Single-run timings and trial score dispersion are limited stability evidence. Native best artifacts require exact Phase 2 feature ordering.

Pending: real DagsHub repository/access and link for academic remote evidence, operational feature availability, separate approval for any Phase 4 work. This phase stops without SHAP/LIME, Production evaluation, drift tests, monitoring, dashboard, app, deployment or publishing. A later authorized phase may examine explanations and further validation; do not execute it automatically.

PHASE 3: COMPLETE
