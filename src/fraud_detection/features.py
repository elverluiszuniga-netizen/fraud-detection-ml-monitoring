"""Row-local features; the principal benchmark scores before transaction execution."""
import numpy as np
import pandas as pd

TYPES = ('CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER')
BASE = ('step', 'amount', 'oldbalanceOrg', 'oldbalanceDest')
DERIVED = ('amount_to_oldbalanceOrg', 'orig_balance_zero', 'orig_balance_emptied', 'dest_is_merchant')
MODEL_COLUMNS = BASE + DERIVED + tuple('type_' + t for t in TYPES) + ('type_UNKNOWN',)
POST_COLUMNS = ('orig_balance_diff', 'dest_balance_diff', 'orig_balance_error', 'dest_balance_error')

def engineer_features(frame: pd.DataFrame, include_review: bool = False) -> pd.DataFrame:
    """Ratio zero sentinel plus indicator; emptied uses 0.01 absolute monetary tolerance.

    No labels, fitted statistics, entity identities or future rows are consulted.
    Post-event residuals are review-only and never passed to principal models.
    """
    x = frame.loc[:, BASE].astype('float64').copy()
    if not np.isfinite(x.to_numpy()).all() or (x < 0).any().any():
        raise ValueError('Base features must be finite and nonnegative')
    old = x.oldbalanceOrg.to_numpy()
    amount = x.amount.to_numpy()
    x['amount_to_oldbalanceOrg'] = np.divide(amount, old, out=np.zeros(len(x)), where=old != 0)
    x['orig_balance_zero'] = (old == 0).astype('uint8')
    x['orig_balance_emptied'] = ((old > 0) & (np.abs(old - amount) <= 0.01)).astype('uint8')
    x['dest_is_merchant'] = frame.nameDest.str.startswith('M', na=False).astype('uint8')
    for kind in TYPES:
        x['type_' + kind] = (frame.type == kind).astype('uint8')
    x['type_UNKNOWN'] = (~frame.type.isin(TYPES)).astype('uint8')
    if include_review:
        x['orig_balance_diff'] = frame.oldbalanceOrg - frame.newbalanceOrig
        x['dest_balance_diff'] = frame.newbalanceDest - frame.oldbalanceDest
        # Residuals meaningful for outgoing origin and incoming destination only.
        outgoing = frame.type.isin(('TRANSFER', 'CASH_OUT'))
        x['orig_balance_error'] = (x.orig_balance_diff - frame.amount).where(outgoing, 0)
        x['dest_balance_error'] = (x.dest_balance_diff - frame.amount).where(outgoing, 0)
    if not np.isfinite(x.to_numpy()).all():
        raise ValueError('Nonfinite engineered features')
    return x
