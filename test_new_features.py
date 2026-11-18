from barcode_engine import ean_valid, is_product_code, lookup_barcode
from gst_engine import load_dataset
from invoice_engine import compute_invoice, valid_gstin

META, RECORDS = load_dataset()


def test_invoice_intra_state_splits_half_and_half():
    res = compute_invoice(
        [{"description": "Test item", "hsn": "1006", "qty": 1, "unit_price": 1000, "gst_pct": 18}],
        "intra")
    assert res["taxable"] == "1000.00"
    assert res["cgst"] == "90.00"
    assert res["sgst"] == "90.00"
    assert res["igst"] == "0.00"
    assert res["grand_total"] == "1180.00"


def test_invoice_inter_state_uses_igst():
    res = compute_invoice(
        [{"description": "Test item", "hsn": "1006", "qty": 2, "unit_price": 500, "gst_pct": 5}],
        "inter")
    assert res["cgst"] == "0.00"
    assert res["igst"] == "50.00"
    assert res["grand_total"] == "1050.00"


def test_invoice_rejects_empty_and_bad_rate():
    try:
        compute_invoice([], "intra")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected error for no items")
    try:
        compute_invoice([{"description": "x", "qty": 1, "unit_price": 1, "gst_pct": 150}], "intra")
    except ValueError:
        return
    raise AssertionError("Expected error for GST above 100")


def test_gstin_format():
    assert valid_gstin("00AAAAA0000A1Z5")
    assert not valid_gstin("00AAAAA0000A1Z")
    assert not valid_gstin("")


def test_ean13_check_digit():
    assert ean_valid("4006381333931")
    assert not ean_valid("4006381333932")


def test_product_code_length_and_digits():
    assert is_product_code("4006381333931")
    assert not is_product_code("ABC123")
    assert not is_product_code("12345")


def test_unlinked_barcode_returns_none():
    assert lookup_barcode("4006381333931", [], RECORDS) is None
