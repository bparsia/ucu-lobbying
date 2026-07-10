"""Redundancies map — job losses across the sector."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import (
    load_institutions, load_constituencies, load_redundancies,
    load_branches, PARTY_COLOURS,
)

st.title("Redundancies Across the Sector")
st.caption("Source: QMUCU tracker (qmucu.org). Data for institutions A–N is more detailed; "
           "O–Z entries may be less precise. Last reviewed June 2026.")

inst = load_institutions()
cons = load_constituencies()
red  = load_redundancies()
brs  = load_branches()

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
with col_f1:
    type_filter = st.multiselect(
        "Redundancy type",
        ["compulsory", "mixed", "voluntary"],
        default=["compulsory", "mixed", "voluntary"],
    )
with col_f2:
    party_filter = st.multiselect(
        "MP party", options=sorted(cons["mp_party"].dropna().unique()), default=[]
    )

# Aggregate redundancies to institution level
red_filt = red[red["compulsory"].isin(type_filter)] if type_filter else red

red_agg = (
    red_filt.groupby("ukprn")
    .agg(
        total_posts=("posts_at_risk", "sum"),
        announcements=("institution_name", "count"),
        has_compulsory=("compulsory", lambda x: "compulsory" in x.values),
        latest_date=("announcement_date", "max"),
        institution_name=("institution_name", "first"),
    )
    .reset_index()
)
red_agg["total_posts"] = red_agg["total_posts"].replace(0, pd.NA)

# Join to institutions
df = (
    inst.dropna(subset=["latitude", "longitude"])
        .merge(red_agg, on="ukprn", how="inner")
        .merge(cons[["constituency_name", "mp_name", "mp_party"]],
               left_on="constituency_2024", right_on="constituency_name", how="left")
)

if party_filter:
    df = df[df["mp_party"].isin(party_filter)]

# ── Map ───────────────────────────────────────────────────────────────────────
df = df.copy()
df["marker_colour"] = df["has_compulsory"].map({True: "#c0392b", False: "#e67e22"})
df["latest_date_str"] = df["latest_date"].dt.strftime("%b %Y").fillna("date unknown")
df["posts_str"] = df["total_posts"].apply(
    lambda v: f"{int(v):,}" if pd.notna(v) else "not specified"
)
df["hover"] = (
    "<b>" + df["name"] + "</b><br>"
    + df["constituency_2024"].fillna("") + "<br>"
    + "MP: " + df["mp_name"].fillna("") + " (" + df["mp_party"].fillna("") + ")<br>"
    + "Posts at risk: " + df["posts_str"] + "<br>"
    + "Announcements: " + df["announcements"].astype(str) + "<br>"
    + "Latest: " + df["latest_date_str"] + "<br>"
    + "Includes compulsory: " + df["has_compulsory"].map({True: "Yes", False: "No"})
)

fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lat=df["latitude"],
    lon=df["longitude"],
    mode="markers",
    marker=dict(
        size=(pd.to_numeric(df["total_posts"], errors="coerce").fillna(df["announcements"] * 50).clip(upper=1000) / 1000 * 20 + 6).tolist(),
        color=df["marker_colour"],
        line=dict(width=0.5, color="white"),
        opacity=0.85,
    ),
    text=df["hover"],
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

# Legend note
st.plotly_chart(fig, use_container_width=True)
st.caption("Red = includes compulsory redundancies. Orange = voluntary/mixed only. "
           "Dot size reflects posts at risk (estimated where not specified).")

# ── Posts at risk over time ────────────────────────────────────────────────────
type_colours = {"compulsory": "#c0392b", "mixed": "#e67e22", "voluntary": "#27ae60"}

red_dated = red_filt.dropna(subset=["announcement_date"]).copy()
red_dated["quarter"] = red_dated["announcement_date"].dt.to_period("Q").dt.to_timestamp()

timeline = (
    red_dated.groupby(["quarter", "compulsory"])["posts_at_risk"]
    .sum().reset_index()
)
total_known = int(red_filt["posts_at_risk"].sum())
n_unknown = red_filt["posts_at_risk"].isna().sum()

mc1, mc2 = st.columns(2)
mc1.metric("Total posts at risk (known figures)", f"{total_known:,}")
mc2.metric("Announcements without post count", n_unknown)

st.subheader("Posts at risk by quarter")
fig_t = go.Figure()
for typ, colour in type_colours.items():
    d = timeline[timeline["compulsory"] == typ]
    fig_t.add_trace(go.Bar(
        x=d["quarter"], y=d["posts_at_risk"],
        name=typ.capitalize(), marker_color=colour,
    ))
fig_t.update_layout(
    barmode="stack",
    height=300,
    margin=dict(t=10, b=10),
    legend_title_text="Type",
    yaxis=dict(title="Posts at risk", rangemode="tozero"),
)
st.plotly_chart(fig_t, use_container_width=True)
st.caption("Only announcements with known posts-at-risk figures are included in this chart.")

# ── Table ───────────────────────────────────────���─────────────────────────────
# ── Savings targets ───────────────────────────────────────────────────────────
st.subheader("Reported savings targets / deficits")
savings = (
    red_filt[red_filt.get("savings_target_gbpm", pd.Series(dtype=float)).notna()]
    .merge(inst[["ukprn", "name"]], on="ukprn", how="left")
    .groupby(["ukprn", "name"], as_index=False)["savings_target_gbpm"].max()
    .sort_values("savings_target_gbpm", ascending=False)
) if "savings_target_gbpm" in red_filt.columns else pd.DataFrame()
if savings.empty:
    st.info("No savings figures in current filter.")
else:
    total_savings = savings["savings_target_gbpm"].sum()
    st.metric("Total reported savings targets (known figures)", f"£{total_savings:,.0f}m")
    stbl = savings[["name", "savings_target_gbpm"]].copy()
    stbl.columns = ["Institution", "Savings target (£m)"]
    st.dataframe(stbl, use_container_width=True, hide_index=True)
    st.caption("Parsed from QMUCU tracker notes. Figures may relate to different years or programme scopes. Manual verification recommended.")

st.subheader("All redundancy entries")
tbl = red_filt.merge(inst[["ukprn", "name", "constituency_2024"]], on="ukprn", how="left")
tbl = tbl.merge(cons[["constituency_name", "mp_name", "mp_party"]],
                left_on="constituency_2024", right_on="constituency_name", how="left")
tbl["announcement_date"] = tbl["announcement_date"].dt.strftime("%b %Y")
tbl["posts_at_risk"] = tbl["posts_at_risk"].apply(
    lambda v: f"{int(v):,}" if pd.notna(v) else ""
)
tbl = tbl[["name", "announcement_date", "posts_at_risk", "compulsory",
           "constituency_2024", "mp_name", "mp_party", "notes", "source_url"]].copy()
tbl.columns = ["Institution", "Date", "Posts", "Type",
               "Constituency", "MP", "Party", "Notes", "Source"]
st.dataframe(
    tbl.sort_values(["Institution", "Date"]).reset_index(drop=True),
    use_container_width=True, hide_index=True,
    column_config={"Source": st.column_config.LinkColumn("Source", display_text="→ Source")},
)
