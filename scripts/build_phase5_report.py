"""Build offline phase report and executed notebook from frozen-monitoring evidence."""
import os
os.environ.setdefault('DO_NOT_TRACK','1');os.environ.setdefault('MLFLOW_DISABLE_TELEMETRY','true')
import base64,contextlib,io,json,subprocess,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import fisher_exact
from IPython.display import Image,Markdown
import mlflow
from mlflow.tracking import MlflowClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fraud_detection.monitoring import sha256,verify_frozen,wilson_interval

def table(df):
    lines=['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    for row in df.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(('undefined' if pd.isna(v) else f'{v:.8f}') if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(lines)

def main():
    r=json.loads((ROOT/'artifacts/monitoring_summary.json').read_text(encoding='utf-8'))
    frozen=json.loads((ROOT/'artifacts/production_monitoring_freeze.json').read_text(encoding='utf-8'))
    if r['status']!='COMPLETE' or not r['mlflow']['historical_runs_unchanged']:raise ValueError('Incomplete monitoring')
    verify_frozen(Path(frozen['model_path']),frozen['model_sha256'])
    for relative,digest in frozen['previous_phase_hashes'].items():
        if sha256(ROOT/relative)!=digest:raise ValueError('Previous phase changed')
    tests=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True,timeout=180)
    if tests.returncode:raise RuntimeError(tests.stdout+tests.stderr)
    comparison=pd.read_csv(ROOT/'artifacts/production_model_comparison.csv')
    drift=pd.read_csv(ROOT/'artifacts/data_drift_features.csv')
    conditioned=pd.read_csv(ROOT/'artifacts/type_conditioned_drift.csv')
    windows=pd.read_csv(ROOT/'artifacts/monitoring_windows.csv')
    bytype=pd.read_csv(ROOT/'artifacts/monitoring_by_type.csv')
    scores=pd.read_csv(ROOT/'artifacts/monitoring_scores.csv')
    relations=pd.read_csv(ROOT/'artifacts/monitoring_relation_checks.csv')
    atypical=pd.read_csv(ROOT/'artifacts/monitoring_atypical_cases.csv')
    prod=r['production']['metrics'];val=r['validation']
    intervals=[]
    for period,metrics in [('Validation',val),('Production',prod)]:
        a,b=wilson_interval(metrics['tp'],metrics['tp']+metrics['fn'])
        c,d=wilson_interval(metrics['fp'],metrics['fp']+metrics['tn'])
        intervals.append(dict(period=period,recall=metrics['recall_05'],recall_ci_low=a,recall_ci_high=b,fpr_ci_low=c,fpr_ci_high=d))
    fisher=fisher_exact([[prod['fn'],prod['tp']],[val['fn'],val['tp']]],alternative='two-sided')
    fisher_p=float(fisher.pvalue)
    errors=atypical.loc[(atypical.period=='Production')&(atypical.category=='false_negative'),['period_row_index','step','amount','oldbalanceOrg','amount_to_oldbalanceOrg','oldbalanceDest','score']]
    metrics_cols=['period','observations','frauds','prevalence','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','tp','fp','tn','fn']
    top_cols=['period']+[name for name in comparison.columns if name.startswith(('k_','recall_top_','precision_top_'))]
    git=['git','-c',f'safe.directory={ROOT.as_posix()}']
    branch=subprocess.check_output(git+['branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='development':raise ValueError('Wrong branch')
    tracked=subprocess.check_output(git+['ls-files'],cwd=ROOT,text=True).splitlines()
    forbidden=[p for p in tracked if (p.startswith(('mlruns/','mlartifacts/','optuna_studies/','data/processed/')) and not p.endswith('.gitkeep')) or p.startswith('.env') or p=='PS_20174392719_1491204439457_log.csv']
    if forbidden:raise ValueError('Forbidden tracked files '+str(forbidden))
    report=f'''# Phase 5 Production Evaluation and Monitoring Report

## 1 Executive summary
Frozen XGBoost tuned evaluated out of time on {r['production']['rows']:,} Production transactions and {r['production']['frauds']:,} frauds. AP {prod['pr_auc']:.9f}, ROC-AUC {prod['roc_auc']:.9f}, precision {prod['precision_05']:.6f}, recall {prod['recall_05']:.6f}, F2 {prod['f2_05']:.6f}. TP {prod['tp']}, FP {prod['fp']}, TN {prod['tn']}, FN {prod['fn']}. No model, features, calibration, threshold or champion selection changed after viewing Production.

There are {r['statistical_shift_features']} statistically shifted non-time features, but {r['drift_features']} pass both statistical and predeclared practical alert criteria. This is not evidence that all changes are operationally irrelevant: rare fraud-linked features and alert burden increased substantially. Prediction distribution changes and a modest observed recall decline are reported separately from concept drift. **Concept drift not conclusively established.**

## 2 Received state frozen identity and verification
Reviewed all four previous phase reports, feature catalog, Phase 3 identity/configuration, native models, existing modules/scripts/tests/notebooks, pyproject and Git before modifications. Existing uncommitted work preserved on development. No prior training or optimization was repeated.

Before first Production access, scripts/freeze_monitoring_model.py loaded the exact native XGBoost and reproduced every saved Validation metric to tolerance 1e-10. Freeze records model SHA256 `{frozen['model_sha256']}`, source run `{frozen['source_run_id']}`, fourteen ordered MODEL_COLUMNS, features.py hash, recorded training parameters and native inference configuration. Best_iteration+1={frozen['effective_iterations']}; the original saved artifact still contains 44 rounds but inference uses only the 24 effective rounds. No retraining or parameter-setting call occurs. Native serialization need not retain training constructor defaults; hash and reproduced metrics authenticate the learned artifact and its source-run parameter metadata.

Training parameters:
```json
{json.dumps(frozen['recorded_training_parameters'],indent=2)}
```

Freeze also fixes reference threshold 0.5, Top-K capacities 0.1%, 0.5%, 1%, 72-hour windows anchored at step 401, support warning threshold 30 positives, drift rules and reference-only histogram boundaries. Freeze artifact SHA256 `{r['freeze_sha256']}`. Model hash and earlier phase fingerprints rechecked after evaluation. Production is used only for retrospective evaluation and monitoring, never selection, tuning, calibration, early stopping or changes to the model.

## 3 Temporal definitions size and prevalence
step is treated as a simulation hour for this academic analysis, not mapped to a real calendar. Reference/Development: steps 1–400, {r['reference']['rows']:,} rows, {r['reference']['frauds']:,} frauds, prevalence {100*r['reference']['prevalence']:.6f}%. Validation: steps 321–400. Actual Production range: {r['production']['step_min']}–{r['production']['step_max']}, not the proposed upper bound 744. Production prevalence {100*prod['prevalence']:.6f}%, approximately {prod['prevalence']/r['reference']['prevalence']:.3f} times Reference.

Only one chunked raw CSV scan selects Production. Reference uses existing development matrices; principal feature engineering is reused without fitting or altering it. No duplicate raw CSV, full-score export or giant new matrices are saved. Validation is a development holdout previously reused for tuning; Production is the first out-of-time evaluation after model freeze, not an optimization set. Target labels simulate retrospective availability and may arrive later in a real system.

## 4 Validation vs Production and operational ranking
{table(comparison[metrics_cols])}

AP is non-interpolated sklearn Average Precision. It depends on class prevalence and the distribution of score ranks; comparisons across differing prevalence require caution. ROC-AUC is secondary; near-one ROC values must not hide actual error counts. Precision/Recall/F1/F2 use the fixed reference threshold 0.5, not a final production threshold. Natural prevalence is preserved.

{table(comparison[top_cols])}

Top0.1% in Production reviews 576 observations while there are 3,736 frauds. Its maximum possible recall at that capacity is {100*r['top_k_capacity_limits']['0.001']:.6f}%, and the frozen model reaches that bound with precision 1.0. The drop from Validation Top0.1% recall 100% to Production {100*prod['recall_top_0.1pct']:.6f}% is therefore a capacity/prevalence effect rather than evidence of poor top-risk ranking. Top0.5% also saturates its bound, while Top1% captures all frauds. Stable original row order breaks score ties as in prior phases. Ranking is global retrospective review capacity, not a deployed streaming review policy.

## 5 Data and covariate drift
Primary full-data comparison: Reference <=400 vs Production >=401. Continuous variables use two-sample asymptotic KS, binary indicators use chi-square and total variation. Holm adjustment applies to thirteen non-time features. A primary alert requires adjusted p<0.05 **and** KS D>=0.10 for numeric features or TV>=0.05 for binary features. PSI uses reference-only decile boundaries, deduplicated for zero-inflated distributions and Jeffreys pseudocount 0.5 per bin; PSI>=0.20 is a separate review flag. These thresholds are documented engineering conventions, not universal statistical laws or cost-validated fraud limits.

{table(drift)}

step has KS D=1 because the time periods are disjoint; it is displayed as structural separation and excluded from alert counts. type_UNKNOWN is constant, with no distribution shift. P-values shown as zero can reflect numerical underflow at very large support, not literally zero probability. The largest non-time distances are modest under these fixed rules. In particular the rare orig_balance_emptied feature changes by roughly half a percentage point, potentially important for fraud workload despite falling below a generic 5-percentage-point TV threshold. Do not interpret zero primary alerts as no covariate shift or no operational concern. Temporal dependence of simulated transactions limits iid significance interpretations; effect sizes and domain context are essential.

## 6 Transaction mixture and within-type changes
Overall transaction-type TV distance {r['type_composition']['total_variation']:.6f}. Type composition changes can drive shifts in amount, balance and scores without a changed mechanism within a transaction type. The following within-type distances provide contextual diagnostics, not another set of unadjusted alert claims:

{table(conditioned)}

## 7 Prediction and output distribution monitoring
{table(scores)}

Frozen score KS: Reference vs Production D={r['score_shift']['reference_KS_D']:.6f}, p={r['score_shift']['reference_p']:.6g}; Validation vs Production D={r['score_shift']['validation_KS_D']:.6f}, p={r['score_shift']['validation_p']:.6g}. Means and upper-tail percentiles rise, while medians remain similar. Validation alert rate {100*val['alert_rate']:.6f}% vs Production {100*prod['alert_rate']:.6f}%, approximately {prod['alert_rate']/val['alert_rate']:.3f} times. A higher alert burden is operationally meaningful even when broad distribution distances are small. Scores are outputs of the weighted frozen model, not calibrated fraud probabilities. Prediction drift is not automatically concept drift or model deterioration. The learned model artifact itself did not drift or change.

## 8 Performance monitoring and evidence
Observed recall decreases by {100*(val['recall_05']-prod['recall_05']):.6f} percentage points, from one FN among 868 frauds to thirteen FN among 3,736. Precision remains 1.0 with no FP; F2 decreases modestly. These are observed performance differences, not a claim of established stochastic degradation.

Descriptive 95% Wilson intervals:
{table(pd.DataFrame(intervals))}

A two-sided Fisher comparison of FN vs TP between periods gives p={fisher_p:.6f}. This simple labeled comparison is descriptive, assumes exchangeable/independent observations and does not control for feature mixture or temporal clustering. It is not proof of unchanged performance when non-significant, nor proof of concept drift. AP lacks an independent confidence interval here; do not fabricate statistical superiority or equivalence from its small change. Larger business costs of missed fraud may matter despite small aggregate metric changes.

## 9 Prevalence shift and concept drift
A descriptive increase in P(Y) is established in these simulated periods. A changed P(Y) does not by itself establish changed P(Y|X), and classical pure label shift would additionally require stable P(X|Y), which is not established here. Covariate and prediction shifts are evaluated separately. Coarse feature-target relation checks:

{table(relations[['period','rule','observations','frauds','prevalence','pr_auc','precision_05','recall_05','fn','support_warning']])}

Changes in P(Y|a coarse rule) do not establish changes conditional on the full feature vector: within-group covariate composition can change, and performance was selected on Development. Formal conditional change testing or an independent design is not supplied. **Concept drift not conclusively established.** Do not use ambiguous model drift terminology; this report explicitly describes outputs, metric differences and immutable artifact identity.

## 10 Fixed temporal windows and evolution
Windows are 72 simulation hours anchored at 401, chosen before Production. Final window is shortened at real max step 743. No window boundary was selected for favorable results. Support and undefined metrics are preserved; AP/recall are undefined with no positives, ROC-AUC with a single class, and precision with no alerts. Few positives (<30) produce explicit warnings; all-positive windows have trivial AP and a warning. No empty/artificial balanced windows are invented.

{table(windows[['window','step_min','step_max','observations','frauds','prevalence','pr_auc','roc_auc','precision_05','recall_05','f2_05','fp','fn','support_warning']])}

Fraud prevalence increases across these windows while total transaction volume varies; use rates alongside counts. production_step_profile.csv includes all observed steps, counts, frauds, alerts, FN and mean scores. No calendar interpretation beyond the simulation-hour assumption is inferred.

## 11 Performance by type
{table(bytype[['period','type','observations','frauds','pr_auc','roc_auc','precision_05','recall_05','f2_05','fp','fn','support_warning']])}

Categories with no fraud cannot support fraud AP/recall or ROC separation; their undefined cells are deliberate rather than fabricated zero performance. No type-specific model or threshold is selected.

## 12 Atypical transactions and errors
Production contains {r['atypical']['fraud_amount_zero']} amount-zero frauds; detected {r['atypical']['amount_zero_detected']} at fixed threshold. Twelve of the thirteen FN have amount=0 and oldbalanceOrg=0, resembling the Validation FN (score 0.057349). Some Production zero-amount cases score 0.499480, just below 0.5. They remain FN: no rounding, threshold adjustment or calibration is applied. The remaining FN has amount about 399,045, prior balance about 10,399,045, ratio about 0.03837 and score about 0.004741, outside the dominant emptying pattern.

{table(errors)}

There are {r['atypical']['outside_rule_frauds']} Production frauds without orig_balance_emptied, and {r['atypical']['outside_rule_detected']} are detected at 0.5. The fraction is {100*r['atypical']['outside_rule_frauds']/prod['frauds']:.6f}%, versus 1.843318% in Validation. Full case rows and ten highest-scored legitimate transactions per period are saved in monitoring_atypical_cases.csv. Maximum legitimate Production score is {r['atypical']['maximum_legitimate_score']:.9f}; none crosses 0.5. Observed patterns may be simulator-specific; labels and zero amounts are documented, not automatically corrected or used to revise the model.

## 13 HTML and Evidently integration
Evidently {r['evidently']['version']} status {r['evidently']['status']}. Reproducible uniform samples of 25,000 Reference and 25,000 Production rows, seed 42, explicit numerical/categorical mappings, PSI method and 0.2 threshold. Step excluded from this supplementary drift preset. Samples conserve random natural prevalence and are not balanced. Evidently decisions use a distinct sample/PSI design and must not be conflated with the full-data KS/TV decision table above. The primary full-data custom HTML reports preserve all computed metrics and support.

Files in reports/monitoring/: data_drift.html, prediction_drift.html, performance_monitoring.html, evidently_data_drift.html, evidently_prediction_drift.html. All open locally as HTML; no project server, dashboard, application, cloud or deployment is created. Custom files have no external assets. Evidently embeds its report payload/assets locally; opening files rather than uploading the dataset provides academic evidence. Output sizes are checked before MLflow upload. If future Evidently APIs fail, the adapter records the exception and the full-data standalone HTML is a reproducible documented fallback.

## 14 MLflow identity and artifacts
One new Production Monitoring run `{r['mlflow']['run_id']}`, status {r['mlflow']['run_status']}, local experiment {r['mlflow']['experiment_id']}, URI `{r['mlflow']['tracking_uri']}`. Model identity, window configuration, Production metrics, comparisons, drift tables, case subsets, small HTML and plots logged. Historical Phase 3 and Phase 4 run metadata fingerprinted and unchanged. No full dataset, credentials or full score arrays uploaded; no DagsHub remote integration.

## 15 Tests execution and files
Full synthetic suite:
```
{tests.stdout.strip()}
```
Tests cover boundary 400/401, frozen hash rejection, support without/few positives, single-class windows, drift identity/change/categories, Holm adjustment, binning, reference window anchor, unknown types, chunked Production selection, HTML escaping/undefined metrics, and descriptive intervals. Pytest never reads the 500 MB raw dataset. Tests use tiny synthetic arrays and CSVs; no large model training.

Monitoring computation and logging: {r['total_seconds']:.2f} seconds; Production inference {r['production_inference_seconds']:.6f} seconds; reference inference {r['reference']['inference_seconds']:.6f} seconds. Timings exclude installation, code authoring, tests and report regeneration. No repeated training or tuning.

New modules/scripts: src/fraud_detection/monitoring.py, scripts/freeze_monitoring_model.py, scripts/run_monitoring.py, scripts/build_phase5_report.py, tests/test_monitoring.py. Artifacts: production_monitoring_freeze.json, monitoring_summary.json, production_model_comparison.csv, data_drift_features.csv, type_conditioned_drift.csv, monitoring_windows.csv, monitoring_by_type.csv, monitoring_scores.csv, monitoring_relation_checks.csv, monitoring_atypical_cases.csv, production_step_profile.csv; small figures under reports/figures/monitoring; five HTML reports; notebooks/05_monitoring.ipynb. README, pyproject.toml, uv.lock and .gitignore updated minimally. Evidently and SciPy are direct dependencies; existing pipelines and model untouched.

## 16 Git limitations and next phase
Branch {branch}. Tracked-path audit found no raw dataset, .env, MLflow store, Optuna DB or large processed artifacts. No real secrets introduced. Previous phase hashes and model hash remain valid; no commit, push, new remote, PR, merge, tag or release. Existing uncommitted work preserved.

Limits: simulator rules dominate, temporal dependence weakens iid tests, generic practical thresholds are not fraud-cost thresholds, sample PSI differs from full-data tests, AP changes with prevalence, Validation was selected against, labels are assumed retrospectively available, this is one out-of-time period, conditional concept drift is not conclusively assessed, and zero-amount semantics warrant domain review. No model change follows from Production analysis.

For an explicitly authorized Phase 6 dashboard, present frozen-model identity, time ranges, support warnings, thresholds, full-data vs sample methods, alert volume, review-capacity ceilings, FP/FN cases, and prevalence alongside scores. Avoid equating p-value significance with business impact or score changes with concept drift. Do not start Phase 6 automatically.

## Reproduction
```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
$env:DO_NOT_TRACK = '1'
$env:MLFLOW_DISABLE_TELEMETRY = 'true'
uv sync --locked
uv run python scripts/freeze_monitoring_model.py
uv run python scripts/run_monitoring.py
uv run python scripts/build_phase5_report.py
uv run python -m pytest -q
```
Freeze uses only Development and Validation. The monitoring script reads Production only after verifying that freeze. Regenerating this report/notebook reads small artifacts and does not repeat Production evaluation or create a new MLflow run.

[Installed Evidently Report/Snapshot API](https://evidentlyai.github.io/evidently/api-reference/main/evidently/core/report.html), [Evidently DataDriftPreset API](https://evidentlyai.github.io/evidently/api-reference/main/evidently/presets.html).

PHASE 5: COMPLETE
'''
    (ROOT/'PHASE_5_MONITORING_REPORT.md').write_text(report,encoding='utf-8')
    def md(text):return dict(cell_type='markdown',metadata={},source=text.splitlines(keepends=True))
    def code(text):return dict(cell_type='code',metadata={},source=text.splitlines(keepends=True),execution_count=None,outputs=[])
    cells=[md('# Phase 5 Out-of-time evaluation and monitoring\n\nFrozen XGBoost, natural Production prevalence, no retraining or selection. Distinguish covariate, output, label and performance changes from concept drift.'),
        code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd()\nif ROOT.name=='notebooks': ROOT=ROOT.parent\nr=json.loads((ROOT/'artifacts/monitoring_summary.json').read_text(encoding='utf-8'))\nfreeze=json.loads((ROOT/'artifacts/production_monitoring_freeze.json').read_text(encoding='utf-8'))\ndisplay({k:freeze[k] for k in ['model_sha256','effective_iterations','threshold','top_fractions','window_width_hours']})\ndisplay(r['production'])"),
        md('## Out-of-time comparison\n\nAP is prevalence-sensitive. Top0.1% capacity cannot capture more frauds than reviewed rows. Production is not an optimization set.'),
        code("display(pd.read_csv(ROOT/'artifacts/production_model_comparison.csv'))\ndisplay(r['top_k_capacity_limits'])"),
        md('## Covariate drift\n\nSeparate statistical significance from practical magnitude. Step is structurally disjoint and excluded from counts. Within-type comparisons address mixture confounding. Rare-feature changes may remain operationally important below generic alert thresholds.'),
        code("display(pd.read_csv(ROOT/'artifacts/data_drift_features.csv'))\ndisplay(pd.read_csv(ROOT/'artifacts/type_conditioned_drift.csv'))\ndisplay(r['evidently'])"),
        md('## Prediction and performance monitoring\n\nChanged scores do not automatically imply concept drift. Recall point estimate falls modestly; inspect actual missed fraud and support rather than near-one aggregate scores.'),
        code("display(pd.read_csv(ROOT/'artifacts/monitoring_scores.csv'))\ndisplay(pd.read_csv(ROOT/'artifacts/monitoring_windows.csv'))\ndisplay(pd.read_csv(ROOT/'artifacts/monitoring_by_type.csv'))\nfor name in ['score_distributions.png','production_evolution.png']:\n    display(Image(filename=str(ROOT/'reports/figures/monitoring'/name)))"),
        md('## Atypical cases and conditional uncertainty\n\n12 amount-zero frauds are missed at 0.5. Cases at 0.499480 remain errors; Production must not motivate a threshold change. Coarse conditional label shifts do not establish full P(Y|X) change.'),
        code("display(pd.read_csv(ROOT/'artifacts/monitoring_relation_checks.csv'))\ndisplay(pd.read_csv(ROOT/'artifacts/monitoring_atypical_cases.csv'))\ndisplay(r['concept_drift'])\ndisplay(r['mlflow'])"),
        md('## Conclusions and complete report\n\nConcept drift not conclusively established. No new champion, calibration or threshold. Phase 6 requires separate authorization.'),
        code("display(Markdown((ROOT/'PHASE_5_MONITORING_REPORT.md').read_text(encoding='utf-8')))"),
        md('## Offline HTML evidence\n\nOpen reports/monitoring/data_drift.html, prediction_drift.html, performance_monitoring.html and the two evidently_*.html files locally. Evidently uses sampled PSI; the full-data report uses KS/TV/Holm. Heavy logic remains in monitoring.py and run_monitoring.py. No model training or CSV scanning in this notebook.')]
    namespace={};number=0
    for i,cell in enumerate(cells):
        cell['id']=f'phase5-{i:02d}'
        if cell['cell_type']!='code':continue
        number+=1;outputs=[]
        def capture(*values):
            for value in values:
                if isinstance(value,Image):data={'image/png':base64.b64encode(value.data).decode()}
                elif isinstance(value,Markdown):data={'text/markdown':value.data}
                elif isinstance(value,pd.DataFrame):data={'text/html':value.to_html(),'text/plain':value.to_string()}
                else:data={'text/plain':str(value)}
                outputs.append(dict(output_type='display_data',metadata={},data=data))
        namespace['display']=capture
        source=''.join(cell['source']).replace('from IPython.display import display, Image, Markdown','from IPython.display import Image, Markdown')
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):exec(compile(source,f'phase5-cell-{i}','exec'),namespace)
        cell['execution_count']=number;cell['outputs']=outputs
    notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python')),nbformat=4,nbformat_minor=5)
    (ROOT/'notebooks/05_monitoring.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    mlflow.set_tracking_uri('sqlite:///' + (ROOT/'mlruns/mlflow.db').resolve().as_posix());client=MlflowClient()
    for relative in ['PHASE_5_MONITORING_REPORT.md','notebooks/05_monitoring.ipynb','src/fraud_detection/monitoring.py','scripts/run_monitoring.py','scripts/freeze_monitoring_model.py','scripts/build_phase5_report.py','pyproject.toml','uv.lock']:
        client.log_artifact(r['mlflow']['run_id'],str(ROOT/relative),'presentation_and_source')
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_interpretability import history_fingerprints
    if history_fingerprints(client,list(r['mlflow']['historical_hashes']))!=r['mlflow']['historical_hashes']:raise ValueError('Historical runs changed')
    print(tests.stdout.strip());print('Notebook cells',number);print('PHASE 5: COMPLETE')

if __name__=='__main__':main()
