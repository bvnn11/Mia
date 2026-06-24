"""
pages/4_Facturi.py — scanare facturi cu AI + confirmare înainte de scriere.
"""

import streamlit as st
from datetime import date

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id
from sheets import (
    read_tab, rows_to_dicts, dicts_to_rows,
    append_rows, overwrite_tab, TAB_STOC, TAB_FACTURI,
)
from ai_ocr import scan_factura
from ui_helpers import inject_css, page_header

st.set_page_config(page_title="Facturi", page_icon="🧾", layout="wide")
inject_css()

HEADERS_FACTURI = ["Data", "Furnizor", "NrFactura", "Total", "Produse"]
HEADERS_STOC = ["Produs", "Cantitate", "Unitate", "Pret_Unitar", "Data", "Stoc_Minim"]


def show():
    sid = get_spreadsheet_id()
    page_header("Facturi", "Scanează o factură — verifică — adaugă în stoc")

    st.info(
        "📸 **Flux:** Încarci poza → AI extrage datele → **Tu verifici și corectezi** → Confirmi adăugarea în stoc.\n\n"
        "Nicio scriere automată fără confirmare ta.",
        icon=None,
    )

    uploaded = st.file_uploader(
        "Încarcă fotografia facturii",
        type=["jpg", "jpeg", "png", "webp"],
        help="Fotografie clară, fără umbre. JPG/PNG/WEBP.",
    )

    if not uploaded:
        st.markdown("---")
        _show_facturi_log(sid)
        return

    col_img, col_form = st.columns([1, 1.5])

    with col_img:
        st.image(uploaded, caption="Factura încărcată", use_container_width=True)

    with col_form:
        # ── Extragere AI ──────────────────────────────────────────────
        scan_key = f"factura_scan_{uploaded.name}"

        if scan_key not in st.session_state:
            with st.spinner("🤖 AI analizează factura..."):
                try:
                    image_bytes = uploaded.read()
                    mime = uploaded.type or "image/jpeg"
                    rezultat = scan_factura(image_bytes, mime)
                    st.session_state[scan_key] = rezultat
                except ValueError as e:
                    st.error(str(e))
                    return

        rezultat = st.session_state[scan_key]

        st.markdown("### ✏️ Verificați și corectați datele extrase")

        with st.form("form_confirma_factura"):
            c1, c2 = st.columns(2)
            with c1:
                furnizor = st.text_input("Furnizor", value=rezultat.get("furnizor", ""))
            with c2:
                nr_factura = st.text_input("Nr. factură", value=rezultat.get("nr_factura", ""))

            c3, c4 = st.columns(2)
            with c3:
                data_factura = st.text_input("Data (YYYY-MM-DD)", value=rezultat.get("data", str(date.today())))
            with c4:
                total = st.number_input("Total (lei)", value=float(rezultat.get("total", 0) or 0), step=0.01)

            st.markdown("**Produse detectate** (editați dacă e necesar):")
            produse = rezultat.get("produse", [])

            produse_editate = []
            for i, prod in enumerate(produse):
                st.markdown(f"*Produs {i+1}*")
                pc1, pc2, pc3, pc4 = st.columns([3, 1.5, 1, 1.5])
                with pc1:
                    n = st.text_input(f"Nume_{i}", value=prod.get("nume", ""), label_visibility="collapsed")
                with pc2:
                    q = st.number_input(f"Cant_{i}", value=float(prod.get("cantitate", 0) or 0),
                                        step=0.1, label_visibility="collapsed")
                with pc3:
                    u = st.selectbox(f"UM_{i}", ["kg","g","l","ml","buc"],
                                     index=["kg","g","l","ml","buc"].index(prod.get("unitate","kg"))
                                     if prod.get("unitate","kg") in ["kg","g","l","ml","buc"] else 0,
                                     label_visibility="collapsed")
                with pc4:
                    p = st.number_input(f"Pret_{i}", value=float(prod.get("pret_unitar", 0) or 0),
                                        step=0.01, label_visibility="collapsed")
                produse_editate.append({"nume": n, "cantitate": q, "unitate": u, "pret_unitar": p})

            st.markdown("---")
            submitted = st.form_submit_button(
                "✅ Confirmat — Adaugă în stoc și FacturiLog",
                use_container_width=True,
            )

        if submitted:
            _salveaza_factura(sid, furnizor, nr_factura, data_factura, total, produse_editate)
            del st.session_state[scan_key]
            st.rerun()

    st.markdown("---")
    _show_facturi_log(sid)


def _salveaza_factura(sid, furnizor, nr_factura, data_f, total, produse):
    """Scrie în FacturiLog + actualizează Stoc."""
    stoc_rows = read_tab(sid, TAB_STOC)
    stoc = rows_to_dicts(stoc_rows)
    stoc_map = {p["Produs"].lower(): p for p in stoc}

    # Actualizăm stocul
    for prod in produse:
        if not prod["nume"].strip():
            continue
        key = prod["nume"].strip().lower()
        qty = float(prod["cantitate"] or 0)
        pret = float(prod["pret_unitar"] or 0)

        if key in stoc_map:
            p = stoc_map[key]
            old_qty = float(p.get("Cantitate", 0) or 0)
            p["Cantitate"] = str(old_qty + qty)
            p["Pret_Unitar"] = str(pret) if pret > 0 else p["Pret_Unitar"]
            p["Data"] = str(date.today())
        else:
            # Produs nou din factură → adăugăm în stoc
            stoc.append({
                "Produs": prod["nume"].strip(),
                "Cantitate": str(qty),
                "Unitate": prod.get("unitate", "kg"),
                "Pret_Unitar": str(pret),
                "Data": str(date.today()),
                "Stoc_Minim": "0",
            })

    overwrite_tab(sid, TAB_STOC, dicts_to_rows(stoc, HEADERS_STOC))

    # Log factură
    produse_str = "; ".join(
        f"{p['nume']} {p['cantitate']}{p['unitate']}@{p['pret_unitar']}lei"
        for p in produse if p["nume"].strip()
    )
    factura_row = [str(date.today()), furnizor, nr_factura, str(total), produse_str]
    facturi_existente = read_tab(sid, TAB_FACTURI)
    if not facturi_existente:
        append_rows(sid, TAB_FACTURI, [HEADERS_FACTURI, factura_row])
    else:
        append_rows(sid, TAB_FACTURI, [factura_row])

    st.success(f"✅ Factură salvată și stoc actualizat cu {len([p for p in produse if p['nume'].strip()])} produse.")


def _show_facturi_log(sid):
    st.markdown("### Istoric facturi")
    facturi_rows = read_tab(sid, TAB_FACTURI)
    facturi = rows_to_dicts(facturi_rows)
    if facturi:
        import pandas as pd
        st.dataframe(pd.DataFrame(facturi), use_container_width=True, hide_index=True)
    else:
        st.info("Nu există facturi înregistrate.")


show()
