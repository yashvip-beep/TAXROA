from decimal import Decimal

from gst_engine import (
    NOT_FOUND_MSG,
    calculate,
    load_dataset,
    normalise,
    search_code,
    search_text,
    total_gst_pct,
)

META, RECORDS = load_dataset()


def by_id(record_id):
    return next(r for r in RECORDS if r["id"] == record_id)


def test_dataset_loads_with_unique_ids():
    ids = [r["id"] for r in RECORDS]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 30


def test_prepackaged_rice_is_5_percent_total():
    assert total_gst_pct(by_id("G001")) == Decimal("5")


def test_loose_rice_is_exempt_zero():
    rec = by_id("G002")
    assert rec["treatment"] == "exempt"
    assert total_gst_pct(rec) == Decimal("0")


def test_cement_is_18_percent_total():
    assert total_gst_pct(by_id("G016")) == Decimal("18")


def test_gold_jewellery_is_3_percent_total():
    assert total_gst_pct(by_id("G017")) == Decimal("3")


def test_exact_name_search_returns_rice_records():
    exact, _ = search_text("rice", RECORDS, "goods")
    assert {"G001", "G002"} <= {r["id"] for r in exact}


def test_misspelling_gives_suggestion_not_exact_match():
    exact, suggestions = search_text("ricee", RECORDS, "goods")
    assert exact == []
    assert "G001" in {r["id"] for r in suggestions}


def test_unknown_item_returns_nothing():
    exact, suggestions = search_text("zqxvwk", RECORDS, "goods")
    assert exact == [] and suggestions == []
    assert NOT_FOUND_MSG.startswith("Item not found")


def test_hsn_prefix_search():
    assert {"G001", "G002"} <= {r["id"] for r in search_code("1006", RECORDS, "goods")}


def test_hsn_code_must_be_4_6_or_8_digits():
    try:
        search_code("12", RECORDS, "goods")
    except ValueError:
        return
    raise AssertionError("Expected ValueError for a 2-digit code")


def test_service_name_search_uses_service_kind_only():
    exact, _ = search_text("restaurant", RECORDS, "service")
    assert exact and all(r["kind"] == "service" for r in exact)


def test_normalise_strips_punctuation_and_case():
    assert normalise("  Fresh-Milk!!  ") == "fresh milk"


def test_add_mode_intra_state():
    res = calculate("1000", "18", "intra", "add")
    assert res["total_tax"] == "180.00"
    assert res["cgst"] == "90.00"
    assert res["sgst_utgst"] == "90.00"
    assert res["igst"] == "0.00"
    assert res["final_amount"] == "1180.00"


def test_extract_mode_inter_state():
    res = calculate("1180", "18", "inter", "extract")
    assert res["taxable_value"] == "1000.00"
    assert res["igst"] == "180.00"
    assert res["cgst"] == "0.00"


def test_split_always_adds_up_with_odd_paise():
    res = calculate("100.01", "5", "intra", "add")
    assert abs(float(res["cgst"]) + float(res["sgst_utgst"]) - float(res["total_tax"])) < 0.001


def test_invalid_amount_rejected():
    for bad in ["0", "-5", "abc"]:
        try:
            calculate(bad, "18", "intra", "add")
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for amount {bad!r}")
