"""
pages/1_Dashboard.py — vizualizare generală: vânzări, food cost, marjă, alerte stoc.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id, get_restaurant_name
from sheets import read_tabs, rows_to_dicts, TAB_STOC, TAB_VANZARI, TAB_RETETAR, TAB_CONFIG
from finance import calculeaza_cascada, food_cost_preparat
from ui_helpers import inject_css, page_header, alert_stoc_minim


st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
inject_css()


def _load_config(config_rows: list[dict]) -> dict:
    return {r["Cheie"]: r["Valoare"] for r in config_rows if r.get("Cheie")}


def show():
    sid = get_spreadsheet_id()
    page_header("Dashboard", f"Bun venit, {get_restaurant_name()}")

    with st.spinner("Se încarcă datele..."):
        tabs = read_tabs(sid, [TAB_STOC, TAB_VANZARI, TAB_RETETAR, TAB_CONFIG])

    stoc = rows_to_dicts(tabs[TAB_STOC])
    vanzari = rows_to_dicts(tabs[TAB_VANZARI])
    retetar = rows_to_dicts(tabs[TAB_RETETAR])
    config = _load_config(rows_to_dicts(tabs[TAB_CONFIG]))

    # ── Alerte stoc minim ────────────────────────────────────────────────
    sub_minim = []
    for p in stoc:
        try:
            qty = float(p.get("Cantitate", 0) or 0)
            minim = float(p.get("Stoc_Minim", 0) or 0)
            if minim > 0 and qty < minim:
                sub_minim.append(p)
        except ValueError:
            continue
    alert_stoc_minim(sub_minim)

    # ── Calcule vânzări ultimele 30 zile ────────────────────────────────
    today = date.today()
    cutoff = today - timedelta(days=30)

    # Construim map preparat → food_cost din rețetar + stoc
    pret_stoc = {p["Produs"]: float(p.get("Pret_Unitar", 0) or 0) for p in stoc}

    food_cost_map: dict[str, float] = {}
    preparate_unice = {r["Preparat"] for r in retetar if r.get("Preparat")}
    for preparat in preparate_unice:
        ingrediente = [
            {
                "gramaj": r.get("Gramaj", 0),
                "pret_unitar": pret_stoc.get(r.get("Ingredient", ""), 0),
            }
            for r in retetar if r.get("Preparat") == preparat
        ]
        food_cost_map[preparat] = food_cost_preparat(ingrediente)

    # Calculăm vânzări brute + food cost din vânzări recente
    pret_vanzare_map: dict[str, float] = {}
    for r in retetar:
        prep = r.get("Preparat", "")
        pv = r.get("Pret_Vanzare", "")
        if prep and pv:
            try:
                pret_vanzare_map[prep] = float(pv)
            except ValueError:
                pass

    vanzari_brute_30 = 0.0
    food_cost_30 = 0.0
    for v in vanzari:
        try:
            data_v = date.fromisoformat(v.get("Data", "")[:10])
        except (ValueError, TypeError):
            continue
        if data_v < cutoff:
            continue
        preparat = v.get("Preparat", "")
        cant = float(v.get("Cantitate_Vanduta", 0) or 0)
        pret = pret_vanzare_map.get(preparat, 0)
        vanzari_brute_30 += pret * cant
        food_cost_30 += food_cost_map.get(preparat, 0) * cant

    # ── Cascadă financiară ───────────────────────────────────────────────
    cota_tva = float(config.get("cota_tva", "0.09"))
    chirie = float(config.get("chirie_lunara", "0"))
    salarii = float(config.get("salarii_lunare", "0"))
    utilitati = float(config.get("utilitati_lunare", "0"))
    regim = config.get("regim_fiscal", "micro1")
    cota_div = float(config.get("cota_dividend", "0.08"))

    # Vânzări de azi (approx: 1/30 din ultimele 30 zile)
    vanzari_azi = vanzari_brute_30 / 30 if vanzari_brute_30 else 0

    cascada = calculeaza_cascada(
        vanzari_brute=vanzari_azi,
        cota_tva=cota_tva,
        chirie_lunara=chirie,
        salarii_lunare=salarii,
        utilitati_lunare=utilitati,
        regim_fiscal=regim,
        cota_dividend=cota_div,
        food_cost_calculat=(food_cost_30 / 30) if food_cost_30 else None,
    )

    # ── KPI metrics ──────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Vânzări brute (30 zile)",
            f"{vanzari_brute_30:,.0f} lei",
        )
    with col2:
        food_cost_pct = (food_cost_30 / vanzari_brute_30 * 100) if vanzari_brute_30 else 0
        st.metric(
            "Food cost mediu",
            f"{food_cost_pct:.1f}%",
            delta=f"{'⚠️ >35%' if food_cost_pct > 35 else '✓ OK'}",
        )
    with col3:
        st.metric(
            "Marjă netă (estimat/zi)",
            f"{cascada.marja_neta_pct:.1f}%",
        )
    with col4:
        st.metric(
            "Produse sub stoc minim",
            f"{len(sub_minim)}",
            delta=f"{'⚠️ Necesită reaprovizionare' if sub_minim else '✓ Stoc OK'}",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Grafic vânzări ultimele 30 zile ─────────────────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("**Vânzări zilnice (ultimele 30 zile)**")
        if vanzari:
            df_v = pd.DataFrame(vanzari)
            df_v = df_v[df_v["Preparat"].notna() & df_v["Data"].notna()].copy()
            df_v["data_dt"] = pd.to_datetime(df_v["Data"], errors="coerce").dt.date
            df_v["Cantitate_Vanduta"] = pd.to_numeric(df_v["Cantitate_Vanduta"], errors="coerce").fillna(0)
            df_v["preparat_key"] = df_v["Preparat"].map(pret_vanzare_map).fillna(0)
            df_v["vanzari_lei"] = df_v["Cantitate_Vanduta"] * df_v["preparat_key"]

            df_grouped = (
                df_v[df_v["data_dt"] >= cutoff]
                .groupby("data_dt")["vanzari_lei"]
                .sum()
                .reset_index()
                .rename(columns={"data_dt": "Data", "vanzari_lei": "Vânzări (lei)"})
            )
            if not df_grouped.empty:
                st.line_chart(df_grouped.set_index("Data"), color="#7C3AED")
            else:
                st.info("Nicio vânzare înregistrată în ultimele 30 de zile.")
        else:
            st.info("Nu există date de vânzări încă.")

    with col_right:
        st.markdown("**Stoc — produse critice**")
        if sub_minim:
            df_crit = pd.DataFrame(sub_minim)[["Produs", "Cantitate", "Stoc_Minim", "Unitate"]]
            st.dataframe(df_crit, use_container_width=True, hide_index=True)
        else:
            st.success("Toate produsele sunt în stoc suficient.")


show()
