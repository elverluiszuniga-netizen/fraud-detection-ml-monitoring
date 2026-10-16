"""Temporal design is chosen using counts, never benchmark scores."""
import math
import pandas as pd

def temporal_profile(frame: pd.DataFrame) -> pd.DataFrame:
    dev = frame.loc[frame.step.between(1, 400)]
    result = dev.groupby('step').isFraud.agg(transactions='size', frauds='sum')
    result['fraud_rate'] = result.frauds / result.transactions
    return result

def choose_cutoff(profile: pd.DataFrame, minimum_frauds: int = 100) -> int:
    """Use 80% of the fixed 400-step window if each side has >=100 frauds.

    Insufficient counts are a design blocker, not an invitation to optimize splits.
    """
    cutoff = math.floor(400 * 0.8)
    if (profile.loc[profile.index <= cutoff, 'frauds'].sum() < minimum_frauds or
            profile.loc[profile.index > cutoff, 'frauds'].sum() < minimum_frauds):
        raise ValueError('Insufficient frauds for the prespecified temporal split')
    return cutoff

def temporal_masks(steps: pd.Series, cutoff: int = 320):
    if not 1 <= cutoff < 400:
        raise ValueError('Cutoff must lie inside Development')
    if steps.isna().any() or ((steps < 1) | (steps % 1 != 0)).any():
        raise ValueError('Invalid steps')
    return steps <= cutoff, (steps > cutoff) & (steps <= 400), steps >= 401

def assert_training_steps(steps: pd.Series, cutoff: int) -> None:
    if steps.empty or not steps.between(1, cutoff).all() or (steps % 1 != 0).any():
        raise ValueError('Training contains invalid, validation or Production steps')
