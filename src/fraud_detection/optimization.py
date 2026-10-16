"""Finite-budget seeded Optuna search and validated Development-only objectives."""
from dataclasses import dataclass
import time
import numpy as np
import optuna
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from xgboost import XGBClassifier
from .features import MODEL_COLUMNS
from .metrics import evaluate

SEED = 42
SEARCH_SPACES = {
    'XGBoost': {
        'n_estimators': ('int', 80, 200, 'Upper bound on boosting rounds; early stopping may use fewer'),
        'max_depth': ('int', 3, 7, 'Bound tree complexity'),
        'learning_rate': ('log', 0.03, 0.15, 'Moderate shrinkage'),
        'min_child_weight': ('log', 0.5, 10.0, 'Leaf Hessian regularization'),
        'subsample': ('float', 0.8, 1.0, 'Controlled row sampling inside Train'),
        'colsample_bytree': ('float', 0.8, 1.0, 'Controlled feature sampling'),
        'reg_alpha': ('log', 1e-4, 1.0, 'L1 regularization'),
        'reg_lambda': ('log', 0.5, 5.0, 'L2 regularization'),
        'gamma': ('float', 0.0, 1.0, 'Split gain requirement'),
    },
    'LightGBM': {
        'n_estimators': ('int', 80, 200, 'Upper bound on boosting rounds'),
        'learning_rate': ('log', 0.03, 0.15, 'Moderate shrinkage'),
        'num_leaves': ('int', 15, 31, 'Bound leaf count; capped by selected depth'),
        'max_depth': ('int', 4, 7, 'Bound tree complexity'),
        'min_child_samples': ('int', 20, 100, 'Minimum leaf observations'),
        'subsample': ('float', 0.8, 1.0, 'Train bagging; subsample_freq fixed to 1'),
        'colsample_bytree': ('float', 0.8, 1.0, 'Feature sampling'),
        'reg_alpha': ('log', 1e-4, 1.0, 'L1 regularization'),
        'reg_lambda': ('log', 0.5, 5.0, 'L2 regularization'),
    },
}
WEIGHTS = (1.0, 10.0, 100.0)  # Controlled alternatives, not automatic full inverse prevalence.

@dataclass
class DevelopmentData:
    x_train: np.ndarray
    y_train: np.ndarray
    x_validation: np.ndarray
    y_validation: np.ndarray
    feature_names: tuple = MODEL_COLUMNS

    def validate(self) -> None:
        if tuple(self.feature_names) != MODEL_COLUMNS:
            raise ValueError('Unexpected feature schema')
        for x, y, low, high in ((self.x_train, self.y_train, 1, 320),
                               (self.x_validation, self.y_validation, 321, 400)):
            if x.ndim != 2 or x.shape != (len(y), len(MODEL_COLUMNS)) or len(y) == 0:
                raise ValueError('Invalid matrix shape')
            if not np.isfinite(x).all() or not np.isin(y, (0, 1)).all() or len(np.unique(y)) != 2:
                raise ValueError('Invalid values or single-class data')
            steps = x[:, 0]
            if not ((steps >= low) & (steps <= high) & (steps % 1 == 0)).all():
                raise ValueError('Temporal boundary breach, including Production')


def suggest_parameters(trial, algorithm: str) -> dict:
    if algorithm not in SEARCH_SPACES:
        raise ValueError('Unsupported algorithm')
    params = {}
    for name, (kind, low, high, _) in SEARCH_SPACES[algorithm].items():
        if name == 'num_leaves':
            # max_depth suggested first without creating an inconsistent distribution.
            depth = trial.suggest_int('max_depth', 4, 7)
            high = min(high, 2 ** depth)
        if name == 'max_depth' and algorithm == 'LightGBM':
            params[name] = depth
        elif kind == 'int':
            params[name] = trial.suggest_int(name, low, high)
        else:
            params[name] = trial.suggest_float(name, low, high, log=kind == 'log')
    params['scale_pos_weight'] = trial.suggest_categorical('scale_pos_weight', list(WEIGHTS))
    return params


def build_candidate(algorithm: str, parameters: dict, patience: int = 20, seed: int = SEED):
    common = dict(random_state=seed, n_jobs=4, **parameters)
    if algorithm == 'XGBoost':
        return XGBClassifier(**common, tree_method='hist', objective='binary:logistic',
            eval_metric='aucpr', early_stopping_rounds=patience)
    if algorithm == 'LightGBM':
        return LGBMClassifier(**common, objective='binary', metric='average_precision',
            deterministic=True, force_col_wise=True, max_delta_step=1.0,
            subsample_freq=1, verbosity=-1)
    raise ValueError('Unsupported algorithm')


def fit_and_evaluate(algorithm: str, parameters: dict, data: DevelopmentData, patience: int = 20, seed: int = SEED):
    """Fit on Train only; early stopping and exact final AP use Development Validation."""
    data.validate()
    model = build_candidate(algorithm, parameters, patience, seed)
    start = time.perf_counter()
    kwargs = dict(eval_set=[(data.x_validation, data.y_validation)])
    if algorithm == 'XGBoost':
        kwargs['verbose'] = False
    else:
        kwargs = dict(eval_X=data.x_validation, eval_y=data.y_validation)
        kwargs['callbacks'] = [early_stopping(patience, first_metric_only=True, verbose=False), log_evaluation(0)]
    model.fit(data.x_train, data.y_train, **kwargs)
    training_seconds = time.perf_counter() - start
    start = time.perf_counter()
    scores = model.predict_proba(data.x_validation)[:, 1]
    prediction_seconds = time.perf_counter() - start
    metrics = dict(evaluate(data.y_validation, scores), training_seconds=training_seconds,
                   prediction_seconds=prediction_seconds)
    iterations = int(model.best_iteration + 1) if algorithm == 'XGBoost' else int(model.best_iteration_)
    metrics['effective_iterations'] = iterations
    return model, metrics, scores


def select_best_trial(study):
    """Maximum exact AP, deterministic earliest trial for an exact score tie."""
    trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None]
    if not trials:
        raise ValueError('No completed trials')
    return min(trials, key=lambda t: (-t.value, t.number))


def saturation_reached(values, minimum_trials=10, window=5, floor=0.9999, tolerance=1e-5) -> bool:
    """Predeclared practical plateau; makes no statistical equivalence claim."""
    if len(values) < max(minimum_trials, window + 1):
        return False
    before = max(values[:-window]); after = max(values)
    return after >= floor and after - before <= tolerance


def make_objective(algorithm, data, recorder, results):
    data.validate()
    def objective(trial):
        parameters = suggest_parameters(trial, algorithm)
        # Open a tracked run before fit; exceptions leave a failed MLflow run.
        with recorder(trial.number, parameters) as record:
            model, metrics, _ = fit_and_evaluate(algorithm, parameters, data)
            run_id = record(metrics)
            trial.set_user_attr('mlflow_run_id', run_id)
            trial.set_user_attr('metrics', metrics)
            results.append(dict(algorithm=algorithm, trial=trial.number, mlflow_run_id=run_id,
                                parameters=parameters, **metrics))
            del model
            return float(metrics['pr_auc'])
    return objective

