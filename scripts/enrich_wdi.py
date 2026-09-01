"""Fetch World Bank WDI 2023 population/GDP and add normalized finance metrics."""
from pathlib import Path
import pandas as pd

try:
    from scripts.wdi import fetch_wdi_2023, add_wdi_normalization
except ModuleNotFoundError:
    from wdi import fetch_wdi_2023, add_wdi_normalization

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    country_path = ROOT / "data" / "country_climate_finance_vs_ndgain.csv"
    wdi_path = ROOT / "data" / "wdi_2023.csv"
    out_path = ROOT / "data" / "country_climate_finance_vs_ndgain_wdi.csv"

    print("Fetching 2023 population and GDP from World Bank WDI...")
    wdi = fetch_wdi_2023()
    wdi.to_csv(wdi_path, index=False)
    country = pd.read_csv(country_path)
    enriched = add_wdi_normalization(country, wdi)
    enriched.to_csv(out_path, index=False)

    usable = enriched[
        enriched["population_2023"].notna() & enriched["gdp_current_usd_2023"].notna()
    ]
    print(f"Wrote {len(wdi):,} WDI observations to {wdi_path}")
    print(f"Wrote {len(enriched):,} country rows to {out_path}")
    print(f"Countries/entities with population + GDP: {len(usable):,}")


if __name__ == "__main__":
    main()
