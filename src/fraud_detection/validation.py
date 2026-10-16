import math

EXPECTED_COLUMNS = "step type amount nameOrig oldbalanceOrg newbalanceOrig nameDest oldbalanceDest newbalanceDest isFraud isFlaggedFraud".split()

def missing_columns(columns):
    return sorted(set(EXPECTED_COLUMNS) - set(columns))

def binary(value):
    return value in ("0", "1")

def segment(value):
    try:
        step = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(step) or step < 1 or not step.is_integer():
        return None
    return "reference" if step <= 400 else "production"
