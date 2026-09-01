# World Bank Climate Finance Flow Tracker

FY23 IBRD/IDA project-level climate finance and country-level ND-GAIN analysis, with optional 2023 World Development Indicators normalization.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data and methodology

The project uses the World Bank FY23 project-level climate finance data, a frozen 2023 ND-GAIN snapshot, and optional World Development Indicators (WDI) data. Project-level climate finance is reconstructed from total commitment and the reported climate-finance percentage. Because project percentages are rounded, the reconstructed total can differ slightly from the official aggregate.

The country-level analysis maps project entities to ISO3 codes using `data/country_name_mapping.csv` as the authoritative mapping. Regional and multicountry projects are retained separately rather than being forced into a single-country interpretation.

The ND-GAIN analysis is descriptive and does not establish causality.

## Validation

The repository includes automated tests for project counts, financial totals, mappings, ND-GAIN matching, aggregation reconciliation, and statistical reproducibility.

```bash
pytest -q
python scripts/validate_data.py
```

## Structure

- `app.py` — Streamlit dashboard
- `data/` — curated input and generated analysis datasets
- `scripts/` — download, parse, mapping, enrichment, analysis, and validation pipeline
- `tests/` — automated validation tests

## Sources

See `data/source_urls.txt` and `data/ndgain_metadata.txt` for source and attribution details.
