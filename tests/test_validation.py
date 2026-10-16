import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fraud_detection.validation import EXPECTED_COLUMNS, binary, missing_columns, segment

class ValidationTests(unittest.TestCase):
    def test_boundary(self):
        self.assertEqual(segment("400"), "reference")
        self.assertEqual(segment("401"), "production")
    def test_invalid_steps(self):
        for value in ("", "nan", "inf", "0", "-1", "400.5", "x"):
            self.assertIsNone(segment(value))
    def test_columns(self):
        self.assertEqual(missing_columns(EXPECTED_COLUMNS), [])
        self.assertEqual(missing_columns(EXPECTED_COLUMNS[:-1]), ["isFlaggedFraud"])
    def test_binary(self):
        self.assertTrue(binary("0")); self.assertTrue(binary("1"))
        for value in ("", "2", "-1", "nan"):
            self.assertFalse(binary(value))

class AuditTests(unittest.TestCase):
    def test_small_csv_exact_counts(self):
        import csv
        import importlib.util
        import tempfile
        spec = importlib.util.spec_from_file_location("audit", Path(__file__).resolve().parents[1] / "scripts/audit_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.csv"
            a = ["400", "TRANSFER", "10", "C1", "20", "10", "C2", "0", "10", "1", "0"]
            b = ["401", "PAYMENT", "30", "C3", "40", "10", "M1", "0", "0", "0", "0"]
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(EXPECTED_COLUMNS)
                writer.writerows([a, a, b])
            result = module.audit(path)
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["duplicates_exact"], 1)
            self.assertEqual(result["unique_entities"], {"origins": 2, "destinations": 2})
            self.assertEqual(result["periods"]["reference"]["fraud"], 2)
            self.assertEqual(result["periods"]["production"]["rows"], 1)
            self.assertTrue(result["validation"]["exhaustive"])

if __name__ == "__main__":
    unittest.main()
