"""Frozen-model monitoring with explicit support and practical drift criteria."""
from pathlib import Path
import hashlib
import html
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, chi2_contingency
from sklearn.metrics import average_precision_score,roc_auc_score,confusion_matrix,precision_score,recall_score,fbeta_score
from .metrics import top_k_metrics
from .features import MODEL_COLUMNS

BINARY_FEATURES=set(MODEL_COLUMNS[5:])
WINDOW_WIDTH=72
MINIMUM_POSITIVES=30
KS_EFFECT_THRESHOLD=0.10
TV_EFFECT_THRESHOLD=0.05
PSI_REVIEW_THRESHOLD=0.20


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):h.update(block)
    return h.hexdigest()


def validate_period(x:np.ndarray,production:bool)->None:
    if x.ndim!=2 or x.shape[1]!=len(MODEL_COLUMNS) or len(x)==0 or not np.isfinite(x).all():raise ValueError('Invalid feature matrix')
    s=x[:,0]
    good=(s>=401) if production else ((s>=1)&(s<=400))
    if not (good&(s%1==0)).all():raise ValueError('Temporal boundary violation')


def verify_frozen(path:Path,expected_hash:str)->None:
    if sha256(path)!=expected_hash:raise ValueError('Frozen model changed')


def supported_metrics(y,scores)->dict:
    y=np.asarray(y);scores=np.asarray(scores)
    if y.shape!=scores.shape or len(y)==0 or not np.isin(y,(0,1)).all() or not np.isfinite(scores).all() or ((scores<0)|(scores>1)).any():raise ValueError('Invalid labels/scores')
    predicted=scores>=0.5;positives=int(y.sum());negatives=len(y)-positives
    tn,fp,fn,tp=confusion_matrix(y,predicted,labels=[0,1]).ravel()
    result=dict(observations=len(y),frauds=positives,prevalence=positives/len(y),
        pr_auc=float(average_precision_score(y,scores)) if positives else np.nan,
        roc_auc=float(roc_auc_score(y,scores)) if positives and negatives else np.nan,
        precision_05=float(precision_score(y,predicted,zero_division=0)) if predicted.any() else np.nan,
        recall_05=float(recall_score(y,predicted,zero_division=0)) if positives else np.nan,
        f1_05=float(fbeta_score(y,predicted,beta=1,zero_division=0)) if positives else np.nan,
        f2_05=float(fbeta_score(y,predicted,beta=2,zero_division=0)) if positives else np.nan,
        tp=int(tp),fp=int(fp),tn=int(tn),fn=int(fn),alerts=int(predicted.sum()),alert_rate=float(predicted.mean()),
        support_warning='no_positive_labels' if not positives else ('no_negative_labels' if not negatives else ('few_positives_below_30' if positives<MINIMUM_POSITIVES else '')))
    result.update(top_k_metrics(y,scores))
    for k in result:
        if k.startswith('recall_top_') and not positives:result[k]=np.nan
    return result


def window_labels(steps:np.ndarray,width:int=WINDOW_WIDTH)->np.ndarray:
    s=np.asarray(steps)
    if width<1 or not np.isfinite(s).all() or (s<401).any() or (s%1!=0).any():raise ValueError('Invalid Production windows')
    return ((s.astype(int)-401)//width).astype(int)


def reference_edges(values:np.ndarray)->np.ndarray:
    quantiles=np.unique(np.quantile(values,np.linspace(0,1,11)))
    # Preserve zero mass with a separate interval when many reference quantiles coincide.
    interior=quantiles[1:-1]
    if (values==0).any() and (values>0).any():interior=np.unique(np.r_[0,np.nextafter(0.0,1.0),interior])
    return np.r_[-np.inf,interior,np.inf]


def psi_from_edges(reference,current,edges)->float:
    # Jeffreys pseudocount 0.5 per bin; bin boundaries fitted only to Reference.
    a=np.histogram(reference,bins=edges)[0].astype(float)+0.5
    b=np.histogram(current,bins=edges)[0].astype(float)+0.5
    a/=a.sum();b/=b.sum()
    return float(np.sum((b-a)*np.log(b/a)))


def categorical_distance(reference,current)->dict:
    labels=np.union1d(reference,current)
    a=np.array([(reference==label).sum() for label in labels]);b=np.array([(current==label).sum() for label in labels])
    tv=float(0.5*np.abs(a/a.sum()-b/b.sum()).sum())
    if len(labels)>1:
        statistic,p,_,_=chi2_contingency(np.vstack([a,b]),correction=False)
    else:statistic,p=0.0,1.0
    return dict(statistic=float(statistic),p_value=float(p),total_variation=tv,categories=len(labels))


def holm_adjust(pvalues):
    p=np.asarray(pvalues,float);order=np.argsort(p);adjusted=np.empty(len(p))
    ordered=np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]);adjusted[order]=np.minimum(ordered,1)
    return adjusted


