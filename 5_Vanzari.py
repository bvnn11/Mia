"""
pages/5_Vanzari.py — raport Z (scanare sau manual) + scădere automată din stoc.
"""

import streamlit as st
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id
from sheets import (
    read_tabs, rows_to_dicts, dicts_to_rows,
    append_rows, overwrite_tab,
    TAB_STOC, TAB_RETETAR, TAB_VANZARI,
)
from ai_ocr import scan_raport_z, fuzzy_match_preparat
from finance import food_cost_preparat
from ui_helpers import inject_css, page_header

st.set_page_config(page_title="Vânzări", page_icon="💰", layout="wide")
inject_css()

HEADERS_VANZARI = ["Preparat", "Cantitate_Vanduta", "Data"]
HEADERS_STOC = ["Produs", "Cantitate", "Unitate", "Pret_Unitar", "Data", "Stoc_Minim"]


def show():
    sid = get_spreadsheet_id()
    page_header("Vânzări", "Raport Z zilnic — scanare sau introducere manuală")

    with st.spinner("Se încarcă datele..."):
        tabs = read_tabs(sid, [TAB_STOC, TAB_RETETAR, TAB_VANZARI])

    stoc = rows_to_dicts(tabs[TAB_STOC])
    retetar = rows_to_dicts(tabs[TAB_RETETAR])
    vanzari_existente = rows_to_dicts(tabs[TAB_VANZARI])

    preparate_unice = list({r["Preparat"] for r in retetar if r.get("Preparat")})

    if not preparate_unice:
        st.warning("Adăugați preparate în Rețetar înainte de a înregistra vânzări.")
        return

    metoda = st.radio(
        "Metodă de înregistrare",
        ["📷 Scanare raport Z", "✍️ Introducere manuală"],
        horizontal=True,
    )

    if metoda == "📷 Scanare raport Z":
        _scanare_raport(sid, preparate_unice, stoc, retetar)
    else:
        _manual_raport(sid, preparate_unice, stoc, retetar)

    st.markdown("---")
    _show_vanzari_recente(vanzari_existente)


