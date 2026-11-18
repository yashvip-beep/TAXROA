"""Core GST logic. No Streamlit imports, so it can be unit-tested with pytest.
Rates are read from data/gst_rates.json, never hard-coded."""
from __future__ import annotations

import csv
import difflib
import io
import json
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "gst_rates.json"

NOT_FOUND_MSG = "Item not found — please check spelling or try a related term."
DISCLAIMER = (
    "This tool is provided for general information and educational purposes. GST classification "
    "and tax treatment depend on the precise nature of the goods or services, facts of the "
    "transaction, applicable notifications and conditions. Verify the relevant official notification "
    "and obtain advice from a qualified tax professional before relying on the result for invoicing, "
    "return filing or other compliance. The tool does not constitute legal or tax advice."
)

HUNDRED = Decimal("100")
CENT = Decimal("0.01")
ZERO = Decimal("0")
FUZZY_CUTOFF = 0.78

REQUIRED_FIELDS = {
    "id", "kind", "name", "aliases", "hsn_sac", "category", "treatment", "cgst_pct",
    "notification", "serial", "condition", "effective_from", "source_url", "note",
}
VALID_KINDS = {"goods", "service"}
VALID_TREATMENTS = {"taxable", "exempt"}


def _validate(records: list[dict]) -> None:
    seen: set[str] = set()
    for rec in records:
        missing = REQUIRED_FIELDS - rec.keys()
        if missing:
            raise ValueError(f"Record {rec.get('id', '?')} is missing fields: {sorted(missing)}")
        if rec["id"] in seen:
            raise ValueError(f"Duplicate record id: {rec['id']}")
        seen.add(rec["id"])
        if rec["kind"] not in VALID_KINDS or rec["treatment"] not in VALID_TREATMENTS:
            raise ValueError(f"Record {rec['id']} has an invalid kind or treatment")
        rate = Decimal(rec["cgst_pct"])
        if rec["treatment"] == "exempt" and rate != ZERO:
            raise ValueError(f"Exempt record {rec['id']} must have cgst_pct of 0")


def load_dataset(path: Path = DATA_FILE) -> tuple[dict, list[dict]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    records = data["records"]
    _validate(records)
    return data["meta"], records


def normalise(text: str) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def hsn_codes(rec: dict) -> list[str]:
    parts = re.split(r"[/,]", rec["hsn_sac"])
    return [digits_only(p) for p in parts if digits_only(p)]


def _word_in(needle: str, haystack: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def central_pct(rec: dict) -> Decimal:
    return Decimal(rec["cgst_pct"]) if rec["treatment"] == "taxable" else ZERO


def total_gst_pct(rec: dict) -> Decimal:
    return central_pct(rec) * 2


def rate_split(rec: dict) -> dict[str, Decimal]:
    c = central_pct(rec)
    return {"cgst": c, "sgst": c, "igst": c * 2}


def fmt_pct(value: Decimal) -> str:
    return f"{format(value.normalize(), 'f')}%"


def status_text(rec: dict) -> str:
    if rec["treatment"] == "taxable":
        return "GST APPLICABLE"
    return "GST NOT APPLICABLE (Exempt, nil rate)"


def search_text(query: str, records: list[dict], kind: str) -> tuple[list[dict], list[dict]]:
    """Return (exact_matches, suggestions). Suggestions are fuzzy and NOT confirmed."""
    q = normalise(query)
    if not q:
        return [], []
    pool = [r for r in records if r["kind"] == kind]
    exact = []
    for rec in pool:
        terms = [normalise(rec["name"])] + [normalise(a) for a in rec["aliases"]]
        if any(_word_in(q, term) for term in terms):
            exact.append(rec)

    exact_ids = {r["id"] for r in exact}
    vocab: dict[str, list[dict]] = {}
    for rec in pool:
        if rec["id"] in exact_ids:
            continue
        for term in [normalise(rec["name"])] + [normalise(a) for a in rec["aliases"]]:
            vocab.setdefault(term, []).append(rec)

    suggestions: list[dict] = []
    seen: set[str] = set()
    for match in difflib.get_close_matches(q, list(vocab), n=8, cutoff=FUZZY_CUTOFF):
        for rec in vocab[match]:
            if rec["id"] not in seen:
                seen.add(rec["id"])
                suggestions.append(rec)
    return exact, suggestions


def search_code(code: str, records: list[dict], kind: str) -> list[dict]:
    digits = digits_only(code)
    if len(digits) not in (4, 6, 8):
        raise ValueError("Enter a 4, 6 or 8-digit HSN/SAC code.")
    return [r for r in records
            if r["kind"] == kind and any(c.startswith(digits) for c in hsn_codes(r))]


def _to_decimal(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number.") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be a finite number.")
    return number


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate(amount, rate_pct, supply: str, mode: str) -> dict[str, str]:
    base = _to_decimal(amount, "Amount")
    rate = _to_decimal(rate_pct, "GST rate")
    if base <= 0:
        raise ValueError("Amount must be greater than zero.")
    if rate < 0 or rate > HUNDRED:
        raise ValueError("GST rate must be between 0% and 100%.")
    if supply not in ("intra", "inter"):
        raise ValueError("Supply type must be 'intra' or 'inter'.")

    if mode == "add":
        taxable = _q(base)
        tax = _q(taxable * rate / HUNDRED)
        final = taxable + tax
    elif mode == "extract":
        taxable = _q(base * HUNDRED / (HUNDRED + rate))
        final = _q(base)
        tax = final - taxable
    else:
        raise ValueError("Mode must be 'add' or 'extract'.")

    if supply == "intra":
        cgst = _q(tax / 2)
        sgst = tax - cgst
        igst = ZERO
    else:
        cgst = ZERO
        sgst = ZERO
        igst = tax

    return {
        "taxable_value": f"{taxable:.2f}",
        "cgst": f"{cgst:.2f}",
        "sgst_utgst": f"{sgst:.2f}",
        "igst": f"{igst:.2f}",
        "total_tax": f"{tax:.2f}",
        "final_amount": f"{final:.2f}",
        "rounding_note": (
            "Amounts are rounded to 2 decimal places (half-up). In intra-State mode, CGST is half "
            "the tax and SGST takes any paise remainder."
        ),
    }


def result_row(rec: dict, supply: str, meta: dict, downloaded_on: str) -> dict[str, str]:
    split = rate_split(rec)
    intra = supply == "intra"
    return {
        "item": rec["name"],
        "type": rec["kind"],
        "hsn_sac": rec["hsn_sac"],
        "status": status_text(rec),
        "total_gst": fmt_pct(total_gst_pct(rec)),
        "supply": "Intra-State" if intra else "Inter-State",
        "cgst": fmt_pct(split["cgst"]) if intra else "0%",
        "sgst_utgst": fmt_pct(split["sgst"]) if intra else "0%",
        "igst": "0%" if intra else fmt_pct(split["igst"]),
        "condition": rec["condition"],
        "notification": rec["notification"],
        "entry": rec["serial"],
        "effective_from": rec["effective_from"],
        "source_url": rec["source_url"],
        "dataset_version": meta["dataset_version"],
        "downloaded_on": downloaded_on,
        "disclaimer": DISCLAIMER,
    }


def to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")
