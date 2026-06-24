"""
ai_ocr.py — extragere date din imagini prin Gemini.

Modelul e definit într-o singură constantă. Dacă Google retrage modelul,
schimbați doar GEMINI_MODEL.

Verificați modelele active la:
https://ai.google.dev/gemini-api/docs/models
"""

from __future__ import annotations
import base64
import json
import re
import logging

import google.generativeai as genai
import streamlit as st

logger = logging.getLogger(__name__)

# ── Singura constantă de model — schimbați doar aici dacă e retras ──────────
GEMINI_MODEL = "gemini-1.5-flash"
# Alternativă stabilă: "gemini-1.5-pro"
# ────────────────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _get_genai_client():
    api_key = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def _image_part(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode(),
        }
    }


def _parse_json_from_response(text: str) -> dict | list:
    """Extrage JSON din răspunsul modelului (poate conține markdown)."""
    # Eliminăm backtick-urile markdown dacă există
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    return json.loads(cleaned)


# ── Scanare factură ──────────────────────────────────────────────────────────

PROMPT_FACTURA = """
Analizează această factură și extrage datele în format JSON exact.
Returnează DOAR JSON valid, fără text suplimentar, fără markdown.

Format cerut:
{
  "furnizor": "Nume Furnizor SRL",
  "nr_factura": "FAC-001",
  "data": "2024-01-15",
  "total": 250.50,
  "produse": [
    {
      "nume": "Făină tip 650",
      "cantitate": 25,
      "unitate": "kg",
      "pret_unitar": 3.20
    }
  ]
}

Dacă un câmp nu e vizibil sau lizibil, lasă string gol "" sau 0.
Unitățile de măsură: kg, g, l, ml, buc.
Data în format YYYY-MM-DD.
Prețurile ca numere zecimale (punct ca separator).
"""


def scan_factura(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Returnează dict cu datele facturii sau ridică ValueError cu mesaj util.
    Rezultatul TREBUIE verificat de utilizator înainte de scriere în Sheet.
    """
    model = _get_genai_client()
    try:
        response = model.generate_content([
            PROMPT_FACTURA,
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}}
        ])
        return _parse_json_from_response(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Modelul AI nu a returnat JSON valid: {e}") from e
    except Exception as e:
        logger.error(f"Eroare scan factură: {e}")
        raise ValueError(f"Eroare la procesarea imaginii: {e}") from e


# ── Scanare Raport Z ─────────────────────────────────────────────────────────

PROMPT_RAPORT_Z = """
Analizează acest bon de casă de marcat / raport Z și extrage vânzările.
Returnează DOAR JSON valid, fără text suplimentar, fără markdown.

Format cerut:
{
  "data": "2024-01-15",
  "total_brut": 1250.00,
  "vanzari": [
    {
      "preparat": "Ciorbă de burtă",
      "cantitate": 15
    }
  ]
}

Dacă nu poți identifica preparatele individuale, returnează lista goală [].
Data în format YYYY-MM-DD.
"""


def scan_raport_z(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Returnează dict cu vânzările din raportul Z.
    Rezultatul TREBUIE verificat și corectat de utilizator.
    """
    model = _get_genai_client()
    try:
        response = model.generate_content([
            PROMPT_RAPORT_Z,
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}}
        ])
        return _parse_json_from_response(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Modelul AI nu a returnat JSON valid: {e}") from e
    except Exception as e:
        logger.error(f"Eroare scan raport Z: {e}")
        raise ValueError(f"Eroare la procesarea imaginii: {e}") from e


# ── Fuzzy matching pentru preparate ──────────────────────────────────────────

def fuzzy_match_preparat(nume_detectat: str, preparate_din_retetar: list[str]) -> str | None:
    """
    Găsește cel mai apropiată potrivire între un nume detectat de AI
    și lista de preparate din Rețetar.
    Returnează None dacă scorul e prea mic.
    """
    from difflib import get_close_matches
    matches = get_close_matches(
        nume_detectat.lower(),
        [p.lower() for p in preparate_din_retetar],
        n=1,
        cutoff=0.5,
    )
    if not matches:
        return None
    # Returnăm originalul (cu majuscule corecte)
    lower_to_original = {p.lower(): p for p in preparate_din_retetar}
    return lower_to_original.get(matches[0])
