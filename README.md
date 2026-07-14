# Treasury Finance Dataset Pipeline

[![CI](https://github.com/ichbinhyeok/treasury-finance-dataset-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/ichbinhyeok/treasury-finance-dataset-pipeline/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Code license: MIT](https://img.shields.io/badge/code%20license-MIT-green.svg)](LICENSE)

A dependency-free Python pipeline that collects the complete **U.S. Treasury
Average Interest Rates** dataset, normalizes it into analysis-ready CSV and
JSONL, preserves source provenance, and emits machine-readable quality results.

This repository is a compact data-engineering portfolio sample: the output is
included, the collection is reproducible, and source-data defects are reported
instead of being silently dropped.

## Snapshot

| Metric | Result |
|---|---:|
| Source rows collected | 4,977 |
| Output rows | 4,977 |
| Date coverage | 2001-01-31 to 2026-06-30 |
| Unique-key duplicates | 0 |
| Primary-key nulls | 0 |
| Source interest-rate nulls | 28 |
| Quality status | `PASS_WITH_WARNINGS` |

The 28 blank rate values are present as literal `null` values in historical
source records. They are retained as blank measures and surfaced in
[`quality_report.json`](data/quality_report.json).

## Deliverables

```text
.
├── collect_treasury_rates.py
├── validate_artifacts.py
├── data/
│   ├── collection_metadata.json
│   ├── manifest.json
│   ├── quality_report.json
│   ├── raw_treasury_average_interest_rates.jsonl
│   ├── schema.json
│   ├── treasury_average_interest_rates.csv
│   └── treasury_average_interest_rates.jsonl
├── tests/
│   └── test_collect_treasury_rates.py
├── .github/workflows/ci.yml
├── DATA_SOURCE.md
├── LICENSE
└── README.md
```

## Reproduce the dataset

Python 3.10 or newer is sufficient. No API key or third-party package is
required.

```bash
python collect_treasury_rates.py --output-dir data
```

Use a different page size to exercise pagination:

```bash
python collect_treasury_rates.py --output-dir data --page-size 777
```

Run the offline unit tests:

```bash
python -m unittest discover -s tests -v
```

Validate every committed artifact without a network request:

```bash
python validate_artifacts.py --output-dir data
```

## What the pipeline checks

- Retries transient request failures with exponential backoff.
- Paginates against the API's declared total rather than assuming one response.
- Fails fast when required source fields disappear.
- Parses dates, percentages, and numeric calendar fields into stable types.
- Uses `record_date + security_type + security_description` as a composite key.
- Fails on empty datasets, blank keys, duplicate keys, invalid domain values,
  and inconsistent calendar or fiscal fields.
- Reports nulls, date coverage, suspicious percentage values, and API metadata.
- Writes the official API endpoint on every output row for durable provenance.
- Saves the raw API rows and verifies both normalized formats against them.
- Records SHA-256 hashes and byte sizes for six generated artifacts.
- Exits non-zero on a failed collection or validation.

GitHub Actions compiles and tests the collector on Python 3.10–3.13, validates
all committed artifacts offline, and performs a complete live-source collection
on branch pushes.

## Data grain

One row represents one Treasury security description or aggregate category on
one reporting date. `average_interest_rate_percent` is expressed as a percent:
`3.409` means **3.409%**, not `0.03409`.

Example:

```csv
record_date,security_type,security_description,average_interest_rate_percent
2026-06-30,Marketable,Treasury Bills,3.706
2026-06-30,Marketable,Treasury Notes,3.283
2026-06-30,Marketable,Treasury Bonds,3.430
```

## Source and licensing

The data comes from the U.S. Department of the Treasury, Bureau of the Fiscal
Service:

- [Official dataset page](https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/)
- [Official API endpoint](https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates)

The MIT license covers this repository's original code. It does not claim
ownership of U.S. Treasury data. See [DATA_SOURCE.md](DATA_SOURCE.md) for source
and usage notes.

## Known limitations

- Treasury controls the reporting schedule and may revise historical values.
- Aggregate categories and individual security categories coexist. They should
  not be summed without understanding the source hierarchy.
- Passing checks confirm collection integrity against the declared contract;
  they do not independently audit Treasury's underlying calculations.
- This project demonstrates implementation capability. It is not evidence that
  a buyer has purchased this specific dataset.

## Adapting the pattern

The same delivery pattern applies to public-web dataset work: define sources
and fields, collect reliably, preserve provenance, deduplicate, validate, and
ship both data and a quality report. A paid pilot should lock the exact URLs,
fields, row volume, refresh cadence, and acceptance tests before collection.
