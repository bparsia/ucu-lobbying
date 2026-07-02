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
        size=df["announcements"].clip(upper=8) * 3 + 6,
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
           "Dot size reflects number of separate announcements.")

# ── Table ───────────────────────────────────────���─────────────────────────────
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
)