def drift_table(reference:np.ndarray,current:np.ndarray,bin_config:dict)->pd.DataFrame:
    rows=[]
    for j,name in enumerate(MODEL_COLUMNS):
        a=reference[:,j];b=current[:,j]
        if name in BINARY_FEATURES:
            test=categorical_distance(a,b);effect=test['total_variation'];threshold=TV_EFFECT_THRESHOLD
            record=dict(test='chi_square',effect_metric='total_variation',effect=effect,p_value=test['p_value'],psi=np.nan)
        else:
            ks=ks_2samp(a,b,method='asymp');effect=float(ks.statistic);threshold=KS_EFFECT_THRESHOLD
            record=dict(test='KS_asymptotic',effect_metric='KS_D',effect=effect,p_value=float(ks.pvalue),
                        psi=psi_from_edges(a,b,np.asarray(bin_config[name],dtype=float)))
        rows.append(dict(feature=name,reference_mean=float(a.mean(dtype='float64')),current_mean=float(b.mean(dtype='float64')),
            practical_threshold=threshold,structural_time=name=='step',**record))
    df=pd.DataFrame(rows);eligible=~df.structural_time
    df['holm_p_value']=1.0;df.loc[eligible,'holm_p_value']=holm_adjust(df.loc[eligible,'p_value'])
    df['statistical_shift']=(df.holm_p_value<0.05)&eligible
    df['practically_material']=df.effect>=df.practical_threshold
    df['drift_detected']=df.statistical_shift&df.practically_material&eligible
    df['psi_review']=(df.psi>=PSI_REVIEW_THRESHOLD)&eligible
    return df


def score_summary(scores)->dict:
    s=np.asarray(scores)
    q=np.quantile(s,[0.01,0.1,0.5,0.9,0.99,0.999])
    return dict(mean=float(s.mean()),median=float(q[2]),p01=float(q[0]),p10=float(q[1]),p90=float(q[3]),p99=float(q[4]),p999=float(q[5]),
                score_ge_05=int((s>=0.5).sum()),alert_rate=float((s>=0.5).mean()),score_ge_09_rate=float((s>=0.9).mean()))


def write_html(path:Path,title:str,sections:list)->None:
    body=[]
    for heading,text,frame in sections:
        body.append('<h2>'+html.escape(heading)+'</h2><p>'+html.escape(text)+'</p>')
        if frame is not None:body.append(frame.to_html(index=False,float_format=lambda n:f'{n:.8g}',na_rep='undefined',escape=True))
    content='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'+html.escape(title)+'</title><style>body{font:16px system-ui;margin:32px;line-height:1.5}table{border-collapse:collapse;font-size:13px}th,td{border:1px solid #ddd;padding:7px}th{background:#eef3f7}h1,h2{color:#111}p{max-width:1100px}</style></head><body><h1>'+html.escape(title)+'</h1>'+''.join(body)+'</body></html>'
    path.write_text(content,encoding='utf-8')



def wilson_interval(successes:int,total:int,z:float=1.959963984540054):
    """Descriptive binomial interval; transaction dependence limits its coverage interpretation."""
    if total==0:return (np.nan,np.nan)
    if not 0<=successes<=total:raise ValueError('Invalid binomial counts')
    p=successes/total;denom=1+z*z/total
    center=(p+z*z/(2*total))/denom
    half=z*np.sqrt(p*(1-p)/total+z*z/(4*total*total))/denom
    return (0.0 if successes==0 else max(0.0,float(center-half))), (1.0 if successes==total else min(1.0,float(center+half)))

