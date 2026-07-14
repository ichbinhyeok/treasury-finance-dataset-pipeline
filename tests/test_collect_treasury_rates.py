import unittest

import collect_treasury_rates as collector


def source_row(**overrides):
    row = {
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
    row.update(overrides)
    return row


class NormalizeTests(unittest.TestCase):
    def test_normalizes_types_and_provenance(self):
        rows, quality = collector.normalize([source_row()])

        self.assertEqual(quality["status"], "PASS")
        self.assertEqual(quality["primary_key_null_count"], 0)
        self.assertEqual(rows[0]["average_interest_rate_percent"], "3.706")
        self.assertEqual(rows[0]["calendar_month"], 6)
        self.assertEqual(rows[0]["source_url"], collector.API_ENDPOINT)

    def test_removes_duplicate_composite_key(self):
        rows, quality = collector.normalize([source_row(), source_row()])

        self.assertEqual(len(rows), 1)
        self.assertEqual(quality["duplicates_removed"], 1)
        self.assertEqual(quality["unique_key_count"], 1)

    def test_preserves_source_null_as_warning(self):
        rows, quality = collector.normalize(
            [source_row(avg_interest_rate_amt="null")]
        )

        self.assertEqual(rows[0]["average_interest_rate_percent"], "")
        self.assertEqual(quality["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(quality["null_counts"]["average_interest_rate_percent"], 1)

    def test_fails_on_schema_drift(self):
        row = source_row()
        del row["security_desc"]

        with self.assertRaisesRegex(ValueError, "Schema drift"):
            collector.normalize([row])

    def test_fails_on_invalid_date(self):
        with self.assertRaisesRegex(ValueError, "Invalid typed value"):
            collector.normalize([source_row(record_date="not-a-date")])


class UrlTests(unittest.TestCase):
    def test_build_url_encodes_pagination_and_sort(self):
        url = collector.build_url(page_number=3, page_size=777)

        self.assertIn("page%5Bnumber%5D=3", url)
        self.assertIn("page%5Bsize%5D=777", url)
        self.assertIn("sort=record_date%2Csecurity_type_desc%2Csecurity_desc", url)


if __name__ == "__main__":
    unittest.main()
