from pathlib import Path
import sys

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROJECT_REQUIRED = {
    "project_id", "index", "project_name", "region_code", "country", "global_practice",
    "climate_finance_pct", "adaptation_musd", "mitigation_musd", "total_commitment_musd",
}
ENRICHED_REQUIRED = PROJECT_REQUIRED | {
    "climate_finance_musd", "is_regional_project", "ndgain_country_match", "ndgain_iso3",
    "country_display", "project_name_display", "global_practice_display",
}


def test_project_schema_counts_and_indices():
    df = pd.read_csv(ROOT / "data/fy23_climate_projects.csv")
    assert PROJECT_REQUIRED.issubset(df.columns)
    assert len(df) == 322
    assert df["project_id"].is_unique
    assert df["index"].tolist() == list(range(1, 323))
    assert not df[list(PROJECT_REQUIRED)].isna().any().any()


def test_project_values_and_climate_finance_calculation():
    raw = pd.read_csv(ROOT / "data/fy23_climate_projects.csv")
    enriched = pd.read_csv(ROOT / "data/fy23_climate_projects_enriched.csv")
    assert ENRICHED_REQUIRED.issubset(enriched.columns)
    assert raw["climate_finance_pct"].between(0, 100).all()
    assert (raw["total_commitment_musd"] >= 0).all()
    assert (raw["adaptation_musd"] >= 0).all()
    assert (raw["mitigation_musd"] >= 0).all()
    expected = raw["climate_finance_pct"] / 100 * raw["total_commitment_musd"]
    assert (expected - enriched["climate_finance_musd"]).abs().max() < 0.01
    assert (raw["adaptation_musd"] <= raw["total_commitment_musd"]).all()
    assert (raw["mitigation_musd"] <= raw["total_commitment_musd"]).all()


def test_official_fy23_total_and_project_count():
    enriched = pd.read_csv(ROOT / "data/fy23_climate_projects_enriched.csv")
    total = enriched["climate_finance_musd"].sum()
    assert abs(total - 29441.0) < 2.0
    assert int((enriched["climate_finance_pct"] > 0).sum()) == 309


def test_historical_series_integrity():
    history = pd.read_csv(ROOT / "data/historical_climate_finance.csv")
    assert history["fy"].tolist() == list(range(2018, 2024))
    assert (history["adaptation_musd"] + history["mitigation_musd"] == history["total_climate_finance_musd"]).all()
    assert history["total_climate_finance_musd"].tolist() == [15703, 14220, 17229, 21208, 26157, 29441]


def test_country_mapping_is_single_source_and_complete():
    mapping = pd.read_csv(ROOT / "data/country_name_mapping.csv", keep_default_na=False)
    projects = pd.read_csv(ROOT / "data/fy23_climate_projects.csv")
    assert mapping["country_wb_label"].is_unique
    assert set(projects["country"]) == set(mapping["country_wb_label"])
    matched = mapping[mapping["match_status"] == "matched"]
    assert matched["ndgain_country"].ne("").all()
    assert matched["ndgain_iso3"].str.len().eq(3).all()
    assert {"BosniaandHerzegovina", "CaboVerde"}.issubset(set(matched["country_wb_label"]))


def test_country_matching_and_regions():
    countries = pd.read_csv(ROOT / "data/country_climate_finance_vs_ndgain.csv")
    nonregional = countries.loc[~countries["is_regional_project"]]
    matched = nonregional.loc[nonregional["ndgain_score_2023"].notna()]
    assert len(countries) == 99
    assert len(nonregional) == 94
    assert len(matched) == 92
    assert set(nonregional.loc[nonregional["ndgain_score_2023"].isna(), "country_wb_label"]) == {"SouthSudan", "Kosovo"}
    assert matched["ndgain_iso3"].notna().all()
    assert matched["ndgain_iso3"].is_unique
    assert matched["ndgain_score_2023"].between(0, 100).all()
    assert (countries["climate_share_of_portfolio_pct"].between(0, 100)).all()


def test_ndgain_snapshot_integrity():
    ndg = pd.read_csv(ROOT / "data/ndgain_2023.csv")
    assert len(ndg) == 187
    assert ndg["country"].is_unique
    assert ndg["rank"].between(1, 187).all()
    assert ndg["ndgain_score"].between(0, 100).all()


def test_statistical_results_are_finite_and_reproducible():
    countries = pd.read_csv(ROOT / "data/country_climate_finance_vs_ndgain.csv")
    df = countries.loc[(~countries["is_regional_project"]) & countries["ndgain_score_2023"].notna()]
    r, p = stats.pearsonr(df["ndgain_score_2023"], df["climate_finance_musd"])
    rs, ps = stats.spearmanr(df["ndgain_score_2023"], df["climate_finance_musd"])
    share_r, share_p = stats.pearsonr(df["ndgain_score_2023"], df["climate_share_of_portfolio_pct"])
    assert (round(r, 3), round(rs, 3), round(share_r, 3)) == (0.016, -0.036, 0.264)
    assert all(pd.notna(v) for v in [r, p, rs, ps, share_r, share_p])


def test_wdi_normalization_math_without_network():
    from scripts.wdi import add_wdi_normalization

    countries = pd.DataFrame({
        "ndgain_country": ["India"], "ndgain_iso3": ["IND"], "climate_finance_musd": [100.0],
        "is_regional_project": [False], "ndgain_score_2023": [44.0],
    })
    wdi = pd.DataFrame({
        "iso3": ["IND"], "population_2023": [1_000_000],
        "gdp_current_usd_2023": [10_000_000_000],
    })
    out = add_wdi_normalization(countries, wdi)
    assert out.loc[0, "climate_finance_per_capita_usd"] == 100.0
    assert out.loc[0, "climate_finance_as_pct_gdp"] == 1.0
