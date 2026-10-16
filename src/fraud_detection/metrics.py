"""Imbalanced classification and operational ranking metrics."""
import math
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, confusion_matrix, precision_score, recall_score, fbeta_score

TOP_FRACTIONS = (0.001, 0.005, 0.01)

def top_k_metrics(y, scores, fractions=TOP_FRACTIONS) -> dict:
    y, scores = np.asarray(y), np.asarray(scores)
    if len(y) == 0 or y.shape != scores.shape or not np.isfinite(scores).all() or not np.isin(y, (0, 1)).all():
        raise ValueError('Invalid labels/scores')
    # Stable deterministic ties by original row order; tied dummy scores carry no ranking information.
    order = np.argsort(-scores, kind='stable')
    result = {}
    for fraction in fractions:
        if not 0 < fraction <= 1:
            raise ValueError('Top fraction must be in (0,1]')
        k = max(1, math.ceil(len(y) * fraction))
        captured = int(y[order[:k]].sum())
        tag = f'{fraction * 100:g}pct'
        result.update({f'k_{tag}': k, f'precision_top_{tag}': captured / k,
                       f'recall_top_{tag}': captured / y.sum() if y.sum() else 0.0})
    return result

def evaluate(y, scores) -> dict:
    predictions = np.asarray(scores) >= 0.5
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    result = dict(pr_auc=average_precision_score(y, scores), roc_auc=roc_auc_score(y, scores),
                  precision_05=precision_score(y, predictions, zero_division=0),
                  recall_05=recall_score(y, predictions, zero_division=0),
                  f1_05=fbeta_score(y, predictions, beta=1, zero_division=0),
                  f2_05=fbeta_score(y, predictions, beta=2, zero_division=0),
                  tp=int(tp), fp=int(fp), tn=int(tn), fn=int(fn))
    result.update(top_k_metrics(y, scores))
    return result
