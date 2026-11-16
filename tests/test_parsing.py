"""Regression tests (run with: python -m pytest tests  or  python tests/test_parsing.py).
Uses synthetic text shaped like an MSEDCL bill text layer - no personal data."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import analytics  # noqa: E402
import ocr_utils  # noqa: E402
import validation  # noqa: E402

# MSEDCL text layers have garbled regional labels but clean numbers.
MSEDCL_LAYER = """\
bill-date-label : 12-10-2026
amount-label : 680.00
due-label : 02-11-2026
late-label : 690.00
8314 1.00 79 0 79 units
21-10-2026 Rs. 670.00
02-11-2026 Rs. 690.00
02-11-2026 Rs. 680.00
Bill Period: 1.03/
next-reading-label:10-11-2026
https://wss.mahadiscom.in/wss
"""


def test_msedcl_layer():
    p = ocr_utils.parse_bill(MSEDCL_LAYER)
    assert (p["month"], p["year"]) == (10, 2026)      # NOT 11 (next reading date)
    assert p["units"] == 79.0
    assert p["amount"] == 680.0                       # due-date amount, not 670/690
    assert p["discom"].startswith("MSEDCL") and p["state"] == "Maharashtra"


def test_ocr_mistake_is_flagged():
    issues = validation.validate_bill(2026, 10, 100, 110000, [])
    assert any(i["field"] == "amount" for i in issues)


def test_prediction_uses_only_verified_bills():
    b = [dict(year=2026, month=9, amount=800.0, units=0.0, state="", discom="", source="x"),
         dict(year=2026, month=10, amount=680.0, units=0.0, state="", discom="", source="x")]
    p = analytics.predict_next(analytics.bills_df(b))
    assert p["avg2"] == 740.0 and p["status"] == "ok"
    one = analytics.predict_next(analytics.bills_df(b[:1]))
    assert one["status"] == "insufficient"


def test_zero_previous_is_na():
    assert analytics.pct_change(10, 0) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
