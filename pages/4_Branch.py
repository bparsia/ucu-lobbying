"""Branch drill-down — all data and talking points."""
import streamlit as st
import plotly.express as px
import pandas as pd
from utils import (
    load_institutions, load_constituencies, load_branches,
    load_financials, load_redundancies, load_hepi,
    fmt_gbp, fmt_pct, institutions_within_km,
    branch_slug, build_branch_slug_map,
)

inst  = load_institutions()
cons  = load_constituencies()
brs   = load_branches()
fin   = load_financials()
red   = load_redundancies()
hepi  = load_hepi()

# ── Branch selector ───────────────────────────────────────────────────────────
branch_options = (
    brs.dropna(subset=["ukprn"])
       .sort_values("branch_name")["branch_name"]
       .tolist()
)
slug_map = build_branch_slug_map(brs)
slug_param = st.query_params.get("branch", "")
default_branch = slug_map.get(slug_param, branch_options[0])
default_idx = branch_options.index(default_branch) if default_branch in branch_options else 0
selected_branch = st.selectbox("Select branch", branch_options, index=default_idx)
st.query_params["branch"] = branch_slug(selected_branch)
branch_row = brs[brs["branch_name"] == selected_branch].iloc[0]
ukprn = branch_row["ukprn"]

# Gather all data for this institution
inst_row = inst[inst["ukprn"] == ukprn]
if inst_row.empty:
    st.warning("No institution data found for this branch.")
    st.stop()
inst_row = inst_row.iloc[0]

con_name = inst_row["constituency_2024"]
con_row  = cons[cons["constituency_name"] == con_name]
con_row  = con_row.iloc[0] if not con_row.empty else None

hepi_row = hepi[hepi["constituency_name"] == con_name]
hepi_row = hepi_row.iloc[0] if not hepi_row.empty else None

fin_inst = fin[fin["ukprn"] == ukprn].sort_values("academic_year")
red_inst = red[red["ukprn"] == ukprn].sort_values("announcement_date")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_data, tab_points = st.tabs(["All data", "Talking points"])

