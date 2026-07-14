# Data source and usage notes

## Source

The generated dataset is collected from the U.S. Department of the Treasury,
Bureau of the Fiscal Service, through the Fiscal Data API.

- Dataset: Average Interest Rates on U.S. Treasury Securities
- Dataset page: https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/
- API: https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates
- Accessed: 2026-07-14 UTC

Each normalized row includes the official API endpoint in `source_url`. The
collection timestamp, source-provided field labels, types, formats, and row
total are retained in `data/collection_metadata.json`.

## Rights and responsibility

The repository's MIT license applies to the original collection and validation
code. It does not claim ownership of source data or grant rights on behalf of
the U.S. Treasury. Downstream users remain responsible for checking the source
site's current policies and requirements for their intended use.

This repository is not affiliated with or endorsed by the U.S. Department of
the Treasury. The data is provided as collected, without financial advice or a
guarantee of correctness.
