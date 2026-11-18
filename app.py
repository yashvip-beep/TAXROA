import datetime as dt
import re

import pandas as pd
import streamlit as st

from barcode_engine import decode_image, ean_valid, is_product_code, load_barcodes, lookup_barcode
from gst_engine import (
    DISCLAIMER,
    NOT_FOUND_MSG,
    calculate,
    digits_only,
    fmt_pct,
    load_dataset,
    rate_split,
    result_row,
    search_code,
    search_text,
    status_text,
    to_csv,
    total_gst_pct,
)
from guides import GUIDES, VIDEO_NOTE
from invoice_engine import compute_invoice, valid_gstin
from invoice_pdf import build_invoice_pdf
from gstin_pages import GSTIN_MENU, GSTIN_ROUTES, clear_gstin_session

APP_NAME = "GST TAXORA"
MAX_HISTORY = 10
TODAY = dt.date.today().isoformat()
SUPPLY_OPTIONS = ["Intra-State (CGST + SGST/UTGST)", "Inter-State (IGST)"]

st.set_page_config(page_title=APP_NAME, page_icon="🧾", layout="wide",
                   initial_sidebar_state="collapsed")

from string import Template

THEMES = {
    "Dark": {
        "bg": "radial-gradient(circle at 0% 0%, rgba(255,122,24,0.20), transparent 35%), radial-gradient(circle at 100% 15%, rgba(179,27,255,0.18), transparent 40%), radial-gradient(circle at 50% 100%, rgba(0,229,255,0.12), transparent 45%), #000000",
        "text": "#ffffff", "muted": "#a7b0bd", "panel": "#08080d", "card": "#13131c",
        "input": "#101018", "border": "#2c2c3a", "accent": "#FF7A18", "accent2": "#FF2D55",
        "metric": "#FFD200", "metric_bg": "linear-gradient(135deg, rgba(255,122,24,0.18), rgba(179,27,255,0.18))",
        "glow": "rgba(255,122,24,0.40)",
    },
    "Light": {
        "bg": "linear-gradient(135deg, #fff7ed 0%, #fdf2f8 50%, #ecfeff 100%)",
        "text": "#111827", "muted": "#4b5563", "panel": "#ffffff", "card": "#ffffff",
        "input": "#ffffff", "border": "#d4d8e0", "accent": "#E8590C", "accent2": "#C2255C",
        "metric": "#B45309", "metric_bg": "linear-gradient(135deg, #fff1e6, #fce7f3)",
        "glow": "rgba(232,89,12,0.25)",
    },
}

CSS_TEMPLATE = Template("""<style>
.stApp { background: $bg !important; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: $panel; border-right: 1px solid $border; }
.block-container { padding-top: 1.2rem; max-width: 1040px; }

h1, h2, h3, h4 { color: $text !important; font-weight: 700; }
p, li, label, [data-testid="stCaptionContainer"], .stCaption { color: $muted !important; }
.stMarkdown p, .stMarkdown li { color: $text !important; }
[data-testid="stRadio"] label p, [data-testid="stCheckbox"] label p,
[data-testid="stWidgetLabel"] p { color: $text !important; }

/* Inputs, selects, text areas */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div,
[data-baseweb="textarea"], div[data-baseweb="input"] > div {
    background: $input !important; border-color: $border !important;
}
input, textarea, [data-baseweb="select"] span { color: $text !important; }

/* Tabs */
[data-baseweb="tab"] { color: $muted !important; }
[data-baseweb="tab"][aria-selected="true"] { color: $accent !important; }
[data-baseweb="tab-highlight"] { background: $accent !important; }
[data-baseweb="tab-border"] { background: $border !important; }

/* Expanders, code blocks, alerts */
[data-testid="stExpander"] details { background: $card; border: 1px solid $border; border-radius: 12px; }
[data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span { color: $text !important; }
pre, code { background: $card !important; color: $text !important; border: 1px solid $border; }
[data-testid="stAlert"] { border-radius: 10px; }

/* Title splash */
.splash { text-align: center; padding: 6rem 1rem 3rem 1rem; }
.splash h1 {
    font-size: 5rem; font-weight: 900; letter-spacing: 4px; margin: 0;
    background: linear-gradient(90deg, #FFD200, #FF7A18, #FF2D55, #B31BFF, #00E5FF);
    -webkit-background-clip: text; background-clip: text; color: transparent !important;
}
.splash p.tag { color: $muted !important; letter-spacing: 2px; margin-top: 0.6rem; }

/* Menu */
.menu-title { text-align: center; font-size: 2rem; font-weight: 800; color: $text; margin-bottom: 0.2rem; }
.menu-sub { text-align: center; color: $muted !important; margin-bottom: 1.4rem; }
.menu-section { font-size: 0.8rem; font-weight: 800; letter-spacing: 2px; text-transform: uppercase;
    margin: 1.6rem 0 0.6rem 0; }
.menu-desc { color: $muted !important; font-size: 0.85rem; margin: 0.25rem 0 0.9rem 0.2rem; }

div.stButton > button {
    min-height: 3rem; border-radius: 12px; font-size: 1rem; font-weight: 600;
    color: $text !important; background: $card; border: 1px solid $border;
    box-shadow: 0 2px 10px rgba(0,0,0,0.12);
    transition: all 0.18s ease;
}
div.stButton > button:hover {
    color: $text !important; border-color: $accent; background: $card;
    box-shadow: 0 0 18px $glow; transform: translateY(-1px);
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, $accent, $accent2) !important; border: none; color: #ffffff !important;
}

/* Metrics and bordered cards */
[data-testid="stMetric"] {
    background: $metric_bg; border: 1px solid $border; padding: 0.8rem; border-radius: 14px;
}
[data-testid="stMetricValue"] { color: $metric !important; }
[data-testid="stMetricLabel"] p { color: $muted !important; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important; border: 1px solid $border !important; background: $panel;
}
</style>""")


