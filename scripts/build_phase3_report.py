"""Generate and execute the Phase 3 academic presentation from real artifacts."""
import base64
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
from IPython.display import Image, Markdown
import mlflow
from mlflow.tracking import MlflowClient
ROOT=Path(__file__).resolve().parents[1]


def table(frame):
    lines=['| '+' | '.join(frame.columns)+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(f'{v:.8f}' if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(lines)


def search_table(space):
    rows=[]
    for algo,parameters in space['algorithms'].items():
        for parameter,(scale,low,high,why) in parameters.items():
            rows.append(dict(algorithm=algo,parameter=parameter,range=f'{low} to {high}',scale=scale,rationale=why))
        rows.append(dict(algorithm=algo,parameter='scale_pos_weight',range='1, 10, 100',scale='categorical',rationale='Controlled native weights, no full inverse-prevalence assumption'))
    return table(pd.DataFrame(rows))


def create_notebook(run,comparison,search):
    def md(text):return dict(cell_type='markdown',metadata={},source=text.splitlines(keepends=True))
    def code(text):return dict(cell_type='code',metadata={},source=text.splitlines(keepends=True),execution_count=None,outputs=[])
    cells=[
        md('# Phase 3 Hyperparameter optimization and MLflow\n\nOptimize XGBoost and LightGBM on Development only. Explain near-perfect simulation results, track finite seeded trials, compare baseline and tuned candidates. Production is reserved.'),
        md('## Completed comparison\n\n'+table(comparison[['model','variant','pr_auc','roc_auc','fp','fn']])),
        code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd()\nif ROOT.name=='notebooks': ROOT=ROOT.parent\nrun=json.loads((ROOT/'artifacts/phase3_run.json').read_text())\ncomparison=pd.read_csv(ROOT/'artifacts/tuned_model_comparison.csv')\ntrials=pd.read_csv(ROOT/'artifacts/optimization_trials.csv')\nsearch=json.loads((ROOT/'artifacts/hyperparameter_search_space.json').read_text())\n"),
        md('## Why Average Precision\n\nValidation has only 868 frauds among 1,398,242 transactions. Accuracy is uninformative. Exact Average Precision is the optimization objective, with ROC-AUC secondary. Threshold 0.5 remains comparative; ranking evaluates scarce review capacity.'),
        md('## Sanity check before tuning\n\nEvery persisted Development feature row was reconstructed from the raw data. No target, flag, post-event balance or raw identifier is a predictor. Mutating prohibited fields preserves features. The fixed approximate-emptying rule explains almost all positives; the implementation audit does not guarantee absence of simulation shortcuts.'),
        code("display(Markdown((ROOT/'docs/perfect_performance_sanity_check.md').read_text(encoding='utf-8-sig')))\nunivariate=pd.read_csv(ROOT/'artifacts/sanity_univariate_features.csv')\ndisplay(univariate.loc[univariate.segment=='validation'].sort_values('pr_auc_high',ascending=False))\ndisplay(pd.read_csv(ROOT/'artifacts/sanity_simple_rules.csv'))"),
        md('## Candidate algorithms\n\nXGBoost and LightGBM offer compact boosting models, fast histogram training and controllable regularization. They also support later tree-explanation workflows, which are outside this phase. Logistic regression is the interpretable reference. Random Forest remains a strong baseline without expensive tuning.'),
        md('## Prespecified search space\n\n'+search_table(search)),
        md('## Optuna protocol\n\nSequential TPESampler seed 42, five startup trials, one enqueued baseline-like configuration, direction maximize, exact Validation AP. Maximum 20 trials; minimum 10 before the fixed saturation criterion (AP >=0.9999, last-five improvement <=0.00001) can stop. No Optuna pruning; estimator early stopping uses Validation only, patience 20. XGBoost aucpr differs from exact AP; LightGBM monitors average_precision. LightGBM retains the numerical leaf-step guard and enables bagging frequency 1.'),
        code("display(run['algorithms'])\ndisplay(trials[['algorithm','trial','pr_auc','fp','fn','effective_iterations','training_seconds','mlflow_run_id']])\ndisplay(Image(filename=str(ROOT/'reports/figures/phase3_optimization_history.png')))"),
        md('## MLflow tracking\n\nLocal SQLite metadata and local artifacts; parent runs per algorithm, child run per trial, saved best-trial runs, Phase 2 baseline references and comparison summary. No dataset or credentials are logged. DagsHub setup is prepared without a remote experiment link.'),
        code("display({k:run[k] for k in ['experiment_name','experiment_id','tracking_uri','mlflow_run_count','all_runs_finished']})\ndisplay(pd.DataFrame(run['runs']))\ndisplay(Markdown((ROOT/'docs/mlflow_dagshub_setup.md').read_text(encoding='utf-8-sig')))"),
        md('## Baseline versus tuned results\n\nScores are development-selection estimates because Validation is reused for tuning and early stopping. Near-equal AP does not establish statistically significant superiority; compare operational errors, latency, effective iterations and trial stability.'),
        code("display(comparison)\nfor algorithm in ['XGBoost','LightGBM']:\n    for kind in ['pr','roc','confusion']:\n        display(Image(filename=str(ROOT/'reports/figures'/f'phase3_{kind}_{algorithm}.png')))"),
        md('## Operational review capacity\n\nRecall@Top0.1% is the share of fraud captured among the highest-scored 1,399 transactions. Precision is reviewed-set fraud yield. Validation prevalence is unchanged. Stable row-order ties follow Phase 2 semantics.'),
        code("display(comparison[['model','variant']+[c for c in comparison.columns if 'top_' in c]])\ndisplay(run['provisional_champion'])"),
        md('## Provisional champion and limitations\n\n'+run['provisional_champion']['reason']+'\n\nThe champion is provisional. No final production threshold, evaluation or deployment. The simulator is nearly deterministic, operational balance availability remains uncertain, and repeated use of one holdout can overfit selection. Trial dispersion is not independent generalization evidence. DagsHub remote prerequisites and external experiment link remain pending.'),
        md('## Reproduce and stop\n\nFrom repository root: `uv sync --locked`; `uv run python scripts/run_sanity_checks.py`; `uv run python scripts/run_optimization.py`; `uv run python scripts/build_phase3_report.py`. Run `uv run python -m pytest -q` for the synthetic suite. Training logic stays in src/fraud_detection/optimization.py and scripts/run_optimization.py. This notebook loads artifacts; it does not retrain models. Do not continue automatically with SHAP, Production or monitoring.')]
    for i,cell in enumerate(cells):cell['id']=f'phase3-{i:02d}'
    notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python')),nbformat=4,nbformat_minor=5)
    namespace={}; number=0
    for i,cell in enumerate(cells):
        if cell['cell_type']!='code':continue
        number+=1; outputs=[]
        def capture(*values):
            for value in values:
                if isinstance(value,Image):data={'image/png':base64.b64encode(value.data).decode()}
                elif isinstance(value,Markdown):data={'text/markdown':value.data}
                elif isinstance(value,pd.DataFrame):data={'text/html':value.to_html(),'text/plain':value.to_string()}
                else:data={'text/plain':str(value)}
                outputs.append(dict(output_type='display_data',metadata={},data=data))
        source=''.join(cell['source']).replace('from IPython.display import display, Image, Markdown','from IPython.display import Image, Markdown')
        namespace['display']=capture
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):exec(compile(source,f'phase3-notebook-{i}','exec'),namespace)
        if stream.getvalue():outputs.append(dict(output_type='stream',name='stdout',text=stream.getvalue()))
        cell['execution_count']=number;cell['outputs']=outputs
    (ROOT/'notebooks/03_hyperparameter_optimization.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    return number


def main():
    run=json.loads((ROOT/'artifacts/phase3_run.json').read_text())
    if run['status']!='COMPLETE' or not run['all_runs_finished']:
        raise ValueError('Completed optimization and finished tracking are required')
    comparison=pd.read_csv(ROOT/'artifacts/tuned_model_comparison.csv')
    trials=pd.read_csv(ROOT/'artifacts/optimization_trials.csv')
    search=json.loads((ROOT/'artifacts/hyperparameter_search_space.json').read_text())
    sanity=json.loads((ROOT/'artifacts/phase3_sanity.json').read_text())
    # Verify prior-phase source/report fingerprints remained unchanged.
    import hashlib
    for relative,digest in sanity['phase2_source_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:
            raise ValueError('Phase 2 source changed during Phase 3')
    tests=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
    if tests.returncode:raise RuntimeError(tests.stdout+tests.stderr)
    git=['git','-c',f'safe.directory={ROOT.as_posix()}']
    branch=subprocess.check_output(git+['branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='development':raise ValueError('Wrong Git branch')
    status=subprocess.check_output(git+['status','--short'],cwd=ROOT,text=True)
    tracked=subprocess.check_output(git+['ls-files'],cwd=ROOT,text=True).splitlines()
    protected_prefixes=('mlruns/','mlartifacts/','optuna_studies/','data/processed/')
    forbidden=[p for p in tracked if p.startswith(protected_prefixes) and not p.endswith('.gitkeep') or p=='.env' or p.startswith('.env.') or p=='PS_20174392719_1491204439457_log.csv']
    if forbidden:raise ValueError('Forbidden data/store files tracked by Git: '+str(forbidden))
    executed=create_notebook(run,comparison,search)
    space_md=search_table(search)
    bests={algo:info['best_parameters'] for algo,info in run['algorithms'].items()}
    trial_stats=trials.groupby('algorithm').agg(trials=('trial','size'),ap_min=('pr_auc','min'),ap_max=('pr_auc','max'),ap_median=('pr_auc','median'),fit_seconds=('training_seconds','sum'))
    cols=['model','variant','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','tp','fp','tn','fn','training_seconds','prediction_seconds','effective_iterations']
    topcols=['model','variant']+[c for c in comparison.columns if c.startswith(('recall_top_','precision_top_','k_'))]
    new_files=['docs/perfect_performance_sanity_check.md','docs/mlflow_dagshub_setup.md','src/fraud_detection/optimization.py','src/fraud_detection/tracking.py','scripts/run_sanity_checks.py','scripts/run_optimization.py','scripts/build_phase3_report.py','tests/test_optimization.py','notebooks/03_hyperparameter_optimization.ipynb','PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md','artifacts/phase3_sanity.json','artifacts/sanity_univariate_features.csv','artifacts/sanity_simple_rules.csv','artifacts/hyperparameter_search_space.json','artifacts/optimization_trials.csv','artifacts/tuned_model_comparison.csv','artifacts/phase3_run.json','reports/figures/phase3_*.png']
    report=f'''# Phase 3 Optimization and MLflow Report

## 1 Executive summary
Sanity checks completed before tuning: all 5,787,030 Development feature/label rows exactly reconstructed from raw Development, no prohibited predictor or implementation leakage detected. Strong simulator shortcuts explain near-perfect separability. XGBoost and LightGBM optimized with finite seeded Optuna searches and local nested MLflow tracking. The selected {run['provisional_champion']['model']} is a PROVISIONAL CHAMPION, not a final production champion. Production remained completely reserved. Validation is now reused for selection and early stopping, so tuned scores are development estimates rather than independent test evidence.

## 2 Received state and scope
Reviewed the Phase 1 audit, Phase 2 report, feature catalog, README, pyproject, src, scripts, tests, baseline comparison, executed Phase 2 notebook and current Git. Branch development throughout. Existing uncommitted Phase 2 work was preserved; no prior phase rerun, no baseline model retraining, no remote, push, merge, tag or release. Fingerprints confirm Phase 2 features.py, modeling.py, run_baselines.py and report remained unchanged. Phase 2 matrices were verified, not rewritten.

Train: steps 1–320, 4,388,788 rows, 3,609 frauds. Validation: steps 321–400, 1,398,242 rows, 868 frauds. No resampling; original Validation prevalence. Production is excluded from sanity checks, optimization, early stopping, class-weight decisions, candidate selection and calibration.

## 3 Sanity check evidence and conclusion
See docs/perfect_performance_sanity_check.md and artifacts/phase3_sanity.json. Exact raw reconstruction, strict nonoverlapping temporal ranges, schema checks and prohibited-column mutation invariance passed. isFraud, isFlaggedFraud, raw IDs, new balances and their derivatives are absent. Fixed row-local features require no fitted preprocessing. Phase 2 logistic scaler fit only on Train.

The fixed rule TRANSFER/CASH_OUT plus requested balance emptying captures 3,533/3,609 Train frauds (97.8942%) and 852/868 Validation frauds (98.1567%), with zero false positives in each segment. The emptied feature has Validation univariate AP approximately 0.981578. Univariate high/low directions for all fourteen columns and seven fixed simple rules are persisted. Development has {sanity['all_fraud_development_steps']} all-fraud low-volume steps containing {sanity['all_fraud_step_transactions']} transactions, indicating a simulation scheduling pattern. No predictors were removed or modified to reduce scores artificially.

A: no implementation evidence of leakage detected. B: near-deterministic simulator relationships present. C: pre-execution balance availability, prefix semantics, generator shortcuts and external generalization remain uncertain. Absence of detected implementation leakage is not proof that simulation label-generation shortcuts are absent.

## 4 Algorithms and optimization rationale
Tune XGBoost and LightGBM: Phase 2 AP is already high, training takes seconds, histogram boosting scales to full Train, and constrained complexity/regularization spaces enable efficient experiments. Compact tree models are suitable for later explanation workflows, including possible SHAP, without implementing explanations here. Logistic regression remains an interpretable baseline and Random Forest a strong benchmark; costly RF search offers little clear value under saturation.

## 5 Objective and search spaces
Direction maximize, objective exact sklearn Average Precision on Validation. Accuracy not optimized or used for selection. Additional ROC-AUC, threshold-0.5 precision/recall/F1/F2/confusion counts, operational Top-K and timing are logged for every trial. No final production threshold selected.

{space_md}

LightGBM num_leaves upper bound is additionally capped at 2**max_depth. Fixed: four workers, random_state 42, XGBoost histogram method, LightGBM deterministic/force_col_wise, max_delta_step 1.0 inherited from the stability correction, subsample_freq 1 to activate bagging. Native scale_pos_weight alternatives are 1, 10, 100; full inverse prevalence is not assumed optimal. There is no artificial class-balanced dataset or balanced Validation.

## 6 Optuna configuration and actual trials
{run['sampler']}; sequential study.optimize n_jobs=1; seed 42; five startup trials; one enqueued baseline-like candidate under the Phase 3 early-stopping protocol. NopPruner; estimator early stopping provides computational control. Upper budget {run['max_trials']} trials per algorithm. At least {run['minimum_trials']} completed trials before the prespecified plateau can stop: best AP >=0.9999 and maximum improvement relative to the best before the last five trials <=0.00001. Fewer trials demonstrate saturation, not global-optimum discovery or statistical equivalence.

{table(trial_stats.reset_index())}

Study completion details:
```json
{json.dumps(run['algorithms'],indent=2)}
```

Persistent Optuna storage: `{run['optuna_storage']}`. Repeated executions create new uniquely named studies; no silent resume. Exact AP ties choose earliest completed trial reproducibly. Selected models were refit using identical Train/Validation protocol and their AP reproduced to tolerance 1e-10. Trial dispersion is hyperparameter sensitivity on one reused holdout, not independent temporal stability. The minimum/median/maximum table deliberately retains poor trials, including any degenerate ranking or threshold behavior. Saturation of the best observed value does not imply that all configurations are stable or that native weighting is always helpful.

## 7 Early stopping
Patience 20, Development Validation only. XGBoost eval_metric aucpr is its native interpolated PR-area metric, which differs from exact Average Precision; the final trial objective always computes exact AP after prediction. LightGBM monitors native average_precision with first_metric_only=True. Selected effective iterations appear in the comparison. No Production early stopping or training on Train+Validation.

## 8 MLflow configuration and experiment evidence
Local metadata URI: `{run['tracking_uri']}`. Artifacts: `mlartifacts/`; experiment `{run['experiment_name']}` id `{run['experiment_id']}`. Execution `{run['execution_id']}` has {run['mlflow_run_count']} FINISHED runs: four imported baseline reference runs, two algorithm parents, {len(trials)} child trials, two best-trial refits/native model runs and one comparison summary. Baseline references log saved Phase 2 evidence and are not newly trained models.

```json
{json.dumps(run['runs'],indent=2)}
```

Each trial logs algorithm, sampled parameters, seed, feature count, Train/Validation step ranges, threshold convention, exact AP, ROC-AUC, P/R/F1/F2, TP/FP/TN/FN, Top0.1%/0.5%/1%, effective iterations and fit/prediction time. Artifacts include metrics and feature list per trial; selected models additionally have native model manifest, PR/ROC curves and confusion matrix. Parents include search summaries, summary run includes comparison, sanity evidence, source, pyproject and lockfile. No dataset, full score arrays, credentials or environment-variable dumps are logged. In-progress/failed fits enter a run before fitting, preserving failure visibility.

## 9 Best parameters
```json
{json.dumps(bests,indent=2)}
```

Best search trial ids and MLflow run ids are included above. Native models are saved locally under ignored data/processed/phase3_models and logged as compact MLflow artifacts. Their ordered features and effective iterations are explicit. Serialization is tested on small synthetic data.

## 10 Baseline versus tuned results
{table(comparison[cols])}

Exact saved values, including best_parameters, are in artifacts/tuned_model_comparison.csv. Imported baseline times were measured during Phase 2; tuned times come from Phase 3 best refits. Protocol differs: Phase 2 baselines had no early stopping while tuned models do. Timing is a single-run observation under local resource conditions and is not a controlled latency benchmark. ROC-AUC values displayed near one do not imply zero errors; inspect FP/FN explicitly.

## 11 Operational Top-K
{table(comparison[topcols])}

Top0.1% = 1,399 transactions; Top0.5% = 6,992; Top1% = 13,983. Recall is fraction of all 868 Validation frauds captured; precision is fraud share of reviewed transactions. This is retrospective ranking at unchanged prevalence, not a demonstrated real-time operational policy. Stable input row order breaks ties, as in Phase 2.

## 12 Timing and saturation analysis
Sanity verification and descriptive analysis: {run['sanity_seconds']:.1f} seconds. Optimization including tracking, best refits and figures: {run['optimization_seconds']:.1f} seconds. Combined compute: {run['total_compute_seconds']:.1f} seconds ({run['total_compute_seconds']/60:.2f} minutes), excluding dependency installation, report construction and human-readable implementation work. Per-trial and per-model timing are recorded separately.

Near-ceiling AP differences do not establish meaningful superiority or statistical significance with 868 positives on one reused holdout. Models in the predeclared practical band of 0.0001 AP are treated as approximately similar for candidate decision-making, not statistically proven equivalent. Compare operational capture, false negatives/positives at the fixed threshold, measured inference time, fitted iterations, training time, complexity and later maintainability. Logistic regression offers interpretability; RF remains a strong reference. Tuning is not presumed to improve every baseline. Some boosting trials achieve high ranking AP while all scores remain below 0.5 and threshold recall is zero; optimizing ranking does not optimize calibration or threshold-specific recall. These results are retained transparently rather than hidden or corrected by selecting a new threshold.

## 13 Provisional champion
{run['provisional_champion']['reason']}

Prespecified selection policy: {run['provisional_champion']['criterion']}. Selection is restricted to tuned candidates for a compact, tracked boosting artifact. The strong RF baseline remains a benchmark and is not declared inferior. Both tuned algorithms support later tree explanation workflows; no SHAP is implemented. Hyperparameter-search saturation and best-trial reproduction offer implementation evidence, not proof of future stability. This provisional decision must be revisited on genuinely independent evidence in a separately authorized phase.

## 14 DagsHub status
Prepared only: docs/mlflow_dagshub_setup.md documents MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD using process environment variables. Remote URI requires explicit --allow-remote-tracking; credential-containing URLs are rejected. No repository or remote experiment created, no token invented, no secrets written, no push. An external academic experiment link is pending real remote access and later authorization; this does not block the independently completed local tracking phase. Local UI instructions use localhost and the actual SQLite store.

## 15 Tests notebook and verification
Full suite:
```
{tests.stdout.strip()}
```

{executed} notebook code cells executed successfully from artifacts; no heavy logic duplicated. Tests use small synthetic arrays and CSVs only, cover valid bounded search spaces, depth/leaves consistency, objective AP/run linkage, deterministic best ties, saturation, metrics, model early stopping and native serialization, local nested MLflow logging and artifacts, exact provenance, and rejection of Production or invalid schema. The initial test cleanup encountered a Windows pooled SQLite lock; disposing the test engine fixed it. MLflow emits a dependency SQLAlchemy noload deprecation warning; it does not prevent logging or pass/fail validation. LightGBM uses its current eval_X/eval_y API.

Phase 2 feature/model/source/report fingerprints verified unchanged. Git tracked-path check found no .env, dataset, processed matrices, MLflow or Optuna stores. Ignore rules exclude large/local artifacts. No real credentials were introduced; remote auth is documented using secure input rather than literals. All MLflow runs for this execution are finished and can be queried locally.

## 16 Files dependencies and Git
New files: {', '.join(new_files)}.
Updated: README.md, pyproject.toml, uv.lock and .gitignore. Added direct dependencies: Optuna and MLflow, with pinned resolution in uv.lock. MLflow brings web-serving libraries transitively; no project web app, service, monitoring or deployment was implemented.

Current branch `{branch}`; existing Phase 2 changes and academic PDF preserved. No commit, push, remote or history modification.
```
{status.strip()}
```

## 17 Limitations pending decisions and next phase
The simulator contains highly discriminating structural rules; metrics cannot be extrapolated to live banking fraud. Operational prior-balance availability and prefix semantics require confirmation. Reused Validation induces selection optimism; no independent final evaluation was performed. Search is intentionally small, does not establish global optimum, and does not justify sixth-decimal superiority. Weighting can affect calibration; no calibration or threshold optimization performed. Single-run timings and trial score dispersion are limited stability evidence. Native best artifacts require exact Phase 2 feature ordering.

Pending: real DagsHub repository/access and link for academic remote evidence, operational feature availability, separate approval for any Phase 4 work. This phase stops without SHAP/LIME, Production evaluation, drift tests, monitoring, dashboard, app, deployment or publishing. A later authorized phase may examine explanations and further validation; do not execute it automatically.

PHASE 3: COMPLETE
'''
    path=ROOT/'PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md';path.write_text(report,encoding='utf-8')
    # Add completed report/notebook evidence to the existing summary run, not a fabricated new run.
    mlflow.set_tracking_uri('sqlite:///' + (ROOT/'mlruns/mlflow.db').resolve().as_posix())
    client=MlflowClient()
    for relative in ('PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md','notebooks/03_hyperparameter_optimization.ipynb','docs/mlflow_dagshub_setup.md'):
        client.log_artifact(run['summary_run_id'],str(ROOT/relative),'presentation')
    print(tests.stdout.strip());print(f'Notebook cells executed: {executed}');print('PHASE 3: COMPLETE')

if __name__=='__main__':main()


