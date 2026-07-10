"""Overview — sector at a glance."""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import (
    load_institutions, load_constituencies, load_branches,
    load_financials, load_redundancies, load_hepi,
    latest_financials, fmt_gbp, PARTY_COLOURS,
)

st.title("UCU Lobbying — Sector Overview")

inst  = load_institutions()
cons  = load_constituencies()
brs   = load_branches()
fin   = load_financials()
red   = load_redundancies()
hepi  = load_hepi()
latest = latest_financials(fin)

# ── Headline metrics ──────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

n_inst   = len(inst)
n_branch = len(brs)
n_cons   = inst["constituency_2024"].nunique()
n_red_inst = red["institution_name"].nunique()
total_posts = int(red["posts_at_risk"].sum())

c1.metric("HE Institutions", n_inst)
c2.metric("UCU Branches (JNCHES)", n_branch)
c3.metric("Constituencies with HE", n_cons)
c4.metric("Institutions with redundancies", n_red_inst)
c5.metric("Posts at risk (known)", f"{total_posts:,}")

st.divider()

# ── Two columns: financials + party breakdown ─────────────────────────────────
left, right = st.columns(2)

with left:
    st.subheader("Financial health — latest year")
    yr_col = "academic_year"
    most_recent = latest["academic_year"].max()
    st.caption(f"Most recent data: {most_recent}")

    latest_named = latest.merge(inst[["ukprn", "name"]], on="ukprn", how="left")
    surplus = latest_named["surplus_vs_income"].dropna()

    bins   = [-float("inf"), -5, 0, 3, float("inf")]
    labels = ["Deficit >5%", "Deficit 0–5%", "Surplus 0–3%", "Surplus >3%"]
    cats   = pd.cut(surplus, bins=bins, labels=labels)
    counts = cats.value_counts().reindex(labels)

    colours = ["#c0392b", "#e67e22", "#27ae60", "#1a6b3a"]
    fig = px.bar(
        x=counts.index, y=counts.values,
        color=counts.index,
        color_discrete_sequence=colours,
        labels={"x": "", "y": "Institutions"},
        height=280,
    )
    fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("MPs in HE constituencies — by party")
    he_cons = inst["constituency_2024"].dropna().unique()
    mp_he = cons[cons["constituency_name"].isin(he_cons)]
    party_counts = mp_he["mp_party"].value_counts().reset_index()
    party_counts.columns = ["party", "count"]
    colours_map = [PARTY_COLOURS.get(p, "#aaaaaa") for p in party_counts["party"]]
    fig2 = px.bar(
        party_counts, x="count", y="party", orientation="h",
        color="party",
        color_discrete_map=PARTY_COLOURS,
        labels={"count": "MPs", "party": ""},
        height=280,
    )
    fig2.update_layout(showlegend=False, margin=dict(t=10, b=10))
    fig2.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Redundancy timeline ───────────────────────────────────────────────────────
st.subheader("Posts at risk over time")

type_colours = {"compulsory": "#c0392b", "mixed": "#e67e22", "voluntary": "#27ae60"}

red_dated = red.dropna(subset=["announcement_date"]).copy()
red_dated["quarter"] = red_dated["announcement_date"].dt.to_period("Q").dt.to_timestamp()

timeline = (
    red_dated.groupby(["quarter", "compulsory"])["posts_at_risk"]
    .sum().reset_index()
)
# Cumulative across all types
cumulative = (
    red_dated.groupby("quarter")["posts_at_risk"].sum()
    .sort_index().cumsum().reset_index()
)

fig3 = go.Figure()
for typ, colour in type_colours.items():
    d = timeline[timeline["compulsory"] == typ]
    fig3.add_trace(go.Bar(
        x=d["quarter"], y=d["posts_at_risk"],
        name=typ.capitalize(), marker_color=colour,
    ))
fig3.add_trace(go.Scatter(
    x=cumulative["quarter"], y=cumulative["posts_at_risk"],
    name="Cumulative", mode="lines",
    line=dict(color="#2c3e50", width=2, dash="dot"),
    yaxis="y2",
))
fig3.update_layout(
    barmode="stack",
    height=260,
    margin=dict(t=10, b=10),
    legend_title_text="Type",
    yaxis=dict(title="Posts at risk"),
    yaxis2=dict(title="Cumulative", overlaying="y", side="right", showgrid=False),
)
st.plotly_chart(fig3, use_container_width=True)
st.caption("Posts at risk where reported. Many announcements do not specify exact numbers.")

st.divider()

# ── HEPI total ────────────────────────────────────────────────────────────────
st.subheader("International student economic value")
total_net = hepi["net_benefit"].sum()
total_gross = hepi["gross_benefit"].sum()
total_students = hepi["intl_students_firstyear"].sum()

hc1, hc2, hc3 = st.columns(3)
hc1.metric("Total gross benefit", fmt_gbp(total_gross))
hc2.metric("Total net benefit", fmt_gbp(total_net))
hc3.metric("First-year international students", f"{int(total_students):,}")
st.caption("Source: HEPI 2024. Uses pre-2024 constituency boundaries.")
