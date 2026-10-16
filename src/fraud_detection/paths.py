"""Portable input resolution without rewriting historical evidence."""
import os
from pathlib import Path

DATASET_NAME = 'PS_20174392719_1491204439457_log.csv'


def raw_csv(root: Path, configured: str | Path | None = None) -> Path:
    """Explicit CLI/env paths fail closed; otherwise prefer data/raw then legacy root."""
    root = Path(root).resolve()
    selected = configured if configured is not None else os.environ.get('FRAUD_DATA_PATH')
    if selected:
        path = Path(selected).expanduser()
        path = path if path.is_absolute() else root / path
        candidates = [path]
    else:
        candidates = [root / 'data/raw' / DATASET_NAME, root / DATASET_NAME]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError('PaySim CSV missing; see data/README.md or set FRAUD_DATA_PATH')


def champion_path(root: Path) -> Path:
    """Prefer the immutable delivery copy, with the original local artifact as fallback."""
    root = Path(root).resolve()
    for relative in ('models/XGBoost.ubj', 'data/processed/phase3_models/XGBoost.ubj'):
        path = root / relative
        if path.is_file():
            return path
    raise FileNotFoundError('Frozen XGBoost missing; see docs/model_recovery.md')


def local_tracking_uri(root: Path) -> str:
    """Historical SQLite URIs are provenance, not portable configuration."""
    return 'sqlite:///' + (Path(root).resolve() / 'mlruns/mlflow.db').as_posix()
