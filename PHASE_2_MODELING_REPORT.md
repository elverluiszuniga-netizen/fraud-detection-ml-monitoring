# Phase 2 Modeling Report

## 1 Executive summary
Five fixed baseline benchmarks trained on full Train, evaluated only on untouched temporal Validation. PR-AUC denotes Average Precision, the principal metric. Production was not evaluated or used for any modeling decision. No definitive champion or production threshold is selected. Principal features assume scoring before execution; post-event balances and residuals are excluded.

## 2 Initial Phase 1 state
Reviewed INITIAL_DATA_AUDIT.md, README.md, pyproject.toml, scripts/audit_data.py, existing tests, repository structure and Git before modification. Phase 1 audited 6,362,620 rows and 11 columns, no nulls or exact duplicates. Development has 5,787,030 observations and 4,477 frauds. Phase 1 was not rerun or rewritten. Initial branch main; switched to development. Preexisting untracked academic PDF was preserved. No remote operations, main changes, commits or integration tools were performed.

## 3 Temporal design and counts
Inspected artifacts/development_temporal_profile.csv containing transactions, frauds and prevalence for every Development step; plotted all three before training. Prespecified cut: floor(0.8 * 400) = 320, accepted only after verifying >=100 frauds in each segment. No cutoff search using model performance.

| Segment | Steps | Observations | Frauds | Prevalence |
|---|---|---:|---:|---:|
| Train | 1–320 | 4,388,788 | 3,609 | 0.082232% |
| Validation | 321–400 | 1,398,242 | 868 | 0.062078% |

The split is exhaustive inside Development and has no step overlap. The 80/20 ratio refers to steps, not row counts. All Train rows and frauds were used for each model. Validation preserves original prevalence. No synthetic sampling or weighting of Validation.

## 4 Feature engineering and leakage review
Final ordered predictors: step, amount, oldbalanceOrg, oldbalanceDest, amount_to_oldbalanceOrg, orig_balance_zero, orig_balance_emptied, dest_is_merchant, type_CASH_IN, type_CASH_OUT, type_DEBIT, type_PAYMENT, type_TRANSFER, type_UNKNOWN.

Base: step, amount, oldbalanceOrg, oldbalanceDest. Derived: amount-to-prior-balance ratio, zero balance indicator, approximate requested emptying, M-prefixed destination, fixed transaction-type indicators and unknown type indicator. Tolerance 0.01 absolute monetary units; positive prior balance required for emptying. Division by zero uses 0 plus zero-denominator indicator; nonfinite features raise errors. Float64 engineering, float32 stored model matrices.

See docs/feature_catalog.md for each source, formula, availability, risk and INCLUDE/EXCLUDE/REVIEW decision. Origin balance difference = oldbalanceOrg - newbalanceOrig; destination difference = newbalanceDest - oldbalanceDest. Residuals subtract amount only for TRANSFER/CASH_OUT, otherwise 0 as not applicable. Implemented review candidates passed a finite-output check on the first 1,000 Development rows, but remain excluded because they need post-event balances. Their predictive performance was not evaluated.

No target-derived features, future aggregates or entity encoding. Logistic scaler is fitted solely on Train. Production is discarded in each raw input chunk before any feature generation or aggregation. Matrices are Development only. Synthetic tests also verify row-locality and invariance to labels, flag, identities within the same prefix class and post-event balances.

## 5 Identifiers and existing rule
nameOrig and raw nameDest are excluded; no ID one-hot or global target encoding. Only the nameDest M-prefix is retained as a structural proxy, not a verified real merchant classification.

isFlaggedFraud is excluded from every predictor matrix. Development-only descriptive rule results:

{
  "train": {
    "flagged": 3,
    "true_fraud": 3,
    "precision": 1.0,
    "recall": 0.0008312551953449709
  },
  "validation": {
    "flagged": 1,
    "true_fraud": 1,
    "precision": 1.0,
    "recall": 0.001152073732718894
  }
}

Precision 1.0 is based on only four flagged events across Development and is highly uncertain; recall is extremely low. No Production rule analysis was performed.

