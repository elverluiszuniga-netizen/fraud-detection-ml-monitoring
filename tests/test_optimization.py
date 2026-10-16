import sys
from pathlib import Path
from contextlib import contextmanager
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import optuna
import mlflow
from mlflow.tracking import MlflowClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fraud_detection.features import MODEL_COLUMNS
from fraud_detection.optimization import (DevelopmentData, SEARCH_SPACES, suggest_parameters, fit_and_evaluate,
    make_objective, select_best_trial, saturation_reached)
from fraud_detection.tracking import configure_tracking, log_evaluation, metric_names


def small_data():
    rng=np.random.default_rng(42)
    def block(low,high,n):
        x=rng.normal(size=(n,len(MODEL_COLUMNS))).astype('float32')
        x[:,0]=rng.integers(low,high+1,size=n)
        y=(x[:,1]>1).astype('uint8')
        return x,y
    tx,ty=block(1,320,200); vx,vy=block(321,400,100)
    return DevelopmentData(tx,ty,vx,vy)

class OptimizationTests(unittest.TestCase):
    def test_search_space_valid_and_depth_consistent(self):
        for algorithm in SEARCH_SPACES:
            study=optuna.create_study(sampler=optuna.samplers.TPESampler(seed=42,n_startup_trials=5,multivariate=False))
            for _ in range(10):
                trial=study.ask(); params=suggest_parameters(trial,algorithm)
                for name,(kind,low,high,_) in SEARCH_SPACES[algorithm].items():
                    self.assertLessEqual(low,params[name]); self.assertLessEqual(params[name],high)
                if algorithm=='LightGBM': self.assertLessEqual(params['num_leaves'],2**params['max_depth'])
                self.assertIn(params['scale_pos_weight'],(1.0,10.0,100.0)); study.tell(trial,0.5)
    def test_schema_and_production_guard(self):
        data=small_data(); data.validate()
        data.x_train[0,0]=401
        with self.assertRaises(ValueError): data.validate()
        data=small_data(); data.x_validation[0,0]=320
        with self.assertRaises(ValueError): data.validate()
        data=small_data(); data.feature_names=tuple(MODEL_COLUMNS[:-1])+('isFraud',)
        with self.assertRaises(ValueError): data.validate()
    def test_saturation_rule(self):
        self.assertFalse(saturation_reached([1.0]*9))
        self.assertTrue(saturation_reached([0.999995]*10))
        self.assertFalse(saturation_reached([0.9]*10))
        self.assertFalse(saturation_reached([0.99]*5+[1.0]*5))
    def test_best_trial_reproducible_tie(self):
        study=optuna.create_study(direction='maximize')
        for value in (0.9,0.99,0.99):
            trial=study.ask(); study.tell(trial,value)
        self.assertEqual(select_best_trial(study).number,1)
        self.assertEqual(select_best_trial(study).number,study.best_trial.number)
    def test_objective_returns_ap_and_records_link(self):
        data=small_data(); records=[]; seen=[]
        @contextmanager
        def recorder(number,params):
            seen.append(number)
            yield lambda metrics:'synthetic-run-id'
        with patch('fraud_detection.optimization.fit_and_evaluate',return_value=(object(),{'pr_auc':0.75},np.array([0.1]))):
            study=optuna.create_study(direction='maximize')
            study.optimize(make_objective('XGBoost',data,recorder,records),n_trials=1)
        self.assertEqual(study.best_value,0.75)
        self.assertEqual(records[0]['mlflow_run_id'],'synthetic-run-id')
        self.assertEqual(seen,[0])
    def test_fit_early_stopping_and_native_serialization(self):
        from xgboost import XGBClassifier
        from lightgbm import Booster
        data=small_data()
        for algorithm in SEARCH_SPACES:
            params={'n_estimators':8,'learning_rate':0.1,'max_depth':3,'scale_pos_weight':1.0}
            if algorithm=='LightGBM': params.update(num_leaves=7,min_child_samples=5)
            model,metrics,scores=fit_and_evaluate(algorithm,params,data,patience=3)
            self.assertTrue(0<=metrics['pr_auc']<=1)
            self.assertTrue(1<=metrics['effective_iterations']<=8)
            self.assertEqual(metrics['tp']+metrics['fp']+metrics['tn']+metrics['fn'],100)
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'model'
                if algorithm=='XGBoost':
                    path=path.with_suffix('.ubj'); model.save_model(path)
                    restored=XGBClassifier(); restored.load_model(path)
                    recovered=restored.predict_proba(data.x_validation)[:,1]
                else:
                    path=path.with_suffix('.txt'); model.booster_.save_model(str(path),num_iteration=model.best_iteration_)
                    restored=Booster(model_file=str(path)); recovered=restored.predict(data.x_validation)
                np.testing.assert_allclose(scores,recovered,atol=1e-7)
    def test_recorder_context_failure_propagates(self):
        @contextmanager
        def recorder(number,params):
            yield lambda metrics:'id'
        with patch('fraud_detection.optimization.fit_and_evaluate',side_effect=ValueError('failed fit')):
            objective=make_objective('XGBoost',small_data(),recorder,[])
            trial=optuna.create_study().ask()
            with self.assertRaises(ValueError): objective(trial)

