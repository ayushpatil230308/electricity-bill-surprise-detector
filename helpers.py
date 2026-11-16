"""Small shared helpers: formatting, constants and safe HTML tables."""
import html

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_SHORT = [m[:3] for m in MONTH_NAMES]

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]


def inr(value) -> str:
    """Format a number as Indian-grouped rupees, e.g. ₹1,23,456."""
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return "N/A"
    s = str(abs(v))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if v < 0 else "") + "₹" + s


def kwh(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{v:,.0f} kWh" if abs(v - round(v)) < 0.05 else f"{v:,.1f} kWh"


def month_label(year: int, month: int, short: bool = False) -> str:
    names = MONTH_SHORT if short else MONTH_NAMES
    return f"{names[month - 1]} {year}"


def fmt_pct(value):
    """Return (text, css_class) for a percentage change; None -> N/A."""
    if value is None or value != value:  # None or NaN (pandas turns None into NaN)
        return ("N/A", "")
    arrow = "▲" if value > 0.05 else ("▼" if value < -0.05 else "■")
    cls = "up" if value > 0.05 else ("down" if value < -0.05 else "")
    return (f"{arrow} {value:+.1f}%", cls)


def html_table(headers, rows) -> str:
    """Readable, mobile-scrollable table. Cells are str or (str, css_class)."""
    head = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = []
    for row in rows:
        cells = []
        for c in row:
            text, cls = (c if isinstance(c, tuple) else (c, ""))
            cells.append(f'<td class="{cls}">{html.escape(str(text))}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="bw-table-wrap"><table class="bw-table"><thead><tr>'
        + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )
