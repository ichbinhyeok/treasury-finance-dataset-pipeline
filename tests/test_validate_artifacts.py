import tempfile
import unittest
from pathlib import Path

import collect_treasury_rates as collector
import validate_artifacts


def source_row():
    return {
        "record_date": "2026-06-30",
        "security_type_desc": "Marketable",
        "security_desc": "Treasury Bills",
        "avg_interest_rate_amt": "3.706",
        "src_line_nbr": "1",
        "record_fiscal_year": "2026",
        "record_fiscal_quarter": "3",
        "record_calendar_year": "2026",
        "record_calendar_quarter": "2",
        "record_calendar_month": "06",
        "record_calendar_day": "30",
    }


class ArtifactValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        raw_rows = [source_row()]
        rows, quality = collector.normalize(raw_rows)
        collection = {
            "api_meta": {},
            "pages_requested": 1,
            "expected_total_rows": 1,
        }
        collector.write_outputs(
            self.output_dir, raw_rows, rows, quality, collection
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validates_complete_artifact_chain(self):
        result = validate_artifacts.validate(self.output_dir)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_rows"], 1)
        self.assertEqual(result["files_hashed"], 6)
        for path in self.output_dir.iterdir():
            if path.is_file():
                self.assertNotIn(b"\r\n", path.read_bytes())

    def test_detects_tampered_artifact(self):
        csv_path = self.output_dir / "treasury_average_interest_rates.csv"
        csv_path.write_text("tampered\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            validate_artifacts.validate(self.output_dir)


if __name__ == "__main__":
    unittest.main()
