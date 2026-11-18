"""Barcode helpers. Barcode-to-item links live in data/barcodes.json and are added only
after you confirm the barcode belongs to that item. The GST rate always comes from the
verified item in data/gst_rates.json."""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BARCODE_FILE = BASE_DIR / "data" / "barcodes.json"
PRODUCT_LENGTHS = (8, 12, 13)  # EAN-8, UPC-A, EAN-13


def is_product_code(code: str) -> bool:
    return (code or "").isdigit() and len(code) in PRODUCT_LENGTHS


def ean_valid(code: str) -> bool:
    if not is_product_code(code):
        return False
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    total = 0
    for i, value in enumerate(body):
        position_from_right = len(body) - 1 - i
        weight = 3 if position_from_right % 2 == 0 else 1
        total += value * weight
    return (10 - total % 10) % 10 == check


def load_barcodes(path: Path = BARCODE_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    records = data.get("records", [])
    for rec in records:
        code = rec.get("barcode", "")
        if not is_product_code(code):
            raise ValueError(f"Barcode '{code}' must be 8, 12 or 13 digits.")
        if not ean_valid(code):
            raise ValueError(f"Barcode '{code}' fails the check digit.")
        if not rec.get("record_id"):
            raise ValueError(f"Barcode '{code}' has no record_id.")
    return records


def lookup_barcode(code: str, barcodes: list[dict], records: list[dict]) -> dict | None:
    by_id = {r["id"]: r for r in records}
    for entry in barcodes:
        if entry["barcode"] == code:
            return by_id.get(entry["record_id"])
    return None


def decode_image(pil_image) -> list[str]:
    """Return the text of every barcode or QR code found in a PIL image."""
    try:
        from pyzbar.pyzbar import decode
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Photo scanning needs pyzbar and libzbar0. Run the install cell again, "
            "or use Type code instead."
        ) from exc
    results = decode(pil_image.convert("RGB"))
    return [r.data.decode("utf-8", errors="replace") for r in results]
