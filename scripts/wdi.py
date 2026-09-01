"""World Bank WDI helpers for 2023 population/GDP normalization."""
from __future__ import annotations

import requests
import pandas as pd

API_URL = "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL;NY.GDP.MKTP.CD"


def fetch_wdi_2023(timeout: int = 30) -> pd.DataFrame:
    """Fetch 2023 population and GDP from the World Bank WDI API."""
    response = requests.get(API_URL, params={"date": "2023", "format": "json", "per_page": 20000}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if len(payload) < 2 or not payload[1]:
        raise ValueError("World Bank API returned no indicator observations.")

    rows = [{
        "iso3": item.get("countryiso3code"),
        "country": item.get("country", {}).get("value"),
        "indicator": item.get("indicator", {}).get("id"),
        "value": item.get("value"),
        "year": int(item.get("date")),
    } for item in payload[1]]
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index=["iso3", "country", "year"], columns="indicator", values="value", aggfunc="first").reset_index()
    wide = wide.rename(columns={"SP.POP.TOTL": "population_2023", "NY.GDP.MKTP.CD": "gdp_current_usd_2023"})
    required = {"iso3", "population_2023", "gdp_current_usd_2023"}
    if not required.issubset(wide.columns):
        raise ValueError(f"WDI response missing required indicators: {sorted(required - set(wide.columns))}")
    return wide


def add_wdi_normalization(country_df: pd.DataFrame, wdi_df: pd.DataFrame) -> pd.DataFrame:
    out = country_df.copy()
    if "ndgain_iso3" not in out.columns:
        raise ValueError("Country data must contain canonical ndgain_iso3 values from country_name_mapping.csv")
    out["iso3"] = out["ndgain_iso3"].replace("", pd.NA)
    out = out.merge(wdi_df[["iso3", "population_2023", "gdp_current_usd_2023"]], on="iso3", how="left", validate="many_to_one")
    pop = out["population_2023"].where(out["population_2023"] > 0)
    gdp = out["gdp_current_usd_2023"].where(out["gdp_current_usd_2023"] > 0)
    out["climate_finance_per_capita_usd"] = (out["climate_finance_musd"] * 1_000_000).div(pop)
    out["climate_finance_as_pct_gdp"] = (out["climate_finance_musd"] * 1_000_000).div(gdp) * 100
    return out
