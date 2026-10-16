import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from fraud_detection.features import engineer_features, MODEL_COLUMNS, POST_COLUMNS
from fraud_detection.splitting import temporal_masks, choose_cutoff, temporal_profile, assert_training_steps
from fraud_detection.metrics import top_k_metrics, evaluate


def sample():
    return pd.DataFrame(dict(step=[1,320,321,400,401],type=['TRANSFER','CASH_OUT','PAYMENT','CASH_IN','NEW'],
       amount=[10.,10.,0.,25.,5.],oldbalanceOrg=[10.,0.,0.,100.,5.],newbalanceOrig=[0.,0.,0.,125.,0.],
       oldbalanceDest=[0.,0.,0.,10.,0.],newbalanceDest=[10.,10.,0.,0.,5.],
       nameOrig=['C1']*5,nameDest=['C2','C3','M1','C4','C5'],isFraud=[1,0,1,0,1],isFlaggedFraud=[0]*5))

class FeaturesTests(unittest.TestCase):
    def test_schema_finite_and_zero(self):
        x=engineer_features(sample())
        self.assertEqual(tuple(x.columns), MODEL_COLUMNS)
        self.assertTrue(np.isfinite(x.to_numpy()).all())
        self.assertEqual(x.loc[1,'amount_to_oldbalanceOrg'],0)
        self.assertEqual(x.loc[1,'orig_balance_zero'],1)
        self.assertEqual(x.loc[2,'orig_balance_emptied'],0)
        self.assertEqual(x.loc[0,'orig_balance_emptied'],1)
        self.assertEqual(x.loc[2,'dest_is_merchant'],1)
        self.assertEqual(x.loc[4,'type_UNKNOWN'],1)
    def test_no_target_identity_flag_or_post_event_leakage(self):
        a=sample(); b=a.copy()
        b['isFraud']=1-b.isFraud; b['isFlaggedFraud']=1
        b['nameOrig']='OTHER'; b['nameDest']=['C999','C998','M999','C997','C996']
        b['newbalanceOrig']=999999.; b['newbalanceDest']=999999.
        pd.testing.assert_frame_equal(engineer_features(a),engineer_features(b))
        self.assertFalse(set(POST_COLUMNS) & set(MODEL_COLUMNS))
    def test_review_sign_and_residual(self):
        x=engineer_features(sample(),include_review=True)
        self.assertEqual(x.loc[0,'orig_balance_diff'],10)
        self.assertEqual(x.loc[0,'dest_balance_diff'],10)
        self.assertEqual(x.loc[0,'orig_balance_error'],0)
        self.assertEqual(x.loc[0,'dest_balance_error'],0)
    def test_invalid_and_row_local(self):
        a=sample(); b=a.copy(); b.loc[0,'amount']=float('inf')
        with self.assertRaises(ValueError): engineer_features(b)
        pd.testing.assert_frame_equal(engineer_features(a.iloc[:2]),engineer_features(a).iloc[:2])
    def test_tolerance(self):
        a=sample(); a.loc[0,'amount']=9.995
        self.assertEqual(engineer_features(a).loc[0,'orig_balance_emptied'],1)
        a.loc[0,'amount']=9.98
        self.assertEqual(engineer_features(a).loc[0,'orig_balance_emptied'],0)

class SplittingTests(unittest.TestCase):
    def test_exhaustive_nonoverlap(self):
        train,valid,prod=temporal_masks(sample().step)
        self.assertEqual(train.tolist(),[True,True,False,False,False])
        self.assertEqual(valid.tolist(),[False,False,True,True,False])
        self.assertEqual(prod.tolist(),[False,False,False,False,True])
        self.assertTrue(((train.astype(int)+valid.astype(int)+prod.astype(int))==1).all())
    def test_training_guard(self):
        assert_training_steps(pd.Series([1,320]),320)
        for s in ([1,401],[321],[0],[1.5],[]):
            with self.assertRaises(ValueError): assert_training_steps(pd.Series(s,dtype=float),320)
    def test_profile_excludes_production_and_count_rule(self):
        p=temporal_profile(sample()); self.assertNotIn(401,p.index)
        self.assertEqual(choose_cutoff(p,minimum_frauds=1),320)
        with self.assertRaises(ValueError): choose_cutoff(p)
    def test_invalid_steps(self):
        for s in ([0],[1.5],[np.nan],[np.inf]):
            with self.assertRaises(ValueError): temporal_masks(pd.Series(s))

class MetricsTests(unittest.TestCase):
    def test_known_ranking(self):
        m=top_k_metrics([0,1,0,1],[0.1,0.9,0.2,0.8],(0.25,0.5))
        self.assertEqual(m['precision_top_25pct'],1)
        self.assertEqual(m['recall_top_25pct'],0.5)
        self.assertEqual(m['recall_top_50pct'],1)
    def test_ties_rounding_no_fraud(self):
        m=top_k_metrics([1,0,0],[0.5]*3,(0.1,))
        self.assertEqual(m['k_10pct'],1); self.assertEqual(m['recall_top_10pct'],1)
        self.assertEqual(top_k_metrics([0,0],[0.2,0.1],(0.5,))['recall_top_50pct'],0)
    def test_invalid(self):
        for y,s in (([],[]),([1],[np.nan]),([2],[0.2]),([1],[0.2,0.3])):
            with self.assertRaises(ValueError): top_k_metrics(y,s)
    def test_confusion_and_f2(self):
        m=evaluate([1,1,0,0],[0.9,0.4,0.7,0.1])
        self.assertEqual((m['tp'],m['fp'],m['tn'],m['fn']),(1,1,1,1))
        self.assertEqual(m['f2_05'],0.5)

if __name__=='__main__': unittest.main()

class PreparationTests(unittest.TestCase):
    def test_stream_filter_never_features_production(self):
        import importlib.util
        import tempfile
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('baselines',root/'scripts/run_baselines.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        frame=pd.concat([sample().iloc[[0,2]]]*100,ignore_index=True)
        production=sample().iloc[[4]].copy(); production['amount']=np.inf
        frame=pd.concat([frame,production],ignore_index=True)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'tiny.csv'; frame.to_csv(path,index=False)
            dev,profile,cut,train,valid=module.prepare(path)
            self.assertEqual(len(dev),200)
            self.assertEqual(cut,320)
            self.assertNotIn(401,profile.index)
            self.assertTrue(np.isfinite(engineer_features(dev).to_numpy()).all())
            self.assertEqual((train.sum(),valid.sum()),(100,100))
