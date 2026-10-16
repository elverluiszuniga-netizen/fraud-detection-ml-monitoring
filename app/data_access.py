"""Small persisted-artifact access and mathematically valid dashboard filtering.

No model, raw CSV, MLflow, Evidently, SHAP or scoring imports belong in this layer.
"""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CSV_FILES={
    'comparison':'production_model_comparison.csv','windows':'monitoring_windows.csv',
    'drift':'data_drift_features.csv','conditioned':'type_conditioned_drift.csv',
    'scores':'monitoring_scores.csv','cases':'monitoring_atypical_cases.csv',
    'steps':'production_step_profile.csv','by_type':'monitoring_by_type.csv'}
JSON_FILES={'summary':'monitoring_summary.json','freeze':'production_monitoring_freeze.json'}
REPORT_FILES={
    'Datos · análisis completo':'data_drift.html',
    'Scores · análisis completo':'prediction_drift.html',
    'Desempeño · análisis completo':'performance_monitoring.html',
    'Evidently · datos (muestra PSI)':'evidently_data_drift.html',
    'Evidently · scores (muestra PSI)':'evidently_prediction_drift.html'}
REQUIRED_COLUMNS={
    'comparison':{'period','observations','frauds','tp','fp','tn','fn','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','prevalence','alert_rate'},
    'windows':{'window','step_min','step_max','observations','frauds','tp','fp','tn','fn','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05'},
    'drift':{'feature','effect','practical_threshold','structural_time','statistical_shift','practically_material','drift_detected','holm_p_value','reference_mean','current_mean'},
    'conditioned':{'type','feature','effect','method'},'scores':{'period','mean','median','p01','p10','p90','p99','p999','alert_rate'},
    'cases':{'period','category','period_row_index','step','score','amount','oldbalanceOrg','prediction_05','label'},
    'steps':{'step','transactions','frauds','alerts','false_negatives','fraud_rate'},
    'by_type':{'period','type','observations','frauds','pr_auc','roc_auc'}}

class ArtifactError(ValueError):pass


def safe_file(root:Path,relative:str)->Path:
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root):raise ArtifactError('Ruta fuera del proyecto')
    if not path.is_file():raise ArtifactError(f'Falta el artifact: {relative}. Genérelo con el pipeline documentado de Fase 5.')
    return path


def count_metrics(row)->dict:
    counts={name:int(row[name]) for name in ('observations','frauds','tp','fp','tn','fn')}
    if any(float(row[name])!=value or value<0 for name,value in counts.items()):raise ArtifactError('Conteos inválidos')
    n=counts['observations'];p=counts['frauds'];tp,fp,tn,fn=(counts[k] for k in ('tp','fp','tn','fn'))
    if n<=0 or tp+fp+tn+fn!=n or tp+fn!=p or p>n:raise ArtifactError('Matriz de confusión inconsistente con soporte')
    def divide(a,b):return a/b if b else np.nan
    return dict(**counts,prevalence=p/n,alerts=tp+fp,alert_rate=(tp+fp)/n,
                precision_05=divide(tp,tp+fp),recall_05=divide(tp,p),
                f1_05=divide(2*tp,2*tp+fp+fn) if p else np.nan,
                f2_05=divide(5*tp,5*tp+4*fn+fp) if p else np.nan)


def validate_bundle(bundle:dict)->None:
    summary=bundle['summary'];freeze=bundle['freeze']
    if summary.get('status')!='COMPLETE' or summary.get('model_changed') is not False or summary.get('production_used_for_optimization') is not False:
        raise ArtifactError('La Fase 5 no está validada o el modelo no está congelado')
    if summary.get('model_sha256')!=freeze.get('model_sha256') or freeze.get('threshold')!=0.5:
        raise ArtifactError('Identidad/threshold congelado inconsistente')
    for key,columns in REQUIRED_COLUMNS.items():
        missing=columns-set(bundle[key].columns)
        if missing:raise ArtifactError(f'{CSV_FILES[key]}: faltan columnas {sorted(missing)}')
    comparison=bundle['comparison']
    if set(comparison.period)!= {'Validation','Production'} or len(comparison)!=2:raise ArtifactError('Períodos duplicados o faltantes')
    for row in comparison.to_dict('records'):
        derived=count_metrics(row)
        for name,value in derived.items():
            if name in row and not np.isclose(value,row[name],equal_nan=True,atol=1e-10,rtol=0):raise ArtifactError(f'KPI inconsistente: {row["period"]} {name}')
        for name in ('pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05'):
            if pd.notna(row[name]) and not 0<=row[name]<=1:raise ArtifactError('Métrica fuera de rango')
        recorded=summary['production']['metrics'] if row['period']=='Production' else summary['validation']
        for name in ('observations','frauds','tp','fp','tn','fn','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','prevalence','alert_rate'):
            if not np.isclose(row[name],recorded[name],equal_nan=True,atol=1e-10,rtol=0):raise ArtifactError('CSV y resumen JSON no coinciden: '+name)
        for fraction in freeze['top_fractions']:
            suffix=f'{fraction*100:g}pct';k=int(row[f'k_{suffix}'])
            if k!=math.ceil(row['observations']*fraction):raise ArtifactError('Capacidad Top-K inconsistente')
            precision=row[f'precision_top_{suffix}'];recall=row[f'recall_top_{suffix}']
            if not np.isclose(precision*k,recall*row['frauds'],atol=1e-8):raise ArtifactError('TP de Top-K inconsistente')
    windows=bundle['windows'].sort_values('step_min')
    if windows.window.duplicated().any() or (windows.step_min> windows.step_max).any() or (windows.step_min.iloc[1:].to_numpy()<=windows.step_max.iloc[:-1].to_numpy()).any():raise ArtifactError('Ventanas solapadas o inválidas')
    for row in windows.to_dict('records'):
        derived=count_metrics(row)
        for name,value in derived.items():
            if name in row and not np.isclose(value,row[name],equal_nan=True,atol=1e-10,rtol=0):raise ArtifactError('Métrica de ventana inconsistente: '+name)
    production=comparison.loc[comparison.period=='Production'].iloc[0]
    for name in ('observations','frauds','tp','fp','tn','fn'):
        if int(windows[name].sum())!=int(production[name]):raise ArtifactError('Ventanas no reconstruyen Production')
    if windows.step_min.min()!=summary['production']['step_min'] or windows.step_max.max()!=summary['production']['step_max']:raise ArtifactError('Rango temporal inconsistente')
    drift=bundle['drift']
    expected=drift.statistical_shift&drift.practically_material&~drift.structural_time
    if not (drift.drift_detected==expected).all():raise ArtifactError('Criterios drift inconsistentes')
    if int(drift.drift_detected.sum())!=summary['drift_features'] or int(drift.statistical_shift.sum())!=summary['statistical_shift_features']:raise ArtifactError('Conteos drift inconsistentes')
    steps=bundle['steps']
    if steps.step.duplicated().any() or steps.transactions.sum()!=production.observations or steps.frauds.sum()!=production.frauds:raise ArtifactError('Perfil temporal inconsistente')
    for row in bundle['scores'].to_dict('records'):
        if not 0<=row['alert_rate']<=1:raise ArtifactError('Tasa de alertas inválida')
    cases=bundle['cases']
    if ((cases.score<0)|(cases.score>1)).any() or not (cases.prediction_05==(cases.score>=freeze['threshold']).astype(int)).all():raise ArtifactError('Casos y predicción congelada inconsistentes')


