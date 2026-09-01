"""Aggregate FY23 World Bank climate co-benefits and join to ND-GAIN 2023."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

try:
    from scripts.country_mapping import load_country_mapping
    from scripts.display_names import clean_pdf_label
except ModuleNotFoundError:
    from country_mapping import load_country_mapping
    from display_names import clean_pdf_label

ROOT = Path(__file__).resolve().parents[1]
REGIONAL_ENTITIES = {
    "EasternandSouthernAfrica", "WesternandCentralAfrica", "CentralAfrica",
    "WesternBalkans", "SouthAsia",
}
REGION_FULL = {
    "AFE": "Eastern & Southern Africa", "AFW": "Western & Central Africa",
    "EAP": "East Asia & Pacific", "ECA": "Europe & Central Asia",
    "LCR": "Latin America & Caribbean", "MNA": "Middle East & North Africa",
    "SAR": "South Asia",
}


def load_ndgain(path: Path | None = None) -> dict[str, dict]:
    path = path or ROOT / "data" / "ndgain_2023.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("ND-GAIN snapshot is empty")
    out = {}
    for row in rows:
        country = row["country"].strip()
        if country in out:
            raise ValueError(f"Duplicate ND-GAIN country: {country}")
        out[country] = {
            "rank": int(row["rank"]),
            "income_group": row["income_group"].strip(),
            "score": float(row["ndgain_score"]),
        }
    return out


def run() -> tuple[list[dict], list[dict]]:
    ndgain = load_ndgain()
    mapping = load_country_mapping()

    projects_path = ROOT / "data" / "fy23_climate_projects.csv"
    with projects_path.open(encoding="utf-8", newline="") as f:
        source_rows = list(csv.DictReader(f))

    if len(source_rows) != 322:
        raise ValueError(f"Expected 322 project rows, found {len(source_rows)}")

    unknown_mapping = sorted({r["country"] for r in source_rows} - set(mapping))
    if unknown_mapping:
        raise ValueError(f"Countries missing from country_name_mapping.csv: {unknown_mapping}")

    country_agg = defaultdict(lambda: {
        "adaptation": 0.0, "mitigation": 0.0, "total_commit": 0.0,
        "climate_finance": 0.0, "n_projects": 0, "region": None,
    })
    enriched_rows = []

    for row in source_rows:
        country_raw = row["country"]
        region_code = row["region_code"]
        adapt = float(row["adaptation_musd"])
        mitig = float(row["mitigation_musd"])
        total = float(row["total_commitment_musd"])
        climate_musd = float(row["climate_finance_pct"]) / 100.0 * total
        map_row = mapping[country_raw]
        ndg_name = map_row["ndgain_country"] or None
        ndg_iso3 = map_row["ndgain_iso3"]

        enriched_rows.append({
            **row,
            "climate_finance_musd": round(climate_musd, 2),
            "is_regional_project": country_raw in REGIONAL_ENTITIES,
            "ndgain_country_match": ndg_name or "",
            "ndgain_iso3": ndg_iso3 or "",
            "country_display": clean_pdf_label(country_raw),
            "project_name_display": clean_pdf_label(row["project_name"]),
            "global_practice_display": clean_pdf_label(row["global_practice"]),
        })

        agg = country_agg[country_raw]
        agg["adaptation"] += adapt
        agg["mitigation"] += mitig
        agg["total_commit"] += total
        agg["climate_finance"] += climate_musd
        agg["n_projects"] += 1
        agg["region"] = REGION_FULL.get(region_code, region_code)

    merged_rows = []
    for country_raw, agg in country_agg.items():
        map_row = mapping[country_raw]
        ndg_name = map_row["ndgain_country"] or None
        ndg = ndgain.get(ndg_name) if ndg_name else None
        ndg_iso3 = map_row["ndgain_iso3"]
        merged_rows.append({
            "country_wb_label": country_raw,
            "country_display": clean_pdf_label(country_raw),
            "ndgain_country": ndg_name or "",
            "ndgain_iso3": ndg_iso3 or "",
            "region": agg["region"],
            "is_regional_project": country_raw in REGIONAL_ENTITIES,
            "n_projects": agg["n_projects"],
            "total_commitment_musd": round(agg["total_commit"], 1),
            "adaptation_musd": round(agg["adaptation"], 1),
            "mitigation_musd": round(agg["mitigation"], 1),
            "climate_finance_musd": round(agg["climate_finance"], 1),
            "climate_share_of_portfolio_pct": round(100 * agg["climate_finance"] / agg["total_commit"], 1) if agg["total_commit"] else None,
            "ndgain_rank_2023": ndg["rank"] if ndg else None,
            "ndgain_score_2023": ndg["score"] if ndg else None,
            "ndgain_income_group": ndg["income_group"] if ndg else None,
        })

    merged_rows.sort(key=lambda r: -r["climate_finance_musd"])
    _write_csv(ROOT / "data" / "country_climate_finance_vs_ndgain.csv", merged_rows)
    _write_csv(ROOT / "data" / "fy23_climate_projects_enriched.csv", enriched_rows)

    matched = [r for r in merged_rows if not r["is_regional_project"] and r["ndgain_score_2023"] is not None]
    unmatched = [r["country_wb_label"] for r in merged_rows if not r["is_regional_project"] and r["ndgain_score_2023"] is None]
    print(f"Wrote {len(merged_rows)} country/entity rows; {len(matched)} single-country rows matched to ND-GAIN.")
    print(f"Regional/multi-country rows excluded from ND-GAIN comparison: {sum(r['is_regional_project'] for r in merged_rows)}")
    print(f"FY23 climate finance across parsed projects: ${sum(r['climate_finance_musd'] for r in enriched_rows):,.2f}M")
    print("Unmatched single-country ND-GAIN labels:", unmatched)
    return merged_rows, enriched_rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty dataset: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()