class TrackingTests(unittest.TestCase):
    def tearDown(self):
        while mlflow.active_run(): mlflow.end_run()
    def test_metric_mapping(self):
        mapped=metric_names({'pr_auc':0.7,'recall_top_0.1pct':0.5,'precision_top_0.5pct':0.1})
        self.assertEqual(mapped['validation_pr_auc'],0.7)
        self.assertIn('recall_top_0_1_pct',mapped); self.assertIn('precision_top_0_5_pct',mapped)
    def test_local_nested_logging(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            uri,exp=configure_tracking(root,uri='sqlite:///'+(root/'test.db').as_posix())
            with mlflow.start_run(run_name='synthetic-parent') as parent:
                with mlflow.start_run(run_name='synthetic-trial',nested=True) as child:
                    log_evaluation({'max_depth':3},{'pr_auc':0.75,'roc_auc':0.8},'XGBoost','trial')
                    child_id=child.info.run_id; parent_id=parent.info.run_id
            client=MlflowClient(tracking_uri=uri); run=client.get_run(child_id)
            self.assertEqual(run.data.metrics['validation_pr_auc'],0.75)
            self.assertEqual(run.data.tags['mlflow.parentRunId'],parent_id)
            self.assertEqual(run.data.params['feature_count'],'14')
            artifacts={item.path for item in client.list_artifacts(child_id)}
            self.assertEqual(artifacts,{'metrics.json','feature_list.json'})
            # SQLite pooled connections lock temporary files on Windows.
            client._tracking_client.store.engine.dispose()
    def test_remote_explicit_and_no_embedded_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError): configure_tracking(Path(temp),uri='https://example.invalid/tracking')
            with self.assertRaises(ValueError): configure_tracking(Path(temp),uri='https://user:password@example.invalid',allow_remote=True)

class SanityProvenanceTests(unittest.TestCase):
    def test_exact_raw_reconstruction_and_production_filter(self):
        import importlib.util
        import pandas as pd
        from fraud_detection.features import engineer_features
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('sanity',root/'scripts/run_sanity_checks.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        raw=pd.DataFrame(dict(step=[1,2,321,322,401],type=['TRANSFER']*5,amount=[10.,5.,20.,3.,float('inf')],
            oldbalanceOrg=[10.,100.,20.,100.,1.],oldbalanceDest=[0.]*5,newbalanceOrig=[0.]*5,newbalanceDest=[0.]*5,
            nameOrig=['C1']*5,nameDest=['C2']*5,isFraud=[1,0,1,0,1],isFlaggedFraud=[0]*5))
        train=raw.iloc[:2]; valid=raw.iloc[2:4]
        data=DevelopmentData(engineer_features(train).to_numpy(dtype='float32'),train.isFraud.to_numpy(),
                             engineer_features(valid).to_numpy(dtype='float32'),valid.isFraud.to_numpy())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'small.csv'; raw.to_csv(path,index=False)
            evidence=module.verify_provenance(path,data)
            self.assertTrue(evidence['exact_reconstruction']); self.assertFalse(evidence['production_used'])
            data.x_train[0,1]=999
            with self.assertRaises(ValueError): module.verify_provenance(path,data)


class CandidateSelectionTests(unittest.TestCase):
    def test_multicriteria_tie_and_config_serialization(self):
        import importlib.util
        import json
        import pandas as pd
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('optimization_runner',root/'scripts/run_optimization.py')
        module=importlib.util.module_from_spec(spec)
        sys.path.insert(0,str(root/'scripts')); spec.loader.exec_module(module)
        rows=pd.DataFrame([
            dict(model='XGBoost',variant='tuned',pr_auc=0.99999,fn=1,fp=0,prediction_seconds=0.2,effective_iterations=40,training_seconds=10,**{'recall_top_0.1pct':1.0}),
            dict(model='LightGBM',variant='tuned',pr_auc=0.99998,fn=0,fp=2,prediction_seconds=0.3,effective_iterations=50,training_seconds=12,**{'recall_top_0.1pct':1.0})])
        chosen=module.select_provisional(rows)
        self.assertEqual(chosen['model'],'LightGBM')
        self.assertEqual(module.select_provisional(rows.sample(frac=1,random_state=42))['model'],'LightGBM')
        self.assertEqual(json.loads(json.dumps(chosen)),chosen)
        trial=optuna.create_study().ask()
        params=suggest_parameters(trial,'LightGBM')
        self.assertEqual(json.loads(json.dumps(params)),params)