## 6 Models and fixed configurations
Dummy uses class priors; LogisticRegression and RandomForest use balanced class weights computed on Train. XGBoost and LightGBM use unweighted objectives. No optimization, early stopping against Validation, threshold selection or resampling. Seed 42; trees use four workers. Scaling only for logistic regression. Fixed small ensembles prioritize efficiency. LightGBM uses max_delta_step=1.0 as a fixed numerical stability safeguard: the initial unrestricted run built 100 trees but predicted a constant zero score on Validation (AP equal to prevalence and ROC-AUC 0.5). This degenerate run was investigated once with identical parameters; leaf update clipping was then introduced without searching parameters or selecting the change by model rank. The final table uses the stabilized configuration; the initial degenerate values are documented here rather than mixed with the final run.

```json
{
  "Dummy": {
    "constant": "None",
    "random_state": "42",
    "strategy": "prior"
  },
  "LogisticRegression": {
    "memory": "None",
    "transform_input": "None",
    "verbose": "False",
    "standardscaler": "StandardScaler()",
    "logisticregression": "LogisticRegression(class_weight='balanced', max_iter=400, random_state=42)"
  },
  "RandomForest": {
    "bootstrap": "True",
    "ccp_alpha": "0.0",
    "class_weight": "balanced",
    "criterion": "gini",
    "max_depth": "12",
    "max_features": "sqrt",
    "max_leaf_nodes": "None",
    "max_samples": "None",
    "min_impurity_decrease": "0.0",
    "min_samples_leaf": "20",
    "min_samples_split": "2",
    "min_weight_fraction_leaf": "0.0",
    "monotonic_cst": "None",
    "n_estimators": "40",
    "n_jobs": "4",
    "oob_score": "False",
    "random_state": "42",
    "verbose": "0",
    "warm_start": "False"
  },
  "XGBoost": {
    "objective": "binary:logistic",
    "base_score": "None",
    "booster": "None",
    "callbacks": "None",
    "colsample_bylevel": "None",
    "colsample_bynode": "None",
    "colsample_bytree": "None",
    "device": "None",
    "early_stopping_rounds": "None",
    "enable_categorical": "True",
    "eval_metric": "logloss",
    "feature_types": "None",
    "feature_weights": "None",
    "gamma": "None",
    "grow_policy": "None",
    "importance_type": "None",
    "interaction_constraints": "None",
    "learning_rate": "0.1",
    "max_bin": "None",
    "max_cat_threshold": "None",
    "max_cat_to_onehot": "None",
    "max_delta_step": "None",
    "max_depth": "5",
    "max_leaves": "None",
    "min_child_weight": "None",
    "missing": "nan",
    "monotone_constraints": "None",
    "multi_strategy": "None",
    "n_estimators": "100",
    "n_jobs": "4",
    "num_parallel_tree": "None",
    "random_state": "42",
    "reg_alpha": "None",
    "reg_lambda": "None",
    "sampling_method": "None",
    "scale_pos_weight": "None",
    "subsample": "None",
    "tree_method": "hist",
    "validate_parameters": "None",
    "verbosity": "None"
  },
  "LightGBM": {
    "boosting_type": "gbdt",
    "class_weight": "None",
    "colsample_bytree": "1.0",
    "importance_type": "split",
    "learning_rate": "0.1",
    "max_depth": "-1",
    "min_child_samples": "20",
    "min_child_weight": "0.001",
    "min_split_gain": "0.0",
    "n_estimators": "100",
    "n_jobs": "4",
    "num_leaves": "31",
    "objective": "None",
    "random_state": "42",
    "reg_alpha": "0.0",
    "reg_lambda": "0.0",
    "subsample": "1.0",
    "subsample_for_bin": "200000",
    "subsample_freq": "0",
    "deterministic": "True",
    "force_col_wise": "True",
    "max_delta_step": "1.0",
    "verbosity": "-1"
  }
}
```

Full estimator configuration is stored in artifacts/phase2_run.json. Dependencies and exact versions are recorded in pyproject.toml and uv.lock.

