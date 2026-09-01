"""
World Bank Climate Finance Flow Tracker
---------------------------------------
FY23 IBRD/IDA project-level climate finance and country-level ND-GAIN analysis,
and optional 2023 World Development Indicators normalization.

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats
import math

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(page_title="World Bank Climate Finance Flow Tracker", layout="wide")

REGION_NAMES = {
    "AFE": "Eastern & Southern Africa", "AFW": "Western & Central Africa",
    "EAP": "East Asia & Pacific", "ECA": "Europe & Central Asia",
    "LCR": "Latin America & Caribbean", "MNA": "Middle East & North Africa",
    "SAR": "South Asia",
}

@st.cache_data
def load_data():
    projects = pd.read_csv(DATA / "fy23_climate_projects_enriched.csv")
    countries = pd.read_csv(DATA / "country_climate_finance_vs_ndgain.csv")
    history = pd.read_csv(DATA / "historical_climate_finance.csv")
    return projects, countries, history

projects, countries, history = load_data()
projects["region_name"] = projects["region_code"].map(REGION_NAMES).fillna(projects["region_code"])

st.title("World Bank Climate Finance Flow Tracker")
st.caption(
    "FY23 IBRD/IDA project-level climate finance and country climate ND-GAIN Country Index. "
    "The analysis is descriptive; it does not claim causality or that financing should equal a country's climate need or resilience."
)

with st.expander("Methodology & definitions"):
    st.markdown(
        """
        **Climate finance:** project-level climate co-benefits calculated as the disclosed climate-finance percentage multiplied by total commitment. The project dataset is the official World Bank FY23 IBRD/IDA disclosure.

        **ND-GAIN Country Index:** the 2023 overall Country Index, a composite measure combining vulnerability and readiness. Higher scores are better. This project does **not** use the separate ND-GAIN Vulnerability or Readiness component.

        **Country aggregation:** multi-country/regional projects are retained in portfolio totals but excluded from the single-country ND-GAIN comparison.

        **Portfolio share:** climate finance divided by the project's/country's total commitment. This is a **portfolio-normalized intensity measure**, not a direct allocation-need metric.

        **Correlation:** Pearson correlation is shown for the FY23 country-level sample. A correlation near zero means the variables have little linear association in this sample; it does not establish why financing was allocated.
        """
    )

total_climate = projects["climate_finance_musd"].sum()
total_commit = projects["total_commitment_musd"].sum()
n_projects = len(projects)
n_country_rows = countries[~countries["is_regional_project"]]
n_countries = n_country_rows["country_wb_label"].nunique()

k1, k2, k3, k4 = st.columns(4)
k1.metric("FY23 climate finance", f"${total_climate/1000:,.1f}B")
k2.metric("Climate share of commitments", f"{100*total_climate/total_commit:,.1f}%")
n_climate_projects = int((projects["climate_finance_pct"] > 0).sum())
k3.metric("Projects in FY23 disclosure", f"{n_projects:,}")
k4.metric("Single-country entities", f"{n_countries}", help=f"{len(countries[countries['is_regional_project']])} regional/multi-country entities are retained separately; {countries.loc[(~countries['is_regional_project']) & countries['ndgain_score_2023'].notna(), 'country_wb_label'].nunique()} have ND-GAIN matches.")
st.caption(f"{n_climate_projects:,} of {n_projects:,} projects have non-zero disclosed climate co-benefits.")

st.divider()

st.subheader("IBRD/IDA climate finance trend")
st.caption("Historical IBRD/IDA totals published in the FY23 project-level climate-finance disclosure. FY18–FY23 are directly comparable within that source.")
trend = history.copy()
fig_hist = px.bar(
    trend, x="fy", y="total_climate_finance_musd", hover_data=["adaptation_musd", "mitigation_musd"],
    labels={"fy": "Fiscal year", "total_climate_finance_musd": "Climate finance (US$M)"},
    text_auto=".1f"
)
fig_hist.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig_hist, use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Climate finance by region")
    region_df = projects.groupby("region_name", as_index=False)["climate_finance_musd"].sum().sort_values("climate_finance_musd")
    fig = px.bar(region_df, x="climate_finance_musd", y="region_name", orientation="h",
                 labels={"climate_finance_musd": "Climate finance (US$M)", "region_name": ""})
    fig.update_layout(height=350, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Climate finance by sector")
    sector_df = projects.groupby("global_practice", as_index=False)["climate_finance_musd"].sum().sort_values("climate_finance_musd").tail(10)
    fig2 = px.bar(sector_df, x="climate_finance_musd", y="global_practice", orientation="h",
                  labels={"climate_finance_musd": "Climate finance (US$M)", "global_practice": ""})
    fig2.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("Climate finance vs. ND-GAIN Country Index")
plot_df = countries[(~countries["is_regional_project"]) & countries["ndgain_score_2023"].notna()].copy()
raw_corr = plot_df["ndgain_score_2023"].corr(plot_df["climate_finance_musd"])
share_corr = plot_df["ndgain_score_2023"].corr(plot_df["climate_share_of_portfolio_pct"])
spearman_raw = plot_df["ndgain_score_2023"].corr(plot_df["climate_finance_musd"], method="spearman")

st.caption(
    "Each dot is a country. Lower ND-GAIN Country Index scores indicate weaker overall climate resilience and readiness. "
    "Raw dollar amounts are shown on a log scale to make small and large portfolios visible together."
)
fig3 = px.scatter(
    plot_df, x="ndgain_score_2023", y="climate_finance_musd", log_y=True,
    size="n_projects", color="region", hover_name="ndgain_country", size_max=38,
    labels={
        "ndgain_score_2023": "ND-GAIN Country Index score (higher = stronger ND-GAIN Country Index)",
        "climate_finance_musd": "FY23 climate finance (US$M, log scale)",
        "region": "Region",
    },
)
fig3.update_layout(height=520)
st.plotly_chart(fig3, use_container_width=True)

m1, m2, m3 = st.columns(3)

def correlation_ci(r: float, n: int, confidence: float = 0.95):
    """Fisher-z confidence interval for a Pearson correlation."""
    if n <= 3 or not math.isfinite(r) or abs(r) >= 1:
        return (float("nan"), float("nan"))
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    zcrit = stats.norm.ppf(1 - (1 - confidence) / 2)
    return tuple(math.tanh(v) for v in (z - zcrit * se, z + zcrit * se))

raw_r, raw_p = stats.pearsonr(plot_df["ndgain_score_2023"], plot_df["climate_finance_musd"])
spearman_r, spearman_p = stats.spearmanr(plot_df["ndgain_score_2023"], plot_df["climate_finance_musd"])
share_r, share_p = stats.pearsonr(plot_df["ndgain_score_2023"], plot_df["climate_share_of_portfolio_pct"])
raw_ci = correlation_ci(raw_r, len(plot_df))
share_ci = correlation_ci(share_r, len(plot_df))

m1.metric("Pearson r: raw finance", f"{raw_r:+.3f}", help=f"N={len(plot_df)}; p={raw_p:.4f}; 95% CI [{raw_ci[0]:+.3f}, {raw_ci[1]:+.3f}]")
m2.metric("Spearman ρ: raw finance", f"{spearman_r:+.3f}", help=f"N={len(plot_df)}; p={spearman_p:.4f}")
m3.metric("Pearson r: portfolio share", f"{share_r:+.3f}", help=f"N={len(plot_df)}; p={share_p:.4f}; 95% CI [{share_ci[0]:+.3f}, {share_ci[1]:+.3f}]")

st.info(
    f"**Interpretation:** The FY23 country sample (N={len(plot_df)}) has a near-zero linear association between ND-GAIN Country Index score and raw climate-finance dollars (Pearson r={raw_r:+.3f}, p={raw_p:.4f}). "
    "This does not establish an allocation rule or causal mechanism. Raw commitments are affected by project scale, country size, and portfolio composition. "
    f"The portfolio-normalized climate-finance share has a modest positive association with the ND-GAIN Country Index (r={share_r:+.3f}, p={share_p:.4f}). Because higher ND-GAIN scores are better, this is a descriptive association, not evidence that resilience causes financing."
)

st.caption(
    f"95% CIs (Fisher z) for Pearson correlations: raw finance [{raw_ci[0]:+.3f}, {raw_ci[1]:+.3f}]; portfolio share [{share_ci[0]:+.3f}, {share_ci[1]:+.3f}]. "
    "The portfolio-share metric is normalization by total commitment, not a direct allocation-need measure. "
    "Per-capita and GDP-normalized analysis can be loaded from the World Bank WDI API below."
)

st.divider()
st.subheader("Optional: population/GDP-normalized analysis")
st.write(
    "The project includes a reproducible World Bank WDI enrichment script for 2023 population and GDP. "
    "This avoids embedding stale macroeconomic values in the repository."
)

if st.button("Load 2023 World Bank WDI normalization"):
    try:
        from scripts.wdi import fetch_wdi_2023, add_wdi_normalization
        with st.spinner("Fetching 2023 population and GDP from the World Bank WDI API..."):
            wdi = fetch_wdi_2023()
            normalized = add_wdi_normalization(countries, wdi)
        base_norm = normalized[(~normalized["is_regional_project"]) & normalized["ndgain_score_2023"].notna()].copy()
        per_cap_df = base_norm[base_norm["population_2023"].notna() & base_norm["climate_finance_per_capita_usd"].notna()].copy()
        gdp_df = base_norm[base_norm["gdp_current_usd_2023"].notna() & base_norm["climate_finance_as_pct_gdp"].notna()].copy()
        st.success(f"Loaded WDI data for {len(wdi):,} observations; {len(per_cap_df):,} countries have usable population normalization and {len(gdp_df):,} have usable GDP normalization.")

        n1, n2 = st.columns(2)
        per_cap_corr = per_cap_df["ndgain_score_2023"].corr(per_cap_df["climate_finance_per_capita_usd"])
        gdp_corr = gdp_df["ndgain_score_2023"].corr(gdp_df["climate_finance_as_pct_gdp"])
        n1.metric("Pearson: finance per capita vs ND-GAIN Country Index", f"{per_cap_corr:+.3f}")
        n2.metric("Pearson: finance as % GDP vs ND-GAIN Country Index", f"{gdp_corr:+.3f}")

        st.caption("These are exploratory normalization measures, not official World Bank allocation metrics. GDP is current US dollars from World Development Indicators.")
        display_cols = [
            "ndgain_country", "ndgain_score_2023", "climate_finance_musd", "population_2023",
            "gdp_current_usd_2023", "climate_finance_per_capita_usd", "climate_finance_as_pct_gdp"
        ]
        st.dataframe(
            base_norm.sort_values("ndgain_score_2023")[display_cols].rename(columns={
                "ndgain_country": "Country", "ndgain_score_2023": "ND-GAIN",
                "climate_finance_musd": "Climate finance (US$M)", "population_2023": "Population (2023)",
                "gdp_current_usd_2023": "GDP (current US$)", "climate_finance_per_capita_usd": "Climate finance / capita (US$)",
                "climate_finance_as_pct_gdp": "Climate finance / GDP (%)"
            }),
            use_container_width=True, hide_index=True
        )
    except Exception as exc:
        st.warning("WDI enrichment could not be loaded in this environment. Run `python scripts/enrich_wdi.py` on a machine with internet access, or use the static FY23 dashboard.")
        st.caption(f"Technical detail: {exc}")

st.divider()
st.subheader("Lowest ND-GAIN Country Index countries: FY23 climate finance")
lowest_ndgain_countries = plot_df.sort_values("ndgain_score_2023").head(20)[
    ["ndgain_country", "ndgain_score_2023", "region", "n_projects", "climate_finance_musd", "climate_share_of_portfolio_pct"]
].rename(columns={
    "ndgain_country": "Country", "ndgain_score_2023": "ND-GAIN Country Index", "region": "Region",
    "n_projects": "# Projects", "climate_finance_musd": "Climate finance (US$M)",
    "climate_share_of_portfolio_pct": "Climate share (%)"
})
st.dataframe(lowest_ndgain_countries, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Country drill-down")
country_list = sorted(plot_df["ndgain_country"].dropna().unique())
default_country = "Bangladesh" if "Bangladesh" in country_list else country_list[0]
selected = st.selectbox("Choose a country", country_list, index=country_list.index(default_country))
sel_row = plot_df[plot_df["ndgain_country"] == selected].iloc[0]
sel_wb_label = sel_row["country_wb_label"]

cc1, cc2, cc3 = st.columns(3)
cc1.metric("ND-GAIN Country Index", f"{sel_row['ndgain_score_2023']:.1f}", help="Higher = higher overall ND-GAIN scores")
cc2.metric("FY23 climate finance", f"${sel_row['climate_finance_musd']:,.0f}M")
cc3.metric("Climate share", f"{sel_row['climate_share_of_portfolio_pct']:.1f}%")

sel_projects = projects[projects["country"] == sel_wb_label][
    ["project_name_display", "global_practice_display", "climate_finance_pct", "adaptation_musd", "mitigation_musd", "total_commitment_musd"]
].rename(columns={
    "project_name_display": "Project", "global_practice_display": "Sector", "climate_finance_pct": "Climate %",
    "adaptation_musd": "Adaptation (US$M)", "mitigation_musd": "Mitigation (US$M)", "total_commitment_musd": "Total (US$M)"
})
st.dataframe(sel_projects, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Sources: World Bank FY23 Project-Level Climate Co-Benefits Data; World Bank Development Finance with Climate Co-Benefits; "
    "ND-GAIN Country Index 2023. WDI normalization uses World Bank World Development Indicators. See README.md for exact URLs, validation, methodology, and limitations."
)