# ════════════════════════════════════════════════════════════════════════════
with tab_data:
    st.header(inst_row["name"])
    st.caption(f"Branch: {selected_branch} ({branch_row['branch_code']})  ·  "
               f"UKPRN: {ukprn}  ·  {inst_row['postcode']}")

    # Institution + MP side by side
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Institution")
        st.write(f"**Town:** {inst_row['town']}")
        st.write(f"**Constituency:** {con_name or 'unknown'}")
        if inst_row.get("website"):
            st.write(f"**Website:** [{inst_row['website']}](https://{inst_row['website']})")
        st.write(f"**JNCHES:** {'Yes' if branch_row.get('jnches') == 'yes' else 'No'}")

    with c2:
        st.subheader("MP")
        if con_row is not None:
            st.write(f"**{con_row['mp_name']}** ({con_row['mp_party']})")
            st.write(f"**Constituency:** {con_row['constituency_name']}")
            mp_id = con_row["mp_id"]
            st.write(f"[Parliament profile](https://members.parliament.uk/member/{mp_id})")
        else:
            st.write("Constituency/MP data not available.")

    st.divider()

    # HEPI
    st.subheader("International student economic value")
    if hepi_row is not None:
        hc1, hc2, hc3 = st.columns(3)
        hc1.metric("Gross benefit", fmt_gbp(hepi_row["gross_benefit"]))
        hc2.metric("Net benefit", fmt_gbp(hepi_row["net_benefit"]))
        hc3.metric("Net benefit per resident", f"£{int(hepi_row['net_benefit_per_resident']):,}")
        st.metric("First-year international students", f"{int(hepi_row['intl_students_firstyear']):,}")
        st.caption("Source: HEPI 2024. Pre-2024 constituency boundaries.")
    else:
        st.info("No HEPI data for this constituency.")

    st.divider()

    # Financials time series
    st.subheader("Financial indicators over time")
    if not fin_inst.empty:
        latest_year = fin_inst["academic_year"].max()
        st.caption(f"Most recent data: {latest_year}")

        metrics = {
            "Surplus/deficit (% income)": "surplus_vs_income",
            "Staff costs (% income)":     "staff_vs_income",
            "Unrestricted reserves (% income)": "unrestricted_vs_income",
            "Net liquidity days":          "net_liquidity_days",
        }
        chart_cols = st.columns(2)
        for i, (label, col) in enumerate(metrics.items()):
            data = fin_inst[["academic_year", col]].dropna()
            if data.empty:
                continue
            fig = px.line(
                data, x="academic_year", y=col,
                markers=True,
                labels={"academic_year": "", col: label},
                height=220,
                title=label,
            )
            if col == "surplus_vs_income":
                fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.4)
            fig.update_layout(margin=dict(t=30, b=10))
            chart_cols[i % 2].plotly_chart(fig, use_container_width=True)

        # Salary data if available
        # avg_salary / academic_salary are in £k; vc_avg_salary is ratio of VC to avg staff
        sal = fin_inst[["academic_year", "avg_salary", "academic_salary"]].dropna(subset=["avg_salary"])
        if not sal.empty:
            st.subheader("Salary data (£k)")
            sal_melt = sal.melt("academic_year", var_name="Role", value_name="Salary (£k)")
            label_map = {"avg_salary": "Average (all staff)", "academic_salary": "Academic staff"}
            sal_melt["Role"] = sal_melt["Role"].map(label_map)
            fig_sal = px.line(
                sal_melt, x="academic_year", y="Salary (£k)",
                color="Role", markers=True,
                labels={"academic_year": ""},
                height=240,
            )
            fig_sal.update_layout(margin=dict(t=10, b=10))
            st.plotly_chart(fig_sal, use_container_width=True)

        vc_ratio_data = fin_inst[["academic_year", "vc_avg_salary"]].dropna(subset=["vc_avg_salary"])
        if not vc_ratio_data.empty:
            fig_vc = px.line(
                vc_ratio_data, x="academic_year", y="vc_avg_salary",
                markers=True, title="VC salary as multiple of average staff salary",
                labels={"academic_year": "", "vc_avg_salary": "VC / avg staff (×)"},
                height=220,
            )
            fig_vc.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig_vc, use_container_width=True)
    else:
        st.info("No financial data available for this institution.")

    st.divider()

    # Redundancies
    st.subheader("Redundancy history")
    if not red_inst.empty:
        for _, r in red_inst.iterrows():
            date_str = r["announcement_date"].strftime("%b %Y") if pd.notna(r["announcement_date"]) else "Date unknown"
            posts_str = f"{int(r['posts_at_risk']):,} posts" if pd.notna(r["posts_at_risk"]) else "posts not specified"
            label = f"**{date_str}** — {posts_str} ({r['compulsory']})"
            with st.expander(label):
                if r.get("notes"):
                    st.write(r["notes"])
                if r.get("source_url"):
                    st.write(f"[Source]({r['source_url']})")
    else:
        st.info("No redundancy entries for this institution.")

    st.divider()

    # Nearby institutions
    st.subheader("Nearby institutions")
    inst_lat = inst_row.get("latitude")
    inst_lon = inst_row.get("longitude")
    if pd.notna(inst_lat) and pd.notna(inst_lon):
        radius = st.slider("Radius (km)", 1, 50, 10, key="branch_radius")
        nearby = institutions_within_km(inst, inst_lat, inst_lon, radius, exclude_ukprn=ukprn)
        if nearby.empty:
            st.info(f"No other institutions within {radius} km.")
        else:
            nearby_full = nearby.merge(
                cons[["constituency_name", "mp_name", "mp_party"]],
                left_on="constituency_2024", right_on="constituency_name", how="left"
            )
            red_flags = red.groupby("ukprn")["compulsory"].apply(
                lambda x: "compulsory" in x.values
            ).reset_index().rename(columns={"compulsory": "has_compulsory"})
            nearby_full = nearby_full.merge(red_flags, on="ukprn", how="left")
            nearby_full["has_compulsory"] = nearby_full["has_compulsory"].fillna(False)

            tbl = nearby_full[["name", "distance_km", "constituency_2024",
                                "mp_name", "mp_party", "has_compulsory"]].copy()
            tbl["distance_km"] = tbl["distance_km"].apply(lambda v: f"{v:.1f} km")
            tbl["has_compulsory"] = tbl["has_compulsory"].map({True: "⚠️ Yes", False: ""})
            tbl.columns = ["Institution", "Distance", "Constituency", "MP", "Party", "Compulsory redundancies"]
            st.dataframe(tbl, use_container_width=True, hide_index=True)

            # Unique MPs across nearby institutions
            nearby_mps = nearby_full[["mp_name", "mp_party", "constituency_2024"]].dropna(subset=["mp_name"])
            nearby_mps = nearby_mps[nearby_mps["constituency_2024"] != con_name]
            nearby_mps = nearby_mps.drop_duplicates("mp_name")
            if not nearby_mps.empty:
                st.caption(f"**Additional MPs you could approach** (representing nearby constituencies):")
                for _, mp in nearby_mps.iterrows():
                    st.write(f"- {mp['mp_name']} ({mp['mp_party']}) — {mp['constituency_2024']}")
    else:
        st.info("No location data available for this institution.")