## 7 Complete Validation results
| model | train_observations | validation_observations | training_seconds | prediction_seconds | pr_auc | roc_auc | precision_05 | recall_05 | f1_05 | f2_05 | tp | fp | tn | fn | k_0.1pct | precision_top_0.1pct | recall_top_0.1pct | k_0.5pct | precision_top_0.5pct | recall_top_0.5pct | k_1pct | precision_top_1pct | recall_top_1pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dummy | 4388788 | 1398242 | 0.183975 | 0.077118 | 0.000621 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 | 0 | 1397374 | 868 | 1399 | 0.000000 | 0.000000 | 6992 | 0.000286 | 0.002304 | 13983 | 0.000429 | 0.006912 |
| LogisticRegression | 4388788 | 1398242 | 10.116063 | 0.189498 | 0.998850 | 0.999525 | 0.997699 | 0.998848 | 0.998273 | 0.998618 | 867 | 2 | 1397372 | 1 | 1399 | 0.619728 | 0.998848 | 6992 | 0.123999 | 0.998848 | 13983 | 0.062004 | 0.998848 |
| RandomForest | 4388788 | 1398242 | 77.542323 | 0.610391 | 0.999997 | 1.000000 | 0.996556 | 1.000000 | 0.998275 | 0.999309 | 868 | 3 | 1397371 | 0 | 1399 | 0.620443 | 1.000000 | 6992 | 0.124142 | 1.000000 | 13983 | 0.062075 | 1.000000 |
| XGBoost | 4388788 | 1398242 | 13.524489 | 0.558082 | 0.999760 | 1.000000 | 1.000000 | 0.998848 | 0.999424 | 0.999078 | 867 | 0 | 1397374 | 1 | 1399 | 0.620443 | 1.000000 | 6992 | 0.124142 | 1.000000 | 13983 | 0.062075 | 1.000000 |
| LightGBM | 4388788 | 1398242 | 11.971916 | 1.421617 | 0.999993 | 1.000000 | 1.000000 | 0.997696 | 0.998847 | 0.998156 | 866 | 0 | 1397374 | 2 | 1399 | 0.620443 | 1.000000 | 6992 | 0.124142 | 1.000000 | 13983 | 0.062075 | 1.000000 |

Precision, Recall, F1, F2 and TP/FP/TN/FN use score >= 0.5. This is the standard benchmark convention, not a chosen production threshold. No exploratory threshold was selected. Accuracy is omitted because it is poorly informative under extreme imbalance. Weighted-model scores are not calibrated prevalence estimates. ROC-AUC is secondary to Average Precision.

## 8 Operational ranking
Precision@Top-K is the fraction of reviewed transactions that are fraudulent. Recall@Top-K (Fraud Capture Rate) is the fraction of all Validation frauds present in the reviewed set. If reviewers can examine only X% of transactions, recall quantifies the share of fraud captured.

Top 0.1%, 0.5%, 1% use ceil(N * fraction) observations. Ranking ties use stable original row order. Dummy scores are constant: its Top-K statistics reflect incidental input order and have no risk ranking interpretation. Metrics are batch-level retrospective rankings rather than a demonstrated online review policy. No threshold or model was chosen using these values.

## 9 Timing and figures
Total preparation, model fitting, prediction, evaluation and figures: 150.8 seconds (2.51 minutes). Individual fit/prediction durations are in the table. Preparation: 23.8 seconds. Times depend on hardware and resource contention.

Figures in reports/figures/: average_precision_comparison.png, confusion_Dummy.png, confusion_LightGBM.png, confusion_LogisticRegression.png, confusion_RandomForest.png, confusion_XGBoost.png, development_temporal.png, precision_recall.png, roc.png. Curves display up to 5,000 sampled curve points for compact plotting; all observations contribute to metrics. Temporal profile and AP comparison use complete aggregate data. Confusion matrices display exact counts.

## 10 Tests and reproducibility
Executed complete existing and new synthetic suite, without loading the large CSV in pytest:

```
...................                                                      [100%]
19 passed in 8.71s
```