def build_css(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES["Dark"])
    return CSS_TEMPLATE.safe_substitute(tokens)


@st.cache_data
def get_dataset():
    return load_dataset()


@st.cache_data
def get_barcodes():
    return load_barcodes()


META, RECORDS = get_dataset()
BARCODES = get_barcodes()


def blank_rows():
    return [{"Description": "", "HSN/SAC": "", "Qty": 1.0, "Unit price (Rs)": 0.0, "GST %": 18.0}]


for key, value in {"page": "splash", "history": [], "inv_rows": blank_rows()}.items():
    st.session_state.setdefault(key, value)

MENU = [
    ("search", "🔎", "Search", "Find the GST rate, HSN or SAC code by name or code"),
    ("browse", "🗂️", "Browse by category", "Filter items by category and GST slab"),
    ("calc", "🧮", "GST calculator", "Add or extract GST, with the CGST/SGST/IGST split"),
    ("scan", "📷", "Barcode & QR scanner", "Scan a product code to get its category and GST rate"),
    ("invoice", "🧾", "GST invoice generator", "Create a printable invoice PDF with GST"),
    ("bulk", "📑", "Bulk check", "Check many items from a CSV file at once"),
    ("guide", "📚", "Step-by-step guide", "Learn each feature with steps and videos"),
    *GSTIN_MENU,
    ("privacy", "🔒", "Privacy & data", "See what is kept and delete your session data"),
]
MENU_TITLE = {key: title for key, _, title, _ in MENU}
MENU_ICON = {key: icon for key, icon, _, _ in MENU}


def go(page):
    st.session_state.page = page


def page_header(key):
    home, back, title = st.columns([1, 1.3, 4])
    home.button("🏠 Home", key=f"home_{key}", on_click=go, args=("splash",))
    back.button("← Back to menu", key=f"back_{key}", on_click=go, args=("menu",))
    title.markdown(f"## {MENU_ICON[key]} {MENU_TITLE[key]}")


def supply_key(label: str) -> str:
    return "intra" if label.startswith("Intra") else "inter"


def remember(entry: str) -> None:
    history = st.session_state.history
    if entry not in history:
        history.insert(0, entry)
        del history[MAX_HISTORY:]


