"""
app.py — punct de intrare principal RestaurantOS.

Gestionează:
- Guard autentificare (toate paginile necesită login)
- Navigare cu st.navigation / st.Page
- CSS global injectat o singură dată
"""

import streamlit as st
from auth import is_logged_in, show_login_page, get_restaurant_name
from ui_helpers import inject_css

st.set_page_config(
    page_title="RestaurantOS",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Guard autentificare ──────────────────────────────────────────────────────
if not is_logged_in():
    show_login_page()
    st.stop()

# ── Sidebar header ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style='padding: 1rem 0.5rem 0.5rem;'>
            <div style='font-size:1.4rem;'>🍽️</div>
            <div style='font-weight:700; font-size:1rem; color:#1C1C1E; margin-top:0.25rem;'>
                RestaurantOS
            </div>
            <div style='font-size:0.8rem; color:#6E6E73; margin-top:0.1rem;'>
                {get_restaurant_name()}
            </div>
        </div>
        <hr style='border:none; border-top:1px solid #E5E0FF; margin:0.75rem 0;'>
        """,
        unsafe_allow_html=True,
    )

# ── Navigare ─────────────────────────────────────────────────────────────────
pages = [
    st.Page("pages/1_Dashboard.py",   title="Dashboard",    icon="📊", default=True),
    st.Page("pages/2_Stoc.py",        title="Stoc",         icon="📦"),
    st.Page("pages/3_Retetar.py",     title="Rețetar",      icon="📖"),
    st.Page("pages/4_Facturi.py",     title="Facturi",      icon="🧾"),
    st.Page("pages/5_Vanzari.py",     title="Vânzări",      icon="💰"),
    st.Page("pages/6_Simulator.py",   title="Simulator",    icon="🧮"),
    st.Page("pages/7_Configurare.py", title="Configurare",  icon="⚙️"),
]

pg = st.navigation(pages)
pg.run()
