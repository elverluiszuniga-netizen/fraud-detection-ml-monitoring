"""Exact native Tree SHAP for the unchanged early-stopped XGBoost model."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
import shap
from xgboost import XGBClassifier, DMatrix
from .features import MODEL_COLUMNS

SEED=42
REFERENCE_THRESHOLD=0.5
THRESHOLD_LABEL='threshold 0.5 = reference threshold, not final production threshold.'


def validate_validation(x: np.ndarray, y: np.ndarray | None = None) -> None:
    if x.ndim!=2 or x.shape[1]!=len(MODEL_COLUMNS) or len(x)==0 or not np.isfinite(x).all():
        raise ValueError('Invalid Validation features')
    if not ((x[:,0]>=321)&(x[:,0]<=400)&(x[:,0]%1==0)).all():
        raise ValueError('Only Validation steps 321-400 allowed; Production excluded')
    if y is not None and (len(y)!=len(x) or not np.isin(y,(0,1)).all()):
        raise ValueError('Invalid labels')


def sample_explanations(x: np.ndarray,y: np.ndarray,nonfrauds: int=2000,seed: int=SEED) -> np.ndarray:
    """All frauds plus uniform without-replacement nonfrauds; explanatory, not prevalence sample."""
    validate_validation(x,y)
    if nonfrauds<1:raise ValueError('Require positive nonfraud budget')
    positives=np.flatnonzero(y==1); negatives=np.flatnonzero(y==0)
    if len(positives)==0 or len(negatives)==0:raise ValueError('Both classes needed')
    rng=np.random.default_rng(seed)
    chosen=rng.choice(negatives,size=min(nonfrauds,len(negatives)),replace=False)
    return np.sort(np.r_[positives,chosen])


def select_local_cases(x: np.ndarray,y: np.ndarray,scores: np.ndarray) -> dict:
    """Deterministic extremes/errors/non-rule TP and closest fixed-threshold case, ties by row."""
    validate_validation(x,y)
    if scores.shape!=y.shape or not np.isfinite(scores).all():raise ValueError('Invalid scores')
    predicted=scores>=REFERENCE_THRESHOLD
    emptied=x[:,MODEL_COLUMNS.index('orig_balance_emptied')]==1
    def choose(mask,key,maximum=False):
        ids=np.flatnonzero(mask)
        if not len(ids):return None
        values=key[ids]
        return int(ids[np.argmax(values) if maximum else np.argmin(values)])
    cases={
        'A_high_score_TP':choose((y==1)&predicted,scores,True),
        'B_low_score_TN':choose((y==0)&~predicted,scores),
        'C_false_negative':choose((y==1)&~predicted,scores),
        'D_false_positive':choose((y==0)&predicted,scores,True),
        'E_non_rule_TP':choose((y==1)&predicted&~emptied,scores,True),
        'F_nearest_reference_threshold':int(np.argmin(np.abs(scores-REFERENCE_THRESHOLD))),
    }
    return cases


def load_champion(path: Path):
    model=XGBClassifier();model.load_model(path)
    if not hasattr(model,'best_iteration'):raise ValueError('Missing saved best-iteration metadata')
    return model


def explain_model(model: XGBClassifier,x: np.ndarray):
    """Native exact path-dependent Tree SHAP in raw log-odds; uses effective trees only.

    Training path-cover statistics already in trees define the reference; no new background
    dataset or labels are supplied. SHAP values explain the margin, not additive probabilities.
    """
    validate_validation(x)
    # SHAP slicing expects ndarray metadata, not a numpy memmap subclass.
    x=np.asarray(x)
    limit=int(model.best_iteration)+1
    booster=model.get_booster()
    matrix=DMatrix(x)
    contributions=booster.predict(matrix,pred_contribs=True,approx_contribs=False,iteration_range=(0,limit))
    margins=booster.predict(matrix,output_margin=True,iteration_range=(0,limit))
    reconstructed=contributions.sum(axis=1)
    if not np.allclose(reconstructed,margins,rtol=1e-5,atol=2e-5):raise ValueError('SHAP additivity failed')
    scores=model.predict_proba(x)[:,1]
    if not np.allclose(expit(reconstructed),scores,rtol=1e-5,atol=2e-6):raise ValueError('Explained margin differs from model score')
    explanation=shap.Explanation(values=contributions[:,:-1],base_values=contributions[:,-1],
                                 data=x,feature_names=list(MODEL_COLUMNS))
    errors=dict(max_margin_error=float(np.max(np.abs(reconstructed-margins))),
                max_probability_error=float(np.max(np.abs(expit(reconstructed)-scores))))
    return explanation,errors


def global_importance(explanation,y: np.ndarray,population_prevalence: float) -> pd.DataFrame:
    if not 0<=population_prevalence<=1 or len(y)!=len(explanation.values) or not np.isin(y,(0,1)).all():
        raise ValueError('Invalid weighting inputs')
    if not (y==1).any() or not (y==0).any():raise ValueError('Need both sampled classes')
    absolute=np.abs(explanation.values)
    fraud=absolute[y==1].mean(axis=0);legitimate=absolute[y==0].mean(axis=0)
    result=pd.DataFrame(dict(feature=MODEL_COLUMNS,mean_abs_shap=absolute.mean(axis=0),
          mean_abs_shap_fraud=fraud,mean_abs_shap_nonfraud=legitimate,
          mean_abs_shap_prevalence_weighted=population_prevalence*fraud+(1-population_prevalence)*legitimate,
          mean_signed_shap_fraud=explanation.values[y==1].mean(axis=0),
          mean_signed_shap_nonfraud=explanation.values[y==0].mean(axis=0)))
    return result.sort_values('mean_abs_shap',ascending=False,kind='stable').reset_index(drop=True)


def native_importance(model) -> pd.DataFrame:
    # Native gain uses exactly the same effective ensemble, not unused post-best-round trees.
    booster=model.get_booster()[:int(model.best_iteration)+1]
    gain=booster.get_score(importance_type='gain')
    weight=booster.get_score(importance_type='weight')
    return pd.DataFrame(dict(feature=MODEL_COLUMNS,native_gain=[gain.get(f'f{i}',0.0) for i in range(len(MODEL_COLUMNS))],
                             native_split_count=[weight.get(f'f{i}',0.0) for i in range(len(MODEL_COLUMNS))]))


def local_contributions(explanation,case: str,index: int,true_label: int,score: float):
    values=explanation.values
    if values.ndim!=1 or len(values)!=len(MODEL_COLUMNS):raise ValueError('Expected single-row explanation')
    order=np.argsort(-np.abs(values),kind='stable')
    return [dict(case=case,validation_row_index=index,true_label=int(true_label),score=float(score),
                 prediction_05=int(score>=0.5),base_log_odds=float(explanation.base_values),
                 feature=MODEL_COLUMNS[i],feature_value=float(explanation.data[i]),shap_log_odds=float(values[i]),
                 absolute_rank=rank+1) for rank,i in enumerate(order)]