def show_result(rec: dict, supply: str) -> None:
    pct = total_gst_pct(rec)
    split = rate_split(rec)
    with st.container(border=True):
        kind_label = "Service (SAC)" if rec["kind"] == "service" else "Goods (HSN)"
        st.subheader(rec["name"])
        st.caption(f"{kind_label}: {rec['hsn_sac']} · Category: {rec['category']}")
        if rec["treatment"] == "taxable":
            st.success("GST APPLICABLE")
        else:
            st.info("GST NOT APPLICABLE — Exempt (nil rate under the exemption notification)")

        if supply == "intra":
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total GST", fmt_pct(pct))
            c2.metric("CGST", fmt_pct(split["cgst"]))
            c3.metric("SGST/UTGST", fmt_pct(split["sgst"]))
            c4.metric("IGST", "Not applicable")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Total GST", fmt_pct(pct))
            c2.metric("IGST", fmt_pct(split["igst"]))

        st.markdown(f"**Cess:** {rec.get('cess', 'Not covered by this dataset - verify on CBIC')}")
        st.markdown(f"**Notification:** {rec['notification']} · **Entry:** {rec['serial']}")
        st.markdown(f"**Condition:** {rec['condition']}")
        st.markdown(f"**Effective from:** {rec['effective_from']}")
        st.markdown(f"**Source:** [CBIC GST portal]({rec['source_url']})")
        if rec["note"]:
            st.caption(f"Note: {rec['note']}")


def history_panel() -> None:
    with st.expander("Recent searches (this session)"):
        if not st.session_state.history:
            st.write("No recent searches.")
        else:
            for entry in st.session_state.history:
                st.write(f"- {entry}")
        st.caption("Kept only in this session's server memory. Not saved to disk or browser storage.")
        if st.button("Clear history", key="clear_history"):
            st.session_state.history = []
            st.rerun()


def splash():
    st.markdown('<div class="splash"><h1>GST TAXORA</h1><p class="tag">GST rates · Calculator · Invoice · GSTIN</p></div>', unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1, 1])
    mid.button("Get started  →", use_container_width=True, on_click=go, args=("menu",), key="start")


def menu_page():
    home, _ = st.columns([1, 4])
    home.button("🏠 Home", key="home_menu", on_click=go, args=("splash",))
    sections = [
        ("GST rates and tax", "#FF7A18", ["search", "browse", "calc"]),
        ("Products and billing", "#00E5FF", ["scan", "invoice", "bulk"]),
        ("GSTIN and business", "#B31BFF", ["gstin", "ghist", "gfav", "gnews"]),
        ("Help and privacy", "#FFD200", ["guide", "privacy"]),
    ]
    by_key = {m[0]: m for m in MENU}
    card_css = "".join(
        f".st-key-menu_{key} button {{ border-left: 6px solid {colour} !important; "
        f"min-height: 3.6rem !important; }}"
        f".st-key-menu_{key} button, .st-key-menu_{key} button p, .st-key-menu_{key} button span "
        f"{{ font-size: 1.25rem !important; font-weight: 700 !important; }}"
        for _, colour, keys in sections for key in keys
    )
    st.markdown(
        f"<style>{card_css}"
        ".menu-desc { font-size: 0.98rem !important; margin: 0.15rem 0 0.7rem 0.2rem !important; }"
        ".menu-section { font-size: 0.95rem !important; margin: 1.1rem 0 0.4rem 0 !important; }"
        "div[data-testid='stVerticalBlock'] > div { gap: 0.35rem; }"
        "</style>",
        unsafe_allow_html=True,
    )
    for heading, colour, keys in sections:
        st.markdown(f"<div class='menu-section' style='color:{colour}'>{heading}</div>",
                    unsafe_allow_html=True)
        for key in keys:
            _, icon, title, desc = by_key[key]
            st.button(f"{icon}  {title}", key=f"menu_{key}", use_container_width=True,
                      on_click=go, args=(key,))
            st.markdown(f"<div class='menu-desc'>{desc}</div>", unsafe_allow_html=True)