Tests cover schema, sign conventions, tolerance, zero denominator, finite features, unknown type, no label/post-event/ID leakage, row-local transformations, cutoff count guard, boundary masks, Production exclusion, training step guard, ranking rounding/ties, confusion counts and F2. README.md documents uv sync --locked, pytest, preparation-only, full baseline and report regeneration commands in PowerShell. notebooks/02_ml_training.ipynb loads saved artifacts without duplicating the implementation.

## 11 Files and dependencies
Principal additions: src/fraud_detection/features.py, splitting.py, metrics.py, modeling.py; scripts/run_baselines.py, build_phase2_report.py, execute_phase2_notebook.py; tests/test_modeling.py; docs/feature_catalog.md; notebooks/02_ml_training.ipynb; PHASE_2_MODELING_REPORT.md; small CSV/JSON artifacts and figures. README.md, pyproject.toml, uv.lock and .gitignore were updated. Raw dataset and Phase 1 audit were preserved. Large feature matrices stay ignored; no giant models saved.

Declared project configuration:
```toml
[project]
name = "fraud-detection-ml-monitoring"
version = "0.1.0"
description = "Inicialización y auditoría temporal del dataset de fraude"
requires-python = ">=3.10"
dependencies = [
    "ipython>=8.39.0",
    "lightgbm>=4.7.0",
    "matplotlib>=3.10.9",
    "numpy>=2.2.6",
    "pandas>=2.3.3",
    "pytest>=9.1.1",
    "scikit-learn>=1.7.2",
    "xgboost>=3.2.0",
]

[tool.uv]
package = false
```

Git review at report generation (preexisting PDF is not part of this phase):
```
M .gitignore
 M README.md
 M pyproject.toml
 M uv.lock
?? PHASE_2_MODELING_REPORT.md
?? "Proyecto Final - Curso MLE3.pdf"
?? artifacts/baseline_model_comparison.csv
?? artifacts/development_temporal_profile.csv
?? artifacts/phase2_run.json
?? docs/feature_catalog.md
?? notebooks/02_ml_training.ipynb
?? reports/figures/average_precision_comparison.png
?? reports/figures/confusion_Dummy.png
?? reports/figures/confusion_LightGBM.png
?? reports/figures/confusion_LogisticRegression.png
?? reports/figures/confusion_RandomForest.png
?? reports/figures/confusion_XGBoost.png
?? reports/figures/development_temporal.png
?? reports/figures/precision_recall.png
?? reports/figures/roc.png
?? scripts/build_phase2_report.py
?? scripts/execute_phase2_notebook.py
?? scripts/run_baselines.py
?? src/fraud_detection/features.py
?? src/fraud_detection/metrics.py
?? src/fraud_detection/modeling.py
?? src/fraud_detection/splitting.py
?? tests/test_modeling.py
```

## 12 Limitations and problems
Near-perfect results can reflect deterministic simulation relationships, particularly amount approximately matching previous balance; they do not establish real-world generalization. Origin/destination prior balances and identifier prefixes are assumed available before execution and need domain confirmation. The step trend may not extrapolate. A single temporal holdout cannot establish stability across many time periods. The Development temporal profile also contains steps with 100% fraud prevalence and very low transaction counts, while busy steps have much lower prevalence; this simulation schedule can make step an unusually informative predictor. Class-weighted scores require later calibration consideration. Validation has 868 positive cases; metrics have sampling uncertainty. Float32 storage can round large amounts. The tolerance is a fixed engineering convention, not tuned.

Windows sandbox process startup failed; authorized local commands used execution outside that failing sandbox. Git reported different directory ownership; safe.directory was scoped to individual commands without changing global configuration. Dependencies installed successfully with uv. No material computational blocker remained. No formal drift analysis, monitoring, SHAP, experiment platform, advanced tuning or final Production evaluation was undertaken.

## 13 Next phase recommendation and approvals
Consider leading benchmarks as candidates only, guided primarily by Validation Average Precision and operational ranking, while reviewing false positives and simulation-specific feature shortcuts. Confirm pre-execution availability of prior destination/origin balances and prefix semantics before operational use. Approve the next academic phase separately; this implementation stops here. No additional approval is needed for the completed Phase 2 under the authorized document instructions. Do not declare a champion or production threshold based on this report.

PHASE 2: COMPLETE
