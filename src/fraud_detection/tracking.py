"""Explicit MLflow logging without autologging, datasets or credentials."""
import os
from pathlib import Path
from urllib.parse import urlsplit
import mlflow
from mlflow.tracking import MlflowClient
from .features import MODEL_COLUMNS

EXPERIMENT_NAME = 'fraud-detection-hyperparameter-optimization'

def configure_tracking(root: Path, uri: str | None = None, allow_remote: bool = False):
    requested = uri or os.environ.get('MLFLOW_TRACKING_URI')
    local_uri = 'sqlite:///' + (root / 'mlruns/mlflow.db').resolve().as_posix()
    selected = requested or local_uri
    remote = selected.startswith(('http://', 'https://'))
    if remote and not allow_remote:
        raise ValueError('Remote tracking requires explicit --allow-remote-tracking')
    if remote and (urlsplit(selected).username or urlsplit(selected).password):
        raise ValueError('Embedded credentials forbidden; use environment variables')
    if not remote and not selected.startswith('sqlite:///'):
        raise ValueError('Use local SQLite or an explicitly enabled HTTP tracking server')
    (root / 'mlruns').mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(selected)
    client = MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        kwargs = {} if remote else {'artifact_location': (root / 'mlartifacts').resolve().as_uri()}
        experiment_id = client.create_experiment(EXPERIMENT_NAME, **kwargs)
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    return selected, experiment_id


def metric_names(metrics: dict) -> dict:
    mapped = {}
    for key, value in metrics.items():
        key = {'pr_auc': 'validation_pr_auc', 'roc_auc': 'validation_roc_auc'}.get(key, key)
        key = key.replace('0.1pct', '0_1_pct').replace('0.5pct', '0_5_pct').replace('1pct', '1_pct')
        mapped[key] = float(value)
    return mapped


def log_evaluation(parameters: dict, metrics: dict, algorithm: str, role: str, **extra):
    mlflow.set_tags({'algorithm': algorithm, 'role': role, 'phase': '3', 'production_used': 'false'})
    mlflow.log_params(dict(algorithm=algorithm, train_step_range='1-320', validation_step_range='321-400',
                           feature_count=len(MODEL_COLUMNS), random_state=42, threshold=0.5,
                           **parameters, **extra))
    mlflow.log_metrics(metric_names(metrics))
    mlflow.log_dict(metrics, 'metrics.json')
    mlflow.log_dict({'ordered_features': list(MODEL_COLUMNS)}, 'feature_list.json')
