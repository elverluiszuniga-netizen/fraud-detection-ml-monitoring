"""Build the academic report/notebook from completed benchmark evidence."""
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def markdown_table(frame):
    columns = list(frame.columns)
    lines = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for values in frame.itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(f'{x:.6f}' if isinstance(x,float) else str(x) for x in values) + ' |')
    return '\n'.join(lines)

def main():
    info = json.loads((ROOT/'artifacts/phase2_run.json').read_text(encoding='utf-8'))
    results = pd.read_csv(ROOT/'artifacts/baseline_model_comparison.csv')
    if 'total_seconds' not in info or len(results) != 5:
        raise RuntimeError('Complete benchmark artifacts are required; no completion report fabricated')
    test = subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
    if test.returncode: raise RuntimeError(test.stdout + test.stderr)
    train, valid = info['split']['train'], info['split']['validation']
    configs = {name:{k:v for k,v in config.items() if '__' not in k and k != 'steps'}
               for name,config in info['configurations'].items()}
    figures = sorted(p.name for p in (ROOT/'reports/figures').glob('*.png'))
    changed = subprocess.run(['git','-c',f'safe.directory={ROOT.as_posix()}','status','--short'],cwd=ROOT,capture_output=True,text=True).stdout
    deps = (ROOT/'pyproject.toml').read_text(encoding='utf-8-sig')
    report = f'''# Phase 2 Modeling Report

## 1 Executive summary
Five fixed baseline benchmarks trained on full Train, evaluated only on untouched temporal Validation. PR-AUC denotes Average Precision, the principal metric. Production was not evaluated or used for any modeling decision. No definitive champion or production threshold is selected. Principal features assume scoring before execution; post-event balances and residuals are excluded.

## 2 Initial Phase 1 state
Reviewed INITIAL_DATA_AUDIT.md, README.md, pyproject.toml, scripts/audit_data.py, existing tests, repository structure and Git before modification. Phase 1 audited 6,362,620 rows and 11 columns, no nulls or exact duplicates. Development has 5,787,030 observations and 4,477 frauds. Phase 1 was not rerun or rewritten. Initial branch main; switched to development. Preexisting untracked academic PDF was preserved. No remote operations, main changes, commits or integration tools were performed.

## 3 Temporal design and counts
Inspected artifacts/development_temporal_profile.csv containing transactions, frauds and prevalence for every Development step; plotted all three before training. Prespecified cut: floor(0.8 * 400) = 320, accepted only after verifying >=100 frauds in each segment. No cutoff search using model performance.

| Segment | Steps | Observations | Frauds | Prevalence |
|---|---|---:|---:|---:|
| Train | {train['step_min']}–{train['step_max']} | {train['rows']:,} | {train['frauds']:,} | {100*train['prevalence']:.6f}% |
| Validation | {valid['step_min']}–{valid['step_max']} | {valid['rows']:,} | {valid['frauds']:,} | {100*valid['prevalence']:.6f}% |

The split is exhaustive inside Development and has no step overlap. The 80/20 ratio refers to steps, not row counts. All Train rows and frauds were used for each model. Validation preserves original prevalence. No synthetic sampling or weighting of Validation.

## 4 Feature engineering and leakage review
Final ordered predictors: {', '.join(info['features'])}.

Base: step, amount, oldbalanceOrg, oldbalanceDest. Derived: amount-to-prior-balance ratio, zero balance indicator, approximate requested emptying, M-prefixed destination, fixed transaction-type indicators and unknown type indicator. Tolerance 0.01 absolute monetary units; positive prior balance required for emptying. Division by zero uses 0 plus zero-denominator indicator; nonfinite features raise errors. Float64 engineering, float32 stored model matrices.

See docs/feature_catalog.md for each source, formula, availability, risk and INCLUDE/EXCLUDE/REVIEW decision. Origin balance difference = oldbalanceOrg - newbalanceOrig; destination difference = newbalanceDest - oldbalanceDest. Residuals subtract amount only for TRANSFER/CASH_OUT, otherwise 0 as not applicable. Implemented review candidates passed a finite-output check on the first 1,000 Development rows, but remain excluded because they need post-event balances. Their predictive performance was not evaluated.

No target-derived features, future aggregates or entity encoding. Logistic scaler is fitted solely on Train. Production is discarded in each raw input chunk before any feature generation or aggregation. Matrices are Development only. Synthetic tests also verify row-locality and invariance to labels, flag, identities within the same prefix class and post-event balances.

## 5 Identifiers and existing rule
nameOrig and raw nameDest are excluded; no ID one-hot or global target encoding. Only the nameDest M-prefix is retained as a structural proxy, not a verified real merchant classification.

isFlaggedFraud is excluded from every predictor matrix. Development-only descriptive rule results:

{json.dumps(info['business_rule'], indent=2)}

Precision 1.0 is based on only four flagged events across Development and is highly uncertain; recall is extremely low. No Production rule analysis was performed.

## 6 Models and fixed configurations
Dummy uses class priors; LogisticRegression and RandomForest use balanced class weights computed on Train. XGBoost and LightGBM use unweighted objectives. No optimization, early stopping against Validation, threshold selection or resampling. Seed 42; trees use four workers. Scaling only for logistic regression. Fixed small ensembles prioritize efficiency. LightGBM uses max_delta_step=1.0 as a fixed numerical stability safeguard: the initial unrestricted run built 100 trees but predicted a constant zero score on Validation (AP equal to prevalence and ROC-AUC 0.5). This degenerate run was investigated once with identical parameters; leaf update clipping was then introduced without searching parameters or selecting the change by model rank. The final table uses the stabilized configuration; the initial degenerate values are documented here rather than mixed with the final run.

```json
{json.dumps(configs, indent=2)}
```

Full estimator configuration is stored in artifacts/phase2_run.json. Dependencies and exact versions are recorded in pyproject.toml and uv.lock.

## 7 Complete Validation results
{markdown_table(results)}

Precision, Recall, F1, F2 and TP/FP/TN/FN use score >= 0.5. This is the standard benchmark convention, not a chosen production threshold. No exploratory threshold was selected. Accuracy is omitted because it is poorly informative under extreme imbalance. Weighted-model scores are not calibrated prevalence estimates. ROC-AUC is secondary to Average Precision.

## 8 Operational ranking
Precision@Top-K is the fraction of reviewed transactions that are fraudulent. Recall@Top-K (Fraud Capture Rate) is the fraction of all Validation frauds present in the reviewed set. If reviewers can examine only X% of transactions, recall quantifies the share of fraud captured.

Top 0.1%, 0.5%, 1% use ceil(N * fraction) observations. Ranking ties use stable original row order. Dummy scores are constant: its Top-K statistics reflect incidental input order and have no risk ranking interpretation. Metrics are batch-level retrospective rankings rather than a demonstrated online review policy. No threshold or model was chosen using these values.

## 9 Timing and figures
Total preparation, model fitting, prediction, evaluation and figures: {info['total_seconds']:.1f} seconds ({info['total_seconds']/60:.2f} minutes). Individual fit/prediction durations are in the table. Preparation: {info['preparation_seconds']:.1f} seconds. Times depend on hardware and resource contention.

Figures in reports/figures/: {', '.join(figures)}. Curves display up to 5,000 sampled curve points for compact plotting; all observations contribute to metrics. Temporal profile and AP comparison use complete aggregate data. Confusion matrices display exact counts.

## 10 Tests and reproducibility
Executed complete existing and new synthetic suite, without loading the large CSV in pytest:

```
{test.stdout.strip()}
```

Tests cover schema, sign conventions, tolerance, zero denominator, finite features, unknown type, no label/post-event/ID leakage, row-local transformations, cutoff count guard, boundary masks, Production exclusion, training step guard, ranking rounding/ties, confusion counts and F2. README.md documents uv sync --locked, pytest, preparation-only, full baseline and report regeneration commands in PowerShell. notebooks/02_ml_training.ipynb loads saved artifacts without duplicating the implementation.

## 11 Files and dependencies
Principal additions: src/fraud_detection/features.py, splitting.py, metrics.py, modeling.py; scripts/run_baselines.py, build_phase2_report.py, execute_phase2_notebook.py; tests/test_modeling.py; docs/feature_catalog.md; notebooks/02_ml_training.ipynb; PHASE_2_MODELING_REPORT.md; small CSV/JSON artifacts and figures. README.md, pyproject.toml, uv.lock and .gitignore were updated. Raw dataset and Phase 1 audit were preserved. Large feature matrices stay ignored; no giant models saved.

Declared project configuration:
```toml
{deps.strip()}
```

Git review at report generation (preexisting PDF is not part of this phase):
```
{changed.strip()}
```

## 12 Limitations and problems
Near-perfect results can reflect deterministic simulation relationships, particularly amount approximately matching previous balance; they do not establish real-world generalization. Origin/destination prior balances and identifier prefixes are assumed available before execution and need domain confirmation. The step trend may not extrapolate. A single temporal holdout cannot establish stability across many time periods. The Development temporal profile also contains steps with 100% fraud prevalence and very low transaction counts, while busy steps have much lower prevalence; this simulation schedule can make step an unusually informative predictor. Class-weighted scores require later calibration consideration. Validation has 868 positive cases; metrics have sampling uncertainty. Float32 storage can round large amounts. The tolerance is a fixed engineering convention, not tuned.

Windows sandbox process startup failed; authorized local commands used execution outside that failing sandbox. Git reported different directory ownership; safe.directory was scoped to individual commands without changing global configuration. Dependencies installed successfully with uv. No material computational blocker remained. No formal drift analysis, monitoring, SHAP, experiment platform, advanced tuning or final Production evaluation was undertaken.

## 13 Next phase recommendation and approvals
Consider leading benchmarks as candidates only, guided primarily by Validation Average Precision and operational ranking, while reviewing false positives and simulation-specific feature shortcuts. Confirm pre-execution availability of prior destination/origin balances and prefix semantics before operational use. Approve the next academic phase separately; this implementation stops here. No additional approval is needed for the completed Phase 2 under the authorized document instructions. Do not declare a champion or production threshold based on this report.

PHASE 2: COMPLETE
'''
    (ROOT/'PHASE_2_MODELING_REPORT.md').write_text(report,encoding='utf-8')
    def md(text): return dict(cell_type='markdown',metadata={},source=text.splitlines(keepends=True))
    def code(text): return dict(cell_type='code',metadata={},execution_count=None,outputs=[],source=text.splitlines(keepends=True))
    cells = [md('# Phase 2 Temporal Baseline Modeling\n\nReproducible analysis of Development only. Production is reserved. Read PHASE_2_MODELING_REPORT.md for completed execution details.'),
      code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT = Path.cwd()\nif ROOT.name == 'notebooks': ROOT = ROOT.parent\nassert (ROOT / 'pyproject.toml').exists()\nrun = json.loads((ROOT / 'artifacts/phase2_run.json').read_text())\ncomparison = pd.read_csv(ROOT / 'artifacts/baseline_model_comparison.csv')\n"),
      md('## Temporal strategy\n\nFirst 80% of fixed Development steps, verified for at least 100 frauds in each segment. Cutoff is not optimized by predictive results. Validation remains untouched.'),
      code("display(pd.DataFrame(run['split']).T)\nprofile = pd.read_csv(ROOT / 'artifacts/development_temporal_profile.csv')\ndisplay(profile)\ndisplay(Image(filename=str(ROOT / 'reports/figures/development_temporal.png')))"),
      md('## Feature availability and leakage\n\nPrincipal scoring occurs before execution. Post-event balances/residuals, raw IDs, business rule and label are excluded. Ratio uses an explicit zero sentinel and indicator. Emptying tolerance is absolute 0.01. No target encoding or future aggregates.'),
      code("display(run['features'])\ndisplay(Markdown((ROOT / 'docs/feature_catalog.md').read_text(encoding='utf-8-sig')))\ndisplay(run['business_rule'])"),
      md('## Fixed baselines\n\nDummy, scaled weighted logistic regression, weighted Random Forest, XGBoost and LightGBM. Full Train for all; no optimization or resampling. Configurations are recorded by the training script.'),
      code("display(run['configurations'])\ndisplay(comparison)"),
      md('## Validation comparison\n\nAverage Precision is the primary metric; ROC-AUC is secondary. Threshold 0.5 is a benchmark convention, not a production decision. Very high scores in a simulator warrant domain review.'),
      code("display(comparison[['model','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05']])\nfor figure in ['average_precision_comparison.png','precision_recall.png','roc.png']:\n    display(Image(filename=str(ROOT / 'reports/figures' / figure)))"),
      md('## Operational review capacity\n\nRecall@Top-K measures the share of Validation frauds captured if only the top X% can be reviewed. Precision measures yield among reviewed transactions. Stable row-order ties make Dummy ranking incidental.'),
      code("display(comparison[['model'] + [c for c in comparison.columns if 'top_' in c or c.startswith('k_')]])\nfor name in comparison.model:\n    display(Image(filename=str(ROOT / 'reports/figures' / f'confusion_{name}.png')))"),
      md('## Reproduce and stop at Phase 2\n\nRun `uv sync --locked`, `uv run python -m pytest -q`, `uv run python scripts/run_baselines.py`, then `uv run python scripts/build_phase2_report.py` from the repository root. For datasets only add `--prepare-only` to run_baselines.py. No champion, tuning, monitoring or Production evaluation is part of this notebook.')]
    # Save a completed presentation with artifact-derived output, without requiring a notebook execution dependency.
    summary = markdown_table(results[['model','pr_auc','roc_auc']])
    cells.insert(1,md('## Completed run summary\n\n'+summary+f"\n\nTrain: {train['rows']:,} rows, {train['frauds']:,} frauds. Validation: {valid['rows']:,} rows, {valid['frauds']:,} frauds. Runtime {info['total_seconds']/60:.2f} minutes."))
    notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python')),nbformat=4,nbformat_minor=5)
    for i, cell in enumerate(cells): cell['id'] = f'phase2-{i:02d}'
    (ROOT/'notebooks/02_ml_training.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT/'scripts/execute_phase2_notebook.py')], cwd=ROOT, check=True)
    print(test.stdout.strip()); print('PHASE 2: COMPLETE')

if __name__=='__main__': main()



