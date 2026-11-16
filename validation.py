"""Validation rules that stop OCR mistakes from silently entering the data."""
import datetime as dt
import statistics

WARN = "warn"
ERROR = "error"

MAX_REASONABLE_BILL = 50_000      # ₹ for a household monthly bill
MIN_RATE, MAX_RATE = 2.0, 25.0    # ₹ per kWh incl. fixed charges, taxes (wide on purpose)
MAX_REASONABLE_UNITS = 5_000


def _issue(level, field, msg):
    return {"level": level, "field": field, "msg": msg}


def validate_bill(year, month, units, amount, existing=None):
    """Return a list of issues. 'error' blocks saving; 'warn' needs user confirmation.

    existing: list of saved bill dicts (keys: year, month, amount).
    """
    existing = existing or []
    out = []

    if month is None or not (1 <= int(month) <= 12):
        out.append(_issue(ERROR, "month", "Billing month is not valid."))
    if year is None or not (2000 <= int(year) <= 2100):
        out.append(_issue(ERROR, "month", "Billing year is not valid."))
    if units is not None and units < 0:
        out.append(_issue(ERROR, "units", "Units cannot be negative."))
    if amount is not None and amount < 0:
        out.append(_issue(ERROR, "amount", "Bill amount cannot be negative."))
    if any(i["level"] == ERROR for i in out):
        return out

    if not units:
        out.append(_issue(WARN, "units", "Units consumed is missing or 0. Please enter it manually."))
    if not amount:
        out.append(_issue(WARN, "amount", "We could not confidently detect the bill amount. Please enter it manually."))

    today = dt.date.today()
    if (int(year), int(month)) > (today.year + (today.month == 12), today.month % 12 + 1):
        out.append(_issue(WARN, "month", "This billing month is in the future. Please check it."))

    if amount and amount > MAX_REASONABLE_BILL:
        out.append(_issue(WARN, "amount", f"₹{amount:,.0f} is extremely high for a monthly household bill. OCR may have added extra digits."))
    if units and units > MAX_REASONABLE_UNITS:
        out.append(_issue(WARN, "units", f"{units:,.0f} kWh is extremely high for one month."))
    if units and 0 < units < 5:
        out.append(_issue(WARN, "units", f"{units:g} kWh is extremely low."))

    if units and amount and units > 0:
        rate = amount / units
        if rate > MAX_RATE or rate < MIN_RATE:
            out.append(_issue(WARN, "amount", f"Amount looks inconsistent with units (₹{rate:.1f} per kWh; usually about ₹{MIN_RATE:.0f}–{MAX_RATE:.0f})."))

    prior = [b["amount"] for b in existing if b.get("amount") and not (b["year"] == year and b["month"] == month)]
    if amount and len(prior) >= 2:
        med = statistics.median(prior)
        if med > 0 and amount > 5 * med:
            out.append(_issue(WARN, "amount", f"This amount is more than 5× your usual bill (about ₹{med:,.0f})."))

    if any(b["year"] == year and b["month"] == month for b in existing):
        out.append(_issue(WARN, "duplicate", "A bill for this month is already saved. Saving will replace it."))
    return out


def suggest_amounts(units, candidates):
    """Other numbers found on the bill that fit the unit count better."""
    if not units or units <= 0:
        return []
    return [c for c in candidates if MIN_RATE <= c / units <= MAX_RATE]
