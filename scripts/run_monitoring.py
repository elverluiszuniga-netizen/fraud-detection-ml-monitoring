"""First out-of-time Production evaluation of the frozen XGBoost; local reports only."""
import os
os.environ.setdefault('DO_NOT_TRACK','1');os.environ.setdefault('MLFLOW_DISABLE_TELEMETRY','true')
import json,logging,sys,time,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import ks_2samp
from xgboost import XGBClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mlflow
from mlflow.tracking import MlflowClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fraud_detection.features import MODEL_COLUMNS,TYPES,engineer_features
from fraud_detection.monitoring import (sha256,verify_frozen,validate_period,supported_metrics,window_labels,
    drift_table,categorical_distance,score_summary,write_html)
from fraud_detection.tracking import configure_tracking
from fraud_detection.paths import raw_csv, champion_path, local_tracking_uri
from run_interpretability import history_fingerprints
LOG=logging.getLogger(__name__)


def load_production(path:Path):
    xs=[];ys=[]
    for chunk in pd.read_csv(path,usecols=['step','type','amount','oldbalanceOrg','oldbalanceDest','nameDest','isFraud'],chunksize=250000):
        selected=chunk.loc[chunk.step>=401]
        if len(selected):
            if not selected.isFraud.isin([0,1]).all():raise ValueError('Invalid target')
            xs.append(engineer_features(selected).to_numpy(dtype='float32'));ys.append(selected.isFraud.to_numpy(dtype='uint8'))
    if not xs:raise ValueError('No Production rows')
    x=np.vstack(xs);y=np.concatenate(ys);validate_period(x,True)
    return x,y


def type_labels(x):
    indicators=x[:,8:13]
    labels=np.asarray(TYPES)[np.argmax(indicators,axis=1)].astype('U12')
    labels[indicators.sum(axis=1)==0]='UNKNOWN'
    return labels


def evidently_exports(reference,current,sref,scurrent,outdir,budget=25000):
    from evidently import Report,Dataset,DataDefinition
    from evidently.presets import DataDriftPreset
    rng=np.random.default_rng(42)
    ri=rng.choice(len(reference),min(budget,len(reference)),replace=False);ci=rng.choice(len(current),min(budget,len(current)),replace=False)
    names=list(MODEL_COLUMNS[1:]);binary=list(MODEL_COLUMNS[5:]);numeric=list(MODEL_COLUMNS[1:5])
    rdf=pd.DataFrame(reference[ri,1:],columns=names);cdf=pd.DataFrame(current[ci,1:],columns=names)
    for name in binary:rdf[name]=rdf[name].astype(int).astype(str);cdf[name]=cdf[name].astype(int).astype(str)
    definition=DataDefinition(numerical_columns=numeric,categorical_columns=binary)
    report=Report([DataDriftPreset(columns=names,method='psi',threshold=0.2)],include_tests=True)
    snapshot=report.run(Dataset.from_pandas(cdf,data_definition=definition),Dataset.from_pandas(rdf,data_definition=definition))
    snapshot.save_html(str(outdir/'evidently_data_drift.html'))
    definition=DataDefinition(numerical_columns=['score'])
    snapshot2=Report([DataDriftPreset(columns=['score'],method='psi',threshold=0.2)],include_tests=True).run(
        Dataset.from_pandas(pd.DataFrame({'score':scurrent[ci]}),data_definition=definition),
        Dataset.from_pandas(pd.DataFrame({'score':sref[ri]}),data_definition=definition))
    snapshot2.save_html(str(outdir/'evidently_prediction_drift.html'))
    return dict(version=importlib.metadata.version('evidently'),status='COMPLETE',reference_sample_rows=len(ri),current_sample_rows=len(ci),
                method='PSI threshold 0.2 on reproducible uniform samples; supplementary, not the full-data primary decision',
                files=['evidently_data_drift.html','evidently_prediction_drift.html'])


