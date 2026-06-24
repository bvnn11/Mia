"""
auth.py — login simplu username + parolă.

Maparea username → {password_hash, spreadsheet_id, restaurant_name}
stă în st.secrets[users][username], editabil din Streamlit Cloud dashboard.
"""

from __future__ import annotations
import streamlit as st
from werkzeug.security import check_password_hash


def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def get_spreadsheet_id() -> str:
    return st.session_state.get("spreadsheet_id", "")


def get_restaurant_name() -> str:
    return st.session_state.get("restaurant_name", "")


def logout():
    for key in ["logged_in", "spreadsheet_id", "restaurant_name", "username"]:
        st.session_state.pop(key, None)
    # Invalidăm și cache-ul de date
    keys_to_delete = [k for k in st.session_state if k.startswith("sheet_cache_")]
    for k in keys_to_delete:
        del st.session_state[k]
    st.rerun()


def show_login_page():
    """Randează pagina de login. Apelați din app.py dacă nu e autentificat."""

    # Layout centrat, Apple-style
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Logo / titlu
        st.markdown(
            """
            <div style='text-align:center; margin-bottom: 2rem;'>
                <div style='font-size:3rem;'>🍽️</div>
                <h1 style='font-size:1.8rem; font-weight:700; color:#1C1C1E; margin:0.5rem 0 0.25rem;'>
                    RestaurantOS
                </h1>
                <p style='color:#6E6E73; font-size:0.95rem; margin:0;'>
                    Gestionează stocul, rețetele și vânzările
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username = st.text_input("Utilizator", placeholder="username")
            password = st.text_input("Parolă", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Intră în cont", use_container_width=True)

        if submitted:
            _attempt_login(username.strip(), password)


def _attempt_login(username: str, password: str):
    users = st.secrets.get("users", {})

    if username not in users:
        st.error("Utilizator sau parolă incorectă.")
        return

    user_cfg = users[username]
    stored_hash = user_cfg.get("password_hash", "")

    if not check_password_hash(stored_hash, password):
        st.error("Utilizator sau parolă incorectă.")
        return

    st.session_state["logged_in"] = True
    st.session_state["username"] = username
    st.session_state["spreadsheet_id"] = user_cfg["spreadsheet_id"]
    st.session_state["restaurant_name"] = user_cfg.get("restaurant_name", username)
    st.rerun()
