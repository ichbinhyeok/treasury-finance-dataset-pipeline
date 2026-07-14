#!/usr/bin/env python3
"""Collect and validate the U.S. Treasury Average Interest Rates dataset.

Uses only Python's standard library. The collector paginates the official
Fiscal Data API, normalizes types, removes exact duplicate keys, and writes
CSV, JSONL, schema, metadata, and a machine-readable quality report.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


API_ENDPOINT = (
    "https://api.fiscaldata.treasury.gov/services/api/"
    "fiscal_service/v2/accounting/od/avg_interest_rates"
)
SOURCE_PAGE = (
    "https://fiscaldata.treasury.gov/datasets/"
    "average-interest-rates-treasury-securities/"
)
OUTPUT_COLUMNS = [
    "record_date",
    "security_type",
    "security_description",
    "average_interest_rate_percent",
    "source_line_number",
    "fiscal_year",
    "fiscal_quarter",
    "calendar_year",
    "calendar_quarter",
    "calendar_month",
    "calendar_day",
    "source_url",
]
REQUIRED_API_FIELDS = {
    "record_date",
    "security_type_desc",
    "security_desc",
    "avg_interest_rate_amt",
    "src_line_nbr",
    "record_fiscal_year",
    "record_fiscal_quarter",
    "record_calendar_year",
    "record_calendar_quarter",
    "record_calendar_month",
    "record_calendar_day",
}


def fetch_json(url: str, retries: int = 3, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "TreasuryDatasetPortfolio/1.0",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"API request failed after {retries} attempts: {last_error}")


def build_url(page_number: int, page_size: int) -> str:
    params = {
        "sort": "record_date,security_type_desc,security_desc",
        "page[number]": str(page_number),
        "page[size]": str(page_size),
    }
    return f"{API_ENDPOINT}?{urllib.parse.urlencode(params)}"


def collect_all(page_size: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page_number = 1
    first_meta: dict[str, Any] = {}
    expected_total: int | None = None

    while True:
        payload = fetch_json(build_url(page_number, page_size))
        page_rows = payload.get("data")
        if not isinstance(page_rows, list):
            raise ValueError("Schema drift: API response does not contain a data list")
        if page_number == 1:
            first_meta = payload.get("meta", {})
            expected_total = int(first_meta.get("total-count", len(page_rows)))
        rows.extend(page_rows)
        if not page_rows or expected_total is None or len(rows) >= expected_total:
            break
        page_number += 1

    return rows, {
        "api_meta": first_meta,
        "pages_requested": page_number,
        "expected_total_rows": expected_total,
    }


def normalize(raw_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[str] = []
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    duplicate_count = 0

    for index, raw in enumerate(raw_rows, start=1):
        missing = REQUIRED_API_FIELDS - raw.keys()
        if missing:
            raise ValueError(f"Schema drift at row {index}: missing {sorted(missing)}")

        try:
            parsed_date = date.fromisoformat(str(raw["record_date"]))
            raw_rate = str(raw["avg_interest_rate_amt"]).strip()
            rate = (
                None
                if raw_rate.lower() in {"", "null", "none"}
                else Decimal(raw_rate)
            )
            source_line = int(raw["src_line_nbr"])
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise ValueError(f"Invalid typed value at row {index}: {exc}") from exc

        if rate is None:
            issues.append(f"row {index}: source interest rate is null")
        elif not Decimal("0") <= rate <= Decimal("100"):
            issues.append(f"row {index}: interest rate outside 0..100")

        key = (
            parsed_date.isoformat(),
            str(raw["security_type_desc"]).strip(),
            str(raw["security_desc"]).strip(),
        )
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)

        normalized.append(
            {
                "record_date": key[0],
                "security_type": key[1],
                "security_description": key[2],
                "average_interest_rate_percent": (
                    "" if rate is None else format(rate, "f")
                ),
                "source_line_number": source_line,
                "fiscal_year": int(raw["record_fiscal_year"]),
                "fiscal_quarter": int(raw["record_fiscal_quarter"]),
                "calendar_year": int(raw["record_calendar_year"]),
                "calendar_quarter": int(raw["record_calendar_quarter"]),
                "calendar_month": int(raw["record_calendar_month"]),
                "calendar_day": int(raw["record_calendar_day"]),
                "source_url": API_ENDPOINT,
            }
        )

    normalized.sort(
        key=lambda row: (
            row["record_date"],
            row["security_type"],
            row["security_description"],
        )
    )
    null_counts = {
        column: sum(row[column] in (None, "") for row in normalized)
        for column in OUTPUT_COLUMNS
    }
    dates = [row["record_date"] for row in normalized]
    key_null_count = sum(
        row[column] in (None, "")
        for row in normalized
        for column in ("record_date", "security_type", "security_description")
    )
    quality = {
        "status": "PASS_WITH_WARNINGS" if issues else "PASS",
        "raw_row_count": len(raw_rows),
        "output_row_count": len(normalized),
        "duplicates_removed": duplicate_count,
        "unique_key": ["record_date", "security_type", "security_description"],
        "unique_key_count": len(seen),
        "null_counts": null_counts,
        "primary_key_null_count": key_null_count,
        "min_record_date": min(dates) if dates else None,
        "max_record_date": max(dates) if dates else None,
        "validation_issues": issues,
    }
    return normalized, quality


def write_outputs(
    output_dir: Path,
    rows: list[dict[str, Any]],
    quality: dict[str, Any],
    collection: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "treasury_average_interest_rates.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "treasury_average_interest_rates.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    schema = {
        "dataset": "U.S. Treasury Average Interest Rates",
        "primary_key": ["record_date", "security_type", "security_description"],
        "fields": {
            "record_date": "ISO 8601 date reported by Treasury",
            "security_type": "Top-level security category",
            "security_description": "Treasury security or aggregate description",
            "average_interest_rate_percent": "Decimal percentage, not a fraction",
            "source_line_number": "Line number in the source Treasury table",
            "fiscal_year": "U.S. federal fiscal year",
            "fiscal_quarter": "U.S. federal fiscal quarter, 1-4",
            "calendar_year": "Calendar year",
            "calendar_quarter": "Calendar quarter, 1-4",
            "calendar_month": "Calendar month, 1-12",
            "calendar_day": "Calendar day, 1-31",
            "source_url": "Official API endpoint used for provenance",
        },
    }
    metadata = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_page": SOURCE_PAGE,
        "api_endpoint": API_ENDPOINT,
        "license_note": "Public U.S. government source; verify downstream usage requirements.",
        **collection,
    }

    for filename, payload in (
        ("schema.json", schema),
        ("quality_report.json", quality),
        ("collection_metadata.json", metadata),
    ):
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 10_000:
        parser.error("--page-size must be between 1 and 10000")

    raw_rows, collection = collect_all(args.page_size)
    rows, quality = normalize(raw_rows)
    if collection["expected_total_rows"] != len(raw_rows):
        quality["status"] = "FAIL"
        quality["validation_issues"].append(
            "API total-count does not match collected raw rows"
        )
    write_outputs(args.output_dir, rows, quality, collection)
    print(
        json.dumps(
            {
                "status": quality["status"],
                "rows": len(rows),
                "output_dir": str(args.output_dir.resolve()),
            }
        )
    )
    return 0 if quality["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
