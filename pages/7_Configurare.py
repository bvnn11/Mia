"""
pages/7_Configurare.py — setări fiscale și operaționale per restaurant.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id, get_restaurant_name, logout
from sheets import read_tab, rows_to_dicts, overwrite_tab, TAB_CONFIG
from ui_helpers import inject_css, page_header

st.set_page_config(page_title="Configurare", page_icon="⚙️", layout="wide")
inject_css()

HEADERS_CONFIG = ["Cheie", "Valoare"]

REGIMURI = {
    "Microîntreprindere 1% (cifră afaceri < 500k EUR, 1 angajat)": "micro1",
    "Microîntreprindere 3% (fără angajați)": "micro3",
    "Impozit pe profit 16%": "profit16",
}
COTE_TVA = {"9% (restaurante)": 0.09, "19% (standard)": 0.19, "5%": 0.05}


def show():
    sid = get_spreadsheet_id()
    page_header("Configurare", f"Setări fiscale și operaționale — {get_restaurant_name()}")

    with st.spinner("Se încarcă configurarea..."):
        config_rows = read_tab(sid, TAB_CONFIG)

    config = {r["Cheie"]: r["Valoare"] for r in rows_to_dicts(config_rows) if r.get("Cheie")}

    def _get(key, default=""):
        return config.get(key, default)

    with st.form("form_config"):
        st.markdown("#### Regim fiscal")
        regim_label = st.selectbox(
            "Regim impozitare firmă",
            list(REGIMURI.keys()),
            index=list(REGIMURI.values()).index(_get("regim_fiscal", "micro1"))
            if _get("regim_fiscal", "micro1") in REGIMURI.values() else 0,
        )

        cota_tva_label = st.selectbox(
            "Cotă TVA",
            list(COTE_TVA.keys()),
            index=0,
        )

        c1, c2 = st.columns(2)
        with c1:
            cota_dividend = st.number_input(
                "Cotă impozit dividende (%)",
                min_value=0.0, max_value=50.0, step=0.5,
                value=float(_get("cota_dividend", "0.08")) * 100,
            )
        with c2:
            nr_clienti = st.number_input(
                "Clienți estimați / lună",
                min_value=1, step=10,
                value=int(_get("nr_clienti_luna", "300") or "300"),
            )

        st.markdown("#### Cheltuieli fixe lunare")
        c3, c4, c5 = st.columns(3)
        with c3:
            chirie = st.number_input("Chirie (lei/lună)", min_value=0.0, step=100.0,
                                      value=float(_get("chirie_lunara", "0") or "0"))
        with c4:
            salarii = st.number_input("Salarii (lei/lună)", min_value=0.0, step=100.0,
                                       value=float(_get("salarii_lunare", "0") or "0"))
        with c5:
            utilitati = st.number_input("Utilități (lei/lună)", min_value=0.0, step=50.0,
                                         value=float(_get("utilitati_lunare", "0") or "0"))

        submitted = st.form_submit_button("💾 Salvează configurarea", use_container_width=True)

    if submitted:
        new_config = {
            "regim_fiscal": REGIMURI[regim_label],
            "cota_tva": str(COTE_TVA[cota_tva_label]),
            "cota_dividend": str(cota_dividend / 100),
            "nr_clienti_luna": str(int(nr_clienti)),
            "chirie_lunara": str(chirie),
            "salarii_lunare": str(salarii),
            "utilitati_lunare": str(utilitati),
        }
        rows = [HEADERS_CONFIG] + [[k, v] for k, v in new_config.items()]
        overwrite_tab(sid, TAB_CONFIG, rows)
        st.success("✅ Configurare salvată.")
        st.rerun()

    # ── Rezumat ──────────────────────────────────────────────────────────
    if config:
        st.markdown("---")
        st.markdown("#### Configurare curentă")
        total_fix_lunar = (
            float(_get("chirie_lunara", "0") or "0") +
            float(_get("salarii_lunare", "0") or "0") +
            float(_get("utilitati_lunare", "0") or "0")
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Cheltuieli fixe / lună", f"{total_fix_lunar:,.0f} lei")
        with col2:
            st.metric("Cheltuieli fixe / zi", f"{total_fix_lunar/30:,.0f} lei")
        with col3:
            st.metric("Regim fiscal activ", _get("regim_fiscal", "—").upper())

    # ── Logout ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Sesiune")
    if st.button("🚪 Deconectare", type="secondary"):
        logout()


show()
