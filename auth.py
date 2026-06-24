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
    sid = st.session_state.get("spreadsheet_id", "")
    if not sid:
        st.error(
            "⚠️ **spreadsheet_id lipsește din sesiune.**\n\n"
            "Verificați că în `secrets.toml` aveți exact formatul:\n"
            "```toml\n"
            "[users.numeutilizator]\n"
            'password_hash = "pbkdf2:sha256:..."\n'
            'spreadsheet_id = "1ABC...XYZ"\n'
            'restaurant_name = "Numele Restaurantului"\n'
            "```\n\n"
            "Apoi deconectați-vă și reconectați-vă."
        )
    return sid


def get_restaurant_name() -> str:
    return st.session_state.get("restaurant_name", "")


def logout():
    for key in ["logged_in", "spreadsheet_id", "restaurant_name", "username"]:
        st.session_state.pop(key, None)
    keys_to_delete = [k for k in st.session_state if k.startswith("sheet_cache_")]
    for k in keys_to_delete:
        del st.session_state[k]
    st.rerun()


def show_login_page():
    """Randează pagina de login. Apelați din app.py dacă nu e autentificat."""

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

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

        # ── Debug helper: arată ce users există în secrets ──────────────
        with st.expander("🔧 Debug secrets", expanded=False):
            users = st.secrets.get("users", {})
            if not users:
                st.error("❌ Secțiunea `[users]` lipsește din secrets.toml!")
            else:
                st.success(f"✅ Utilizatori găsiți: {list(users.keys())}")
                for uname, ucfg in users.items():
                    sid = ucfg.get("spreadsheet_id", "")
                    st.write(f"**{uname}**: spreadsheet_id = `{sid[:20]}...`" if sid else f"**{uname}**: ⚠️ spreadsheet_id LIPSEȘTE!")


def _attempt_login(username: str, password: str):
    users = st.secrets.get("users", {})

    if not users:
        st.error("❌ Nu există utilizatori configurați în secrets.toml. Adăugați secțiunea `[users]`.")
        return

    if username not in users:
        st.error("Utilizator sau parolă incorectă.")
        return

    user_cfg = users[username]
    stored_hash = user_cfg.get("password_hash", "")

    if not stored_hash:
        st.error(f"❌ `password_hash` lipsește pentru utilizatorul `{username}` în secrets.toml.")
        return

    if not check_password_hash(stored_hash, password):
        st.error("Utilizator sau parolă incorectă.")
        return

    spreadsheet_id = user_cfg.get("spreadsheet_id", "")
    if not spreadsheet_id:
        st.error(
            f"❌ `spreadsheet_id` lipsește pentru utilizatorul `{username}` în secrets.toml.\n\n"
            "Adăugați ID-ul Google Sheet-ului (găsiți în URL-ul sheet-ului, între `/d/` și `/edit`)."
        )
        return

    st.session_state["logged_in"] = True
    st.session_state["username"] = username
    st.session_state["spreadsheet_id"] = spreadsheet_id
    st.session_state["restaurant_name"] = user_cfg.get("restaurant_name", username)
    st.rerun()
