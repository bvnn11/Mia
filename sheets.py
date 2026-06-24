"""
sheets.py — wrapper Google Sheets cu caching, batch read și retry.

Reguli stricte:
- Orice citire e cache-uită; cache-ul e invalidat imediat după scriere.
- Toate tab-urile necesare unei pagini se citesc într-un singur batchGet.
- Retry cu exponential backoff pe 429/503.
- Erori diferențiate pe cod HTTP.
"""

from __future__ import annotations
import time
import logging
from typing import Any

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Tab-uri disponibile în template
TAB_STOC = "Stoc"
TAB_RETETAR = "Retetar"
TAB_VANZARI = "Vanzari"
TAB_CONFIG = "Config"
TAB_FACTURI = "FacturiLog"


# ── Autentificare ───────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_credentials() -> Credentials:
    """Cache-uiește credentials pentru întreaga sesiune (nu regenera la fiecare call)."""
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return creds


@st.cache_resource(show_spinner=False)
def _get_sheets_service():
    """Serviciu Google Sheets API v4 cache-uit."""
    return build("sheets", "v4", credentials=_get_credentials(), cache_discovery=False)


@st.cache_resource(show_spinner=False)
def _get_gspread_client() -> gspread.Client:
    return gspread.authorize(_get_credentials())


# ── Retry logic ─────────────────────────────────────────────────────────────

def _retry(fn, *args, max_attempts: int = 4, **kwargs) -> Any:
    """
    Execută fn cu exponential backoff pe 429/503.
    Aruncă excepție diferențiată după max_attempts.
    """
    delays = [1, 2, 4, 8]
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:
            code = e.resp.status
            if code in (429, 503) and attempt < max_attempts - 1:
                wait = delays[attempt]
                logger.warning(f"HTTP {code} — aștept {wait}s (încercarea {attempt+1})")
                time.sleep(wait)
                continue
            _raise_friendly(code)
        except Exception as e:
            raise RuntimeError(f"Eroare neașteptată Sheets API: {e}") from e
    _raise_friendly(429)


def _raise_friendly(code: int):
    messages = {
        401: "🔐 Autentificare invalidă. Verificați service account și cheile din Secrets.",
        403: "🚫 Permisiuni insuficiente. Asigurați-vă că service account-ul are acces Editor la acest spreadsheet.",
        404: "🔍 Spreadsheet-ul nu a fost găsit. Verificați spreadsheet_id din Secrets.",
        429: "⏳ Prea multe cereri Google Sheets (rate limit). Așteptați 1-2 minute și reîncercați.",
        503: "🔧 Serviciu Google temporar indisponibil. Reîncercați peste câteva secunde.",
    }
    msg = messages.get(code, f"❌ Eroare Google Sheets (HTTP {code}).")
    raise RuntimeError(msg)


# ── Cache cheie și invalidare ────────────────────────────────────────────────

def _cache_key(spreadsheet_id: str, tab: str) -> str:
    return f"sheet_cache_{spreadsheet_id}_{tab}"


def invalidate_tab(spreadsheet_id: str, tab: str):
    """Apelează imediat după orice scriere pe tab-ul respectiv."""
    key = _cache_key(spreadsheet_id, tab)
    if key in st.session_state:
        del st.session_state[key]


# ── Citire (batch) ───────────────────────────────────────────────────────────

def read_tabs(spreadsheet_id: str, tabs: list[str]) -> dict[str, list[list]]:
    """
    Citește mai multe tab-uri dintr-un singur batchGet.
    Rezultatele sunt cache-uite în session_state.
    Returnează {tab_name: [[row], [row], ...]} cu header pe prima linie.
    """
    needed = []
    cached = {}

    for tab in tabs:
        key = _cache_key(spreadsheet_id, tab)
        if key in st.session_state:
            cached[tab] = st.session_state[key]
        else:
            needed.append(tab)

    if needed:
        ranges = [f"'{t}'!A:Z" for t in needed]
        svc = _get_sheets_service()

        def _fetch():
            return (
                svc.spreadsheets()
                .values()
                .batchGet(spreadsheetId=spreadsheet_id, ranges=ranges)
                .execute()
            )

        result = _retry(_fetch)
        value_ranges = result.get("valueRanges", [])

        for tab, vr in zip(needed, value_ranges):
            rows = vr.get("values", [])
            key = _cache_key(spreadsheet_id, tab)
            st.session_state[key] = rows
            cached[tab] = rows

    return cached


def read_tab(spreadsheet_id: str, tab: str) -> list[list]:
    return read_tabs(spreadsheet_id, [tab])[tab]


# ── Scriere ──────────────────────────────────────────────────────────────────

def append_rows(spreadsheet_id: str, tab: str, rows: list[list]):
    """Adaugă rânduri la finalul tab-ului și invalidează cache-ul."""
    svc = _get_sheets_service()

    def _append():
        svc.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

    _retry(_append)
    invalidate_tab(spreadsheet_id, tab)


def update_cell_range(spreadsheet_id: str, tab: str, range_a1: str, values: list[list]):
    """Actualizează un range specific și invalidează cache-ul."""
    svc = _get_sheets_service()

    def _update():
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab}'!{range_a1}",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()

    _retry(_update)
    invalidate_tab(spreadsheet_id, tab)


def overwrite_tab(spreadsheet_id: str, tab: str, rows: list[list]):
    """
    Suprascrie tab-ul complet (clear + write).
    Folosit la actualizare stoc după vânzare.
    """
    svc = _get_sheets_service()

    def _clear():
        svc.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab}'!A:Z",
        ).execute()

    def _write():
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": rows},
        ).execute()

    _retry(_clear)
    _retry(_write)
    invalidate_tab(spreadsheet_id, tab)


# ── Helpers pentru parsare date ──────────────────────────────────────────────

def rows_to_dicts(rows: list[list]) -> list[dict]:
    """Transformă [[header], [row1], [row2]] în [{"col": val}, ...]."""
    if not rows:
        return []
    headers = rows[0]
    result = []
    for row in rows[1:]:
        padded = row + [""] * (len(headers) - len(row))
        result.append(dict(zip(headers, padded)))
    return result


def dicts_to_rows(dicts: list[dict], headers: list[str]) -> list[list]:
    """Inversul lui rows_to_dicts. headers = ordinea coloanelor."""
    result = [headers]
    for d in dicts:
        result.append([str(d.get(h, "")) for h in headers])
    return result