def search_page():
    page_header("search")
    mode = st.radio("What are you looking up?",
                    ["Goods by name", "Goods by HSN code", "Services by name or SAC code"],
                    horizontal=True, key="search_mode")
    supply = supply_key(st.radio("Supply type", SUPPLY_OPTIONS, horizontal=True, key="supply_type"))
    keep = st.checkbox("Keep my recent searches for this session (off by default)",
                       value=False, key="keep_history")
    query = st.text_input("Item, HSN code or SAC code", key="query",
                          placeholder="e.g. rice, ricee, 1006, cement, restaurant, 9963")
    history_panel()

    if not query.strip():
        st.caption("Type a name (small spelling mistakes are fine) or a 4, 6 or 8-digit code.")
        return

    try:
        if mode == "Goods by HSN code":
            exact, suggestions = search_code(query, RECORDS, "goods"), []
        elif mode == "Goods by name":
            exact, suggestions = search_text(query, RECORDS, "goods")
        elif digits_only(query):
            exact, suggestions = search_code(query, RECORDS, "service"), []
        else:
            exact, suggestions = search_text(query, RECORDS, "service")
    except ValueError as err:
        st.error(str(err))
        return

    if not exact and not suggestions:
        st.warning(NOT_FOUND_MSG)
        return
    if keep:
        remember(f"{query.strip()} [{mode}]")

    for rec in exact[:10]:
        show_result(rec, supply)
    if len(exact) > 10:
        st.caption(f"Showing the first 10 of {len(exact)} matches. Refine your search to narrow it.")
    if suggestions:
        st.info("Suggestions only — these are NOT confirmed classifications.")
        for rec in suggestions[:5]:
            st.write(f"- {rec['name']} (HSN/SAC {rec['hsn_sac']})")
    if exact:
        rows = [result_row(r, supply, META, TODAY) for r in exact]
        st.download_button("Download these results (CSV)", data=to_csv(rows),
                           file_name=f"gst_results_{TODAY}.csv", mime="text/csv", key="dl_results")


def browse_page():
    page_header("browse")
    categories = ["All categories"] + sorted({r["category"] for r in RECORDS})
    slabs = {"All rates": None}
    for pct in sorted({total_gst_pct(r) for r in RECORDS}):
        slabs["0% (exempt / nil)" if pct == 0 else fmt_pct(pct)] = pct

    c1, c2, c3 = st.columns(3)
    category = c1.selectbox("Category", categories, key="browse_cat")
    kind = c2.radio("Type", ["Both", "Goods", "Services"], horizontal=True, key="browse_kind")
    slab_label = c3.selectbox("GST slab (from the dataset)", list(slabs), key="browse_slab")

    rows = []
    for rec in RECORDS:
        if category != "All categories" and rec["category"] != category:
            continue
        if kind == "Goods" and rec["kind"] != "goods":
            continue
        if kind == "Services" and rec["kind"] != "service":
            continue
        if slabs[slab_label] is not None and total_gst_pct(rec) != slabs[slab_label]:
            continue
        rows.append({
            "Item": rec["name"],
            "Type": "Service" if rec["kind"] == "service" else "Goods",
            "HSN/SAC": rec["hsn_sac"],
            "Status": "Applicable" if rec["treatment"] == "taxable" else "Exempt",
            "Total GST": fmt_pct(total_gst_pct(rec)),
            "Notification": rec["notification"],
            "Entry": rec["serial"],
        })
    if not rows:
        st.info("No items match these filters.")
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption("Use Search to see the full condition and notes for an item.")


def calc_page():
    page_header("calc")
    st.caption("An estimate based on the classification you choose. Rounded to 2 decimal places.")
    taxable = [r for r in RECORDS if r["treatment"] == "taxable"]
    labels = ["Manual rate"] + [f"{r['name']} — {fmt_pct(total_gst_pct(r))}" for r in taxable]

    c1, c2 = st.columns(2)
    base = c1.number_input("Base amount (₹)", min_value=0.01, value=1000.0, step=100.0,
                           format="%.2f", key="calc_base")
    choice = c2.selectbox("Rate source", labels, key="calc_choice")

    if choice == "Manual rate":
        rate = st.number_input("GST rate (%)", min_value=0.0, max_value=100.0, value=18.0,
                               step=0.25, format="%.3f", key="calc_rate")
        st.caption("Manual rate: you are responsible for confirming that it applies to your item.")
    else:
        rec = taxable[labels.index(choice) - 1]
        rate = float(total_gst_pct(rec))
        st.caption(f"Rate taken from {rec['notification']}, {rec['serial']}.")

    c3, c4 = st.columns(2)
    supply = supply_key(c3.radio("Supply type", SUPPLY_OPTIONS, key="calc_supply"))
    mode_label = c4.radio("Mode", ["Add GST to base amount", "Extract GST from inclusive amount"],
                          key="calc_mode")
    mode = "add" if mode_label.startswith("Add") else "extract"

    try:
        res = calculate(base, rate, supply, mode)
    except ValueError as err:
        st.error(str(err))
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Taxable value", f"₹{res['taxable_value']}")
    m2.metric("CGST", f"₹{res['cgst']}")
    m3.metric("SGST/UTGST", f"₹{res['sgst_utgst']}")
    m4, m5, m6 = st.columns(3)
    m4.metric("IGST", f"₹{res['igst']}")
    m5.metric("Total tax", f"₹{res['total_tax']}")
    m6.metric("Final amount", f"₹{res['final_amount']}")
    st.caption(res["rounding_note"])

    export = [{
        **res,
        "rate_pct": str(rate),
        "supply": "Intra-State" if supply == "intra" else "Inter-State",
        "mode": "Add GST" if mode == "add" else "Extract GST",
        "dataset_version": META["dataset_version"],
        "downloaded_on": TODAY,
        "disclaimer": DISCLAIMER,
    }]
    st.download_button("Download calculation (CSV)", data=to_csv(export),
                       file_name=f"gst_calc_{TODAY}.csv", mime="text/csv", key="dl_calc")


