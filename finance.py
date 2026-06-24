"""
finance.py — formula cascadei financiare validată contabil.
Nicio logică de UI aici — doar calcule pure.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class CascadaFinanciara:
    vanzari_brute: float
    tva_colectat: float
    vanzari_fara_tva: float
    cheltuieli_fixe_zi: float
    food_cost_efectiv: float
    profit_brut: float
    impozit_firma: float
    profit_dupa_impozit: float
    impozit_dividend: float
    profit_net_real: float
    marja_neta_pct: float


def calculeaza_cascada(
    vanzari_brute: float,
    cota_tva: float,               # ex: 0.09 sau 0.19
    chirie_lunara: float,
    salarii_lunare: float,
    utilitati_lunare: float,
    regim_fiscal: str,             # "micro1" | "micro3" | "profit16"
    cota_dividend: float,          # ex: 0.08
    food_cost_calculat: float | None = None,  # None → estimare 30%
) -> CascadaFinanciara:
    tva_colectat = vanzari_brute - vanzari_brute / (1 + cota_tva)
    vanzari_fara_tva = vanzari_brute / (1 + cota_tva)

    cheltuieli_fixe_zi = (chirie_lunara + salarii_lunare + utilitati_lunare) / 30

    if food_cost_calculat is not None:
        food_cost_efectiv = food_cost_calculat
    else:
        food_cost_efectiv = vanzari_fara_tva * 0.30  # estimare implicită

    profit_brut = vanzari_fara_tva - food_cost_efectiv - cheltuieli_fixe_zi

    cote = {"micro1": 0.01, "micro3": 0.03, "profit16": 0.16}
    cota_impozit = cote.get(regim_fiscal, 0.01)

    impozit_firma = profit_brut * cota_impozit
    profit_dupa_impozit = profit_brut - impozit_firma
    impozit_dividend = profit_dupa_impozit * cota_dividend
    profit_net_real = profit_dupa_impozit - impozit_dividend

    marja_neta_pct = (profit_net_real / vanzari_brute * 100) if vanzari_brute else 0.0

    return CascadaFinanciara(
        vanzari_brute=vanzari_brute,
        tva_colectat=tva_colectat,
        vanzari_fara_tva=vanzari_fara_tva,
        cheltuieli_fixe_zi=cheltuieli_fixe_zi,
        food_cost_efectiv=food_cost_efectiv,
        profit_brut=profit_brut,
        impozit_firma=impozit_firma,
        profit_dupa_impozit=profit_dupa_impozit,
        impozit_dividend=impozit_dividend,
        profit_net_real=profit_net_real,
        marja_neta_pct=marja_neta_pct,
    )


def food_cost_preparat(ingrediente: list[dict]) -> float:
    """
    ingrediente = [{"gramaj": 200, "pret_unitar": 5.0}, ...]
    pret_unitar e per kg (sau per unitate pt buc/ml).
    """
    total = 0.0
    for ing in ingrediente:
        try:
            gramaj = float(ing.get("gramaj", 0))
            pret = float(ing.get("pret_unitar", 0))
            total += (gramaj / 1000) * pret
        except (ValueError, TypeError):
            continue
    return total


def pret_recomandat(food_cost: float, marja_tinta_pct: float = 30.0) -> float:
    """
    Calculează prețul minim de vânzare pentru o marjă netă țintă.
    Simplificat: pret = food_cost / (1 - marja_tinta/100)
    """
    if marja_tinta_pct >= 100:
        return float("inf")
    return food_cost / (1 - marja_tinta_pct / 100)
