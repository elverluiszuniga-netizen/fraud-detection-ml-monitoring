"""Relocation must preserve identity and never silently ignore explicit inputs."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fraud_detection.paths import raw_csv, champion_path, local_tracking_uri, DATASET_NAME


class PortablePathsTests(unittest.TestCase):
    def test_relocated_raw_and_explicit_override_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict('os.environ', {}, clear=True):
            root = Path(temp); (root / 'data/raw').mkdir(parents=True)
            path = root / 'data/raw' / DATASET_NAME; path.write_text('fixture')
            self.assertEqual(raw_csv(root), path.resolve())
            with self.assertRaises(FileNotFoundError):
                raw_csv(root, 'missing.csv')
            with patch.dict('os.environ', {'FRAUD_DATA_PATH': 'data/raw/' + DATASET_NAME}):
                self.assertEqual(raw_csv(root), path.resolve())

    def test_delivery_model_loading_after_relocation(self):
        import hashlib
        from xgboost import XGBClassifier
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'models').mkdir()
            shutil.copyfile(ROOT / 'models/XGBoost.ubj', root / 'models/XGBoost.ubj')
            path = champion_path(root)
            manifest = json.loads((ROOT / 'models/manifest.json').read_text())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest['model_sha256'])
            model = XGBClassifier(); model.load_model(path)
            self.assertEqual(model.best_iteration + 1, 24)
            self.assertEqual(model.n_features_in_, 14)
            self.assertIn(root.resolve().as_posix(), local_tracking_uri(root))


if __name__ == '__main__':
    unittest.main()
