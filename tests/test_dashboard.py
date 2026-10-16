import sys,json,shutil,tempfile,unittest,ast
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.data_access import (load_bundle,validate_bundle,filtered_metrics,filter_step_rows,report_paths,
    count_metrics,ArtifactError,CSV_FILES,JSON_FILES,REPORT_FILES,safe_file)

class DashboardTests(unittest.TestCase):
    def setUp(self):self.bundle=load_bundle(ROOT)
    def fixture_copy(self,temp):
        root=Path(temp);(root/'artifacts').mkdir()
        for name in list(CSV_FILES.values())+list(JSON_FILES.values()):shutil.copy2(ROOT/'artifacts'/name,root/'artifacts'/name)
        return root
    def test_real_artifact_consistency(self):
        b=self.bundle;p=b['comparison'].query("period=='Production'").iloc[0]
        self.assertEqual(p.observations,b['summary']['production']['rows'])
        self.assertEqual(p.fn,b['summary']['production']['metrics']['fn'])
        self.assertEqual(b['drift'].drift_detected.sum(),b['summary']['drift_features'])
    def test_missing_file_no_invented_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root=self.fixture_copy(temp);(root/'artifacts'/CSV_FILES['scores']).unlink()
            with self.assertRaisesRegex(ArtifactError,'monitoring_scores'):load_bundle(root)
    def test_corrupted_kpi_rejected(self):
        b=load_bundle(ROOT);b['comparison'].loc[b['comparison'].period=='Production','recall_05']=0.5
        with self.assertRaises(ArtifactError):validate_bundle(b)
        b=load_bundle(ROOT);b['summary']['production']['metrics']['pr_auc']=0.5
        with self.assertRaises(ArtifactError):validate_bundle(b)
    def test_window_counts_and_metrics_corruption(self):
        b=load_bundle(ROOT);b['windows'].loc[0,'precision_05']=0.4
        with self.assertRaises(ArtifactError):validate_bundle(b)
        b=load_bundle(ROOT);b['windows'].loc[0,'tp']+=1
        with self.assertRaises(ArtifactError):validate_bundle(b)
    def test_global_and_single_window_exact_rank_metrics(self):
        b=self.bundle;m=filtered_metrics(b,b['windows'].window.tolist())
        production=b['comparison'].query("period=='Production'").iloc[0]
        self.assertAlmostEqual(m['pr_auc'],production.pr_auc)
        self.assertEqual(m['fn'],production.fn)
        one=filtered_metrics(b,[0]);row=b['windows'].loc[b['windows'].window==0].iloc[0]
        self.assertAlmostEqual(one['pr_auc'],row.pr_auc);self.assertEqual(one['observations'],row.observations)
    def test_multi_window_no_ap_averaging_and_valid_derived_metrics(self):
        b=self.bundle;subset=b['windows'].query('window in [0,2]');m=filtered_metrics(b,[0,2])
        self.assertTrue(np.isnan(m['pr_auc']));self.assertTrue(np.isnan(m['roc_auc']))
        self.assertTrue(all(np.isnan(row['recall']) for row in m['top_k']))
        self.assertEqual(m['observations'],subset.observations.sum())
        self.assertAlmostEqual(m['recall_05'],subset.tp.sum()/(subset.tp.sum()+subset.fn.sum()))
        self.assertEqual(m['fn'],subset.fn.sum())
        for top in m['top_k']:self.assertLessEqual(top['theoretical_recall'],1)
    def test_invalid_empty_selection(self):
        for selection in ([],[999]):
            with self.assertRaises(ArtifactError):filtered_metrics(self.bundle,selection)
    def test_noncontiguous_temporal_filter(self):
        b=self.bundle;subset=filter_step_rows(b['steps'],b['windows'],[0,2])
        self.assertFalse(subset.step.between(473,544).any())
        self.assertEqual(subset.transactions.sum(),filtered_metrics(b,[0,2])['observations'])
    def test_reports_exist_and_traversal_rejected(self):
        paths=report_paths(ROOT);self.assertEqual(len(paths),len(REPORT_FILES))
        self.assertTrue(all(path.is_file() and path.suffix=='.html' for path in paths.values()))
        with self.assertRaises(ArtifactError):safe_file(ROOT,'../outside.html')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ArtifactError):report_paths(Path(temp))
    def test_undefined_derived_metrics(self):
        m=count_metrics(dict(observations=3,frauds=0,tp=0,fp=0,tn=3,fn=0))
        self.assertTrue(np.isnan(m['precision_05']));self.assertTrue(np.isnan(m['recall_05']))
        with self.assertRaises(ArtifactError):count_metrics(dict(observations=3,frauds=1,tp=0,fp=0,tn=3,fn=1))
    def test_read_only_no_scoring_or_raw_imports(self):
        for relative in ('app/data_access.py','app/main.py'):
            source=(ROOT/relative).read_text(encoding='utf-8-sig');tree=ast.parse(source)
            modules=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):modules.extend(alias.name.split('.')[0] for alias in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:modules.append(node.module.split('.')[0])
            self.assertFalse({'xgboost','mlflow','optuna','evidently','shap'}&set(modules))
            self.assertNotIn('PS_20174392719_1491204439457_log.csv',source)
