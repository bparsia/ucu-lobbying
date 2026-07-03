"""Shared data loaders and helpers for UCU Lobbying app."""
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
DATA = ROOT / "data"

PARTY_COLOURS = {
    "Labour":                "#E4003B",
    "Labour (Co-op)":        "#E4003B",
    "Conservative":          "#0087DC",
    "Liberal Democrat":      "#FAA61A",
    "Scottish National Party": "#FDF38E",
    "Green Party":           "#02A95B",
    "Plaid Cymru":           "#005B54",
    "Democratic Unionist Party": "#D46A4C",
    "Sinn Féin":             "#326760",
    "Social Democratic & Labour Party": "#2AA82C",
    "Independent":           "#909090",
    "Your Party":            "#909090",
}


@st.cache_data
def load_institutions() -> pd.DataFrame:
    df = pd.read_csv(DATA / "institutions.csv", dtype={"ukprn": str})
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df


@st.cache_data
def load_constituencies() -> pd.DataFrame:
    df = pd.read_csv(DATA / "constituencies.csv", dtype={"pcon_code": str, "mp_id": str})
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    return df


@st.cache_data
def load_branches() -> pd.DataFrame:
    return pd.read_csv(DATA / "branches.csv", dtype={"ukprn": str})


@st.cache_data
def load_financials() -> pd.DataFrame:
    df = pd.read_csv(DATA / "financials.csv", dtype={"ukprn": str})
    numeric_cols = [
        "surplus_vs_income", "staff_vs_income", "unrestricted_vs_income",
        "net_liquidity_days", "external_borrowing_vs_income", "current_ratio",
        "debt_service_ratio", "avg_salary", "academic_salary",
        "vc_avg_salary", "vc_avg_remunerate",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_hepi() -> pd.DataFrame:
    df = pd.read_csv(DATA / "hepi_constituency.csv")
    # Normalise diacritic mismatch for join purposes
    df["constituency_name"] = df["constituency_name"].str.replace("ŵ", "ŵ", regex=False)
    numeric_cols = ["intl_students_firstyear", "gross_benefit", "costs",
                    "net_benefit", "net_benefit_per_resident", "region_impact"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_redundancies() -> pd.DataFrame:
    df = pd.read_csv(DATA / "redundancies.csv", dtype={"ukprn": str})
    df["posts_at_risk"] = pd.to_numeric(df["posts_at_risk"], errors="coerce")
    df["announcement_date"] = pd.to_datetime(df["announcement_date"], errors="coerce")
    return df


def latest_financials(fin: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent year's row per institution."""
    return (
        fin.sort_values("academic_year")
           .groupby("ukprn", as_index=False)
           .last()
    )


def fmt_gbp(v: float, decimals: int = 0) -> str:
    if pd.isna(v):
        return "n/a"
    if abs(v) >= 1_000_000_000:
        return f"£{v/1_000_000_000:.1f}bn"
    if abs(v) >= 1_000_000:
        return f"£{v/1_000_000:.1f}m"
    if abs(v) >= 1_000:
        return f"£{v/1_000:.1f}k"
    return f"£{v:,.{decimals}f}"


def fmt_pct(v: float) -> str:
    if pd.isna(v):
        return "n/a"
    return f"{v:+.1f}%" if v != 0 else "0.0%"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    import math
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def institutions_within_km(
    inst: pd.DataFrame,
    lat: float,
    lon: float,
    radius_km: float,
    exclude_ukprn: str | None = None,
) -> pd.DataFrame:
    """Return institutions within radius_km of (lat, lon), sorted by distance."""
    df = inst.dropna(subset=["latitude", "longitude"]).copy()
    if exclude_ukprn:
        df = df[df["ukprn"] != exclude_ukprn]
    df["distance_km"] = df.apply(
        lambda r: haversine_km(lat, lon, r["latitude"], r["longitude"]), axis=1
    )
    return df[df["distance_km"] <= radius_km].sort_values("distance_km")
