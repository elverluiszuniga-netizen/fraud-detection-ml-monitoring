import sys,tempfile,unittest
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fraud_detection.features import MODEL_COLUMNS,engineer_features
from fraud_detection.monitoring import supported_metrics,window_labels,reference_edges,psi_from_edges,categorical_distance,holm_adjust,drift_table,validate_period,verify_frozen,sha256,write_html

class MonitoringTests(unittest.TestCase):
    def test_boundary_and_window_anchor(self):
        x=np.zeros((2,14));x[:,0]=[400,401]
        with self.assertRaises(ValueError):validate_period(x,True)
        with self.assertRaises(ValueError):validate_period(x,False)
        np.testing.assert_array_equal(window_labels(np.array([401,472,473,544,545,743])),[0,0,1,1,2,4])
        for steps in ([400],[401.5],[np.nan]):
            with self.assertRaises(ValueError):window_labels(np.array(steps))
    def test_no_and_few_positives(self):
        m=supported_metrics([0,0,0],[0.1,0.2,0.8])
        self.assertTrue(np.isnan(m['pr_auc']));self.assertTrue(np.isnan(m['roc_auc']))
        self.assertTrue(np.isnan(m['recall_05']));self.assertTrue(np.isnan(m['recall_top_0.1pct']))
        self.assertEqual(m['fp'],1);self.assertEqual(m['precision_05'],0)
        m=supported_metrics([0,1],[0.1,0.9]);self.assertEqual(m['support_warning'],'few_positives_below_30')
        self.assertEqual(m['pr_auc'],1)
        m=supported_metrics([1,1],[0.8,0.9]);self.assertTrue(np.isnan(m['roc_auc']));self.assertEqual(m['support_warning'],'no_negative_labels')
    def test_invalid_scores_and_no_alerts(self):
        for scores in ([np.nan,0.1],[-1,0.2],[1.1,0.2]):
            with self.assertRaises(ValueError):supported_metrics([0,1],scores)
        self.assertTrue(np.isnan(supported_metrics([0,1],[0.1,0.2])['precision_05']))
    def test_drift_zero_identity_and_large_change(self):
        a=np.linspace(0,1,100);edges=reference_edges(a)
        self.assertEqual(psi_from_edges(a,a,edges),0)
        self.assertGreater(psi_from_edges(a,a+5,edges),0.2)
        self.assertEqual(categorical_distance(np.array(['A','B']),np.array(['A','B']))['total_variation'],0)
        self.assertEqual(categorical_distance(np.array(['A','A']),np.array(['B','B']))['total_variation'],1)
        np.testing.assert_allclose(holm_adjust([0.01,0.03,0.8]),[0.03,0.06,0.8])
    def test_primary_effect_count_excludes_step(self):
        a=np.zeros((100,14));b=a.copy();a[:,0]=np.arange(1,101);b[:,0]=np.arange(401,501)
        bins={name:reference_edges(a[:,j]).tolist() for j,name in enumerate(MODEL_COLUMNS[:5])}
        result=drift_table(a,b,bins)
        self.assertTrue(result.loc[result.feature=='step','practically_material'].iloc[0])
        self.assertEqual(result.drift_detected.sum(),0)
        b[:,6]=1;result=drift_table(a,b,bins)
        self.assertTrue(result.loc[result.feature=='orig_balance_emptied','drift_detected'].iloc[0])
    def test_frozen_hash_and_offline_html(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'model';path.write_bytes(b'frozen');digest=sha256(path);verify_frozen(path,digest)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_frozen(path,digest)
            report=Path(temp)/'report.html';write_html(report,'<test>',[('Support','Undefined accepted',pd.DataFrame({'AP':[np.nan]}))])
            text=report.read_text(encoding='utf-8');self.assertIn('undefined',text);self.assertIn('&lt;test&gt;',text)
            self.assertNotIn('<script src=',text)
    def test_stream_production_filter_and_unknown_category(self):
        import importlib.util
        root=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(root/'scripts'))
        spec=importlib.util.spec_from_file_location('monitoring_runner',root/'scripts/run_monitoring.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        rows=pd.DataFrame(dict(step=[400,401],type=['TRANSFER','NEW'],amount=[10.,20.],oldbalanceOrg=[10.,30.],oldbalanceDest=[0.,0.],nameDest=['C1','M1'],isFraud=[1,0]))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'tiny.csv';rows.to_csv(path,index=False)
            x,y=module.load_production(path)
            self.assertEqual(x.shape,(1,14));self.assertEqual(x[0,0],401);self.assertEqual(x[0,-1],1)
            self.assertEqual(module.type_labels(x)[0],'UNKNOWN');self.assertEqual(y.tolist(),[0])

class WilsonSupportTests(unittest.TestCase):
    def test_empty_and_extreme_support(self):
        from fraud_detection.monitoring import wilson_interval
        self.assertTrue(np.isnan(wilson_interval(0,0)[0]))
        low,high=wilson_interval(0,100);self.assertEqual(low,0);self.assertGreater(high,0)
        low,high=wilson_interval(100,100);self.assertLess(low,1);self.assertAlmostEqual(high,1)
