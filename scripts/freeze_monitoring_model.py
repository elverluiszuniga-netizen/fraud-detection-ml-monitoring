"""Freeze identity and monitoring design before any Production evaluation."""
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBClassifier
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fraud_detection.features import MODEL_COLUMNS
from fraud_detection.paths import champion_path
from fraud_detection.monitoring import sha256,verify_frozen,validate_period,reference_edges
from fraud_detection.metrics import evaluate

def main():
    phase3=json.loads((ROOT/'artifacts/phase3_run.json').read_text(encoding='utf-8'))
    phase4=json.loads((ROOT/'artifacts/interpretability_summary.json').read_text(encoding='utf-8'))
    model_path=champion_path(ROOT)
    verify_frozen(model_path,phase4['model_sha256'])
    model=XGBClassifier();model.load_model(model_path)
    xval=np.load(ROOT/'data/processed/validation_X.npy',mmap_mode='r');yval=np.load(ROOT/'data/processed/validation_y.npy')
    validate_period(xval,False)
    if not ((xval[:,0]>=321)&(xval[:,0]<=400)).all() or model.n_features_in_!=len(MODEL_COLUMNS):raise ValueError('Validation/schema mismatch')
    metrics=evaluate(yval,model.predict_proba(xval)[:,1])
    expected=pd.read_csv(ROOT/'artifacts/tuned_model_comparison.csv').query("model=='XGBoost' and variant=='tuned'").iloc[0]
    for key,value in metrics.items():
        if not np.isclose(value,expected[key],rtol=0,atol=1e-10):raise ValueError('Metric mismatch '+key)
    xtrain=np.load(ROOT/'data/processed/train_X.npy',mmap_mode='r');validate_period(xtrain,False)
    reference=np.vstack([xtrain,xval])
    bins={name:reference_edges(reference[:,j]).tolist() for j,name in enumerate(MODEL_COLUMNS[:5])}
    freeze=dict(model_path=model_path.relative_to(ROOT).as_posix(),model_sha256=sha256(model_path),
        source_run_id=phase3['algorithms']['XGBoost']['best_run_id'],feature_names=list(MODEL_COLUMNS),
        feature_source_sha256=sha256(ROOT/'src/fraud_detection/features.py'),
        recorded_training_parameters=phase3['algorithms']['XGBoost']['best_parameters'],
        hyperparameter_provenance='Recorded Phase3 parameters authenticated by unchanged model hash and source run; native loaded artifact need not preserve constructor training defaults.',
        native_configuration=json.loads(model.get_booster().save_config()),effective_iterations=model.best_iteration+1,
        threshold=0.5,threshold_status='Reference evaluation threshold, not final production threshold',top_fractions=[0.001,0.005,0.01],
        validation_reproduction=metrics,window_width_hours=72,window_anchor_step=401,minimum_positive_warning=30,
        practical_thresholds=dict(KS_D=0.10,total_variation=0.05,PSI_review=0.20,Holm_alpha=0.05),
        step_role='Structural time separation; report but exclude step from drift alert count',
        reference_steps=[1,400],reference_quantile_bins=bins,evidently_sample_rows=25000,random_state=42,
        production_not_yet_analyzed=True,previous_phase_hashes={name:sha256(ROOT/name) for name in [
        'PHASE_2_MODELING_REPORT.md','PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md','PHASE_4_INTERPRETABILITY_REPORT.md',
        'artifacts/phase3_run.json','src/fraud_detection/features.py','src/fraud_detection/modeling.py','src/fraud_detection/optimization.py',
        'notebooks/02_ml_training.ipynb','notebooks/03_hyperparameter_optimization.ipynb','notebooks/04_interpretability.ipynb']})
    # +/- infinity used only as histogram boundaries; serialize them as strings for strict JSON.
    freeze['reference_quantile_bins']={name:[str(v) if np.isinf(v) else v for v in values] for name,values in bins.items()}
    (ROOT/'artifacts/production_monitoring_freeze.json').write_text(json.dumps(freeze,indent=2,allow_nan=False),encoding='utf-8')
    print('Frozen hash',freeze['model_sha256'],'effective rounds',freeze['effective_iterations'],'Validation AP',metrics['pr_auc'])

if __name__=='__main__':main()
