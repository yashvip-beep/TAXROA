"""GSTIN search, business details, history, favourites, reports, sharing and news."""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import quote

import streamlit as st

from gst_engine import DISCLAIMER
from gstin_engine import format_details_text, validate_gstin
from gstin_pdf import build_gstin_report

BASE_DIR = Path(__file__).resolve().parent
NEWS_FILE = BASE_DIR / "data" / "news.json"
OFFICIAL_SEARCH_URL = "https://services.gst.gov.in/services/searchtp"
HISTORY_MAX = 15
STATUS_OPTIONS = ["Active", "Suspended", "Cancelled", "Not checked"]


def _init():
    st.session_state.setdefault("gstin_history", [])
    st.session_state.setdefault("gstin_favs", {})
    st.session_state.setdefault("gstin_details", {})
    st.session_state.setdefault("gstin_last_seen", "")


def _go(page):
    st.session_state.page = page


def _open(gstin):
    st.session_state.gstin_input = gstin
    st.session_state.page = "gstin"


def _header(title, icon):
    left, right = st.columns([1.3, 5])
    left.button("← Back to menu", key=f"gback_{title}", on_click=_go, args=("menu",))
    right.markdown(f"## {icon} {title}")


def _remember(gstin, name):
    hist = st.session_state.gstin_history
    hist[:] = [h for h in hist if h["gstin"] != gstin]
    hist.insert(0, {"gstin": gstin, "name": name,
                    "when": dt.datetime.now().strftime("%d %b %Y, %H:%M")})
    del hist[HISTORY_MAX:]


def _toggle_fav(gstin):
    favs = st.session_state.gstin_favs
    if gstin in favs:
        del favs[gstin]
    else:
        d = st.session_state.gstin_details.get(gstin)
        favs[gstin] = {"name": d["legal_name"] if d else "", "details": d}


def _clear_hist():
    st.session_state.gstin_history = []
    st.session_state.gstin_last_seen = ""


def clear_gstin_session():
    st.session_state.gstin_history = []
    st.session_state.gstin_favs = {}
    st.session_state.gstin_details = {}
    st.session_state.gstin_last_seen = ""
    st.session_state.pop("gstin_input", None)


def _details_card(gstin, info, d):
    with st.container(border=True):
        st.subheader(d["legal_name"])
        st.caption(f"GSTIN {gstin} · {info['state']}")
        st.markdown(f"**Trade name:** {d['trade_name'] or '—'}")
        st.markdown(f"**Principal place of business:** {d['address'] or '—'}")
        st.markdown(f"**Registration date:** {d['reg_date'] or '—'}")
        st.markdown(f"**Business type:** {d['business_type'] or '—'}")
        st.markdown(f"**Taxpayer category:** {d['category'] or '—'}")
        st.markdown(f"**Registration status (as entered):** {d['status']}")
        st.caption(f"Entered by you on {d['saved_on']}. Not verified by GST TAXORA.")


def _actions(gstin, info, d):
    is_fav = gstin in st.session_state.gstin_favs
    text = format_details_text(gstin, info["state"], d)
    today = dt.date.today().strftime("%d %b %Y")
    pdf = build_gstin_report(gstin, info["state"], d, info["message"], DISCLAIMER, today)
    c1, c2, c3, c4 = st.columns(4)
    c1.button("⭐ Remove favourite" if is_fav else "☆ Save to favourites",
              key=f"fav_{gstin}", on_click=_toggle_fav, args=(gstin,))
    c2.download_button("Download PDF", data=pdf, file_name=f"GSTIN_{gstin}.pdf",
                       mime="application/pdf", key=f"pdf_{gstin}")
    c3.link_button("Share on WhatsApp", "https://wa.me/?text=" + quote(text), key=f"wa_{gstin}")
    c4.link_button("Share by email",
                   "mailto:?subject=" + quote(f"GSTIN {gstin} details") + "&body=" + quote(text),
                   key=f"mail_{gstin}")
    st.caption("To copy everything, use the copy icon at the top right of the box below.")
    st.code(text, language=None)


