import sys
from pathlib import Path
import unittest
import tempfile
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fraud_detection.features import MODEL_COLUMNS
from fraud_detection.interpretability import (validate_validation,sample_explanations,select_local_cases,
    explain_model,global_importance,native_importance,local_contributions,load_champion)


def synthetic():
    rng=np.random.default_rng(42)
    x=np.zeros((120,len(MODEL_COLUMNS)),dtype='float32')
    x[:,0]=rng.integers(321,401,size=len(x));x[:,1]=rng.uniform(0,10,len(x))
    x[:,2]=rng.uniform(0,20,len(x));x[:,6]=(x[:,1]>7).astype(float)
    y=(x[:,1]>7).astype('uint8')
    return x,y

class InterpretabilityTests(unittest.TestCase):
    def test_reproducible_sample_all_frauds_and_unique(self):
        x,y=synthetic();first=sample_explanations(x,y,20,42);second=sample_explanations(x,y,20,42)
        np.testing.assert_array_equal(first,second)
        self.assertEqual(len(first),int(y.sum())+20)
        self.assertEqual(len(np.unique(first)),len(first))
        self.assertTrue(set(np.flatnonzero(y==1)).issubset(first))
        self.assertEqual(int((y[first]==0).sum()),20)
    def test_production_and_train_rejected(self):
        x,y=synthetic()
        for step in (320,401,float('nan'),321.5):
            changed=x.copy();changed[0,0]=step
            with self.assertRaises(ValueError):validate_validation(changed,y)
            with self.assertRaises(ValueError):sample_explanations(changed,y)
            with self.assertRaises(ValueError):select_local_cases(changed,y,np.ones(len(y)))
    def test_sample_budget_and_class_missing(self):
        x,y=synthetic()
        with self.assertRaises(ValueError):sample_explanations(x,y,0)
        with self.assertRaises(ValueError):sample_explanations(x,np.zeros(len(y)))
        self.assertEqual(len(sample_explanations(x,y,1000)),len(x))
    def test_local_cases_with_and_without_errors(self):
        x=np.zeros((6,len(MODEL_COLUMNS)),dtype='float32');x[:,0]=330;x[:,6]=[1,0,0,0,0,0]
        y=np.array([1,0,1,0,1,0]);scores=np.array([0.99,0.01,0.2,0.9,0.8,0.49])
        cases=select_local_cases(x,y,scores)
        self.assertEqual(cases,{'A_high_score_TP':0,'B_low_score_TN':1,'C_false_negative':2,
            'D_false_positive':3,'E_non_rule_TP':4,'F_nearest_reference_threshold':5})
        np.testing.assert_equal(cases,select_local_cases(x,y,scores))
        cases=select_local_cases(x,y,np.where(y==1,0.9,0.1))
        self.assertIsNone(cases['C_false_negative']);self.assertIsNone(cases['D_false_positive'])
    def test_native_shap_additivity_structure_and_best_round_limit(self):
        x,y=synthetic();tx=x.copy();tx[:,0]=100
        model=XGBClassifier(n_estimators=20,max_depth=2,learning_rate=0.2,n_jobs=1,
                            eval_metric='aucpr',early_stopping_rounds=3,random_state=42)
        model.fit(tx,y,eval_set=[(x,y)],verbose=False)
        explanation,errors=explain_model(model,x[:12])
        self.assertEqual(explanation.values.shape,(12,14));self.assertEqual(explanation.feature_names,list(MODEL_COLUMNS))
        self.assertLess(errors['max_probability_error'],2e-6)
        # Stored trees extend past best iteration: exact SHAP must still explain sklearn predictions.
        self.assertGreater(model.get_booster().num_boosted_rounds(),model.best_iteration+1)
        importance=global_importance(explanation,y[:12],float(y.mean()))
        self.assertEqual(set(importance.feature),set(MODEL_COLUMNS))
        self.assertTrue((importance.mean_abs_shap>=0).all())
        native=native_importance(model);self.assertEqual(len(native),14)
        rows=local_contributions(explanation[0],'test',0,int(y[0]),float(model.predict_proba(x[:1])[0,1]))
        self.assertEqual(len(rows),14);self.assertEqual(rows[0]['absolute_rank'],1)
        self.assertIn('base_log_odds',rows[0]);self.assertIn('shap_log_odds',rows[0])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model.ubj';model.save_model(path)
            loaded=load_champion(path)
            again,_=explain_model(loaded,x[:12]);np.testing.assert_allclose(explanation.values,again.values)
    def test_explanation_rejects_production(self):
        x,y=synthetic();model=XGBClassifier(n_estimators=2,n_jobs=1)
        model.fit(x,y);x[0,0]=401
        with self.assertRaises(ValueError):explain_model(model,x[:1])

class MemmapExplanationTests(unittest.TestCase):
    def test_single_row_shap_metadata_from_persisted_matrix(self):
        x,y=synthetic();model=XGBClassifier(n_estimators=6,max_depth=2,n_jobs=1,
                                          eval_metric='aucpr',early_stopping_rounds=2)
        model.fit(x,y,eval_set=[(x,y)],verbose=False)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'x.npy';np.save(path,x)
            persisted=np.load(path,mmap_mode='r')
            explanation,_=explain_model(model,persisted[:1].copy())
            self.assertEqual(explanation[0].data.shape,(14,))
            self.assertEqual(len(local_contributions(explanation[0],'test',0,int(y[0]),0.2)),14)
            del persisted
