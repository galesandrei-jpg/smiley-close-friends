import re
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Smiley Close Friends — Signup", page_icon="⭐", layout="centered")

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
    # Streamlit secrets must contain the service account JSON under GOOGLE_SERVICE_ACCOUNT
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

    # Ensure header exists (only once)
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
      <h1 style="margin-bottom: 6px;">⭐ Close Friends access</h1>
      <p style="font-size: 1.05rem; margin-top: 0;">
        Leave your Instagram handle to be considered for <b>Smiley’s Close Friends</b>.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Join the list")
    st.caption("We’ll use this only to identify your IG account and add you manually if selected.")

    # Optional campaign source via URL: ?src=tiktok, ?src=yt, etc.
    source = st.query_params.get("src", "")

    ig = st.text_input("Instagram handle", placeholder="@username")
    email = st.text_input("Email (optional)", placeholder="name@email.com")

    consent = st.checkbox(
        "I agree that my Instagram handle may be used to manually add me to Smiley’s Close Friends list.",
        value=False,
    )

    submitted = st.button("Submit", type="primary", use_container_width=True)

    if submitted:
        ig_n = normalize_handle(ig).lower()
        email_n = (email or "").strip() or ""

        if not ig_n:
            st.error("Please enter your Instagram handle.")
        elif not valid_handle(ig_n):
            st.error("That doesn’t look like a valid IG handle. Use letters, numbers, dots, underscores (max 30).")
        elif not consent:
            st.error("Please check the consent box to submit.")
        else:
            created_at = datetime.now(timezone.utc).isoformat()
            sheet_id = st.secrets["SHEET_ID"]

            try:
                append_row(
                    sheet_id,
                    [ig_n, email_n, source, created_at, "yes"],
                )
                st.success("Thanks! You’re on the list ✅")
            except Exception as e:
                st.error("Something went wrong saving your submission. Please try again later.")
                # Optional: log error internally
                st.stop()

st.divider()

# -------------------------
# Optional admin export (private)
# -------------------------
st.subheader("Admin (private)")
st.caption("Only for Smiley team. Users cannot see the list unless they have the password.")

admin_pw = st.text_input("Admin password", type="password")
expected_pw = st.secrets.get("ADMIN_PASSWORD", "")

if expected_pw and admin_pw == expected_pw:
    df = read_all_rows(st.secrets["SHEET_ID"])
    st.write(f"Total signups: **{len(df)}**")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv,
        file_name="smiley_close_friends_signups.csv",
        mime="text/csv",
        use_container_width=True,
    )
else:
    st.info("Enter the admin password to export the list.")