# ════════════════════════════════════════════════════════════════════════════
with tab_points:
    st.header(f"Talking points: {inst_row['name']}")
    st.caption("Auto-generated from data. Verify figures before use.")

    points = []

    # MP
    if con_row is not None:
        points.append(
            f"**Your MP is {con_row['mp_name']} ({con_row['mp_party']})**, "
            f"representing {con_row['constituency_name']}."
        )

    # HEPI
    if hepi_row is not None:
        net = fmt_gbp(hepi_row["net_benefit"])
        per_res = f"£{int(hepi_row['net_benefit_per_resident']):,}"
        students = f"{int(hepi_row['intl_students_firstyear']):,}"
        points.append(
            f"**International students contribute {net} net to {con_name}** — "
            f"{per_res} per resident — with {students} first-year international students "
            f"enrolled at institutions in this constituency."
        )

    # Financial health
    if not fin_inst.empty:
        latest = fin_inst.iloc[-1]
        year = latest["academic_year"]
        surplus = latest["surplus_vs_income"]
        liquidity = latest["net_liquidity_days"]
        staff = latest["staff_vs_income"]

        if pd.notna(surplus):
            direction = "surplus" if surplus >= 0 else "deficit"
            points.append(
                f"**In {year}, {inst_row['name']} reported a {direction} of {fmt_pct(surplus)} of income.** "
                + ("This indicates financial stress." if surplus < 0
                   else "Margins remain thin across the sector." if surplus < 3
                   else "")
            )
        if pd.notna(liquidity):
            points.append(
                f"**Net liquidity stands at {liquidity:.0f} days** ({year}). "
                + ("This is a low buffer." if liquidity < 60 else "")
            )
        if pd.notna(staff):
            points.append(
                f"**Staff costs represent {fmt_pct(staff)} of total income** ({year}), "
                f"reflecting the institution's dependence on its workforce."
            )

        # VC pay — vc_avg_salary is the ratio of VC salary to average staff salary (from kfi.csv)
        # avg_salary is in £k
        vc = fin_inst.dropna(subset=["vc_avg_salary"])
        if not vc.empty:
            vc_latest = vc.iloc[-1]
            vc_ratio = vc_latest["vc_avg_salary"]   # ratio: VC / avg staff
            vc_year  = vc_latest["academic_year"]
            avg_sal  = vc_latest.get("avg_salary")  # £k
            if pd.notna(vc_ratio):
                salary_str = ""
                if pd.notna(avg_sal) and avg_sal > 0:
                    vc_abs = vc_ratio * avg_sal  # £k
                    salary_str = f" (approximately £{vc_abs:,.0f}k)"
                points.append(
                    f"**The Vice-Chancellor's salary is {vc_ratio:.1f}× the average staff salary{salary_str}** "
                    f"({vc_year})."
                )

    # Redundancies
    if not red_inst.empty:
        total_posts = int(red_inst["posts_at_risk"].sum())
        n_compulsory = (red_inst["compulsory"] == "compulsory").sum()
        latest_red = red_inst.iloc[-1]
        date_str = latest_red["announcement_date"].strftime("%B %Y") if pd.notna(latest_red["announcement_date"]) else "recently"
        posts_str = f"at least {total_posts:,} posts at risk" if total_posts > 0 else "posts at risk"
        points.append(
            f"**{inst_row['name']} has announced redundancies across {len(red_inst)} separate rounds**, "
            f"with {posts_str} recorded. "
            + (f"**{n_compulsory} round(s) included compulsory redundancies.** " if n_compulsory else "")
            + f"The most recent announcement was in {date_str}."
        )

    # Render
    for i, point in enumerate(points, 1):
        st.markdown(f"{i}. {point}")

    st.divider()
    st.subheader("Suggested ask")
    mp_name = con_row["mp_name"] if con_row is not None else "your MP"
    st.markdown(
        f"Ask {mp_name} to:\n"
        "- **Oppose further cuts to HE funding** and press government to address the international "
        "student fee cap and visa environment which is threatening institutions' income.\n"
        "- **Raise the impact on the local economy** — international students bring significant "
        "economic value to this constituency that is put at risk by institutional financial distress.\n"
        "- **Support fair pay and job security** for HE staff, and call on employers to halt "
        "compulsory redundancies while sector-wide negotiations continue."
    )

    st.caption("Suggested ask is templated — edit as appropriate for your meeting.")
