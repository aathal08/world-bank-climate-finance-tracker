"""Validate the reproducible FY23 climate-finance pipeline."""
from pathlib import Path

import pandas as pd
from scipy import stats

try:
    from scripts.country_mapping import load_country_mapping
except ModuleNotFoundError:
    from country_mapping import load_country_mapping

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    projects = pd.read_csv(ROOT / "data" / "fy23_climate_projects.csv")
    enriched = pd.read_csv(ROOT / "data" / "fy23_climate_projects_enriched.csv")
    countries = pd.read_csv(ROOT / "data" / "country_climate_finance_vs_ndgain.csv")
    history = pd.read_csv(ROOT / "data" / "historical_climate_finance.csv")
    ndgain = pd.read_csv(ROOT / "data" / "ndgain_2023.csv")
    mapping = load_country_mapping()

    require(len(projects) == 322, f"Expected 322 projects, found {len(projects)}")
    require(projects["project_id"].is_unique, "Duplicate project IDs detected")
    require(projects["index"].tolist() == list(range(1, 323)), "Project indices must run 1..322")
    require(projects["climate_finance_pct"].between(0, 100).all(), "Invalid climate-finance percentages")
    require((projects[["adaptation_musd", "mitigation_musd", "total_commitment_musd"]] >= 0).all().all(), "Negative financial values detected")
    require((projects["adaptation_musd"] <= projects["total_commitment_musd"]).all(), "Adaptation exceeds commitment")
    require((projects["mitigation_musd"] <= projects["total_commitment_musd"]).all(), "Mitigation exceeds commitment")
    require({"country_display", "project_name_display", "global_practice_display"}.issubset(enriched.columns), "Display fields missing from enriched data")
    require(set(projects["country"]) == set(mapping), "Country mapping is not complete for project data")
    require(history["fy"].tolist() == list(range(2018, 2024)), "Historical series is incomplete or out of order")
    require((history["adaptation_musd"] + history["mitigation_musd"] == history["total_climate_finance_musd"]).all(), "Historical totals do not equal adaptation + mitigation")
    require(history["total_climate_finance_musd"].tolist() == [15703, 14220, 17229, 21208, 26157, 29441], "Historical series values changed unexpectedly")
    require(set(projects["region_code"].unique()).issubset({"AFE", "AFW", "EAP", "ECA", "LCR", "MNA", "SAR"}), "Unexpected World Bank region code")

    expected = projects["climate_finance_pct"] / 100 * projects["total_commitment_musd"]
    max_error = (expected - enriched["climate_finance_musd"]).abs().max()
    require(max_error < 0.01, f"Project climate-finance calculation mismatch: max error {max_error}")

    project_total = enriched["climate_finance_musd"].sum()
    require(abs(project_total - 29441.0) < 2.0, f"Project total {project_total:.2f}M differs from official FY23 total by >= $2M")
    require(int((projects["climate_finance_pct"] > 0).sum()) == 309, "Expected 309 projects with non-zero climate finance")

    require(len(ndgain) == 187, f"Expected 187 ND-GAIN snapshot rows, found {len(ndgain)}")
    require(ndgain["country"].is_unique, "Duplicate ND-GAIN countries detected")
    require(ndgain["rank"].between(1, 187).all(), "ND-GAIN ranks outside valid range")
    require(ndgain["ndgain_score"].between(0, 100).all(), "ND-GAIN scores outside 0-100")

    nonregional = countries.loc[~countries["is_regional_project"]].copy()
    matched = nonregional.loc[nonregional["ndgain_score_2023"].notna()].copy()
    unmatched = nonregional.loc[nonregional["ndgain_score_2023"].isna(), "country_wb_label"].tolist()
    require(len(countries) == 99, f"Expected 99 country/entity rows, found {len(countries)}")
    require(len(nonregional) == 94, f"Expected 94 single-country entities, found {len(nonregional)}")
    require(len(matched) == 92, f"Expected 92 ND-GAIN matches, found {len(matched)}")
    require(set(unmatched) == {"SouthSudan", "Kosovo"}, f"Unexpected unmatched countries: {unmatched}")
    require(matched["ndgain_iso3"].is_unique, "Duplicate ND-GAIN ISO3 codes detected")
    require(matched["ndgain_score_2023"].between(0, 100).all(), "Invalid matched ND-GAIN scores")

    mapping_df = pd.read_csv(ROOT / "data" / "country_name_mapping.csv", keep_default_na=False)
    merged_map = countries[["country_wb_label", "ndgain_country", "ndgain_iso3"]].merge(
        mapping_df[["country_wb_label", "ndgain_country", "ndgain_iso3"]],
        on="country_wb_label", suffixes=("_output", "_mapping"), validate="one_to_one"
    )
    require((merged_map["ndgain_country_output"] == merged_map["ndgain_country_mapping"]).all(), "Output ND-GAIN names differ from canonical mapping")
    require((merged_map["ndgain_iso3_output"] == merged_map["ndgain_iso3_mapping"]).all(), "Output ISO3 values differ from canonical mapping")

    r, p = stats.pearsonr(matched["ndgain_score_2023"], matched["climate_finance_musd"])
    rs, ps = stats.spearmanr(matched["ndgain_score_2023"], matched["climate_finance_musd"])
    rshare, pshare = stats.pearsonr(matched["ndgain_score_2023"], matched["climate_share_of_portfolio_pct"])

    print("PASS: 322 unique project records")
    print("PASS: project indices run 1..322")
    print("PASS: financial values and climate-finance percentages are valid")
    print(f"PASS: project climate-finance formula matches; max error = ${max_error:.4f}M")
    print(f"PASS: parsed FY23 climate finance = ${project_total/1000:.3f}B; official = $29.441B")
    print("PASS: historical FY18-FY23 series matches the documented source")
    print("PASS: ND-GAIN snapshot contains 187 unique country rows with valid scores")
    print(f"PASS: 94 single-country entities; 92 matched to ND-GAIN; unmatched = {unmatched}")
    print("PASS: country output mappings exactly match country_name_mapping.csv")
    print(f"ND-GAIN overall score vs raw finance: Pearson r={r:+.3f}, p={p:.4f}; Spearman rho={rs:+.3f}, p={ps:.4f}")
    print(f"ND-GAIN overall score vs portfolio share: Pearson r={rshare:+.3f}, p={pshare:.4f}")


if __name__ == "__main__":
    main()
