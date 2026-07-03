"""MP drill-down — institutions in and near a constituency."""
import streamlit as st
import pandas as pd
from utils import (
    load_institutions, load_constituencies, load_branches,
    load_financials, load_redundancies, load_hepi,
    latest_financials, fmt_gbp, fmt_pct, institutions_within_km,
    mp_slug, build_mp_slug_map, branch_slug,
)

inst  = load_institutions()
cons  = load_constituencies()
brs   = load_branches()
fin   = load_financials()
red   = load_redundancies()
hepi  = load_hepi()
latest = latest_financials(fin)

# UKPRN -> first branch slug lookup (reused in tables)
_ukprn_to_bslug = (
    brs.dropna(subset=["ukprn"])
       .assign(bslug=lambda d: d["branch_name"].map(branch_slug))
       .groupby("ukprn")["bslug"].first()
)

def _branch_url(ukprn):
    slug = _ukprn_to_bslug.get(ukprn)
    return f"Branch?branch={slug}" if slug else None

def _mp_url(name):
    return f"MP?mp={mp_slug(name)}" if pd.notna(name) else None

# ── MP selector ───────────────────────────────────────────────────────────────
mp_options = cons.sort_values("mp_name")["mp_name"].tolist()
slug_map = build_mp_slug_map(cons)
slug_param = st.query_params.get("mp", "")
default_mp = slug_map.get(slug_param, mp_options[0])
default_idx = mp_options.index(default_mp) if default_mp in mp_options else 0
selected_mp = st.selectbox("Select MP", mp_options, index=default_idx)
st.query_params["mp"] = mp_slug(selected_mp)
con_row = cons[cons["mp_name"] == selected_mp].iloc[0]
con_name = con_row["constituency_name"]

st.header(f"{selected_mp}")
st.subheader(f"{con_name} · {con_row['mp_party']}")

mp_id = con_row["mp_id"]
st.write(f"[Parliament profile](https://members.parliament.uk/member/{mp_id})")

# HEPI for this constituency
hepi_row = hepi[hepi["constituency_name"] == con_name]
hepi_row = hepi_row.iloc[0] if not hepi_row.empty else None
if hepi_row is not None:
    hc1, hc2, hc3 = st.columns(3)
    hc1.metric("Intl student net benefit", fmt_gbp(hepi_row["net_benefit"]))
    hc2.metric("Per resident", f"£{int(hepi_row['net_benefit_per_resident']):,}")
    hc3.metric("First-year intl students", f"{int(hepi_row['intl_students_firstyear']):,}")
    st.caption("Source: HEPI 2024. Pre-2024 constituency boundaries.")

st.divider()

# ── Institutions in constituency ───────────────────────────────────────────────
inst_in = inst[inst["constituency_2024"] == con_name]

st.subheader(f"Institutions in {con_name}")
if inst_in.empty:
    st.info("No HE institutions with a registered address in this constituency.")
else:
    _show = inst_in.merge(latest[["ukprn", "surplus_vs_income", "academic_year"]], on="ukprn", how="left")
    _show = _show.merge(brs[["ukprn", "branch_name"]].dropna(subset=["ukprn"]), on="ukprn", how="left")
    red_flags = red.groupby("ukprn")["compulsory"].apply(lambda x: "compulsory" in x.values).reset_index()
    red_flags.columns = ["ukprn", "has_compulsory"]
    _show = _show.merge(red_flags, on="ukprn", how="left")
    _show["surplus_vs_income"] = _show["surplus_vs_income"].apply(fmt_pct)
    _show["has_compulsory"] = _show["has_compulsory"].fillna(False).map({True: "⚠️ Yes", False: ""})
    _show["branch_url"] = _show["ukprn"].map(_branch_url)
    tbl = _show[["name", "branch_url", "branch_name", "surplus_vs_income", "academic_year", "has_compulsory"]].copy()
    tbl.columns = ["Institution", "Branch link", "Branch", "Surplus/deficit", "Year", "Compulsory redundancies"]
    st.dataframe(
        tbl, use_container_width=True, hide_index=True,
        column_config={"Branch link": st.column_config.LinkColumn("Branch link", display_text="→ Branch")},
    )

st.divider()

# ── Nearby institutions ────────────────────────────────────────────────────────
st.subheader("Nearby institutions")

# Use centroid of this constituency as the reference point
con_lat = con_row.get("latitude")
con_lon = con_row.get("longitude")

# If institutions exist in constituency, use their mean location instead
if not inst_in.empty and inst_in["latitude"].notna().any():
    con_lat = inst_in["latitude"].mean()
    con_lon = inst_in["longitude"].mean()
    st.caption("Distance measured from institution(s) in constituency.")
else:
    st.caption("No institution in this constituency — distance measured from constituency centroid.")

if pd.notna(con_lat) and pd.notna(con_lon):
    radius = st.slider("Radius (km)", 1, 50, 10, key="mp_radius")

    # Exclude institutions already in constituency
    in_ukprns = inst_in["ukprn"].tolist()
    nearby = institutions_within_km(inst, con_lat, con_lon, radius)
    nearby = nearby[~nearby["ukprn"].isin(in_ukprns)]

    if nearby.empty:
        st.info(f"No institutions within {radius} km (outside this constituency).")
    else:
        nearby_full = nearby.merge(
            cons[["constituency_name", "mp_name", "mp_party"]],
            left_on="constituency_2024", right_on="constituency_name", how="left"
        ).merge(
            latest[["ukprn", "surplus_vs_income", "academic_year"]], on="ukprn", how="left"
        ).merge(
            brs[["ukprn", "branch_name"]].dropna(subset=["ukprn"]), on="ukprn", how="left"
        )
        red_flags2 = red.groupby("ukprn")["compulsory"].apply(lambda x: "compulsory" in x.values).reset_index()
        red_flags2.columns = ["ukprn", "has_compulsory"]
        nearby_full = nearby_full.merge(red_flags2, on="ukprn", how="left")
        nearby_full["has_compulsory"] = nearby_full["has_compulsory"].fillna(False).map({True: "⚠️ Yes", False: ""})
        nearby_full["surplus_vs_income"] = nearby_full["surplus_vs_income"].apply(fmt_pct)
        nearby_full["distance_km"] = nearby_full["distance_km"].apply(lambda v: f"{v:.1f} km")
        nearby_full["branch_url"] = nearby_full["ukprn"].map(_branch_url)
        nearby_full["mp_url"] = nearby_full["mp_name"].map(_mp_url)

        tbl2 = nearby_full[["name", "branch_url", "distance_km", "branch_name", "constituency_2024",
                             "mp_name", "mp_url", "surplus_vs_income", "academic_year", "has_compulsory"]].copy()
        tbl2.columns = ["Institution", "Branch link", "Distance", "Branch", "Constituency",
                        "MP", "MP link", "Surplus/deficit", "Year", "Compulsory redundancies"]
        st.dataframe(
            tbl2, use_container_width=True, hide_index=True,
            column_config={
                "Branch link": st.column_config.LinkColumn("Branch link", display_text="→ Branch"),
                "MP link":     st.column_config.LinkColumn("MP link",     display_text="→ MP page"),
            },
        )
else:
    st.info("No centroid data available for this constituency.")