def clean_json(value):
    if isinstance(value,dict):return {key:clean_json(v) for key,v in value.items()}
    if isinstance(value,list):return [clean_json(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(np.floating,float)):return float(value) if np.isfinite(value) else None
    if isinstance(value,(np.bool_,)):return bool(value)
    return value


def main():
    started=time.perf_counter();logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    frozen_path=ROOT/'artifacts/production_monitoring_freeze.json'
    freeze=json.loads(frozen_path.read_text(encoding='utf-8'))
    model_path=champion_path(ROOT);verify_frozen(model_path,freeze['model_sha256'])
    if list(MODEL_COLUMNS)!=freeze['feature_names'] or sha256(ROOT/'src/fraud_detection/features.py')!=freeze['feature_source_sha256']:raise ValueError('Pipeline changed')
    for relative,digest in freeze['previous_phase_hashes'].items():
        if sha256(ROOT/relative)!=digest:raise ValueError('Previous phase changed')
    model=XGBClassifier();model.load_model(model_path)
    if model.best_iteration+1!=freeze['effective_iterations']:raise ValueError('Effective model changed')
    xval=np.load(ROOT/'data/processed/validation_X.npy',mmap_mode='r');yval=np.load(ROOT/'data/processed/validation_y.npy')
    validate_period(xval,False);sval=model.predict_proba(xval)[:,1]
    val_metrics=supported_metrics(yval,sval)
    for key,value in freeze['validation_reproduction'].items():
        if not np.isclose(value,val_metrics[key],rtol=0,atol=1e-10):raise ValueError('Validation failed before Production access')
    LOG.info('Frozen identity and Validation verified before Production read')
    xtrain=np.load(ROOT/'data/processed/train_X.npy',mmap_mode='r');ytrain=np.load(ROOT/'data/processed/train_y.npy')
    reference=np.vstack([xtrain,xval]);reference_y=np.r_[ytrain,yval];validate_period(reference,False)
    clock=time.perf_counter();sref=model.predict_proba(reference)[:,1];ref_seconds=time.perf_counter()-clock
    xprod,yprod=load_production(raw_csv(ROOT))
    clock=time.perf_counter();sprod=model.predict_proba(xprod)[:,1];prod_seconds=time.perf_counter()-clock
    prod_metrics=supported_metrics(yprod,sprod)
    LOG.info('Production rows=%s frauds=%s step range=%s-%s AP=%.8f',len(yprod),yprod.sum(),xprod[:,0].min(),xprod[:,0].max(),prod_metrics['pr_auc'])
    comparison=pd.DataFrame([dict(period='Validation',**val_metrics),dict(period='Production',**prod_metrics)])
    comparison.to_csv(ROOT/'artifacts/production_model_comparison.csv',index=False)
    drift=drift_table(reference,xprod,freeze['reference_quantile_bins']);drift.to_csv(ROOT/'artifacts/data_drift_features.csv',index=False)
    LOG.info('Full-data primary drift criteria: %s material features, excluding structural step',drift.drift_detected.sum())
    tr=type_labels(reference);tp=type_labels(xprod);tv=type_labels(xval)
    conditioned=[]
    # Within-type diagnostics avoid interpreting transaction mixture as within-operation change.
    for kind in sorted(set(tr)|set(tp)):
        a=tr==kind;b=tp==kind
        if not a.any() or not b.any():continue
        for name in ('amount','oldbalanceOrg','oldbalanceDest','amount_to_oldbalanceOrg','orig_balance_emptied'):
            j=MODEL_COLUMNS.index(name)
            if name=='orig_balance_emptied':d=categorical_distance(reference[a,j],xprod[b,j])['total_variation'];method='TV'
            else:d=float(ks_2samp(reference[a,j],xprod[b,j],method='asymp').statistic);method='KS_D'
            conditioned.append(dict(type=kind,feature=name,reference_rows=int(a.sum()),production_rows=int(b.sum()),effect=d,method=method))
    pd.DataFrame(conditioned).to_csv(ROOT/'artifacts/type_conditioned_drift.csv',index=False)
    windows=[]
    labels=window_labels(xprod[:,0],freeze['window_width_hours'])
    for window in np.unique(labels):
        mask=labels==window
        windows.append(dict(window=int(window),step_min=int(xprod[mask,0].min()),step_max=int(xprod[mask,0].max()),
                            **supported_metrics(yprod[mask],sprod[mask])))
    windows=pd.DataFrame(windows);windows.to_csv(ROOT/'artifacts/monitoring_windows.csv',index=False)
    bytype=[]
    for period,x,y,s,types in (('Validation',xval,yval,sval,tv),('Production',xprod,yprod,sprod,tp)):
        for kind in sorted(set(types)):
            mask=types==kind;bytype.append(dict(period=period,type=kind,**supported_metrics(y[mask],s[mask])))
    bytype=pd.DataFrame(bytype);bytype.to_csv(ROOT/'artifacts/monitoring_by_type.csv',index=False)
    relation=[]
    for period,x,y,s in (('Validation',xval,yval,sval),('Production',xprod,yprod,sprod)):
        for rule,mask in [('emptied_1',x[:,6]==1),('emptied_0',x[:,6]==0),('amount_zero',x[:,1]==0),('positive_balance_ratio_near_1',(x[:,2]>0)&(np.abs(x[:,4]-1)<=1e-6))]:
            if mask.any():relation.append(dict(period=period,rule=rule,**supported_metrics(y[mask],s[mask])))
    relation=pd.DataFrame(relation);relation.to_csv(ROOT/'artifacts/monitoring_relation_checks.csv',index=False)
    score_rows=pd.DataFrame([dict(period='Reference_Development',**score_summary(sref)),dict(period='Validation',**score_summary(sval)),dict(period='Production',**score_summary(sprod))])
    score_rows.to_csv(ROOT/'artifacts/monitoring_scores.csv',index=False)
    score_ks_ref=ks_2samp(sref,sprod,method='asymp');score_ks_val=ks_2samp(sval,sprod,method='asymp')
    atypical=[]
    for period,x,y,s in (('Validation',xval,yval,sval),('Production',xprod,yprod,sprod)):
        masks={'fraud_amount_zero':(y==1)&(x[:,1]==0),'fraud_outside_emptying':(y==1)&(x[:,6]==0),
               'false_negative':(y==1)&(s<0.5)}
        for category,mask in masks.items():
            for index in np.flatnonzero(mask):
                atypical.append(dict(period=period,category=category,period_row_index=int(index),label=int(y[index]),score=float(s[index]),
                                     prediction_05=int(s[index]>=0.5),**{name:float(x[index,j]) for j,name in enumerate(MODEL_COLUMNS)}))
        legitimate=np.flatnonzero(y==0)
        for index in legitimate[np.argsort(-s[legitimate],kind='stable')[:10]]:
            atypical.append(dict(period=period,category='top_scored_legitimate',period_row_index=int(index),label=0,score=float(s[index]),
                                  prediction_05=int(s[index]>=0.5),**{name:float(x[index,j]) for j,name in enumerate(MODEL_COLUMNS)}))
    atypical=pd.DataFrame(atypical);atypical.to_csv(ROOT/'artifacts/monitoring_atypical_cases.csv',index=False)
    frame=pd.DataFrame({'step':xprod[:,0].astype(int),'target':yprod,'score':sprod,'alerts':sprod>=0.5,'false_negative':(yprod==1)&(sprod<0.5)})
    profile=frame.groupby('step').agg(transactions=('target','size'),frauds=('target','sum'),alerts=('alerts','sum'),false_negatives=('false_negative','sum'),mean_score=('score','mean')).reset_index()
    profile['fraud_rate']=profile.frauds/profile.transactions;profile.to_csv(ROOT/'artifacts/production_step_profile.csv',index=False)
    figdir=ROOT/'reports/figures/monitoring';figdir.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for ax,name in zip(axes,['transactions','fraud_rate','false_negatives']):ax.plot(profile.step,profile[name]);ax.set_ylabel(name)
    axes[-1].set_xlabel('Production step (simulation hour)');fig.tight_layout();fig.savefig(figdir/'production_evolution.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for name,s in [('Validation',sval),('Production',sprod)]:
        axes[0].hist(s,bins=np.linspace(0,1,31),weights=np.ones(len(s))/len(s),histtype='step',label=name)
        points=np.linspace(0,1,1001);ordered=np.sort(s);axes[1].plot(points,np.searchsorted(ordered,points,side='right')/len(s),label=name)
    axes[0].set(xlabel='Frozen score',ylabel='Fraction',yscale='log');axes[1].set(xlabel='Frozen score',ylabel='Empirical CDF')
    for ax in axes:ax.legend()
    fig.tight_layout();fig.savefig(figdir/'score_distributions.png',dpi=160);plt.close(fig)
    reportdir=ROOT/'reports/monitoring';reportdir.mkdir(parents=True,exist_ok=True)
    write_html(reportdir/'data_drift.html','Full-data covariate drift',[
        ('Decision rules','KS/chi-square p-values with Holm adjustment and practical thresholds KS D>=0.10 or categorical TV>=0.05. PSI>=0.20 is a separate review flag. Thresholds are engineering conventions. Step is structurally disjoint and excluded from alert count.',drift),
        ('Within transaction type','Effect sizes within type distinguish composition shifts from within-operation changes; these diagnostics have no standalone alert decision.',pd.DataFrame(conditioned))])
    write_html(reportdir/'prediction_drift.html','Frozen prediction-output monitoring',[
        ('Score distributions','Prediction distribution changes are not automatically concept drift or model deterioration. Class weighting means scores are not calibrated.',score_rows),
        ('Statistical distance',f'Reference KS D={score_ks_ref.statistic:.6f}, p={score_ks_ref.pvalue:.6g}; Validation KS D={score_ks_val.statistic:.6f}, p={score_ks_val.pvalue:.6g}. Small distances may be significant at this sample size.',None)])
    write_html(reportdir/'performance_monitoring.html','Out-of-time performance monitoring',[
        ('Validation vs Production','AP depends on prevalence. Production was untouched during model selection; this retrospective labeled evaluation does not tune or modify the model.',comparison),
        ('Fixed 72-hour windows','Anchor step 401; width fixed before Production. Support warnings retained; undefined metrics shown explicitly. All-positive AP can be trivially 1 and is not evidence of separation.',windows),
        ('By transaction type','No positives or no predicted alerts produce undefined corresponding metrics.',bytype),
        ('Feature-target relationship','Concept drift not conclusively established. These coarse rule-based groups are descriptive, not proof of changed P(Y|X).',relation),
        ('Atypical cases','No case is used to change model, features, calibration or threshold.',atypical)])
    try:
        evidence=evidently_exports(reference,xprod,sref,sprod,reportdir,freeze['evidently_sample_rows'])
    except Exception as exc:
        evidence=dict(status='FALLBACK',version=importlib.metadata.version('evidently'),error=f'{type(exc).__name__}: {exc}',
                      alternative='Full-data custom standalone data/prediction/performance HTML remains authoritative.')
        LOG.warning('Evidently unavailable: %s',evidence['error'])
    verify_frozen(model_path,freeze['model_sha256'])
    zero=(yprod==1)&(xprod[:,1]==0);outside=(yprod==1)&(xprod[:,6]==0)
    summary=dict(status='COMPLETE',model_sha256=freeze['model_sha256'],freeze_sha256=sha256(frozen_path),
        production=dict(rows=len(yprod),frauds=int(yprod.sum()),step_min=int(xprod[:,0].min()),step_max=int(xprod[:,0].max()),metrics=prod_metrics),
        validation=val_metrics,reference=dict(rows=len(reference),frauds=int(reference_y.sum()),prevalence=float(reference_y.mean()),inference_seconds=ref_seconds),
        production_inference_seconds=prod_seconds,drift_features=int(drift.drift_detected.sum()),statistical_shift_features=int(drift.statistical_shift.sum()),
        psi_review_features=int(drift.psi_review.sum()),score_shift=dict(reference_KS_D=float(score_ks_ref.statistic),reference_p=float(score_ks_ref.pvalue),
        validation_KS_D=float(score_ks_val.statistic),validation_p=float(score_ks_val.pvalue)),
        type_composition=categorical_distance(tr,tp),evidently=evidence,windows=windows[['window','step_min','step_max','observations','frauds','support_warning']].to_dict('records'),
        atypical=dict(fraud_amount_zero=int(zero.sum()),amount_zero_detected=int((sprod[zero]>=0.5).sum()),outside_rule_frauds=int(outside.sum()),
            outside_rule_detected=int((sprod[outside]>=0.5).sum()),maximum_legitimate_score=float(sprod[yprod==0].max())),
        concept_drift='Concept drift not conclusively established.',model_changed=False,production_used_for_optimization=False,
        top_k_capacity_limits={str(f):min(1,float(np.ceil(len(yprod)*f)/yprod.sum())) for f in freeze['top_fractions']},
        previous_phase_hashes=freeze['previous_phase_hashes'],versions={name:importlib.metadata.version(name) for name in ('evidently','xgboost','scipy','pandas')})
    phase3=json.loads((ROOT/'artifacts/phase3_run.json').read_text(encoding='utf-8'));phase4=json.loads((ROOT/'artifacts/interpretability_summary.json').read_text(encoding='utf-8'))
    uri,exp=configure_tracking(ROOT,uri=local_tracking_uri(ROOT));client=MlflowClient()
    historical_ids=[run['run_id'] for run in phase3['runs']]+[phase4['mlflow']['run_id']]
    history=history_fingerprints(client,historical_ids)
    with mlflow.start_run(run_name='phase5_frozen_XGBoost_production_monitoring') as run:
        summary['mlflow']=dict(run_id=run.info.run_id,experiment_id=exp,tracking_uri=uri,historical_hashes=history)
        mlflow.set_tags({'phase':'5','role':'production_monitoring','model_sha256':freeze['model_sha256'],'model_frozen':'true'})
        mlflow.log_params(dict(model_source_run_id=freeze['source_run_id'],reference_steps='1-400',production_step_min=summary['production']['step_min'],
            production_step_max=summary['production']['step_max'],window_hours=72,reference_threshold=0.5,top_fractions='0.001,0.005,0.01',model_sha256=freeze['model_sha256']))
        mlflow.log_metrics({('production_'+name.replace('.','_')):float(value) for name,value in prod_metrics.items() if isinstance(value,(int,float,np.number)) and np.isfinite(value)})
        mlflow.log_metrics(dict(material_drift_features=summary['drift_features'],statistical_shift_features=summary['statistical_shift_features'],
                               prediction_KS_D=summary['score_shift']['validation_KS_D'],production_inference_seconds=prod_seconds))
        for path in (ROOT/'artifacts').glob('*.csv'):
            if path.name.startswith(('production_','monitoring_','data_drift_','type_conditioned_')):mlflow.log_artifact(str(path))
        mlflow.log_artifact(str(frozen_path))
        for path in reportdir.glob('*.html'):
            if path.stat().st_size<=25*2**20:mlflow.log_artifact(str(path),'html')
        for path in figdir.glob('*.png'):mlflow.log_artifact(str(path),'figures')
    summary['mlflow']['historical_runs_unchanged']=history_fingerprints(client,historical_ids)==history
    if not summary['mlflow']['historical_runs_unchanged']:raise ValueError('Historical runs changed')
    summary['mlflow']['run_status']=client.get_run(summary['mlflow']['run_id']).info.status
    summary['total_seconds']=time.perf_counter()-started
    summary=clean_json(summary)
    (ROOT/'artifacts/monitoring_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    client.log_artifact(summary['mlflow']['run_id'],str(ROOT/'artifacts/monitoring_summary.json'))
    print(comparison[['period','observations','frauds','pr_auc','roc_auc','precision_05','recall_05','f2_05','tp','fp','tn','fn','recall_top_0.1pct']].to_string(index=False))
    print(json.dumps({key:summary[key] for key in ['drift_features','statistical_shift_features','atypical','evidently','total_seconds']},indent=2))

if __name__=='__main__':main()
