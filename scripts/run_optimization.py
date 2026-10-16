"""Finite Optuna searches on full Train, nested MLflow runs and native best models."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.metadata
import json
import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import optuna
import mlflow
from mlflow.tracking import MlflowClient
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, roc_curve, ConfusionMatrixDisplay
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fraud_detection.optimization import SEARCH_SPACES, WEIGHTS, SEED, make_objective, select_best_trial, saturation_reached, fit_and_evaluate
from fraud_detection.tracking import configure_tracking, log_evaluation
from run_sanity_checks import load_development, file_hash

LOG=logging.getLogger(__name__)


def save_trial_table(records):
    serial=[dict(r,parameters=json.dumps(r['parameters'],sort_keys=True)) for r in records]
    pd.DataFrame(serial).to_csv(ROOT/'artifacts/optimization_trials.csv',index=False)


def save_plots(algorithm,y,scores,figures):
    paths=[]
    precision,recall,_=precision_recall_curve(y,scores)
    # Preserve every recall change and neighboring point to avoid hiding rare fraud transitions.
    changes=np.flatnonzero(np.diff(recall)!=0)
    idx=np.unique(np.r_[0,len(recall)-1,changes,np.minimum(changes+1,len(recall)-1),
                         np.linspace(0,len(recall)-1,min(3000,len(recall))).astype(int)])
    fig,ax=plt.subplots(figsize=(7,5)); ax.step(recall[idx],precision[idx],where='post')
    ax.axhline(y.mean(),color='gray',linestyle='--'); ax.set(xlabel='Recall',ylabel='Precision',title=algorithm+' tuned')
    fig.tight_layout(); path=figures/f'phase3_pr_{algorithm}.png'; fig.savefig(path,dpi=160); plt.close(fig); paths.append(path)
    fpr,tpr,_=roc_curve(y,scores)
    fig,ax=plt.subplots(figsize=(7,5)); ax.plot(fpr,tpr); ax.plot([0,1],[0,1],linestyle='--',color='gray')
    ax.set(xlabel='False positive rate',ylabel='True positive rate',title=algorithm+' tuned')
    fig.tight_layout(); path=figures/f'phase3_roc_{algorithm}.png'; fig.savefig(path,dpi=160); plt.close(fig); paths.append(path)
    fig,ax=plt.subplots(figsize=(5,4)); ConfusionMatrixDisplay.from_predictions(y,scores>=0.5,ax=ax,values_format='d',colorbar=False)
    ax.set_title(algorithm+' tuned threshold 0.5'); fig.tight_layout()
    path=figures/f'phase3_confusion_{algorithm}.png'; fig.savefig(path,dpi=160); plt.close(fig); paths.append(path)
    return paths


def select_provisional(comparison: pd.DataFrame):
    """Prespecified practical AP band, then operational errors, latency and complexity.

    Candidate must preserve full Top0.1% capture and AP within 0.0001 of maximum.
    No statistical-equivalence claim is made with a single reused holdout.
    """
    pool=comparison.loc[comparison.variant=='tuned'].copy()
    best=pool.pr_auc.max()
    near=pool.loc[(pool.pr_auc>=best-0.0001)&(pool['recall_top_0.1pct']>=1.0-1e-12)]
    if near.empty: near=pool.loc[pool.pr_auc>=best-0.0001]
    choice=near.sort_values(['fn','fp','prediction_seconds','effective_iterations','training_seconds','model'],kind='stable').iloc[0]
    return dict(model=choice.model,variant='tuned',status='PROVISIONAL CHAMPION',
                criterion='Tuned candidates within 0.0001 AP of best; full Top0.1% capture preferred; then FN, FP, measured prediction latency, effective iterations, training time and name',
                reason=f"{choice.model} in practical AP band, Top0.1% recall={choice['recall_top_0.1pct']:.6f}; threshold 0.5 FN={int(choice.fn)}, FP={int(choice.fp)}; prediction={choice.prediction_seconds:.3f}s; effective iterations={int(choice.effective_iterations)}. No statistically proven superiority; times are one-run measurements.")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--max-trials',type=int,default=20)
    parser.add_argument('--minimum-trials',type=int,default=10)
    parser.add_argument('--allow-remote-tracking',action='store_true')
    args=parser.parse_args()
    if not 10<=args.minimum_trials<=args.max_trials<=30: parser.error('Require 10 <= minimum <= maximum <=30')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    started=time.perf_counter()
    sanity=json.loads((ROOT/'artifacts/phase3_sanity.json').read_text())
    if not sanity.get('exact_reconstruction') or sanity.get('production_used'):
        raise ValueError('Completed clean sanity check is required before optimization')
    for name,digest in sanity['matrix_sha256'].items():
        if file_hash(ROOT/'data/processed'/name)!=digest: raise ValueError('Matrices changed since sanity check')
    data=load_development()
    uri,experiment_id=configure_tracking(ROOT,allow_remote=args.allow_remote_tracking)
    execution_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    figures=ROOT/'reports/figures'; models=ROOT/'data/processed/phase3_models'; models.mkdir(exist_ok=True)
    storage_dir=ROOT/'optuna_studies'; storage_dir.mkdir(exist_ok=True)
    storage='sqlite:///'+(storage_dir/'phase3.db').resolve().as_posix()
    metadata=dict(execution_id=execution_id,status='RUNNING',experiment_id=experiment_id,
                  experiment_name='fraud-detection-hyperparameter-optimization',tracking_uri=uri,
                  optuna_storage=storage,seed=SEED,max_trials=args.max_trials,minimum_trials=args.minimum_trials,
                  saturation=dict(window=5,floor=0.9999,tolerance=1e-5),production_used=False,
                  sampler='TPESampler(seed=42,n_startup_trials=5,multivariate=False)',
                  direction='maximize',objective='exact Validation average_precision_score',
                  pruning='NopPruner; estimator early stopping only',
                  early_stopping=dict(patience=20,XGBoost_metric='aucpr (interpolated PR area, not exact AP)',
                                      LightGBM_metric='average_precision',validation_steps=[321,400]),
                  versions={p:importlib.metadata.version(p) for p in ('optuna','mlflow','numpy','pandas','scikit-learn','xgboost','lightgbm')},
                  algorithms={},runs=[])
    search=dict(algorithms=SEARCH_SPACES,scale_pos_weight=dict(values=list(WEIGHTS),rationale='Controlled unweighted/moderate weighting; not automatic inverse prevalence'),
                LightGBM_fixed=dict(max_delta_step=1.0,subsample_freq=1),seed=42,
                saturation=metadata['saturation'],minimum_trials=args.minimum_trials,maximum_trials=args.max_trials,
                champion_selection='AP practical tolerance 0.0001 then full top0.1% capture, FN, FP, inference, iterations, fitting time; tuned models only')
    (ROOT/'artifacts/hyperparameter_search_space.json').write_text(json.dumps(search,indent=2),encoding='utf-8')
    (ROOT/'artifacts/phase3_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    phase2=json.loads((ROOT/'artifacts/phase2_run.json').read_text())
    baseline=pd.read_csv(ROOT/'artifacts/baseline_model_comparison.csv')
    baseline=baseline.loc[baseline.model!='Dummy'].copy()
    baseline['variant']='baseline'
    baseline['best_parameters']=baseline.model.map(lambda name:json.dumps(phase2['configurations'][name],sort_keys=True))
    baseline['effective_iterations']=baseline.model.map({'LogisticRegression':np.nan,'RandomForest':40,'XGBoost':100,'LightGBM':100})
    for row in baseline.to_dict('records'):
        with mlflow.start_run(run_name=row['model']+'_baseline_phase2_reference') as run:
            mlflow.set_tag('execution_id',execution_id)
            keys=[k for k in row if k not in ('model','variant','best_parameters') and pd.notna(row[k])]
            log_evaluation({}, {k:row[k] for k in keys}, row['model'],'baseline_reference',origin='Phase2_saved_artifact_not_retrained')
            mlflow.log_dict(phase2['configurations'][row['model']],'phase2_configuration.json')
            mlflow.log_artifact(str(ROOT/'artifacts/baseline_model_comparison.csv'))
            metadata['runs'].append(dict(role='baseline_reference',algorithm=row['model'],run_id=run.info.run_id))
    records=[]; tuned_rows=[]
    for algorithm in ('XGBoost','LightGBM'):
        study_name=execution_id+'_'+algorithm
        study=optuna.create_study(study_name=study_name,storage=storage,direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=SEED,n_startup_trials=5,multivariate=False),pruner=optuna.pruners.NopPruner())
        # First trial is a seeded baseline-like configuration under the phase-3 ES protocol.
        if algorithm=='XGBoost':
            initial=dict(n_estimators=100,max_depth=5,learning_rate=0.1,min_child_weight=1.0,subsample=1.0,
                         colsample_bytree=1.0,reg_alpha=1e-4,reg_lambda=1.0,gamma=0.0,scale_pos_weight=1.0)
        else:
            initial=dict(n_estimators=100,learning_rate=0.1,num_leaves=31,max_depth=5,min_child_samples=20,
                         subsample=1.0,colsample_bytree=1.0,reg_alpha=1e-4,reg_lambda=0.5,scale_pos_weight=1.0)
        study.enqueue_trial(initial)
        with mlflow.start_run(run_name=algorithm+'_optimization') as parent:
            mlflow.set_tags({'execution_id':execution_id,'role':'algorithm_parent','algorithm':algorithm,'production_used':'false'})
            mlflow.log_params(dict(max_trials=args.max_trials,minimum_trials=args.minimum_trials,objective='validation_average_precision',
                                   sampler='TPE',random_state=SEED,train_steps='1-320',validation_steps='321-400',early_stopping_rounds=20))
            mlflow.log_artifact(str(ROOT/'artifacts/hyperparameter_search_space.json'))
            metadata['runs'].append(dict(role='algorithm_parent',algorithm=algorithm,run_id=parent.info.run_id))
            @contextmanager
            def recorder(number,parameters):
                LOG.info('%s trial %s starting',algorithm,number)
                with mlflow.start_run(run_name=f'{algorithm}_trial_{number:02d}',nested=True) as child:
                    mlflow.set_tags({'execution_id':execution_id,'trial_number':str(number),'role':'trial','algorithm':algorithm})
                    mlflow.log_params(parameters)
                    def record(metrics):
                        log_evaluation(parameters,metrics,algorithm,'trial',trial_number=number,early_stopping_rounds=20,
                            early_stopping_metric='aucpr' if algorithm=='XGBoost' else 'average_precision')
                        metadata['runs'].append(dict(role='trial',algorithm=algorithm,trial=number,run_id=child.info.run_id))
                        LOG.info('%s trial %s AP=%.8f FN=%s FP=%s fit=%.1fs iterations=%s',algorithm,number,
                                 metrics['pr_auc'],metrics['fn'],metrics['fp'],metrics['training_seconds'],metrics['effective_iterations'])
                        return child.info.run_id
                    yield record
            objective=make_objective(algorithm,data,recorder,records)
            stop_reason={'reason':'maximum_trials'}
            def callback(current,trial):
                save_trial_table(records)
                completed=[t.value for t in current.trials if t.state==optuna.trial.TrialState.COMPLETE]
                if saturation_reached(completed,minimum_trials=args.minimum_trials):
                    stop_reason['reason']='prespecified_practical_saturation'
                    LOG.info('%s: saturation rule reached after %s trials',algorithm,len(completed))
                    current.stop()
            study.optimize(objective,n_trials=args.max_trials,n_jobs=1,callbacks=[callback],gc_after_trial=True)
            best=select_best_trial(study)
            completed=[t for t in study.trials if t.state==optuna.trial.TrialState.COMPLETE]
            metadata['algorithms'][algorithm]=dict(study_name=study_name,trials=len(completed),best_trial=best.number,
                best_parameters=best.params,best_trial_value=best.value,best_trial_run_id=best.user_attrs['mlflow_run_id'],
                stop_reason=stop_reason['reason'],trial_pr_auc_min=min(t.value for t in completed),
                trial_pr_auc_max=max(t.value for t in completed))
            mlflow.log_metrics(dict(completed_trials=len(completed),best_validation_pr_auc=best.value))
            mlflow.log_dict(metadata['algorithms'][algorithm],'search_summary.json')
            mlflow.log_artifact(str(ROOT/'artifacts/optimization_trials.csv'))
            with mlflow.start_run(run_name=algorithm+'_best_trial',nested=True) as best_run:
                mlflow.set_tag('execution_id',execution_id)
                model,metrics,scores=fit_and_evaluate(algorithm,best.params,data)
                if abs(metrics['pr_auc']-best.value)>1e-10:
                    raise ValueError('Best trial exact AP did not reproduce')
                log_evaluation(best.params,metrics,algorithm,'best_trial_refit',best_trial=best.number,
                               source_trial_run_id=best.user_attrs['mlflow_run_id'])
                metadata['runs'].append(dict(role='best_trial_refit',algorithm=algorithm,run_id=best_run.info.run_id))
                metadata['algorithms'][algorithm]['best_run_id']=best_run.info.run_id
                metadata['algorithms'][algorithm]['refit_matches_best_trial']=True
                native=models/(algorithm+('.ubj' if algorithm=='XGBoost' else '.txt'))
                if algorithm=='XGBoost': model.save_model(native)
                else: model.booster_.save_model(str(native),num_iteration=model.best_iteration_)
                mlflow.log_artifact(str(native),'model')
                mlflow.log_dict({'format':'XGBoost UBJ' if algorithm=='XGBoost' else 'LightGBM native text',
                                 'features':list(data.feature_names),'parameters':best.params,
                                 'effective_iterations':metrics['effective_iterations'],'target':'isFraud'},'model_manifest.json')
                for path in save_plots(algorithm,data.y_validation,scores,figures): mlflow.log_artifact(str(path),'figures')
                tuned_rows.append(dict(model=algorithm,variant='tuned',train_observations=len(data.y_train),
                    validation_observations=len(data.y_validation),best_parameters=json.dumps(best.params,sort_keys=True),**metrics))
                del model,scores
        (ROOT/'artifacts/phase3_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    comparison=pd.concat([baseline,pd.DataFrame(tuned_rows)],ignore_index=True)
    comparison.to_csv(ROOT/'artifacts/tuned_model_comparison.csv',index=False)
    metadata['provisional_champion']=select_provisional(comparison)
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for algorithm in ('XGBoost','LightGBM'):
        table=pd.DataFrame([r for r in records if r['algorithm']==algorithm])
        axes[0].plot(table.trial,table.pr_auc,marker='o',label=algorithm)
        axes[1].plot(table.trial,np.maximum.accumulate(table.pr_auc),marker='o',label=algorithm)
    for ax,title in zip(axes,('Trial AP','Best AP so far')):
        ax.set(xlabel='Trial number',ylabel='Validation Average Precision',title=title); ax.legend()
    fig.tight_layout(); history=figures/'phase3_optimization_history.png'; fig.savefig(history,dpi=160); plt.close(fig)
    metadata['optimization_seconds']=time.perf_counter()-started
    metadata['sanity_seconds']=sanity['seconds']
    metadata['total_compute_seconds']=metadata['optimization_seconds']+sanity['seconds']
    with mlflow.start_run(run_name='phase3_comparison_and_provisional_champion') as summary_run:
        mlflow.set_tags({'execution_id':execution_id,'role':'comparison_summary','champion_status':'provisional','production_used':'false'})
        metadata['summary_run_id']=summary_run.info.run_id
        metadata['runs'].append(dict(role='comparison_summary',run_id=summary_run.info.run_id))
        mlflow.log_dict(metadata['provisional_champion'],'provisional_champion.json')
        mlflow.log_dict(metadata['versions'],'environment_versions.json')
        for relative in ('artifacts/tuned_model_comparison.csv','artifacts/optimization_trials.csv',
                         'artifacts/hyperparameter_search_space.json','artifacts/phase3_sanity.json',
                         'docs/perfect_performance_sanity_check.md','artifacts/sanity_simple_rules.csv',
                         'artifacts/sanity_univariate_features.csv','pyproject.toml','uv.lock'):
            mlflow.log_artifact(str(ROOT/relative))
        for relative in ('src/fraud_detection/features.py','src/fraud_detection/optimization.py','src/fraud_detection/tracking.py','scripts/run_optimization.py'):
            mlflow.log_artifact(str(ROOT/relative),'source')
        mlflow.log_artifact(str(history),'figures')
        mlflow.log_metrics(dict(total_compute_seconds=metadata['total_compute_seconds'],optimization_seconds=metadata['optimization_seconds']))
    metadata['status']='COMPLETE'
    client=MlflowClient()
    runs=client.search_runs([experiment_id],filter_string=f"tags.execution_id = '{execution_id}'",max_results=1000)
    metadata['mlflow_run_count']=len(runs)
    metadata['all_runs_finished']=all(r.info.status=='FINISHED' for r in runs)
    if not metadata['all_runs_finished']: raise ValueError('Some MLflow runs did not finish')
    (ROOT/'artifacts/phase3_run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(comparison[['model','variant','pr_auc','roc_auc','fp','fn']].to_string(index=False))
    LOG.info('Phase3 optimized in %.1fs; runs=%s',metadata['optimization_seconds'],len(runs))

if __name__=='__main__':main()
