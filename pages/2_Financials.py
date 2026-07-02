"""Financials map — institutional financial health."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import (
    load_institutions, load_constituencies, load_financials,
    load_branches, latest_financials, fmt_pct, PARTY_COLOURS,
)

st.title("Institutional Financial Health")

inst  = load_institutions()
cons  = load_constituencies()
fin   = load_financials()
brs   = load_branches()

latest = latest_financials(fin)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
with col_f1:
    metric_label = st.selectbox("Metric", [
        "Surplus/deficit as % of income",
        "Staff costs as % of income",
        "Unrestricted reserves as % of income",
        "Net liquidity days",
    ])
with col_f2:
    party_filter = st.multiselect("MP party", options=sorted(cons["mp_party"].dropna().unique()), default=[])

metric_map = {
    "Surplus/deficit as % of income":          "surplus_vs_income",
    "Staff costs as % of income":              "staff_vs_income",
    "Unrestricted reserves as % of income":    "unrestricted_vs_income",
    "Net liquidity days":                      "net_liquidity_days",
}
metric_col = metric_map[metric_label]

# Build plot dataframe
df = (
    inst.dropna(subset=["latitude", "longitude"])
        .merge(latest[["ukprn", metric_col, "academic_year"]],
               on="ukprn", how="left")
        .merge(cons[["constituency_name", "mp_name", "mp_party"]],
               left_on="constituency_2024", right_on="constituency_name", how="left")
        .merge(brs[["ukprn", "branch_name"]].dropna(subset=["ukprn"]),
               on="ukprn", how="left")
)

if party_filter:
    df = df[df["mp_party"].isin(party_filter)]

plot_df = df.dropna(subset=[metric_col])

# ── Map ───────────────────────────────────────────────────────────────────────
is_surplus = metric_col == "surplus_vs_income"
colorscale = "RdYlGn" if is_surplus else "YlOrRd"

import pandas as _pd
def _fmt(v, col):
    if _pd.isna(v):
        return "n/a"
    if col in ("surplus_vs_income", "staff_vs_income", "unrestricted_vs_income"):
        return fmt_pct(v)
    return f"{v:.0f} days"

plot_df = plot_df.copy()
plot_df["hover"] = (
    "<b>" + plot_df["name"] + "</b><br>"
    + plot_df["constituency_2024"].fillna("") + "<br>"
    + "MP: " + plot_df["mp_name"].fillna("") + " (" + plot_df["mp_party"].fillna("") + ")<br>"
    + metric_label + ": " + plot_df[metric_col].apply(lambda v: _fmt(v, metric_col)) + "<br>"
    + "Year: " + plot_df["academic_year"].fillna("")
)

fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lat=plot_df["latitude"],
    lon=plot_df["longitude"],
    mode="markers",
    marker=dict(
        size=10,
        color=plot_df[metric_col],
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(title=metric_label),
        line=dict(width=0.5, color="white"),
    ),
    text=plot_df["hover"],
    hoverinfo="text",
))
fig.update_geos(
    scope="europe",
    center=dict(lat=54.5, lon=-3),
    projection_scale=6,
    showland=True, landcolor="#f0f0f0",
    showcoastlines=True, coastlinecolor="#cccccc",
    showcountries=True, countrycolor="#dddddd",
    showframe=False,
)
fig.update_layout(height=560, margin=dict(t=0, b=0, l=0, r=0))
st.plotly_chart(fig, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────────────────────
st.subheader("All institutions")
tbl = plot_df[["name", "branch_name", "constituency_2024", "mp_name", "mp_party",
               metric_col, "academic_year"]].copy()
tbl[metric_col] = tbl[metric_col].apply(lambda v: _fmt(v, metric_col))
tbl.columns = ["Institution", "Branch", "Constituency", "MP", "Party", metric_label, "Year"]
st.dataframe(
    tbl.sort_values(metric_label).reset_index(drop=True),
    use_container_width=True, hide_index=True,
)
