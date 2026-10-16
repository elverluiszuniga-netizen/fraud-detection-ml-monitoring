"""Prepare Development only and execute fixed baselines, saving reviewable artifacts."""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, roc_curve, ConfusionMatrixDisplay
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fraud_detection.features import engineer_features, MODEL_COLUMNS
from fraud_detection.splitting import temporal_profile, choose_cutoff, temporal_masks, assert_training_steps
from fraud_detection.metrics import evaluate
from fraud_detection.modeling import build_models
from fraud_detection.paths import raw_csv

LOG = logging.getLogger(__name__)

def prepare(path: Path):
    """Chunk-filter before concatenation; Production never enters a model dataset."""
    chunks = []
    for chunk in pd.read_csv(path, chunksize=250_000):
        chunks.append(chunk.loc[chunk.step.between(1, 400)].copy())
    dev = pd.concat(chunks, ignore_index=True)
    profile = temporal_profile(dev)
    cutoff = choose_cutoff(profile)
    train, valid, production = temporal_masks(dev.step, cutoff)
    assert not production.any()
    assert_training_steps(dev.loc[train, 'step'], cutoff)
    LOG.info('Prespecified cutoff=%s; Train=%s frauds=%s; Validation=%s frauds=%s',
             cutoff, train.sum(), dev.loc[train, 'isFraud'].sum(), valid.sum(), dev.loc[valid, 'isFraud'].sum())
    return dev, profile, cutoff, train, valid

def plot_temporal(profile, figures, cutoff):
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax, col, label in zip(axes, ('transactions', 'frauds', 'fraud_rate'), ('Transactions', 'Frauds', 'Fraud prevalence')):
        ax.plot(profile.index, profile[col], linewidth=1)
        ax.axvline(cutoff, color='black', linestyle='--')
        ax.set_ylabel(label)
    axes[-1].set_xlabel('Development step')
    fig.tight_layout(); fig.savefig(figures / 'development_temporal.png', dpi=160); plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=None)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    started = time.perf_counter()
    artifacts, figures, processed = ROOT / 'artifacts', ROOT / 'reports/figures', ROOT / 'data/processed'
    for directory in (artifacts, figures, processed): directory.mkdir(parents=True, exist_ok=True)
    dev, profile, cutoff, train, valid = prepare(raw_csv(ROOT, args.input))
    profile.to_csv(artifacts / 'development_temporal_profile.csv')
    plot_temporal(profile, figures, cutoff)
    info = dict(cutoff=cutoff, seed=42, scoring='pre_execution', production_used=False,
                input_bytes=raw_csv(ROOT, args.input).stat().st_size, input=str(raw_csv(ROOT, args.input)), features=list(MODEL_COLUMNS),
                split={}, business_rule={})
    for name, mask in (('train', train), ('validation', valid)):
        data = dev.loc[mask]
        y = data.isFraud.to_numpy(dtype='uint8')
        x = engineer_features(data).to_numpy(dtype='float32')
        np.save(processed / f'{name}_X.npy', x); np.save(processed / f'{name}_y.npy', y)
        info['split'][name] = dict(rows=len(data), frauds=int(y.sum()), prevalence=float(y.mean()),
                                  step_min=int(data.step.min()), step_max=int(data.step.max()))
        flags = data.isFlaggedFraud == 1
        tp = int(data.loc[flags, 'isFraud'].sum())
        info['business_rule'][name] = dict(flagged=int(flags.sum()), true_fraud=tp,
                     precision=tp / int(flags.sum()) if flags.sum() else None,
                     recall=tp / int(y.sum()))
    # Calculate review candidates on Development to verify their implementation, not for model selection.
    reviewed = engineer_features(dev.iloc[:1000], include_review=True)
    info['review_feature_finite_check'] = bool(np.isfinite(reviewed.to_numpy()).all())
    info['preparation_seconds'] = time.perf_counter() - started
    (artifacts / 'phase2_run.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    del dev, reviewed
    if args.prepare_only: return
    xtrain = np.load(processed / 'train_X.npy', mmap_mode='r')
    ytrain = np.load(processed / 'train_y.npy')
    xvalid = np.load(processed / 'validation_X.npy', mmap_mode='r')
    yvalid = np.load(processed / 'validation_y.npy')
    prfig, prax = plt.subplots(figsize=(8, 6)); rocfig, rocax = plt.subplots(figsize=(8, 6))
    rows = []
    info['configurations'] = {}
    for name, model in build_models().items():
        LOG.info('Training %s on all %s Train observations', name, len(ytrain))
        info['configurations'][name] = {k: str(v) for k,v in model.get_params().items()}
        clock = time.perf_counter(); model.fit(xtrain, ytrain); fit_seconds = time.perf_counter() - clock
        clock = time.perf_counter(); scores = model.predict_proba(xvalid)[:, 1]; prediction_seconds = time.perf_counter() - clock
        row = dict(model=name, train_observations=len(ytrain), validation_observations=len(yvalid),
                   training_seconds=fit_seconds, prediction_seconds=prediction_seconds, **evaluate(yvalid, scores))
        rows.append(row)
        pd.DataFrame(rows).to_csv(artifacts / 'baseline_model_comparison.csv', index=False)
        LOG.info('%s AP=%.6f ROC=%.6f training=%.1fs', name, row['pr_auc'], row['roc_auc'], fit_seconds)
        precision, recall, _ = precision_recall_curve(yvalid, scores)
        fpr, tpr, _ = roc_curve(yvalid, scores)
        # Plot sampled curve points; metrics above use every observation.
        for ax, xx, yy in ((prax, recall, precision), (rocax, fpr, tpr)):
            idx = np.unique(np.linspace(0, len(xx)-1, min(5000, len(xx))).astype(int))
            ax.plot(xx[idx], yy[idx], label=name)
        fig, ax = plt.subplots(figsize=(5, 4))
        ConfusionMatrixDisplay.from_predictions(yvalid, scores >= 0.5, ax=ax, colorbar=False, values_format='d')
        ax.set_title(name + ' threshold 0.5'); fig.tight_layout()
        fig.savefig(figures / f'confusion_{name}.png', dpi=140); plt.close(fig)
        del model, scores
    prax.axhline(yvalid.mean(), linestyle='--', color='gray', label='Validation prevalence')
    for fig, ax, xlabel, ylabel, filename in ((prfig,prax,'Recall','Precision','precision_recall.png'),
                      (rocfig,rocax,'False positive rate','True positive rate','roc.png')):
        ax.set(xlabel=xlabel,ylabel=ylabel); ax.legend(); fig.tight_layout(); fig.savefig(figures / filename,dpi=160); plt.close(fig)
    comparison = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8,5)); ax.bar(comparison.model,comparison.pr_auc)
    ax.set_ylabel('Average Precision'); ax.tick_params(axis='x', rotation=20)
    fig.tight_layout(); fig.savefig(figures / 'average_precision_comparison.png',dpi=160); plt.close(fig)
    info['total_seconds'] = time.perf_counter() - started
    (artifacts / 'phase2_run.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    LOG.info('Finished in %.1f seconds', info['total_seconds'])

if __name__ == '__main__': main()