def handle_code(code: str, supply: str):
    st.markdown(f"**Code read:** `{code}`")
    if not is_product_code(code):
        st.info("This is not an EAN-8, UPC-A or EAN-13 product barcode, so no product GST rate can be shown.")
        return
    if not ean_valid(code):
        st.warning("The check digit does not match. Scan again or type the number carefully.")
        return
    rec = lookup_barcode(code, BARCODES, RECORDS)
    if rec is None:
        st.info("This barcode is valid but is not yet linked to a verified item, so no rate is shown. "
                "Use Search to find the item by name.")
        return
    st.success(f"Category: {rec['category']}")
    show_result(rec, supply)


def scan_page():
    page_header("scan")
    supply = supply_key(st.radio("Supply type", SUPPLY_OPTIONS, horizontal=True, key="scan_supply"))
    tab_cam, tab_photo, tab_type = st.tabs(["📸 Camera", "🖼️ Upload photo", "⌨️ Type code"])

    with tab_cam:
        cam = st.camera_input("Point the camera at the barcode or QR code", key="scan_cam")
    with tab_photo:
        up = st.file_uploader("Upload a clear photo of the barcode or QR code",
                              type=["png", "jpg", "jpeg"], key="scan_up")
    with tab_type:
        typed = st.text_input("Barcode number (EAN-8, UPC-A or EAN-13)", key="scan_typed")

    codes: list[str] = []
    source = cam if cam is not None else up
    if source is not None:
        try:
            from PIL import Image
            codes = decode_image(Image.open(source))
            if not codes:
                st.warning("No barcode or QR code found in this image. Try a closer, sharper photo.")
        except RuntimeError as err:
            st.error(str(err))
        except Exception:
            st.warning("Could not read this image. Try another photo or type the number.")

    if typed.strip():
        codes = [typed.strip()]
    for code in codes:
        handle_code(code, supply)


def _txt(value) -> str:
    return "" if value is None or pd.isna(value) else str(value).strip()


def _num(value, default: float) -> float:
    return default if value is None or pd.isna(value) else float(value)


def clear_invoice():
    for key in ["inv_s_name", "inv_s_gstin", "inv_s_addr", "inv_b_name", "inv_b_gstin",
                "inv_b_addr", "inv_no", "inv_date", "inv_supply", "inv_editor"]:
        st.session_state.pop(key, None)
    st.session_state.inv_rows = blank_rows()