def gstin_page():
    _init()
    _header("GSTIN search & verify", "🪪")
    st.text_input("Enter a 15-digit GSTIN", key="gstin_input", max_chars=20,
                  placeholder="e.g. 27AAPFU0939F1ZV")
    raw = st.session_state.get("gstin_input", "") or ""

    if not raw.strip():
        st.caption("Type a GSTIN to check its format and check character. If you have verified the "
                   "details on the official portal, save them here to build a report.")
        st.link_button("Open the official GST portal search ↗", OFFICIAL_SEARCH_URL, key="official_idle")
        return

    info = validate_gstin(raw)
    if not info["valid"]:
        st.error(info["message"])
        return

    gstin = info["gstin"]
    store = st.session_state.gstin_details
    d = store.get(gstin)
    if st.session_state.gstin_last_seen != gstin:
        _remember(gstin, d["legal_name"] if d else "No details saved")
        st.session_state.gstin_last_seen = gstin

    st.success(info["message"])
    st.write(f"**State:** {info['state']} (from the first two digits)")
    st.warning("This app does not contact the GST portal. Registration status is shown only "
               "if you enter it below after checking the official portal yourself.")
    st.link_button("Verify on the official GST portal ↗", OFFICIAL_SEARCH_URL, key=f"official_{gstin}")

    with st.expander("Enter details you verified on the official portal", expanded=d is None):
        with st.form(f"form_{gstin}"):
            legal = st.text_input("Legal name *")
            trade = st.text_input("Trade name (optional)")
            addr = st.text_area("Principal place of business (address)", height=80)
            reg_date = st.text_input("Registration date (DD/MM/YYYY)")
            btype = st.text_input("Business type (e.g. Proprietorship, Private Limited)")
            category = st.text_input("Taxpayer category (e.g. Regular, Composition)")
            status = st.selectbox("Registration status", STATUS_OPTIONS)
            submitted = st.form_submit_button("Save for this session")
        if submitted:
            if not legal.strip():
                st.warning("Enter the legal name to save.")
            else:
                d = {
                    "legal_name": legal.strip(), "trade_name": trade.strip(),
                    "address": addr.strip(), "reg_date": reg_date.strip(),
                    "business_type": btype.strip(), "category": category.strip(),
                    "status": status, "saved_on": dt.date.today().strftime("%d %b %Y"),
                }
                store[gstin] = d
                if gstin in st.session_state.gstin_favs:
                    st.session_state.gstin_favs[gstin] = {"name": d["legal_name"], "details": d}
                _remember(gstin, d["legal_name"])
                st.success("Saved for this session.")

    if d is None:
        st.info("No business details saved yet for this GSTIN.")
        st.code(gstin, language=None)
        return

    _details_card(gstin, info, d)
    _actions(gstin, info, d)


def history_page():
    _init()
    _header("Search history", "🕘")
    hist = st.session_state.gstin_history
    st.caption("Kept only in this session. Use Search again to open a GSTIN without typing it.")
    if not hist:
        st.info("No GSTIN searches yet in this session.")
        return
    for i, h in enumerate(hist):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1.4])
            c1.markdown(f"**{h['gstin']}**")
            c1.caption(f"{h['name']} · {h['when']}")
            c2.button("Search again", key=f"hagain_{i}_{h['gstin']}", on_click=_open, args=(h["gstin"],))
    st.button("Clear history", key="hclear", on_click=_clear_hist)


def favs_page():
    _init()
    _header("Favourites", "⭐")
    favs = st.session_state.gstin_favs
    if not favs:
        st.info("No favourites yet. Open a GSTIN and tap Save to favourites.")
        return
    for gstin, entry in list(favs.items()):
        d = entry.get("details") or st.session_state.gstin_details.get(gstin)
        with st.container(border=True):
            st.markdown(f"**{gstin}**")
            st.caption(entry.get("name") or "No details saved")
            if d:
                st.write(f"Trade name: {d['trade_name'] or '—'} · Status (as entered): {d['status']}")
                st.write(f"Address: {d['address'] or '—'}")
            c1, c2 = st.columns(2)
            c1.button("Open", key=f"fopen_{gstin}", on_click=_open, args=(gstin,))
            c2.button("Remove", key=f"frem_{gstin}", on_click=_toggle_fav, args=(gstin,))


@st.cache_data
def _load_news():
    with open(NEWS_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def news_page():
    _init()
    _header("GST news & updates", "📰")
    data = _load_news()
    items = sorted(data["items"], key=lambda x: x["date"], reverse=True)
    st.caption(f"Curated from the notifications in the project files, last checked "
               f"{data['meta']['last_checked']}. This app does not fetch live news, so check "
               "CBIC for the latest.")
    cats = ["All"] + sorted({i["category"] for i in items})
    choice = st.selectbox("Show", cats, key="news_cat")
    for item in [i for i in items if choice == "All" or i["category"] == choice]:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['category']} · Notified {item['date']} · Effective {item['effective']}")
            st.write(item["summary"])
            st.caption(f"Reference: {item['reference']}")
            st.link_button(f"Read more on {item.get('source_name', 'the official site')} ↗", item["source_url"], key=f"news_{item['id']}")


GSTIN_MENU = [
    ("gstin", "🪪", "GSTIN search & verify", "Check format, view and save business details"),
    ("ghist", "🕘", "Search history", "Recent GSTIN searches, search again in one click"),
    ("gfav", "⭐", "Favourites", "Saved GST numbers for quick access"),
    ("gnews", "📰", "GST news & updates", "Rate changes, notifications and new rules"),
]

GSTIN_ROUTES = {
    "gstin": gstin_page,
    "ghist": history_page,
    "gfav": favs_page,
    "gnews": news_page,
}
