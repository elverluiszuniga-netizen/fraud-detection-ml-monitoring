"""Fixed, small benchmark configurations without tuning or resampling."""
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

SEED = 42

def build_models():
    return {
        'Dummy': DummyClassifier(strategy='prior', random_state=SEED),
        'LogisticRegression': make_pipeline(StandardScaler(), LogisticRegression(
            class_weight='balanced', max_iter=400, tol=1e-4, random_state=SEED)),
        'RandomForest': RandomForestClassifier(n_estimators=40, max_depth=12,
            min_samples_leaf=20, max_features='sqrt', class_weight='balanced', n_jobs=4, random_state=SEED),
        'XGBoost': XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1,
            tree_method='hist', n_jobs=4, random_state=SEED, eval_metric='logloss'),
        'LightGBM': LGBMClassifier(n_estimators=100, num_leaves=31, max_depth=-1,
            learning_rate=0.1, n_jobs=4, random_state=SEED, deterministic=True,
            force_col_wise=True, max_delta_step=1.0, verbosity=-1),
    }

