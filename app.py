import io
import re
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance

try:
    import fitz
except ImportError:
    fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


st.set_page_config(
    page_title="BillWise India | Smart Energy Companion",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- DESIGN --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

.stApp {
    background: #f5f9fb;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#102d3a,#1a5260);
}
[data-testid="stSidebar"] * {
    color: white !important;
}
.block-container {
    max-width: 1280px;
    padding-top: 2rem;
}
.bw-hero {
    background: linear-gradient(115deg,#103746,#087f8c,#0e9f88);
    color: white;
    border-radius: 25px;
    padding: 30px;
    margin-bottom: 25px;
}
.bw-title {
    color: white !important;
    font-size: 42px;
    font-weight: 800;
}
.bw-subtitle {
    color: #e1f6f5;
    font-size: 17px;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e2ecef;
    border-radius: 16px;
    padding: 15px;
}
div[data-testid="stMetricValue"] {
    color: #087f8c;
}
div[data-testid="stExpander"] {
    border-radius: 15px;
    border: 1px solid #dce8ec;
}
.stButton > button {
    border-radius: 10px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bw-hero">
    <div>YOUR SMART ENERGY COMPANION</div>
    <div class="bw-title">BillWise India ⚡</div>
    <p class="bw-subtitle">
        Understand electricity bills, detect surprising changes,
        explore appliance usage and discover ways to save.
    </p>
    ✦ 5-month comparison &nbsp; | &nbsp;
    Multilingual OCR &nbsp; | &nbsp;
    Bill surprise alerts
</div>
""", unsafe_allow_html=True)

st.subheader("Your electricity, made easier to understand")
st.caption("Upload up to five monthly electricity bills and verify the extracted details.")

st.warning(
    "OCR results must be checked against your original electricity bill. "
    "Different DISCOMs use different bill formats."
)

# -------------------- CONSTANTS --------------------

LANGUAGES = {
    "English": "eng",
    "Marathi": "mar",
    "Hindi": "hin",
    "Gujarati": "guj",
    "Bengali": "ben",
    "Tamil": "tam",
    "Telugu": "tel",
    "Kannada": "kan",
    "Malayalam": "mal",
    "Punjabi": "pan",
    "Urdu": "urd",
    "Odia": "ori",
    "Assamese": "asm",
    "Nepali": "nep"
}

DISCOMS = [
    "Not sure / Other",
    "MSEDCL / Mahavitaran (Maharashtra)",
    "Adani Electricity Mumbai",
    "Tata Power",
    "BEST Mumbai",
    "Torrent Power",
    "GUVNL Gujarat",
    "BESCOM Karnataka",
    "TANGEDCO Tamil Nadu",
    "KSEB Kerala",
    "TGSPDCL Telangana",
    "APSPDCL Andhra Pradesh",
    "BSES / TPDDL Delhi",
    "UPPCL Uttar Pradesh",
    "WBSEDCL West Bengal",
    "Other Indian DISCOM"
]

STATES = [
    "Not selected", "Andhra Pradesh", "Arunachal Pradesh",
    "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry",
    "Chandigarh", "Andaman and Nicobar Islands"
]

AMOUNT_LABELS = [
    r"total\s*amount\s*due",
    r"net\s*amount\s*payable",
    r"amount\s*payable",
    r"amount\s*due",
    r"bill\s*amount",
    r"total\s*bill",
    r"grand\s*total",
    r"total\s*payable",
    r"current\s*bill\s*amount",
    r"देयक\s*रक्कम",
    r"निव्वळ\s*रक्कम"
]

UNITS_LABELS = [
    r"units?\s*consumed",
    r"consumed\s*units",
    r"energy\s*consumed",
    r"kwh\s*consumed",
    r"billable\s*units",
    r"total\s*consumption",
    r"consumption\s*\(?\s*kwh\s*\)?",
    r"units?\s*\(\s*kwh\s*\)",
    r"energy\s*units"
]

NUMBER_RE = re.compile(
    r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
)

CURRENCY_RE = re.compile(
    r"(?:₹|Rs\.?|INR|रु\.?|रुपये)\s*[.):：]?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.I
)

# -------------------- SESSION --------------------

if "bill_records" not in st.session_state:
    st.session_state.bill_records = []

if "chat" not in st.session_state:
    st.session_state.chat = []


# -------------------- OCR FUNCTIONS --------------------

def preprocess(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(1.35)


@st.cache_data(show_spinner=False, max_entries=8)
def installed_ocr_languages():
    if pytesseract is None:
        return ()
    try:
        return tuple(pytesseract.get_languages(config=""))
    except Exception:
        return ()


def readable_embedded_text(text):
    if not text or len(text.strip()) < 35:
        return False

    if any(x in text for x in ["�", "□", "Ã", "Â"]):
        return False

    visible = sum(
        ch.isalnum() or ch in "₹.,:/-%() \n\t"
        for ch in text
    )

    return visible / max(len(text), 1) >= 0.70


def ocr_image(image, language_codes, is_msedcl=False):

    if pytesseract is None:
        return "", "pytesseract is missing."

    installed = set(installed_ocr_languages())

    if not installed:
        return "", "Tesseract or language data is unavailable."

    if is_msedcl and {"mar", "eng"}.issubset(installed):
        primary = "mar+eng"

    elif language_codes in installed and "eng" in installed:
        primary = (
            language_codes if language_codes == "eng"
            else f"{language_codes}+eng"
        )

    elif language_codes in installed:
        primary = language_codes

    elif "eng" in installed:
        primary = "eng"

    else:
        return "", f"Language {language_codes} is not installed."

    attempts = [
        (primary, 6, 20),
        (primary, 11, 12)
    ]

    best = ""
    errors = []

    for lang, psm, timeout_seconds in attempts:
        try:
            result = pytesseract.image_to_string(
                image,
                lang=lang,
                config=f"--oem 1 --psm {psm}",
                timeout=timeout_seconds
            ).strip()

            if len(result) > len(best):
                best = result

            if sum(ch.isalnum() for ch in result) >= 25:
                return result, f"OCR successful: {lang}, PSM {psm}"

        except Exception as exc:
            errors.append(type(exc).__name__)

    if best:
        return best, "Partial OCR text found. Verify manually."

    return "", "OCR failed: " + ", ".join(errors)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_page_ocr(png_bytes, language_codes, is_msedcl):

    image = Image.open(
        io.BytesIO(png_bytes)
    ).convert("RGB")

    return ocr_image(
        preprocess(image),
        language_codes,
        is_msedcl
    )


def read_pdf_bytes(file_bytes, language_codes, force_ocr, dpi, filename=""):

    if fitz is None:
        return "", "PyMuPDF is missing."

    pages = []
    notes = []

    is_msedcl = "msedcl" in filename.lower()

    scale_map = {
        1: 1.15,
        2: 1.35,
        3: 1.60
    }

    scale = scale_map.get(int(dpi), 1.35)

    try:
        with fitz.open(
            stream=file_bytes,
            filetype="pdf"
        ) as pdf:

            total_pages = min(len(pdf), 3)

            if total_pages == 0:
                return "", "PDF has no pages."

            progress = st.progress(0)
            status = st.status("Starting PDF reading...", expanded=True)

            for i in range(total_pages):

                page = pdf[i]

                status.update(
                    label=f"Processing page {i + 1} of {total_pages}..."
                )

                embedded = (
                    page.get_text("text") or ""
                ).strip()

                if (
                    not force_ocr
                    and readable_embedded_text(embedded)
                ):

                    pages.append(embedded)
                    notes.append(f"Page {i+1}: Embedded text used.")

                else:

                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(scale, scale),
                        alpha=False
                    )

                    scanned, note = cached_page_ocr(
                        pix.tobytes("png"),
                        language_codes,
                        is_msedcl
                    )

                    pages.append(scanned or embedded)
                    notes.append(f"Page {i+1}: {note}")

                progress.progress((i + 1) / total_pages)

            status.update(
                label="PDF reading completed.",
                state="complete",
                expanded=False
            )

            if len(pdf) > total_pages:
                notes.append("Only first 3 pages processed for speed.")

        return "\n\n".join(pages), " | ".join(notes)

    except Exception as exc:
        return "", f"PDF error: {type(exc).__name__}: {exc}"


@st.cache_data(show_spinner=False, max_entries=32)
def read_pdf_cached(file_bytes, language_codes, force_ocr, dpi, filename=""):
    return read_pdf_bytes(
        file_bytes, language_codes, force_ocr, dpi, filename
    )


@st.cache_data(show_spinner=False, max_entries=64)
def read_image_cached(file_bytes, language_codes, filename=""):

    try:
        image = Image.open(
            io.BytesIO(file_bytes)
        ).convert("RGB")

        return ocr_image(
            preprocess(image),
            language_codes,
            "msedcl" in filename.lower()
        )

    except Exception as exc:
        return "", f"Image error: {type(exc).__name__}: {exc}"


def read_file(upload, language_codes, force_ocr, dpi):

    data = upload.getvalue()

    if Path(upload.name).suffix.lower() == ".pdf":
        return read_pdf_cached(
            data, language_codes, force_ocr, dpi, upload.name
        )

    return read_image_cached(
        data, language_codes, upload.name
    )


# -------------------- EXTRACTION --------------------

def parse_num(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def find_labeled_value(text, patterns, kind="number"):

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]

    for i, line in enumerate(lines):

        for pattern in patterns:

            match = re.search(pattern, line, re.I)

            if not match:
                continue

            candidates = (
                [line[match.end():]]
                + lines[i+1:i+3]
            )

            for candidate in candidates:

                values = (
                    CURRENCY_RE.findall(candidate)
                    if kind == "amount"
                    else NUMBER_RE.findall(candidate)
                )

                parsed = [
                    parse_num(v) for v in values
                ]

                parsed = [
                    v for v in parsed
                    if v is not None and v > 0
                ]

                if parsed:
                    return parsed[0], candidate[:180]

    return None, ""


def extract_amount_candidates(text):

    found = []

    for line in (text or "").splitlines():

        for value in CURRENCY_RE.findall(line):

            number = parse_num(value)

            if number is not None and 1 <= number <= 10000000:

                found.append({
                    "Candidate amount (₹)": number,
                    "Source line": line.strip()[:180]
                })

    return (
        pd.DataFrame(found).drop_duplicates()
        if found else pd.DataFrame()
    )


def guess_month(text, filename):

    months = (
        "January|February|March|April|May|June|July|August|"
        "September|October|November|December"
    )

    name = Path(filename).stem

    code = re.search(
        r"(?:^|[_-])(\d{2})(0[1-9]|1[0-2])(?:[_-]|$)",
        name
    )

    if code and "msedcl" in name.lower():

        return datetime(
            2000 + int(code.group(1)),
            int(code.group(2)),
            1
        ).strftime("%B %Y")

    match = re.search(
        rf"(?:billing\s*(?:month|period)|bill\s*(?:month|period|for))[^\n]{{0,50}}?\b({months})\s*,?\s*(20\d{{2}})\b",
        text or "",
        re.I
    )

    if match:
        return f"{match.group(1).title()} {match.group(2)}"

    return ""


# -------------------- BILL REVIEW --------------------

def bill_form(upload, idx, text, note):

    st.caption(note)

    with st.expander("View extracted text"):
        st.text_area(
            "OCR output",
            text[:15000],
            height=180,
            key=f"text_{idx}"
        )

    amount, amount_evidence = find_labeled_value(
        text, AMOUNT_LABELS, "amount"
    )

    units, units_evidence = find_labeled_value(
        text, UNITS_LABELS, "number"
    )

    month_guess = guess_month(text, upload.name)
    candidates = extract_amount_candidates(text)

    st.markdown("**Review detected details**")

    c1, c2 = st.columns(2)

    with c1:

        month = st.text_input(
            "Billing month",
            value=month_guess,
            key=f"month_{idx}",
            placeholder="October 2026"
        )

        amount_value = st.number_input(
            "Final payable amount (₹)",
            min_value=0.0,
            value=float(amount or 0),
            step=10.0,
            key=f"amount_{idx}"
        )

        if amount is None:
            st.warning("Amount not confidently detected. Verify original bill.")

        st.caption("Amount evidence: " + (amount_evidence or "Not found"))

    with c2:

        units_value = st.number_input(
            "Units consumed (kWh)",
            min_value=0.0,
            value=float(units or 0),
            step=1.0,
            key=f"units_{idx}"
        )

        if units is None:
            st.warning("Units not confidently detected. Verify original bill.")

        st.caption("Units evidence: " + (units_evidence or "Not found"))

    if amount is None and not candidates.empty:

        st.warning(
            "Candidate amounts are not confirmed payable amounts. "
            "Check the original bill."
        )

        st.dataframe(
            candidates,
            use_container_width=True,
            hide_index=True
        )

    c3, c4 = st.columns(2)

    with c3:

        discom = st.selectbox(
            "Electricity company",
            DISCOMS,
            key=f"discom_{idx}",
            index=1 if "msedcl" in upload.name.lower() else 0
        )

    with c4:

        state = st.selectbox(
            "State / UT",
            STATES,
            key=f"state_{idx}",
            index=14 if "msedcl" in upload.name.lower() else 0
        )

    if st.button(
        "Save verified bill",
        key=f"save_{idx}",
        type="primary"
    ):

        if not month.strip() or amount_value <= 0 or units_value <= 0:

            st.error(
                "Enter valid month, amount and units from original bill."
            )

        elif any(
            r["Billing month"].lower() == month.strip().lower()
            for r in st.session_state.bill_records
        ):

            st.error("This month is already saved.")

        else:

            st.session_state.bill_records.append({
                "Billing month": month.strip(),
                "Bill amount (₹)": float(amount_value),
                "Units (kWh)": float(units_value),
                "State/UT": state,
                "DISCOM": discom,
                "Source file": upload.name
            })

            st.success("Verified bill saved.")


# -------------------- SIDEBAR --------------------

with st.sidebar:

    st.header("Bill settings")

    chosen_language = st.selectbox(
        "Main bill language",
        list(LANGUAGES.keys())
    )

    force_ocr = st.checkbox(
        "Force OCR for scanned PDFs",
        value=False
    )

    dpi = st.slider(
        "PDF OCR quality",
        1, 3, 2,
        help="1 = Fast, 2 = Balanced, 3 = Higher quality"
    )

    installed = set(installed_ocr_languages())

    if pytesseract is None or not installed:

        st.error("OCR engine is unavailable. Check deployment packages.")

    else:

        ready = sorted(
            installed.intersection(set(LANGUAGES.values()))
        )

        st.success(
            "OCR ready: " + (", ".join(ready) if ready else "No language packs")
        )

    st.caption("MSEDCL files try Marathi + English if both packs are installed.")

language_code = LANGUAGES[chosen_language]


# -------------------- UPLOAD --------------------

st.header("01 · Upload your bills")

st.write(
    "Upload up to five monthly bills. Scan one bill at a time."
)

uploads = st.file_uploader(
    "Upload electricity bills",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploads:

    if len(uploads) > 5:
        st.warning("Only first five files will be processed.")

    for idx, upload in enumerate(uploads[:5]):

        digest = hashlib.sha256(
            upload.getvalue()
        ).hexdigest()[:16]

        scan_key = f"bill_scan_{digest}"

        with st.expander(
            f"Bill {idx+1}: {upload.name}",
            expanded=(idx == 0)
        ):

            if scan_key not in st.session_state:

                if st.button(
                    "Scan this bill",
                    key=f"scan_{digest}",
                    type="primary"
                ):

                    with st.spinner("Reading bill..."):

                        st.session_state[scan_key] = read_file(
                            upload,
                            language_code,
                            force_ocr,
                            dpi
                        )

                    st.rerun()

                st.info("Click Scan this bill to begin.")

            else:

                text, note = st.session_state[scan_key]

                if not text.strip():

                    st.error(
                        "No readable text found. Check OCR language packs "
                        "or enter values manually."
                    )

                    if st.button(
                        "Retry scan",
                        key=f"retry_{digest}"
                    ):

                        st.session_state.pop(scan_key, None)
                        st.rerun()

                bill_form(upload, digest, text, note)


# -------------------- MONTHLY INSIGHTS --------------------

st.divider()
st.header("02 · Monthly insights")

if st.session_state.bill_records:

    df = pd.DataFrame(st.session_state.bill_records)

    df["_date"] = pd.to_datetime(
        df["Billing month"],
        format="%B %Y",
        errors="coerce"
    )

    df = (
        df.sort_values("_date", na_position="last")
        .drop(columns="_date")
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    a, b, c = st.columns(3)

    a.metric("Bills saved", f"{len(df)} / 5")

    b.metric(
        "Average monthly bill",
        f"₹{df['Bill amount (₹)'].mean():,.2f}"
    )

    c.metric(
        "Average monthly usage",
        f"{df['Units (kWh)'].mean():,.1f} kWh"
    )

    st.subheader("Monthly comparison")

    st.line_chart(
        df.set_index("Billing month")[
            ["Bill amount (₹)", "Units (kWh)"]
        ]
    )

    left, right = st.columns(2)

    with left:
        st.bar_chart(
            df.set_index("Billing month")["Bill amount (₹)"]
        )

    with right:
        st.bar_chart(
            df.set_index("Billing month")["Units (kWh)"]
        )

    if len(df) >= 2:

        previous = df.iloc[-2]
        latest = df.iloc[-1]

        if previous["Units (kWh)"] > 0:

            change = (
                latest["Units (kWh)"] -
                previous["Units (kWh)"]
            ) / previous["Units (kWh)"] * 100

            if change >= 20:
                st.error(f"Usage increased by {change:.1f}%.")

            elif change <= -20:
                st.success(f"Usage decreased by {abs(change):.1f}%.")

            else:
                st.info(f"Usage changed by {change:+.1f}%.")

        if previous["Bill amount (₹)"] > 0:

            bill_change = (
                latest["Bill amount (₹)"] -
                previous["Bill amount (₹)"]
            ) / previous["Bill amount (₹)"] * 100

            if bill_change >= 20:

                st.warning(
                    f"Bill increased by {bill_change:.1f}%. "
                    "Check tariff, taxes, arrears and billing days."
                )

    st.download_button(
        "Download analysis CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "billwise_analysis.csv",
        "text/csv"
    )

    if st.button("Clear all saved bills"):
        st.session_state.bill_records = []
        st.rerun()

else:

    st.info("Save at least two verified bills to see comparisons.")


# -------------------- APPLIANCE ESTIMATOR --------------------

st.divider()
st.header("03 · Appliance energy estimator")

st.caption(
    "Estimates are based on wattage and hours entered by you. "
    "A bill alone cannot identify the exact appliance."
)

APPLIANCES = {
    "Geyser / Water Heater": 2000,
    "Refrigerator": 150,
    "Washing Machine": 500,
    "Ceiling Fan": 70,
    "LED Bulb": 9,
    "Television": 100,
    "Electric Iron": 1000,
    "Water Pump": 750,
    "Induction Cooktop": 1800,
    "Desktop Computer": 200,
    "Microwave": 1200,
    "Room Heater": 2000,
    "Air Conditioner": 1500
}

with st.form("appliances"):

    selected = st.multiselect(
        "Select appliances",
        list(APPLIANCES),
        default=["Refrigerator", "Ceiling Fan"]
    )

    rows_input = []

    for i, name in enumerate(selected):

        st.markdown(f"**{name}**")

        x, y, z = st.columns(3)

        watts = x.number_input(
            "Rated watts",
            1, 20000,
            APPLIANCES[name],
            key=f"w_{i}"
        )

        hours = y.number_input(
            "Hours daily",
            0.0, 24.0,
            4.0,
            0.5,
            key=f"h_{i}"
        )

        quantity = z.number_input(
            "Quantity",
            1, 100,
            1,
            key=f"q_{i}"
        )

        rows_input.append(
            (name, watts, hours, quantity)
        )

    tariff = st.number_input(
        "Approximate rate (₹/kWh)",
        0.0, 100.0,
        8.0,
        0.5
    )

    submitted = st.form_submit_button(
        "Estimate consumption"
    )

if submitted:

    rows = []

    for name, watts, hours, quantity in rows_input:

        units = watts / 1000 * hours * 30 * quantity

        rows.append({
            "Appliance": name,
            "Estimated kWh/month": round(units, 2),
            "Estimated cost (₹)": round(units * tariff, 2)
        })

    if rows:

        appliance_df = pd.DataFrame(rows)

        appliance_df = appliance_df.sort_values(
            "Estimated kWh/month",
            ascending=False
        )

        st.dataframe(
            appliance_df,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            appliance_df.set_index("Appliance")[
                "Estimated kWh/month"
            ]
        )


# -------------------- SAVING IDEAS --------------------

st.divider()
st.header("04 · Smart saving ideas")

st.markdown("""
- Use LED lights.
- Switch off unused appliances.
- Use a geyser timer.
- Run full washing-machine loads.
- Check refrigerator door seals.
- Check water-pump leaks.
- Compare billing days and meter readings.
- Check tariff, taxes and previous dues if the bill increases.
""")

if st.session_state.bill_records:

    latest_units = float(
        st.session_state.bill_records[-1]["Units (kWh)"]
    )

    goal = st.slider(
        "Monthly usage reduction goal (%)",
        0, 30, 10, 5
    )

    rate = st.number_input(
        "Energy rate for estimate (₹/kWh)",
        0.0, 100.0, 8.0, 0.5
    )

    saved = latest_units * goal / 100

    x, y = st.columns(2)

    x.metric("Potential units saved", f"{saved:.1f} kWh")

    y.metric(
        "Potential energy saving",
        f"₹{saved * rate:.2f}"
    )


# -------------------- BILL SURPRISE FINGERPRINT --------------------

st.divider()
st.header("05 · Bill Surprise Fingerprint")

if len(st.session_state.bill_records) >= 2:

    ordered = pd.DataFrame(
        st.session_state.bill_records
    ).copy()

    ordered["_date"] = pd.to_datetime(
        ordered["Billing month"],
        format="%B %Y",
        errors="coerce"
    )

    ordered = ordered.sort_values("_date")

    previous = ordered.iloc[-2]
    latest = ordered.iloc[-1]

    pu = float(previous["Units (kWh)"])
    cu = float(latest["Units (kWh)"])

    pb = float(previous["Bill amount (₹)"])
    cb = float(latest["Bill amount (₹)"])

    usage_change = (
        (cu - pu) / pu * 100 if pu > 0 else None
    )

    bill_change = (
        (cb - pb) / pb * 100 if pb > 0 else None
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Latest units",
        f"{cu:.1f} kWh",
        None if usage_change is None else f"{usage_change:+.1f}%"
    )

    c2.metric(
        "Latest bill",
        f"₹{cb:,.2f}",
        None if bill_change is None else f"{bill_change:+.1f}%"
    )

    current_rate = cb / cu if cu > 0 else 0
    previous_rate = pb / pu if pu > 0 else 0

    c3.metric(
        "Effective bill per unit",
        f"₹{current_rate:.2f}",
        f"{current_rate-previous_rate:+.2f}"
    )

    if usage_change is not None and bill_change is not None:

        if bill_change >= 15 and usage_change >= 15:

            st.error(
                "Both bill and usage increased. "
                "Check appliance use and billing days."
            )

        elif bill_change >= 15 and usage_change < 5:

            st.warning(
                "Bill increased but usage stayed nearly flat. "
                "Check tariff, fixed charges, taxes and arrears."
            )

        elif bill_change >= 15:

            st.warning(
                "Mixed pattern. Review both usage and bill components."
            )

        elif usage_change >= 20:

            st.info(
                "Usage increased noticeably. Check meter readings and appliances."
            )

        else:

            st.success("No large increase detected by these simple rules.")

else:

    st.info("Save at least two bills to generate this analysis.")


# -------------------- NEXT MONTH ESTIMATE --------------------

st.divider()
st.header("06 · Next-month usage estimate")

if len(st.session_state.bill_records) >= 3:

    import numpy as np

    forecast_df = pd.DataFrame(
        st.session_state.bill_records
    ).copy()

    forecast_df["_date"] = pd.to_datetime(
        forecast_df["Billing month"],
        format="%B %Y",
        errors="coerce"
    )

    forecast_df = forecast_df.sort_values("_date")

    values = forecast_df["Units (kWh)"].astype(float).to_numpy()

    x_values = np.arange(len(values), dtype=float)

    slope, intercept = np.polyfit(
        x_values,
        values,
        1
    )

    prediction = max(
        0.0,
        float(intercept + slope * len(values))
    )

    st.metric(
        "Indicative next-month units",
        f"{prediction:.1f} kWh"
    )

    st.caption(
        "This is a simple trend estimate, not a trained ML prediction."
    )

else:

    st.info("Save at least 3 bills to see the usage estimate.")


# -------------------- SUPPORT CHATBOT --------------------

st.divider()
st.header("07 · BillWise support assistant")

st.caption("Rule-based assistant for common electricity bill questions.")

def answer_question(question):

    q = question.lower()

    if any(x in q for x in ["language", "marathi", "hindi", "ocr", "scan"]):

        return (
            "Select your bill language in the sidebar. "
            "Scanned PDFs need Tesseract and the relevant language pack. "
            "Always verify the extracted details."
        )

    if any(x in q for x in ["units", "kwh", "consumption", "usage"]):

        return (
            "One electricity unit generally equals 1 kWh. "
            "Compare units across months and consider billing days."
        )

    if any(x in q for x in ["high bill", "bill increased", "why bill", "expensive"]):

        return (
            "Compare units, billing days, meter readings, tariff slabs, "
            "fixed charges, taxes, arrears and late fees."
        )

    if any(x in q for x in ["ac", "geyser", "appliance", "fan", "fridge"]):

        return (
            "Estimated usage = watts / 1000 × hours per day × 30 × quantity. "
            "This is an estimate, not actual appliance measurement."
        )

    if any(x in q for x in ["save", "reduce", "saving"]):

        return (
            "Use LEDs, reduce unnecessary appliance runtime, "
            "use a geyser timer and run full washing-machine loads."
        )

    if any(x in q for x in ["complaint", "wrong bill", "meter", "dispute"]):

        return (
            "Compare meter readings and billing days. "
            "Contact your DISCOM using the official helpline on your bill."
        )

    return (
        "Ask about bill scanning, units, high bills, appliances, "
        "savings or billing complaints."
    )


for message in st.session_state.chat:

    with st.chat_message(message["role"]):
        st.write(message["content"])


question = st.chat_input(
    "Ask about your electricity bill"
)

if question:

    st.session_state.chat.append({
        "role": "user",
        "content": question
    })

    st.session_state.chat.append({
        "role": "assistant",
        "content": answer_question(question)
    })

    st.rerun()


# -------------------- FOOTER --------------------

st.markdown("""
<hr>
<center>
<strong style="color:#087f8c;">BillWise India ⚡</strong>
<br>
Always verify extracted values with your original electricity bill.
<br>
Estimates are informational and are not official DISCOM billing advice.
</center>
""", unsafe_allow_html=True)
