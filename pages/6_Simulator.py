"""
pages/6_Simulator.py — simulator preparat nou: food cost, cascadă financiară, marjă.
"""

import streamlit as st

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from auth import get_spreadsheet_id
from sheets import read_tabs, rows_to_dicts, TAB_STOC, TAB_CONFIG
from finance import food_cost_preparat, calculeaza_cascada, pret_recomandat
from ui_helpers import inject_css, page_header, GREEN, RED, ORANGE, PURPLE, SURFACE

st.set_page_config(page_title="Simulator", page_icon="🧮", layout="wide")
inject_css()


def show():
    sid = get_spreadsheet_id()
    page_header("Simulator preparat nou", "Calculează food cost și marja înainte de a pune pe meniu")

    with st.spinner("Se încarcă datele..."):
        tabs = read_tabs(sid, [TAB_STOC, TAB_CONFIG])

    stoc = rows_to_dicts(tabs[TAB_STOC])
    config_rows = rows_to_dicts(tabs[TAB_CONFIG])
    config = {r["Cheie"]: r["Valoare"] for r in config_rows if r.get("Cheie")}

    if not stoc:
        st.warning("Adăugați ingrediente în Stoc pentru a folosi simulatorul.")
        return

    produse_disponibile = [p["Produs"] for p in stoc]
    pret_stoc = {p["Produs"]: float(p.get("Pret_Unitar", 0) or 0) for p in stoc}
    unitate_stoc = {p["Produs"]: p.get("Unitate", "kg") for p in stoc}

    # ── Configurare simulare ─────────────────────────────────────────────
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown("### Ingrediente preparat")

        n_ing = st.number_input("Număr de ingrediente", min_value=1, max_value=15, value=3, step=1)

        ingrediente_sim = []
        for i in range(int(n_ing)):
            c1, c2 = st.columns([2, 1])
            with c1:
                ing = st.selectbox(f"Ingredient {i+1}", produse_disponibile, key=f"sim_ing_{i}")
            with c2:
                gramaj = st.number_input(
                    f"Gramaj (g) {i+1}", min_value=0.0, step=1.0, key=f"sim_gramaj_{i}",
                    help=f"Unitate stoc: {unitate_stoc.get(ing, 'kg')} | Preț: {pret_stoc.get(ing, 0):.2f} lei/kg"
                )
            ingrediente_sim.append({
                "ingredient": ing,
                "gramaj": gramaj,
                "pret_unitar": pret_stoc.get(ing, 0),
            })

        pret_vanzare = st.number_input("Preț de vânzare propus (lei, cu TVA)", min_value=0.0, step=0.5, value=30.0)

    with col_right:
        # ── Calcule live ─────────────────────────────────────────────────
        fc = food_cost_preparat([
            {"gramaj": i["gramaj"], "pret_unitar": i["pret_unitar"]}
            for i in ingrediente_sim
        ])

        marja_bruta_pct = ((pret_vanzare - fc) / pret_vanzare * 100) if pret_vanzare > 0 else 0

        # Cascadă per preparat vândut
        cota_tva = float(config.get("cota_tva", "0.09"))
        chirie = float(config.get("chirie_lunara", "0"))
        salarii = float(config.get("salarii_lunare", "0"))
        utilitati = float(config.get("utilitati_lunare", "0"))
        regim = config.get("regim_fiscal", "micro1")
        cota_div = float(config.get("cota_dividend", "0.08"))
        nr_clienti = float(config.get("nr_clienti_luna", "300") or "300")

        # Cheltuieli fixe per preparat (estimat)
        cheltuieli_fixe_pe_preparat = (chirie + salarii + utilitati) / max(nr_clienti, 1)

        cascada = calculeaza_cascada(
            vanzari_brute=pret_vanzare,
            cota_tva=cota_tva,
            chirie_lunara=chirie / max(nr_clienti, 1) * 30,
            salarii_lunare=salarii / max(nr_clienti, 1) * 30,
            utilitati_lunare=utilitati / max(nr_clienti, 1) * 30,
            regim_fiscal=regim,
            cota_dividend=cota_div,
            food_cost_calculat=fc,
        )

        prag_marja = 25.0  # % — sub acest prag avertizăm
        marja_ok = cascada.marja_neta_pct >= prag_marja

        # ── UI rezultate ──────────────────────────────────────────────
        st.markdown("### Rezultate")

        marja_color = GREEN if marja_ok else (ORANGE if cascada.marja_neta_pct >= 15 else RED)

        st.markdown(
            f"""
            <div style='background:{SURFACE}; border:1px solid #E5E0FF; border-radius:16px; padding:1.5rem;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:1rem;'>
                    <span style='color:#6E6E73; font-size:0.85rem; font-weight:600; text-transform:uppercase;'>Food cost</span>
                    <span style='font-size:1.2rem; font-weight:700;'>{fc:.2f} lei</span>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:1rem;'>
                    <span style='color:#6E6E73; font-size:0.85rem; font-weight:600; text-transform:uppercase;'>Food cost %</span>
                    <span style='font-size:1.2rem; font-weight:700;'>{(fc/pret_vanzare*100) if pret_vanzare else 0:.1f}%</span>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:1rem;'>
                    <span style='color:#6E6E73; font-size:0.85rem; font-weight:600; text-transform:uppercase;'>Marjă brută</span>
                    <span style='font-size:1.2rem; font-weight:700;'>{marja_bruta_pct:.1f}%</span>
                </div>
                <div style='border-top:1px solid #E5E0FF; padding-top:1rem; margin-top:0.5rem;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <span style='color:#6E6E73; font-size:0.85rem; font-weight:600; text-transform:uppercase;'>Profit net real</span>
                        <span style='font-size:1.4rem; font-weight:800; color:{marja_color};'>
                            {cascada.profit_net_real:.2f} lei
                        </span>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:0.5rem;'>
                        <span style='color:#6E6E73; font-size:0.85rem; font-weight:600; text-transform:uppercase;'>Marjă netă</span>
                        <span style='font-size:1.4rem; font-weight:800; color:{marja_color};'>
                            {cascada.marja_neta_pct:.1f}%
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if not marja_ok:
            pret_rec = pret_recomandat(fc + cheltuieli_fixe_pe_preparat, prag_marja)
            st.error(
                f"❌ **Marjă netă sub {prag_marja}%**\n\n"
                f"La prețul de **{pret_vanzare:.2f} lei**, preparatul nu este sustenabil.\n\n"
                f"**Preț recomandat minim:** {pret_rec:.2f} lei (pentru {prag_marja}% marjă netă)"
            )
        else:
            st.success(f"✅ Preparat profitabil la {pret_vanzare:.2f} lei.")

        # ── Detaliu cascadă ───────────────────────────────────────────
        with st.expander("📊 Detaliu cascadă financiară"):
            cascada_items = [
                ("Vânzări brute (cu TVA)", f"{cascada.vanzari_brute:.2f} lei"),
                ("— TVA colectat", f"- {cascada.tva_colectat:.2f} lei"),
                ("= Vânzări fără TVA", f"{cascada.vanzari_fara_tva:.2f} lei"),
                ("— Food cost", f"- {cascada.food_cost_efectiv:.2f} lei"),
                ("— Cheltuieli fixe (cotă/preparat)", f"- {cascada.cheltuieli_fixe_zi:.2f} lei"),
                ("= Profit brut", f"{cascada.profit_brut:.2f} lei"),
                (f"— Impozit firmă ({regim})", f"- {cascada.impozit_firma:.2f} lei"),
                ("= Profit după impozit", f"{cascada.profit_dupa_impozit:.2f} lei"),
                (f"— Impozit dividend ({cota_div*100:.0f}%)", f"- {cascada.impozit_dividend:.2f} lei"),
                ("= Profit net real", f"{cascada.profit_net_real:.2f} lei"),
            ]
            for label, val in cascada_items:
                is_total = label.startswith("=")
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; "
                    f"padding:0.3rem 0; "
                    f"{'font-weight:700; border-top:1px solid #E5E0FF;' if is_total else ''}'>"
                    f"<span>{label}</span><span>{val}</span></div>",
                    unsafe_allow_html=True,
                )


show()
