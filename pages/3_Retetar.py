"""
pages/3_Retetar.py — rețete și food cost per preparat.
"""

import streamlit as st
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id
from sheets import (
    read_tabs, rows_to_dicts,
    append_rows, TAB_STOC, TAB_RETETAR,
)
from finance import food_cost_preparat
from ui_helpers import inject_css, page_header, TEXT_SECONDARY

st.set_page_config(page_title="Rețetar", page_icon="📖", layout="wide")
inject_css()

HEADERS_RETETAR = ["Preparat", "Ingredient", "Gramaj", "Pret_Vanzare"]


def show():
    sid = get_spreadsheet_id()
    page_header("Rețetar", "Preparate, ingrediente și food cost calculat automat")

    with st.spinner("Se încarcă rețetarul..."):
        tabs = read_tabs(sid, [TAB_RETETAR, TAB_STOC])

    retetar = rows_to_dicts(tabs[TAB_RETETAR])
    stoc = rows_to_dicts(tabs[TAB_STOC])

    pret_stoc = {p["Produs"]: float(p.get("Pret_Unitar", 0) or 0) for p in stoc}

    # ── Afișare preparate existente ──────────────────────────────────────
    preparate = {}
    for r in retetar:
        prep = r.get("Preparat", "")
        if prep:
            preparate.setdefault(prep, {
                "ingrediente": [],
                "pret_vanzare": float(r.get("Pret_Vanzare", 0) or 0),
            })
            preparate[prep]["ingrediente"].append({
                "Ingredient": r.get("Ingredient", ""),
                "Gramaj": r.get("Gramaj", ""),
                "Pret_Unitar": pret_stoc.get(r.get("Ingredient", ""), 0),
            })

    if preparate:
        st.markdown("### Preparate")
        for prep_name, data in preparate.items():
            fc = food_cost_preparat([
                {"gramaj": i["Gramaj"], "pret_unitar": i["Pret_Unitar"]}
                for i in data["ingrediente"]
            ])
            pv = data["pret_vanzare"]
            marja = ((pv - fc) / pv * 100) if pv > 0 else 0
            marja_color = "#34C759" if marja >= 30 else "#FF9500" if marja >= 20 else "#FF3B30"

            with st.expander(
                f"**{prep_name}** — Preț vânzare: {pv:.2f} lei | "
                f"Food cost: {fc:.2f} lei | "
                f"Marjă brută: {marja:.0f}%"
            ):
                df_ing = pd.DataFrame(data["ingrediente"])
                st.dataframe(df_ing, use_container_width=True, hide_index=True)
                st.markdown(
                    f"<span style='color:{marja_color}; font-weight:600;'>"
                    f"{'✓ Marjă bună' if marja >= 30 else '⚠️ Marjă scăzută' if marja >= 20 else '❌ Marjă nesustenabilă'}"
                    f" ({marja:.1f}%)</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("Nu există preparate în rețetar. Adăugați primul preparat mai jos.")

    st.markdown("---")

    # ── Adaugă preparat / ingredient ────────────────────────────────────
    st.markdown("### Adaugă ingredient la un preparat")

    if not stoc:
        st.warning("Adăugați mai întâi produse în Stoc pentru a le folosi în rețete.")
        return

    produse_disponibile = [p["Produs"] for p in stoc]
    preparate_existente = list(preparate.keys())

    with st.form("form_adauga_ingredient"):
        c1, c2 = st.columns(2)
        with c1:
            mod = st.radio("Preparat", ["Preparat nou", "Preparat existent"], horizontal=True)
        with c2:
            if mod == "Preparat nou":
                prep_name = st.text_input("Nume preparat nou *", placeholder="ex: Ciorbă de burtă")
            else:
                if preparate_existente:
                    prep_name = st.selectbox("Alege preparat", preparate_existente)
                else:
                    st.info("Nu există preparate. Creați unul nou.")
                    prep_name = ""

        c3, c4, c5 = st.columns(3)
        with c3:
            ingredient = st.selectbox("Ingredient *", produse_disponibile)
        with c4:
            gramaj = st.number_input("Gramaj (g) *", min_value=0.0, step=1.0)
        with c5:
            pret_vanzare = st.number_input(
                "Preț vânzare (lei) — doar la preparat nou",
                min_value=0.0, step=0.5,
            )

        submitted = st.form_submit_button("➕ Adaugă ingredient", use_container_width=True)

    if submitted:
        name = prep_name.strip() if prep_name else ""
        if not name or not ingredient or gramaj <= 0:
            st.error("Completați: numele preparatului, ingredientul și gramajul.")
        else:
            # La preparat existent, păstrăm prețul de vânzare din prima linie
            if mod == "Preparat existent" and name in preparate:
                pret_vanzare = preparate[name]["pret_vanzare"]

            new_rows = [[name, ingredient, str(gramaj), str(pret_vanzare)]]
            if not retetar:
                append_rows(sid, TAB_RETETAR, [HEADERS_RETETAR] + new_rows)
            else:
                append_rows(sid, TAB_RETETAR, new_rows)
            st.success(f"✅ Ingredient '{ingredient}' adăugat la preparatul '{name}'.")
            st.rerun()


show()
