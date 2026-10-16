"""Explain the unchanged Phase 3 XGBoost using Validation only; no raw CSV read."""
import hashlib
import importlib.metadata
import json
import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
import mlflow
from mlflow.tracking import MlflowClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fraud_detection.features import MODEL_COLUMNS
from fraud_detection.metrics import evaluate
from fraud_detection.interpretability import (validate_validation,sample_explanations,select_local_cases,load_champion,
    explain_model,global_importance,native_importance,local_contributions,THRESHOLD_LABEL)
from fraud_detection.tracking import configure_tracking
from fraud_detection.paths import champion_path, local_tracking_uri
LOG=logging.getLogger(__name__)


def fingerprint(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):digest.update(block)
    return digest.hexdigest()


def history_fingerprints(client,run_ids):
    return {i:hashlib.sha256(json.dumps(client.get_run(i).to_dictionary(),sort_keys=True).encode()).hexdigest() for i in run_ids}


def top_contributors(explanation,positive=True,count=5):
    values=explanation.values
    ids=np.flatnonzero(values>0 if positive else values<0)
    ids=ids[np.argsort(-values[ids] if positive else values[ids],kind='stable')][:count]
    return [dict(feature=MODEL_COLUMNS[i],value=float(explanation.data[i]),shap_log_odds=float(values[i])) for i in ids]


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    started=time.perf_counter()
    phase3=json.loads((ROOT/'artifacts/phase3_run.json').read_text())
    if phase3['provisional_champion']['model']!='XGBoost' or phase3['status']!='COMPLETE':raise ValueError('Expected completed XGBoost champion')
    model_path=champion_path(ROOT)
    x_path=ROOT/'data/processed/validation_X.npy';y_path=ROOT/'data/processed/validation_y.npy'
    # Deliberately open only Validation matrices; no Train or raw CSV access.
    x=np.load(x_path,mmap_mode='r');y=np.load(y_path)
    validate_validation(x,y)
    model=load_champion(model_path)
    scores=model.predict_proba(x)[:,1]
    metrics=evaluate(y,scores)
    comparison=pd.read_csv(ROOT/'artifacts/tuned_model_comparison.csv')
    expected=comparison.loc[(comparison.model=='XGBoost')&(comparison.variant=='tuned')].iloc[0]
    for name,value in metrics.items():
        if not np.isclose(value,expected[name],atol=1e-10,rtol=0):raise ValueError('Loaded model failed metric reproduction: '+name)
    LOG.info('Unchanged native model reproduces all Validation metrics')
    selected=sample_explanations(x,y,nonfrauds=2000,seed=42)
    sample=x[selected].copy();sample_y=y[selected]
    explanation,additivity=explain_model(model,sample)
    LOG.info('Exact Tree SHAP for %s Validation rows',len(selected))
    importance=global_importance(explanation,sample_y,float(y.mean())).merge(native_importance(model),on='feature')
    importance['shap_sample_rank']=importance.mean_abs_shap.rank(method='min',ascending=False).astype(int)
    importance['shap_population_estimate_rank']=importance.mean_abs_shap_prevalence_weighted.rank(method='min',ascending=False).astype(int)
    importance['native_gain_rank']=importance.native_gain.rank(method='min',ascending=False).astype(int)
    importance.to_csv(ROOT/'artifacts/shap_global_importance.csv',index=False)
    figures=ROOT/'reports/figures/interpretability';figures.mkdir(parents=True,exist_ok=True)
    def save_current(name):
        plt.gcf().savefig(figures/name,dpi=160,bbox_inches='tight');plt.close('all')
    np.random.seed(42)
    shap.plots.beeswarm(explanation,max_display=14,show=False)
    save_current('shap_beeswarm.png')
    shap.plots.bar(explanation,max_display=14,show=False)
    save_current('shap_global_bar.png')
    fig,ax=plt.subplots(figsize=(9,6))
    estimated=importance.sort_values('mean_abs_shap_prevalence_weighted')
    ax.barh(estimated.feature,estimated.mean_abs_shap_prevalence_weighted)
    ax.set(xlabel='Estimated mean |SHAP| (log-odds)',title='Validation prevalence-weighted estimate')
    fig.tight_layout();save_current('shap_prevalence_weighted_bar.png')
    directions=[]
    for j,name in enumerate(MODEL_COLUMNS):
        values=sample[:,j];contributions=explanation.values[:,j]
        correlation=None if len(np.unique(values))<2 or len(np.unique(contributions))<2 else float(spearmanr(values,contributions).statistic)
        for group,mask in (('all_enriched',np.ones(len(sample),dtype=bool)),('fraud',sample_y==1),('nonfraud',sample_y==0)):
            directions.append(dict(feature=name,group=group,rows=int(mask.sum()),mean_signed_shap=float(contributions[mask].mean()),
                                   mean_abs_shap=float(np.abs(contributions[mask]).mean()),spearman_value_vs_shap=correlation))
        if set(np.unique(values)).issubset({0,1}):
            for state in (0,1):
                mask=values==state
                if mask.any():directions.append(dict(feature=name,group=f'value_{state}',rows=int(mask.sum()),
                    mean_signed_shap=float(contributions[mask].mean()),mean_abs_shap=float(np.abs(contributions[mask]).mean()),
                    spearman_value_vs_shap=correlation))
    pd.DataFrame(directions).to_csv(ROOT/'artifacts/shap_feature_directions.csv',index=False)
    top=importance.head(3).feature.tolist()
    for name in top:
        j=MODEL_COLUMNS.index(name)
        color_name='amount_to_oldbalanceOrg' if name=='orig_balance_emptied' else 'orig_balance_emptied'
        color_j=MODEL_COLUMNS.index(color_name)
        fig,ax=plt.subplots(figsize=(7,5))
        plotted=sample[:,j]
        if np.max(plotted)>1000:plotted=np.log1p(plotted);xlabel='log1p('+name+')'
        else:xlabel=name
        sc=ax.scatter(plotted,explanation.values[:,j],c=sample[:,color_j],cmap='coolwarm',s=9,alpha=0.6)
        fig.colorbar(sc,ax=ax,label=color_name);ax.axhline(0,color='gray',linestyle='--')
        ax.set(xlabel=xlabel,ylabel='SHAP contribution (log-odds)',title='Dependence: '+name)
        fig.tight_layout();save_current('dependence_'+name+'.png')
    cases=select_local_cases(x,y,scores)
    local_rows=[];case_summaries={}
    for name,index in cases.items():
        if index is None:
            case_summaries[name]=dict(exists=False,reason='No matching Validation observation at reference threshold 0.5')
            continue
        local,errors=explain_model(model,x[index:index+1].copy())
        one=local[0]
        rows=local_contributions(one,name,index,int(y[index]),float(scores[index]));local_rows.extend(rows)
        positives=top_contributors(one,True);negatives=top_contributors(one,False)
        case_summaries[name]=dict(exists=True,validation_row_index=index,step=int(x[index,0]),
            label=int(y[index]),score=float(scores[index]),prediction_05=int(scores[index]>=0.5),
            distance_to_reference_threshold=float(abs(scores[index]-0.5)),base_log_odds=float(one.base_values),
            features={feature:float(x[index,i]) for i,feature in enumerate(MODEL_COLUMNS)},
            positive_contributors=positives,negative_contributors=negatives,additivity=errors,
            interpretation='Model margin relative to its tree-path reference: positive contributions raise the margin and negative contributions lower it. Contributions are associative model attributions, not causes of fraud.')
        shap.plots.waterfall(one,max_display=10,show=False)
        save_current('waterfall_'+name+'.png')
    pd.DataFrame(local_rows).to_csv(ROOT/'artifacts/local_explanations.csv',index=False)
    emptied_idx=MODEL_COLUMNS.index('orig_balance_emptied')
    outside_ids=np.flatnonzero((y==1)&(x[:,emptied_idx]==0))
    outside_lookup=np.searchsorted(selected,outside_ids)
    if not np.array_equal(selected[outside_lookup],outside_ids):raise ValueError('All non-rule frauds must be sampled')
    outside_values=explanation.values[outside_lookup]
    outside_means=np.abs(outside_values).mean(axis=0) if len(outside_ids) else np.zeros(len(MODEL_COLUMNS))
    outside_rows=[]
    for idx,pos in zip(outside_ids,outside_lookup):
        one=explanation[pos]
        ranked=np.argsort(-np.abs(one.values),kind='stable')[:5]
        outside_rows.append(dict(validation_row_index=int(idx),score=float(scores[idx]),prediction_05=int(scores[idx]>=0.5),
            **{feature:float(x[idx,i]) for i,feature in enumerate(MODEL_COLUMNS)},
            top_abs_shap_features=json.dumps([dict(feature=MODEL_COLUMNS[j],shap_log_odds=float(one.values[j])) for j in ranked]),
            positive_contributors=json.dumps(top_contributors(one,True))))
    pd.DataFrame(outside_rows).to_csv(ROOT/'artifacts/non_rule_fraud_explanations.csv',index=False)
    group_rows=[]
    group_masks={'fraud':sample_y==1,'nonfraud':sample_y==0,'confident_correct':((sample_y==1)&(scores[selected]>=0.9))|((sample_y==0)&(scores[selected]<=0.1)),
                 'non_rule_fraud':(sample_y==1)&(sample[:,emptied_idx]==0),
                 'incorrect_or_mid_score':((scores[selected]>=0.5)!=sample_y)|((scores[selected]>0.1)&(scores[selected]<0.9))}
    for group,mask in group_masks.items():
        if not mask.any():continue
        for j,name in enumerate(MODEL_COLUMNS):
            group_rows.append(dict(group=group,rows=int(mask.sum()),feature=name,mean_abs_shap=float(np.abs(explanation.values[mask,j]).mean()),
                                   mean_signed_shap=float(explanation.values[mask,j].mean())))
    pd.DataFrame(group_rows).to_csv(ROOT/'artifacts/shap_group_comparison.csv',index=False)
    # One small interaction diagnostic, no full Validation interaction matrix.
    interaction_ids=np.sort(np.random.default_rng(42).choice(len(sample),size=min(128,len(sample)),replace=False))
    from xgboost import DMatrix
    interactions=model.get_booster().predict(DMatrix(sample[interaction_ids]),pred_interactions=True,iteration_range=(0,int(model.best_iteration)+1))
    interaction_error=float(np.max(np.abs(interactions[:,:-1,:-1].sum(axis=2)-explanation.values[interaction_ids])))
    if interaction_error>1e-4:raise ValueError('Interaction marginal sums inconsistent')
    pairs=[]
    mean_interactions=np.abs(interactions[:,:-1,:-1]).mean(axis=0)
    for i in range(len(MODEL_COLUMNS)):
        for j in range(i+1,len(MODEL_COLUMNS)):
            pairs.append(dict(feature_a=MODEL_COLUMNS[i],feature_b=MODEL_COLUMNS[j],mean_abs_pair_component=float(mean_interactions[i,j])))
    pairs=sorted(pairs,key=lambda p:-p['mean_abs_pair_component'])[:5]
    phi_empty=explanation.values[:,emptied_idx]
    state_summary={}
    for state in (0,1):
        mask=sample[:,emptied_idx]==state
        state_summary[str(state)]=dict(rows=int(mask.sum()),mean_shap=float(phi_empty[mask].mean()),
                median_shap=float(np.median(phi_empty[mask])),mean_score=float(scores[selected][mask].mean()))
    outside_order=np.argsort(-outside_means,kind='stable')[:5]
    outside=dict(rows=len(outside_ids),fraud_fraction=float(len(outside_ids)/y.sum()),detected=int((scores[outside_ids]>=0.5).sum()),
        detection_rate=float((scores[outside_ids]>=0.5).mean()) if len(outside_ids) else None,
        score_min=float(scores[outside_ids].min()) if len(outside_ids) else None,
        score_max=float(scores[outside_ids].max()) if len(outside_ids) else None,
        top_features=[dict(feature=MODEL_COLUMNS[i],mean_abs_shap=float(outside_means[i])) for i in outside_order],
        correctly_detected_score_summary=[float(v) for v in scores[outside_ids][scores[outside_ids]>=0.5]],
        rows_artifact='artifacts/non_rule_fraud_explanations.csv')
    source_paths=['INITIAL_DATA_AUDIT.md','PHASE_2_MODELING_REPORT.md','PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md',
                  'src/fraud_detection/features.py','src/fraud_detection/modeling.py','src/fraud_detection/optimization.py',
                  'src/fraud_detection/tracking.py','scripts/run_baselines.py','scripts/run_optimization.py',
                  'artifacts/phase3_run.json','artifacts/tuned_model_comparison.csv','notebooks/02_ml_training.ipynb','notebooks/03_hyperparameter_optimization.ipynb']
    summary=dict(status='ANALYSIS_COMPLETE',model='XGBoost tuned provisional champion',source_model=str(model_path.resolve()),
        model_sha256=fingerprint(model_path),source_phase3_run_id=phase3['algorithms']['XGBoost']['best_run_id'],
        effective_iterations=int(model.best_iteration)+1,stored_iterations=model.get_booster().num_boosted_rounds(),
        metric_reproduction=True,validation_metrics=metrics,validation_rows=len(y),validation_frauds=int(y.sum()),
        validation_steps=[321,400],production_used=False,raw_csv_read=False,model_retrained=False,
        method='Exact native XGBoost Tree SHAP, approx_contribs=False, tree-path-dependent raw margin',
        units='Raw margin log-odds; sigmoid(base + sum SHAP) reconstructs score. Not calibrated probability or causal effects.',
        reference='Training path-cover statistics already stored in trees; no new background rows',
        threshold_note=THRESHOLD_LABEL,sample=dict(rows=len(selected),frauds=int(sample_y.sum()),nonfrauds=int((sample_y==0).sum()),
             fraud_fraction=float(sample_y.mean()),seed=42,method='All Validation frauds plus uniform 2,000 nonfrauds without replacement',
             selected_indices_sha256=hashlib.sha256(selected.tobytes()).hexdigest(),
             prevalence_weighted_importance='Fraud prevalence * fraud mean absolute SHAP + nonfraud prevalence * random nonfraud mean absolute SHAP; estimated, not full population SHAP'),
        additivity=additivity,top_features=importance.head(5)[['feature','mean_abs_shap']].to_dict('records'),
        emptied=dict(sample_rank=int(importance.loc[importance.feature=='orig_balance_emptied','shap_sample_rank'].iloc[0]),
             mean_abs_shap=float(importance.loc[importance.feature=='orig_balance_emptied','mean_abs_shap'].iloc[0]),states=state_summary),
        outside_rule=outside,local_cases=case_summaries,interaction_sample_rows=len(interaction_ids),
        interaction_marginal_error=interaction_error,top_interaction_components=pairs,
        versions={p:importlib.metadata.version(p) for p in ('shap','xgboost','numpy','pandas')},
        previous_phase_file_hashes={p:fingerprint(ROOT/p) for p in source_paths},
        validation_matrix_hashes={p.name:fingerprint(p) for p in (x_path,y_path)})
    summary['analysis_seconds']=time.perf_counter()-started
    # Force the known local SQLite URI; never inherit a remote endpoint in this phase.
    uri,experiment_id=configure_tracking(ROOT,uri=local_tracking_uri(ROOT))
    if not uri.startswith('sqlite:///'):raise ValueError('Phase4 must use local tracking')
    client=MlflowClient();past_ids=[run['run_id'] for run in phase3['runs']]
    historical=history_fingerprints(client,past_ids)
    with mlflow.start_run(run_name='phase4_XGBoost_interpretability') as run:
        summary['mlflow']=dict(run_id=run.info.run_id,experiment_id=experiment_id,tracking_uri=uri,
                              phase3_history_hashes=historical,new_run_count=1)
        mlflow.set_tags({'phase':'4','role':'interpretability','model':'XGBoost tuned','production_used':'false',
                        'source_model_run_id':summary['source_phase3_run_id']})
        mlflow.log_params(dict(sample_rows=len(selected),sample_frauds=int(sample_y.sum()),sample_nonfrauds=int((sample_y==0).sum()),
                              random_state=42,effective_iterations=summary['effective_iterations'],shap_output='raw_log_odds',
                              shap_method='exact_tree_path_dependent',validation_steps='321-400',reference_threshold=0.5))
        mlflow.log_metrics(dict(analysis_seconds=summary['analysis_seconds'],max_shap_margin_error=additivity['max_margin_error'],
                               non_rule_frauds=outside['rows'],non_rule_detection_rate=outside['detection_rate']))
        summary['status']='COMPLETE'
        (ROOT/'artifacts/interpretability_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
        for file in ('shap_global_importance.csv','local_explanations.csv','interpretability_summary.json','shap_feature_directions.csv','non_rule_fraud_explanations.csv','shap_group_comparison.csv'):
            mlflow.log_artifact(str(ROOT/'artifacts'/file))
        for path in sorted(figures.glob('*.png')):mlflow.log_artifact(str(path),'figures')
        for relative in ('src/fraud_detection/interpretability.py','scripts/run_interpretability.py','pyproject.toml','uv.lock'):
            mlflow.log_artifact(str(ROOT/relative),'source')
    if history_fingerprints(client,past_ids)!=historical:raise ValueError('Historical Phase3 run metadata changed')
    summary['mlflow']['historical_runs_unchanged']=True
    summary['mlflow']['run_status']=client.get_run(summary['mlflow']['run_id']).info.status
    summary['total_seconds']=time.perf_counter()-started
    (ROOT/'artifacts/interpretability_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    client.log_artifact(summary['mlflow']['run_id'],str(ROOT/'artifacts/interpretability_summary.json'))
    print(importance.head(5)[['feature','mean_abs_shap']].to_string(index=False))
    print(json.dumps(dict(outside_rule=outside,local_cases={name:case.get('validation_row_index') for name,case in case_summaries.items()},
                         mlflow_run_id=summary['mlflow']['run_id'],seconds=summary['total_seconds']),indent=2))

if __name__=='__main__':main()

