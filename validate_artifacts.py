#!/usr/bin/env python3
"""Validate committed dataset artifacts without making a network request."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import collect_treasury_rates as collector


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate(output_dir: Path) -> dict[str, Any]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("hash_algorithm") != "sha256":
        raise ValueError("Unsupported or missing manifest hash algorithm")

    for filename, expected in manifest["files"].items():
        path = output_dir / filename
        if not path.is_file():
            raise ValueError(f"Manifest file is missing: {filename}")
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {filename}")
        if path.stat().st_size != expected["bytes"]:
            raise ValueError(f"Byte-size mismatch: {filename}")

    raw_rows = read_jsonl(output_dir / "raw_treasury_average_interest_rates.jsonl")
    normalized_jsonl = read_jsonl(output_dir / "treasury_average_interest_rates.jsonl")
    with (output_dir / "treasury_average_interest_rates.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        normalized_csv = list(csv.DictReader(handle))

    regenerated, regenerated_quality = collector.normalize(raw_rows)
    csv_equivalent = [{key: str(value) for key, value in row.items()} for row in regenerated]
    if normalized_jsonl != regenerated:
        raise ValueError("Normalized JSONL does not match the raw snapshot")
    if normalized_csv != csv_equivalent:
        raise ValueError("Normalized CSV does not match the raw snapshot")

    saved_quality = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
    if saved_quality != regenerated_quality:
        raise ValueError("Quality report does not match regenerated checks")

    counts = manifest["row_counts"]
    if counts != {"raw": len(raw_rows), "normalized": len(regenerated)}:
        raise ValueError("Manifest row counts do not match artifacts")

    metadata = json.loads(
        (output_dir / "collection_metadata.json").read_text(encoding="utf-8")
    )
    if metadata.get("expected_total_rows") != len(raw_rows):
        raise ValueError("API total-count does not match the raw snapshot")

    return {
        "status": "PASS",
        "raw_rows": len(raw_rows),
        "normalized_rows": len(regenerated),
        "quality_status": saved_quality["status"],
        "files_hashed": len(manifest["files"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    result = validate(args.output_dir)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
