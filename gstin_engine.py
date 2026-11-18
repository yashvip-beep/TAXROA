"""GSTIN format and check-character validation. This does NOT confirm registration."""
from __future__ import annotations

import re

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^(\d{2})([A-Z]{5}\d{4}[A-Z])([1-9A-Z])Z([0-9A-Z])$")

STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
    "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya",
    "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}


def normalise_gstin(raw: str) -> str:
    return re.sub(r"\s+", "", (raw or "")).upper()


def checksum_char(first14: str) -> str:
    total = 0
    for i, ch in enumerate(first14):
        product = CHARSET.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return CHARSET[(36 - total % 36) % 36]


def validate_gstin(raw: str) -> dict:
    g = normalise_gstin(raw)
    base = {"gstin": g, "state": "", "valid": False}
    if len(g) != 15:
        return {**base, "message": f"A GSTIN has 15 characters. You entered {len(g)}."}
    m = GSTIN_RE.match(g)
    if not m:
        return {**base, "message": "The format is wrong. Check the letters and digits."}
    state_code = m.group(1)
    if state_code not in STATE_CODES:
        return {**base, "message": f"State code {state_code} is not recognised."}
    if checksum_char(g[:14]) != g[14]:
        return {**base, "message": "The check character does not match, so this GSTIN likely has a typo."}
    return {
        "gstin": g,
        "state": STATE_CODES[state_code],
        "valid": True,
        "message": "Format and check character are valid. This does NOT confirm the number is registered.",
    }


def format_details_text(gstin: str, state: str, d: dict | None) -> str:
    lines = [f"GSTIN: {gstin}", f"State: {state}"]
    if d:
        lines += [
            f"Legal name: {d['legal_name']}",
            f"Trade name: {d['trade_name'] or '-'}",
            f"Address: {d['address'] or '-'}",
            f"Registration date: {d['reg_date'] or '-'}",
            f"Business type: {d['business_type'] or '-'}",
            f"Taxpayer category: {d['category'] or '-'}",
            f"Status (as entered): {d['status']}",
        ]
    lines.append("Note: details entered by a user, not verified by GST TAXORA.")
    return "\n".join(lines)
