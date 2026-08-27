"""
Error Fare Bot — Config GUI
----------------------------
A small web app (free to host on Streamlit Community Cloud) for editing
your error-fare-bot configuration through validated form fields instead of
hand-editing JSON.

Each section only accepts input of the correct type/shape and shows a
specific rejection message if you enter something invalid.

Run locally with:   streamlit run app.py
"""

import json
import re

import streamlit as st

st.set_page_config(page_title="Error Fare Bot Config", page_icon="\u2708\ufe0f")

IATA_RE = re.compile(r"^[A-Z]{3}$")
TELEGRAM_TOKEN_RE = re.compile(r"^\d{6,10}:[A-Za-z0-9_-]{30,45}$")
TELEGRAM_CHAT_ID_RE = re.compile(r"^-?\d{5,15}$")
DESTINATION_RE = re.compile(r"^[A-Za-z\s\-]{2,40}$")

st.title("\u2708\ufe0f Error Fare Bot — Configuration")
st.caption(
    "Fill in each section below. Invalid entries are rejected immediately "
    "with an explanation, so config.json never ends up malformed."
)

# ---------------------------------------------------------------------------
# Section 1: Destinations (free-text keyword filter for the blog aggregator)
# ---------------------------------------------------------------------------
st.header("1. Destinations to watch")
st.write("City, region, or country names — letters, spaces and hyphens only.")

if "destinations" not in st.session_state:
    st.session_state.destinations = []

dest_input = st.text_input("Add a destination (e.g. 'Tokyo', 'South-East Asia')")
if st.button("Add destination"):
    value = dest_input.strip()
    if not value:
        st.error("Input incorrect: destination cannot be empty.")
    elif not DESTINATION_RE.match(value):
        st.error(
            "Input incorrect: destinations may only contain letters, spaces, "
            "and hyphens (2-40 characters). No numbers or symbols."
        )
    elif value in st.session_state.destinations:
        st.warning(f"'{value}' is already in your list.")
    else:
        st.session_state.destinations.append(value)
        st.success(f"Added '{value}'.")

if st.session_state.destinations:
    for i, d in enumerate(st.session_state.destinations):
        col1, col2 = st.columns([4, 1])
        col1.write(f"\u2022 {d}")
        if col2.button("Remove", key=f"rm_dest_{i}"):
            st.session_state.destinations.pop(i)
            st.rerun()

# ---------------------------------------------------------------------------
# Section 2: Routes (IATA origin/destination pairs for the price scorer)
# ---------------------------------------------------------------------------
st.header("2. Routes to price-check")
st.write("3-letter IATA airport codes only, e.g. JFK, LHR, NRT.")

if "routes" not in st.session_state:
    st.session_state.routes = []

col1, col2, col3 = st.columns([2, 2, 1])
origin_input = col1.text_input("Origin airport code", max_chars=3, key="origin_in")
dest_code_input = col2.text_input("Destination airport code", max_chars=3, key="dest_in")
add_route = col3.button("Add route")

if add_route:
    origin = origin_input.strip().upper()
    destination = dest_code_input.strip().upper()
    errors = []
    if not IATA_RE.match(origin):
        errors.append(f"Origin '{origin_input}' is not a valid 3-letter IATA code.")
    if not IATA_RE.match(destination):
        errors.append(f"Destination '{dest_code_input}' is not a valid 3-letter IATA code.")
    if origin and destination and origin == destination:
        errors.append("Origin and destination can't be the same airport.")

    if errors:
        for e in errors:
            st.error(f"Input incorrect: {e}")
    else:
        pair = {"origin": origin, "destination": destination}
        if pair in st.session_state.routes:
            st.warning(f"{origin} → {destination} is already in your list.")
        else:
            st.session_state.routes.append(pair)
            st.success(f"Added route {origin} → {destination}.")

if st.session_state.routes:
    for i, r in enumerate(st.session_state.routes):
        col1, col2 = st.columns([4, 1])
        col1.write(f"\u2022 {r['origin']} \u2192 {r['destination']}")
        if col2.button("Remove", key=f"rm_route_{i}"):
            st.session_state.routes.pop(i)
            st.rerun()

min_savings = st.slider(
    "Minimum savings % to alert on for scored routes", min_value=10, max_value=90, value=40
)

# ---------------------------------------------------------------------------
# Section 3: Notification settings
# ---------------------------------------------------------------------------
st.header("3. Notification settings")
st.write(
    "These are stored as GitHub Secrets, not saved in config.json. "
    "Paste them here only to validate the format before you add them to GitHub."
)

tg_token_input = st.text_input("Telegram bot token", type="password")
if tg_token_input:
    if TELEGRAM_TOKEN_RE.match(tg_token_input):
        st.success("Token format looks valid.")
    else:
        st.error(
            "Input incorrect: a Telegram bot token looks like "
            "'123456789:AAExampleTokenHere' — digits, a colon, then the token body."
        )

tg_chat_id_input = st.text_input("Telegram chat ID")
if tg_chat_id_input:
    if TELEGRAM_CHAT_ID_RE.match(tg_chat_id_input.strip()):
        st.success("Chat ID format looks valid.")
    else:
        st.error("Input incorrect: chat ID should be a numeric value, e.g. 123456789.")

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
st.header("4. Your config.json")
config = {
    "destinations": st.session_state.destinations,
    "only_error_fares": False,
    "routes": st.session_state.routes,
    "min_savings_percent": min_savings,
}
config_text = json.dumps(config, indent=2)
st.code(config_text, language="json")
st.download_button("Download config.json", config_text, file_name="config.json")
st.caption(
    "Download this file and upload it into your GitHub repo, replacing the "
    "existing config.json. Bot token / chat ID / Travelpayouts token stay in "
    "GitHub Secrets — never put them in this file."
)