def load_bundle(root:Path=ROOT)->dict:
    root=Path(root);bundle={}
    for key,name in JSON_FILES.items():
        try:bundle[key]=json.loads(safe_file(root,'artifacts/'+name).read_text(encoding='utf-8'))
        except (json.JSONDecodeError,OSError) as exc:raise ArtifactError(f'{name}: {exc}') from exc
    for key,name in CSV_FILES.items():
        try:bundle[key]=pd.read_csv(safe_file(root,'artifacts/'+name))
        except (pd.errors.ParserError,OSError) as exc:raise ArtifactError(f'{name}: {exc}') from exc
    validate_bundle(bundle)
    return bundle


def artifact_signature(root:Path=ROOT)->tuple:
    names=list(JSON_FILES.values())+list(CSV_FILES.values())
    return tuple((name,safe_file(root,'artifacts/'+name).stat().st_mtime_ns,safe_file(root,'artifacts/'+name).stat().st_size) for name in names)


def filtered_metrics(bundle:dict,window_ids:list)->dict:
    windows=bundle['windows'];ids=set(window_ids)
    if not ids or not ids.issubset(set(windows.window)):raise ArtifactError('Seleccione ventanas válidas')
    selected=windows.loc[windows.window.isin(ids)]
    sums=selected[['observations','frauds','tp','fp','tn','fn']].sum().to_dict()
    metrics=count_metrics(sums)
    metrics.update(step_min=int(selected.step_min.min()),step_max=int(selected.step_max.max()),window_count=len(selected),window_ids=sorted(ids))
    if ids==set(windows.window):
        source=bundle['comparison'].loc[bundle['comparison'].period=='Production'].iloc[0]
        metrics.update(pr_auc=float(source.pr_auc),roc_auc=float(source.roc_auc),ranking_scope='Production completo',ranking_available=True)
    elif len(ids)==1:
        source=selected.iloc[0]
        metrics.update(pr_auc=float(source.pr_auc),roc_auc=float(source.roc_auc),ranking_scope='Ventana individual',ranking_available=True)
    else:
        source=None;metrics.update(pr_auc=np.nan,roc_auc=np.nan,ranking_scope='No disponible: no hay scores individuales para combinar ventanas',ranking_available=False)
    metrics['top_k']=[]
    for fraction in bundle['freeze']['top_fractions']:
        k=math.ceil(metrics['observations']*fraction);suffix=f'{fraction*100:g}pct'
        metrics['top_k'].append(dict(capacity=f'{fraction*100:g}%',reviewed=k,
          precision=float(source[f'precision_top_{suffix}']) if source is not None else np.nan,
          recall=float(source[f'recall_top_{suffix}']) if source is not None else np.nan,
          theoretical_recall=min(1,k/metrics['frauds']) if metrics['frauds'] else np.nan))
    return metrics


def filter_step_rows(frame:pd.DataFrame,windows:pd.DataFrame,window_ids:list,column='step')->pd.DataFrame:
    selected=windows.loc[windows.window.isin(window_ids)]
    mask=np.zeros(len(frame),dtype=bool)
    for row in selected.itertuples():mask|=frame[column].between(row.step_min,row.step_max).to_numpy()
    return frame.loc[mask].copy()


def report_paths(root:Path=ROOT)->dict:
    return {label:safe_file(root,'reports/monitoring/'+name) for label,name in REPORT_FILES.items()}

