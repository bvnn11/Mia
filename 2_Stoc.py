"""
pages/2_Stoc.py — gestionare produse/ingrediente.
"""

import streamlit as st
import pandas as pd
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id
from sheets import (
    read_tab, rows_to_dicts, dicts_to_rows,
    append_rows, overwrite_tab, TAB_STOC,
)
from ui_helpers import inject_css, page_header

st.set_page_config(page_title="Stoc", page_icon="📦", layout="wide")
inject_css()

HEADERS = ["Produs", "Cantitate", "Unitate", "Pret_Unitar", "Data", "Stoc_Minim"]
UNITATI = ["kg", "g", "l", "ml", "buc"]


def show():
    sid = get_spreadsheet_id()
    page_header("Stoc", "Produse și ingrediente disponibile")

    with st.spinner("Se încarcă stocul..."):
        rows = read_tab(sid, TAB_STOC)

    stoc = rows_to_dicts(rows)
    df = pd.DataFrame(stoc) if stoc else pd.DataFrame(columns=HEADERS)

    # ── Alertă stoc minim ────────────────────────────────────────────────
    if stoc:
        sub_minim = []
        for p in stoc:
            try:
                if float(p.get("Cantitate", 0) or 0) < float(p.get("Stoc_Minim", 0) or 0):
                    sub_minim.append(p["Produs"])
            except ValueError:
                pass
        if sub_minim:
            st.warning(f"⚠️ Sub stoc minim: **{', '.join(sub_minim[:8])}**")

    # ── Tabel stoc curent ────────────────────────────────────────────────
    st.markdown("### Stoc curent")

    if not df.empty:
        # Colorăm produsele sub minim
        def highlight_minim(row):
            try:
                if float(row.get("Cantitate", 0) or 0) < float(row.get("Stoc_Minim", 0) or 0):
                    return ["background-color: #FFF3CD"] * len(row)
            except ValueError:
                pass
            return [""] * len(row)

        st.dataframe(
            df.style.apply(highlight_minim, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nu există produse în stoc. Adăugați primul produs mai jos.")

    st.markdown("---")

    # ── Adaugă / actualizează produs ─────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Adaugă produs nou")
        with st.form("form_adauga_produs"):
            name = st.text_input("Nume produs *", placeholder="ex: Făină tip 650")
            c1, c2 = st.columns(2)
            with c1:
                qty = st.number_input("Cantitate *", min_value=0.0, step=0.1)
            with c2:
                unit = st.selectbox("Unitate", UNITATI)
            c3, c4 = st.columns(2)
            with c3:
                pret = st.number_input("Preț unitar (lei)", min_value=0.0, step=0.01)
            with c4:
                stoc_minim = st.number_input("Stoc minim (alertă)", min_value=0.0, step=0.1)
            submitted = st.form_submit_button("➕ Adaugă în stoc", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Numele produsului e obligatoriu.")
            else:
                # Verificăm dacă există deja
                existing = [p for p in stoc if p.get("Produs", "").lower() == name.strip().lower()]
                if existing:
                    st.warning(f"Produsul '{name}' există deja. Folosiți 'Actualizează cantitate'.")
                else:
                    new_row = [
                        name.strip(), str(qty), unit,
                        str(pret), str(date.today()), str(stoc_minim),
                    ]
                    if not rows:
                        # Prima scriere — scriem și header-ul
                        append_rows(sid, TAB_STOC, [HEADERS, new_row])
                    else:
                        append_rows(sid, TAB_STOC, [new_row])
                    st.success(f"✅ '{name}' adăugat în stoc.")
                    st.rerun()

    with col2:
        st.markdown("### Actualizează cantitate")
        if stoc:
            produse_list = [p["Produs"] for p in stoc]
            with st.form("form_update_cantitate"):
                selected = st.selectbox("Produs", produse_list)
                operatie = st.radio("Operație", ["Adaugă", "Setează"], horizontal=True)
                qty_delta = st.number_input("Cantitate", min_value=0.0, step=0.1)
                submitted_upd = st.form_submit_button("💾 Salvează", use_container_width=True)

            if submitted_upd:
                # Actualizăm în lista de dicts și rescriemn tot tab-ul
                updated_stoc = []
                for p in stoc:
                    if p["Produs"] == selected:
                        try:
                            old_qty = float(p.get("Cantitate", 0) or 0)
                        except ValueError:
                            old_qty = 0.0
                        if operatie == "Adaugă":
                            p["Cantitate"] = str(old_qty + qty_delta)
                        else:
                            p["Cantitate"] = str(qty_delta)
                        p["Data"] = str(date.today())
                    updated_stoc.append(p)

                overwrite_tab(sid, TAB_STOC, dicts_to_rows(updated_stoc, HEADERS))
                st.success(f"✅ Stoc actualizat pentru '{selected}'.")
                st.rerun()
        else:
            st.info("Adăugați mai întâi produse pentru a le actualiza.")


show()
