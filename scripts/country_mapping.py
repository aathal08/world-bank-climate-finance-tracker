"""Canonical World Bank-country to ND-GAIN mapping helpers."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "data" / "country_name_mapping.csv"


def load_country_mapping(path: Path = MAPPING_PATH) -> dict[str, dict[str, str]]:
    """Load the single source-of-truth country mapping."""
    if not path.exists():
        raise FileNotFoundError(f"Missing country mapping: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {"country_wb_label", "ndgain_country", "ndgain_iso3", "match_status"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Country mapping must contain columns: {sorted(required)}")
    mapping = {}
    for row in rows:
        key = row["country_wb_label"].strip()
        if not key:
            raise ValueError("Country mapping contains a blank World Bank label")
        if key in mapping:
            raise ValueError(f"Duplicate World Bank country label in mapping: {key}")
        mapping[key] = {k: (row.get(k) or "").strip() for k in required if k != "country_wb_label"}
    return mapping