def invoice_page():
    page_header("invoice")
    st.info("Details you enter stay in this session and are used only to build the PDF.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Seller**")
        s_name = st.text_input("Seller name", key="inv_s_name")
        s_gstin = st.text_input("Seller GSTIN (optional)", key="inv_s_gstin")
        s_addr = st.text_area("Seller address", key="inv_s_addr", height=80)
    with c2:
        st.markdown("**Buyer**")
        b_name = st.text_input("Buyer name", key="inv_b_name")
        b_gstin = st.text_input("Buyer GSTIN (optional)", key="inv_b_gstin")
        b_addr = st.text_area("Buyer address", key="inv_b_addr", height=80)

    if s_gstin.strip() and not valid_gstin(s_gstin):
        st.warning("Seller GSTIN format looks wrong. A GSTIN has 15 characters.")
    if b_gstin.strip() and not valid_gstin(b_gstin):
        st.warning("Buyer GSTIN format looks wrong. A GSTIN has 15 characters.")

    c3, c4, c5 = st.columns(3)
    inv_no = c3.text_input("Invoice number", value="INV-0001", key="inv_no")
    inv_date = c4.date_input("Invoice date", value=dt.date.today(), key="inv_date")
    supply = supply_key(c5.radio("Supply type", SUPPLY_OPTIONS, key="inv_supply"))

    with st.expander("Look up GST % from the dataset"):
        ref = pd.DataFrame([{"Item": r["name"], "HSN/SAC": r["hsn_sac"],
                             "Total GST %": fmt_pct(total_gst_pct(r))} for r in RECORDS])
        st.dataframe(ref, hide_index=True, use_container_width=True)
        st.caption("Copy the GST % into the item table below. Check the notification before invoicing.")

    st.markdown("**Items**")
    edited = st.data_editor(
        pd.DataFrame(st.session_state.inv_rows),
        num_rows="dynamic",
        use_container_width=True,
        key="inv_editor",
        column_config={
            "Description": st.column_config.TextColumn("Item description", width="large"),
            "HSN/SAC": st.column_config.TextColumn("HSN/SAC"),
            "Qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0, format="%.2f"),
            "Unit price (Rs)": st.column_config.NumberColumn("Unit price (Rs)", min_value=0.0, format="%.2f"),
            "GST %": st.column_config.NumberColumn("GST %", min_value=0.0, max_value=100.0, format="%.3f"),
        },
    )
    st.session_state.inv_rows = edited.to_dict("records")

    lines = []
    for r in st.session_state.inv_rows:
        desc = _txt(r.get("Description"))
        if not desc:
            continue
        lines.append({
            "description": desc,
            "hsn": _txt(r.get("HSN/SAC")),
            "qty": _num(r.get("Qty"), 1.0),
            "unit_price": _num(r.get("Unit price (Rs)"), 0.0),
            "gst_pct": _num(r.get("GST %"), 0.0),
        })

    if not lines:
        st.info("Add at least one item with a description to see the invoice totals.")
    else:
        try:
            result = compute_invoice(lines, supply)
        except ValueError as err:
            st.error(str(err))
            result = None

        if result:
            st.markdown("**Invoice preview**")
            st.dataframe(pd.DataFrame([{
                "Item": l["description"], "HSN/SAC": l["hsn"], "Qty": l["qty"],
                "Taxable": l["taxable"], "GST %": l["gst_pct"] + "%",
                "Tax": l["tax"], "Total": l["total"],
            } for l in result["lines"]]), hide_index=True, use_container_width=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Taxable value", f"₹{result['taxable']}")
            m2.metric("CGST", f"₹{result['cgst']}")
            m3.metric("SGST/UTGST", f"₹{result['sgst']}")
            m4.metric("IGST", f"₹{result['igst']}")
            m5.metric("Grand total", f"₹{result['grand_total']}")

            if not s_name.strip() or not b_name.strip():
                st.warning("Enter both seller and buyer names to download the PDF.")
            else:
                seller = {"name": s_name.strip(), "gstin": s_gstin.strip().upper(),
                          "address": s_addr.strip()}
                buyer = {"name": b_name.strip(), "gstin": b_gstin.strip().upper(),
                         "address": b_addr.strip()}
                inv = {"number": inv_no.strip() or "INV-0001", "date": inv_date.isoformat(),
                       "supply": supply}
                pdf_bytes = build_invoice_pdf(seller, buyer, inv, result, DISCLAIMER)
                safe_no = re.sub(r"[^A-Za-z0-9_-]+", "_", inv["number"])
                st.download_button("Download invoice PDF", data=pdf_bytes,
                                   file_name=f"invoice_{safe_no}.pdf", mime="application/pdf",
                                   key="dl_invoice", type="primary")

    st.button("Clear invoice", on_click=clear_invoice, key="inv_clear")


def bulk_page():
    page_header("bulk")
    st.write("Upload a CSV with a column named **item**. Each row is matched to the goods list.")
    sample = pd.DataFrame({"item": ["rice", "cement", "laptop", "fresh milk"]})
    st.download_button("Download sample CSV", data=sample.to_csv(index=False).encode("utf-8-sig"),
                       file_name="bulk_sample.csv", mime="text/csv", key="dl_sample")

    up = st.file_uploader("CSV file", type=["csv"], key="bulk_file")
    if up is None:
        return
    try:
        df = pd.read_csv(up)
    except Exception:
        st.error("Could not read this CSV file.")
        return

    cols = {str(c).strip().lower(): c for c in df.columns}
    if "item" not in cols:
        st.error('The CSV needs a column named "item".')
        return

    items = [str(x).strip() for x in df[cols["item"]].dropna().tolist() if str(x).strip()][:200]
    rows = []
    for item in items:
        exact, _ = search_text(item, RECORDS, "goods")
        if exact:
            rec = exact[0]
            note = f"{len(exact)} matches; first shown" if len(exact) > 1 else ""
            rows.append({"Your item": item, "Matched item": rec["name"], "HSN/SAC": rec["hsn_sac"],
                         "Total GST": fmt_pct(total_gst_pct(rec)), "Status": status_text(rec),
                         "Note": note})
        else:
            rows.append({"Your item": item, "Matched item": "Not found", "HSN/SAC": "",
                         "Total GST": "", "Status": "Not found", "Note": "Try Search for this item"})

    if not rows:
        st.info("The CSV has no items to check.")
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.download_button("Download results (CSV)", data=to_csv(rows),
                       file_name=f"bulk_results_{TODAY}.csv", mime="text/csv", key="dl_bulk")


def guide_page():
    page_header("guide")
    topic = st.selectbox("Choose a guide", list(GUIDES), key="guide_topic")
    g = GUIDES[topic]
    st.markdown(f"### {g['title']}")
    st.write(g["summary"])
    for i, step in enumerate(g["steps"], 1):
        st.markdown(f"**Step {i}.** {step}")

    st.markdown("#### Videos")
    if not g["videos"]:
        st.info(VIDEO_NOTE)
    for video in g["videos"]:
        st.write(f"**{video['title']}**")
        if video["url"]:
            st.video(video["url"])
        else:
            st.info(VIDEO_NOTE)


def clear_all():
    clear_invoice()
    clear_gstin_session()
    st.session_state.history = []
    for key in ["query", "scan_typed", "calc_base", "calc_rate", "bulk_file"]:
        st.session_state.pop(key, None)


def privacy_page():
    page_header("privacy")
    st.markdown("""
**What the app keeps**
- Searches and calculations need no personal data. The app never asks for Aadhaar, PAN, bank or card details, contacts, location or ID documents.
- Recent searches are off by default. If you turn them on, they stay in this session's server memory only.
- Invoice details (seller and buyer names, addresses, GSTIN) are used only to build the PDF in your session. They are not saved to disk or to any database.
- Camera and photo scans are read in memory to find a code. The image is not saved by the app.
- Downloads contain only the data you asked for.

**Hosting and vendors**
- The hosting provider is to be confirmed before launch. It may keep standard server and access logs under its own policy.
- The app has no advertising, behavioural analytics or session-replay tools.

**Your rights and complaints**
- Under the Digital Personal Data Protection Act, 2023, you may seek access, correction, erasure, grievance redressal and nomination. The main obligations take effect on 13 May 2027 (G.S.R. 843(E)).
- Grievance contact: [add a working privacy email before launch].

**Status**
This app is designed to align with the DPDP framework. It is not a claim of compliance and is subject to a documented pre-launch review.
""")
    st.divider()
    st.button("Delete all session data now", on_click=clear_all, key="clear_privacy")
    st.caption("Clears recent searches, invoice details, scanner input and bulk uploads for this session.")


def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚠️ Disclaimer")
        with st.expander("Read the full disclaimer"):
            st.write(DISCLAIMER)
        st.markdown("## 📘 About this data")
        st.write(f"**Dataset version:** {META['dataset_version']}")
        st.write(f"**Last updated:** {META['last_updated']}")
        st.caption(META["status"])
        st.caption(f"Source: [{META['source']}]({META['source']})")


ROUTES = {
    "splash": splash,
    "menu": menu_page,
    "search": search_page,
    "browse": browse_page,
    "calc": calc_page,
    "scan": scan_page,
    "invoice": invoice_page,
    "bulk": bulk_page,
    "guide": guide_page,
    "privacy": privacy_page,
    **GSTIN_ROUTES,
}


def main():
    render_sidebar()
    st.markdown(build_css("Dark"), unsafe_allow_html=True)
    page = st.session_state.page
    ROUTES.get(page, splash)()
    if page not in ("splash", "menu"):
        st.divider()
        st.caption("Informational only. Read the full disclaimer in the sidebar (open with »).")


main()
