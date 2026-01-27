import os
import re
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Smiley Close Friends — Înscriere", page_icon="⭐", layout="centered")

# -------------------------
# Styles (background + blue button)
# -------------------------
st.markdown(
    """
    <style>
      /* Page background */
      .stApp {
        background: #004EE6; /* light blue */
      }

      /* Primary button (our submit) */
      div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #1E73FF !important;  /* blue */
        border: 1px solid #1E73FF !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        font-weight: 700 !important;
      }
      div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #155AD6 !important;
        border-color: #155AD6 !important;
        color: white !important;
      }

      /* Slightly soften inputs */
      input, textarea {
        border-radius: 12px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Top image (robust path handling)
# -------------------------
img_candidates = [
    "assets/IMG_8559.jpg",
    "assets/IMG_8559.JPG",
    "IMG_8559.jpg",
    "IMG_8559.JPG",
]
img_path = next((p for p in img_candidates if os.path.exists(p)), None)

if img_path:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.image(img_path, use_container_width=True)
else:
    st.warning(
        "Imaginea nu a fost găsită în repo. Verifică dacă există `assets/IMG_8559.jpg` "
        "sau `IMG_8559.jpg` și că e commit-uită."
    )

# -------------------------
# Config / validation
# -------------------------
HANDLE_RE = re.compile(r"^[a-zA-Z0-9._]{1,30}$")


def normalize_handle(h: str) -> str:
    h = (h or "").strip()
    if h.startswith("@"):
        h = h[1:]
    return h


def valid_handle(h: str) -> bool:
    return bool(HANDLE_RE.match(h))


# -------------------------
# Google Sheets helpers
# -------------------------
def get_gspread_client():
    sa_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)


def append_row(sheet_id: str, row: list[str]):
    gc = get_gspread_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1

    header = ["ig_handle", "email", "source", "created_at_utc", "consent"]
    if ws.get("A1:E1") == [[]]:
        ws.append_row(header, value_input_option="RAW")

    ws.append_row(row, value_input_option="RAW")


def read_all_rows(sheet_id: str) -> pd.DataFrame:
    gc = get_gspread_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1
    values = ws.get_all_values()
    if not values or len(values) < 2:
        return pd.DataFrame(columns=["ig_handle", "email", "source", "created_at_utc", "consent"])
    df = pd.DataFrame(values[1:], columns=values[0])
    return df


# -------------------------
# UI
# -------------------------
st.markdown(
    """
    <div style="text-align:center; padding-top: 10px; padding-bottom: 10px;">
      <h1 style="margin-bottom: 6px;">⭐ Hai pe Close Friends și devii oficial Omul lui Smiley!</h1>
      <p style="font-size: 1.05rem; margin-top: 0;">
        Lasă-ți username-ul de Instagram ca să fii luat(ă) în considerare pentru Close Friends-ul lui Smiley.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Intră pe listă")
    st.caption("Folosim aceste informații doar ca să-ți identificăm contul și să te adăugăm manual dacă ești selectat(ă).")

    # Optional campaign source via URL: ?src=tiktok, ?src=yt, etc.
    source = st.query_params.get("src", "")

    ig = st.text_input("Username Instagram", placeholder="@username")
    email = st.text_input("Email (opțional)", placeholder="name@email.com")

    consent = st.checkbox(
        "Sunt de acord ca username-ul meu de Instagram să fie folosit pentru a fi adăugat(ă) manual în Close Friends-ul lui Smiley.",
        value=False,
    )

    submitted = st.button("Hai și!", type="primary", use_container_width=True)

    if submitted:
        ig_n = normalize_handle(ig).lower()
        email_n = (email or "").strip() or ""

        if not ig_n:
            st.error("Te rog introdu username-ul tău de Instagram.")
        elif not valid_handle(ig_n):
            st.error("Username invalid. Folosește litere/cifre/punct/underscore (maxim 30 caractere).")
        elif not consent:
            st.error("Te rog bifează acordul ca să poți trimite.")
        else:
            created_at = datetime.now(timezone.utc).isoformat()
            sheet_id = st.secrets["SHEET_ID"]

            try:
                append_row(sheet_id, [ig_n, email_n, source, created_at, "yes"])
                st.success("Gata! Ești pe listă ✅")
            except Exception:
                st.error("Nu am putut salva cererea acum. Te rog încearcă din nou mai târziu.")
                st.stop()

st.divider()

# -------------------------
# Admin export (hidden by password, no extra text)
# -------------------------
admin_pw = st.text_input("Parolă admin", type="password")
expected_pw = st.secrets.get("ADMIN_PASSWORD", "")

if expected_pw and admin_pw == expected_pw:
    df = read_all_rows(st.secrets["SHEET_ID"])
    st.write(f"Total înscrieri: **{len(df)}**")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descarcă CSV",
        data=csv,
        file_name="smiley_close_friends_signups.csv",
        mime="text/csv",
        use_container_width=True,
    )
