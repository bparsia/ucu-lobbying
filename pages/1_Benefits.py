"""Benefits map — international student economic value by institution location."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils import (
    load_institutions, load_constituencies, load_hepi,
    fmt_gbp, PARTY_COLOURS,
)

st.title("International Student Economic Value")
st.caption("Source: HEPI 2024. Constituency-level data uses pre-2024 boundaries — "
           "figures are indicative where boundaries have changed.")

inst  = load_institutions()
cons  = load_constituencies()
hepi  = load_hepi()

# Join institutions → constituency → MP → HEPI
df = (
    inst.dropna(subset=["latitude", "longitude"])
        .merge(cons[["constituency_name", "mp_name", "mp_party"]],
               left_on="constituency_2024", right_on="constituency_name", how="left")
        .merge(hepi[["constituency_name", "net_benefit", "net_benefit_per_resident",
                      "gross_benefit", "intl_students_firstyear"]],
               left_on="constituency_2024", right_on="constituency_name", how="left")
)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    metric_label = st.radio(
        "Colour dots by",
        ["Net benefit (£)", "Net benefit per resident (£)", "First-year international students"],
        horizontal=True,
    )
with col_f2:
    party_filter = st.multiselect(
        "Filter by MP party", options=sorted(df["mp_party"].dropna().unique()),
        default=[],
    )

metric_map = {
    "Net benefit (£)":                    "net_benefit",
    "Net benefit per resident (£)":       "net_benefit_per_resident",
    "First-year international students":  "intl_students_firstyear",
}
metric_col = metric_map[metric_label]

plot_df = df.dropna(subset=[metric_col])
if party_filter:
    plot_df = plot_df[plot_df["mp_party"].isin(party_filter)]

# ── Map ───────────────────────────────────────────────────────────────────────
plot_df = plot_df.copy()
plot_df["dot_colour"] = plot_df["mp_party"].map(PARTY_COLOURS).fillna("#aaaaaa")
plot_df["hover"] = (
    "<b>" + plot_df["name"] + "</b><br>"
    + plot_df["constituency_2024"].fillna("") + "<br>"
    + "MP: " + plot_df["mp_name"].fillna("") + " (" + plot_df["mp_party"].fillna("") + ")<br>"
    + "Net benefit: " + plot_df["net_benefit"].apply(fmt_gbp) + "<br>"
    + "Per resident: £" + plot_df["net_benefit_per_resident"].apply(
        lambda v: f"{int(v):,}" if not __import__("pandas").isna(v) else "n/a") + "<br>"
    + "Intl students (first year): " + plot_df["intl_students_firstyear"].apply(
        lambda v: f"{int(v):,}" if not __import__("pandas").isna(v) else "n/a")
)

fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lat=plot_df["latitude"],
    lon=plot_df["longitude"],
    mode="markers",
    marker=dict(
        size=10,
        color=plot_df[metric_col],
        colorscale=[[0, "#f5f0e8"], [1, "#c9953a"]],
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
fig.update_layout(height=580, margin=dict(t=0, b=0, l=0, r=0))
st.plotly_chart(fig, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────────────────────
st.subheader("All institutions")
tbl = plot_df[["name", "constituency_2024", "mp_name", "mp_party",
               "intl_students_firstyear", "net_benefit", "net_benefit_per_resident"]].copy()
tbl.columns = ["Institution", "Constituency", "MP", "Party",
               "Intl students", "Net benefit", "Per resident (£)"]
tbl["Net benefit"] = tbl["Net benefit"].apply(fmt_gbp)
tbl["Per resident (£)"] = tbl["Per resident (£)"].apply(
    lambda v: f"{int(v):,}" if not __import__("pandas").isna(v) else "n/a")
tbl["Intl students"] = tbl["Intl students"].apply(
    lambda v: f"{int(v):,}" if not __import__("pandas").isna(v) else "n/a")
st.dataframe(tbl.sort_values("Institution"), use_container_width=True, hide_index=True)
