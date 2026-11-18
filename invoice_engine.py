"""Invoice tax calculation. Pure Python, so it can be tested."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

HUNDRED = Decimal("100")
CENT = Decimal("0.01")
ZERO = Decimal("0")

# Format check only: state code, PAN-like block, entity code, Z, check character.
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def valid_gstin(gstin: str) -> bool:
    return bool(GSTIN_RE.match((gstin or "").strip().upper()))


def _d(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a number.") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be a finite number.")
    return number


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _s(value: Decimal) -> str:
    return f"{value:.2f}"


def compute_invoice(lines: list[dict], supply: str) -> dict:
    """lines: description, hsn, qty, unit_price, gst_pct (total GST %).
    supply: 'intra' (CGST + SGST/UTGST) or 'inter' (IGST)."""
    if supply not in ("intra", "inter"):
        raise ValueError("Supply type must be intra-State or inter-State.")
    if not lines:
        raise ValueError("Add at least one item with a description.")

    out = []
    tot_taxable = tot_cgst = tot_sgst = tot_igst = tot_tax = tot_total = ZERO

    for i, ln in enumerate(lines, 1):
        desc = str(ln.get("description", "")).strip()
        if not desc:
            raise ValueError(f"Line {i}: description is required.")
        qty = _d(ln.get("qty"), f"Line {i}: quantity")
        price = _d(ln.get("unit_price"), f"Line {i}: unit price")
        rate = _d(ln.get("gst_pct"), f"Line {i}: GST %")
        if qty <= 0:
            raise ValueError(f"Line {i}: quantity must be greater than zero.")
        if price < 0:
            raise ValueError(f"Line {i}: unit price cannot be negative.")
        if rate < 0 or rate > HUNDRED:
            raise ValueError(f"Line {i}: GST % must be between 0 and 100.")

        taxable = _q(qty * price)
        tax = _q(taxable * rate / HUNDRED)
        if supply == "intra":
            cgst = _q(tax / 2)
            sgst = tax - cgst
            igst = ZERO
        else:
            cgst = ZERO
            sgst = ZERO
            igst = tax
        total = taxable + tax

        out.append({
            "description": desc,
            "hsn": str(ln.get("hsn", "")).strip(),
            "qty": format(qty.normalize(), "f"),
            "unit_price": _s(price),
            "taxable": _s(taxable),
            "gst_pct": format(rate.normalize(), "f"),
            "cgst": _s(cgst),
            "sgst": _s(sgst),
            "igst": _s(igst),
            "tax": _s(tax),
            "total": _s(total),
        })
        tot_taxable += taxable
        tot_cgst += cgst
        tot_sgst += sgst
        tot_igst += igst
        tot_tax += tax
        tot_total += total

    return {
        "lines": out,
        "taxable": _s(tot_taxable),
        "cgst": _s(tot_cgst),
        "sgst": _s(tot_sgst),
        "igst": _s(tot_igst),
        "total_tax": _s(tot_tax),
        "grand_total": _s(tot_total),
    }
