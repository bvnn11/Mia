"""
ui_helpers.py — componente UI reutilizabile, stil Apple alb/mov.
"""

import streamlit as st


PURPLE = "#7C3AED"
PURPLE_LIGHT = "#EDE9FE"
PURPLE_MED = "#A78BFA"
TEXT_PRIMARY = "#1C1C1E"
TEXT_SECONDARY = "#6E6E73"
SURFACE = "#F5F3FF"
WHITE = "#FFFFFF"
RED = "#FF3B30"
GREEN = "#34C759"
ORANGE = "#FF9500"


GLOBAL_CSS = f"""
<style>
/* Reset & base */
.stApp {{
    background: {WHITE};
}}

/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid #E5E0FF;
}}

section[data-testid="stSidebar"] .stMarkdown p {{
    color: {TEXT_SECONDARY};
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    padding: 1rem 0 0.25rem;
}}

/* Butoane principale */
.stButton > button[kind="primary"] {{
    background: {PURPLE};
    border: none;
    border-radius: 12px;
    font-weight: 600;
    letter-spacing: -0.01em;
    padding: 0.6rem 1.5rem;
    transition: opacity 0.15s;
}}
.stButton > button[kind="primary"]:hover {{
    opacity: 0.85;
    background: {PURPLE};
}}

/* Form submit */
.stFormSubmitButton > button {{
    background: {PURPLE};
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    width: 100%;
    padding: 0.65rem;
    transition: opacity 0.15s;
}}
.stFormSubmitButton > button:hover {{
    opacity: 0.85;
    background: {PURPLE};
}}

/* Input fields */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > div > textarea {{
    border-radius: 10px !important;
    border: 1.5px solid #E5E0FF !important;
    background: {WHITE} !important;
}}

/* Metric cards */
[data-testid="metric-container"] {{
    background: {SURFACE};
    border-radius: 14px;
    padding: 1rem 1.2rem;
    border: 1px solid #E5E0FF;
}}

/* Dataframe */
.stDataFrame {{
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #E5E0FF;
}}

/* Alert boxes */
.stAlert {{
    border-radius: 12px;
}}

/* Nasconde il menu hamburger in production */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
</style>
"""


def inject_css():
    """Apelați o singură dată în app.py."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Header de pagină consistent."""
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<p style='color:{TEXT_SECONDARY}; margin-top:-0.5rem; font-size:0.95rem;'>{subtitle}</p>", unsafe_allow_html=True)
    st.markdown("<hr style='border:none; border-top:1px solid #E5E0FF; margin:0.75rem 0 1.5rem;'>", unsafe_allow_html=True)


def alert_stoc_minim(produse_sub_minim: list[dict]):
    """Banner de alertă pentru produse sub stoc minim."""
    if not produse_sub_minim:
        return
    names = ", ".join(p["Produs"] for p in produse_sub_minim[:5])
    extra = f" +{len(produse_sub_minim)-5} altele" if len(produse_sub_minim) > 5 else ""
    st.warning(f"⚠️ **Stoc minim atins:** {names}{extra}")


def badge(text: str, color: str = PURPLE_LIGHT, text_color: str = PURPLE) -> str:
    """Returnează HTML pentru un badge colorat."""
    return (
        f"<span style='background:{color}; color:{text_color}; "
        f"padding:2px 10px; border-radius:20px; font-size:0.8rem; "
        f"font-weight:600;'>{text}</span>"
    )


def card_metric(label: str, value: str, delta: str = "", delta_positive: bool = True):
    """Metric card cu delta colorat."""
    delta_color = GREEN if delta_positive else RED
    delta_html = f"<span style='color:{delta_color}; font-size:0.85rem;'>{delta}</span>" if delta else ""
    st.markdown(
        f"""
        <div style='background:{SURFACE}; border:1px solid #E5E0FF; border-radius:14px;
                    padding:1rem 1.2rem; margin-bottom:0.5rem;'>
            <div style='color:{TEXT_SECONDARY}; font-size:0.8rem; font-weight:600;
                        text-transform:uppercase; letter-spacing:0.06em;'>{label}</div>
            <div style='color:{TEXT_PRIMARY}; font-size:1.6rem; font-weight:700;
                        line-height:1.2; margin:0.25rem 0;'>{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
