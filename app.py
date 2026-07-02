from pathlib import Path
import streamlit as st
from branding.branding import apply_branding

st.set_page_config(
    page_title="UCU Lobbying",
    page_icon=str(Path(__file__).parent / "branding/assets/ucuc-6.png"),
    layout="wide",
)

apply_branding(page_title="UCU Lobbying")

pages = [
    st.Page("pages/0_Overview.py",     title="Overview",       icon="📊", default=True),
    st.Page("pages/1_Benefits.py",     title="Benefits",       icon="🌍"),
    st.Page("pages/2_Financials.py",   title="Financials",     icon="💰"),
    st.Page("pages/3_Redundancies.py", title="Redundancies",   icon="⚠️"),
    st.Page("pages/4_Branch.py",       title="Branch",         icon="🏛️"),
    st.Page("pages/5_About.py",        title="About",          icon="ℹ️"),
]

pg = st.navigation(pages)
pg.run()