def _scanare_raport(sid, preparate_unice, stoc, retetar):
    uploaded = st.file_uploader(
        "Fotografia raportului Z",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if not uploaded:
        return

    scan_key = f"raport_scan_{uploaded.name}"

    col_img, col_form = st.columns([1, 1.5])
    with col_img:
        st.image(uploaded, caption="Raport Z", use_container_width=True)

    with col_form:
        if scan_key not in st.session_state:
            with st.spinner("🤖 AI analizează raportul Z..."):
                try:
                    image_bytes = uploaded.read()
                    mime = uploaded.type or "image/jpeg"
                    rezultat = scan_raport_z(image_bytes, mime)
                    st.session_state[scan_key] = rezultat
                except ValueError as e:
                    st.error(str(e))
                    return

        rezultat = st.session_state[scan_key]
        vanzari_ai = rezultat.get("vanzari", [])

        st.markdown("### ✏️ Verificați vânzările detectate")

        # Fuzzy matching AI → Rețetar
        vanzari_mapate = []
        for v in vanzari_ai:
            matched = fuzzy_match_preparat(v.get("preparat", ""), preparate_unice)
            vanzari_mapate.append({
                "preparat_ai": v.get("preparat", ""),
                "preparat_matched": matched or "",
                "cantitate": v.get("cantitate", 0),
            })

        with st.form("form_confirma_vanzari"):
            data_v = st.date_input("Data vânzărilor", value=date.today())

            confirmate = []
            for i, v in enumerate(vanzari_mapate):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.text_input(f"Detectat_{i}", value=v["preparat_ai"],
                                  disabled=True, label_visibility="collapsed")
                with c2:
                    prep = st.selectbox(
                        f"Preparat_{i}",
                        ["— niciun preparat —"] + preparate_unice,
                        index=(preparate_unice.index(v["preparat_matched"]) + 1)
                        if v["preparat_matched"] in preparate_unice else 0,
                        label_visibility="collapsed",
                    )
                with c3:
                    cant = st.number_input(f"Cant_{i}", value=float(v["cantitate"]),
                                          min_value=0.0, step=1.0, label_visibility="collapsed")
                confirmate.append({"preparat": prep, "cantitate": cant})

            submitted = st.form_submit_button(
                "✅ Confirmat — Salvează și scade din stoc",
                use_container_width=True,
            )

        if submitted:
            linii_valide = [v for v in confirmate if v["preparat"] != "— niciun preparat —" and v["cantitate"] > 0]
            if linii_valide:
                _salveaza_vanzari(sid, linii_valide, str(data_v), stoc, retetar)
                del st.session_state[scan_key]
                st.rerun()
            else:
                st.warning("Selectați cel puțin un preparat vândut.")


def _manual_raport(sid, preparate_unice, stoc, retetar):
    st.markdown("### Adaugă vânzări manual")

    with st.form("form_vanzari_manual"):
        data_v = st.date_input("Data", value=date.today())

        st.markdown("**Adaugă preparate vândute:**")
        n_linii = st.number_input("Număr de preparate diferite", min_value=1, max_value=20, value=1, step=1)

        linii = []
        for i in range(int(n_linii)):
            c1, c2 = st.columns([3, 1])
            with c1:
                prep = st.selectbox(f"Preparat {i+1}", preparate_unice, key=f"m_prep_{i}")
            with c2:
                cant = st.number_input(f"Cantitate {i+1}", min_value=0.0, step=1.0, key=f"m_cant_{i}")
            linii.append({"preparat": prep, "cantitate": cant})

        submitted = st.form_submit_button("✅ Salvează și scade din stoc", use_container_width=True)

    if submitted:
        valide = [l for l in linii if l["cantitate"] > 0]
        if valide:
            _salveaza_vanzari(sid, valide, str(data_v), stoc, retetar)
            st.rerun()
        else:
            st.warning("Introduceți cel puțin o cantitate > 0.")


def _salveaza_vanzari(sid, vanzari_confirmate, data_str, stoc, retetar):
    """Salvează vânzările și scade din stoc conform rețetarului."""

    # Construim map ingredient → cantitate de scăzut
    pret_stoc = {p["Produs"]: float(p.get("Pret_Unitar", 0) or 0) for p in stoc}
    scaderi: dict[str, float] = {}

    for v in vanzari_confirmate:
        preparat = v["preparat"]
        cant_vanduta = float(v["cantitate"])

        ingrediente_reteta = [r for r in retetar if r.get("Preparat") == preparat]
        for ing in ingrediente_reteta:
            ingredient = ing.get("Ingredient", "")
            gramaj = float(ing.get("Gramaj", 0) or 0)
            cantitate_de_scazut = cant_vanduta * gramaj / 1000  # g → kg
            scaderi[ingredient] = scaderi.get(ingredient, 0) + cantitate_de_scazut

    # Actualizăm stocul
    stoc_actualizat = []
    for p in stoc:
        produs = p["Produs"]
        if produs in scaderi:
            old_qty = float(p.get("Cantitate", 0) or 0)
            new_qty = max(0.0, old_qty - scaderi[produs])
            p["Cantitate"] = str(round(new_qty, 4))
            p["Data"] = data_str
        stoc_actualizat.append(p)

    overwrite_tab(sid, TAB_STOC, dicts_to_rows(stoc_actualizat, HEADERS_STOC))

    # Scriem vânzările
    new_rows = [[v["preparat"], str(v["cantitate"]), data_str] for v in vanzari_confirmate]
    vanzari_existente = read_tabs(sid, [TAB_VANZARI])[TAB_VANZARI]
    if not vanzari_existente:
        append_rows(sid, TAB_VANZARI, [HEADERS_VANZARI] + new_rows)
    else:
        append_rows(sid, TAB_VANZARI, new_rows)

    total_prep = len(vanzari_confirmate)
    total_ing_scazute = len(scaderi)
    st.success(
        f"✅ {total_prep} linii de vânzări salvate. "
        f"Stoc actualizat pentru {total_ing_scazute} ingrediente."
    )


def _show_vanzari_recente(vanzari: list[dict]):
    st.markdown("### Vânzări recente")
    if vanzari:
        import pandas as pd
        df = pd.DataFrame(vanzari)
        df = df.sort_values("Data", ascending=False).head(50) if "Data" in df.columns else df
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nu există vânzări înregistrate.")


show()
