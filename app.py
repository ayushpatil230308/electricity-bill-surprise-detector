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
    initial_sidebar_state="expanded",
)

# Polished, responsive styling for Streamlit's native components.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --bw-ink: #172a3a;
        --bw-muted: #627487;
        --bw-teal: #087f8c;
        --bw-mint: #dff7ef;
        --bw-blue: #e9f3ff;
        --bw-cream: #f7faf9;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 5% 0%, rgba(13,148,136,.10), transparent 32%),
            radial-gradient(ellipse at 95% 5%, rgba(59,130,246,.08), transparent 28%),
            #f7fafc;
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"] { background: rgba(247,250,252,.88); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #102d3a 0%, #173f4a 58%, #1a5260 100%);
    }
    [data-testid="stSidebar"] * { color: #f3fbfc !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #172a3a !important;
    }
    .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1280px; }
    h1, h2, h3 { font-family: 'Manrope', sans-serif !important; color: var(--bw-ink); letter-spacing: -0.035em; }
    h1 { font-weight: 800 !important; }
    p, li, label { color: #304457; }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2ecef;
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: 0 7px 24px rgba(23,42,58,.045);
    }
    div[data-testid="stMetricLabel"] { color: #627487; font-weight: 600; }
    div[data-testid="stMetricValue"] { color: #087f8c; font-family: 'Manrope', sans-serif; }
    div[data-testid="stExpander"] {
        border: 1px solid #dce8ec;
        border-radius: 16px;
        background: rgba(255,255,255,.88);
        overflow: hidden;
    }
    div[data-testid="stFileUploader"] section {
        border: 1.5px dashed #7bb8b8;
        border-radius: 18px;
        background: linear-gradient(135deg, #f0fffb, #f4f8ff);
    }
    .stButton > button, .stDownloadButton > button, button[kind="primary"] {
        border-radius: 12px !important;
        border: 0 !important;
        font-weight: 700 !important;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 7px 18px rgba(8,127,140,.16);
    }
    .stButton > button[kind="primary"], button[kind="primary"] {
        background: linear-gradient(100deg, #087f8c, #0e9f88) !important;
        color: white !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid #e2ecef;
        border-radius: 14px;
        overflow: hidden;
    }
    .bw-hero {
        background: linear-gradient(115deg, #103746 0%, #087f8c 55%, #0e9f88 100%);
        color: white;
        border-radius: 26px;
        padding: 30px 32px;
        margin: 0 0 24px 0;
        box-shadow: 0 18px 40px rgba(8,127,140,.18);
        position: relative;
        overflow: hidden;
    }
    .bw-hero:after {
        content: '⚡';
        position: absolute;
        right: 28px;
        top: -28px;
        font-size: 150px;
        opacity: .11;
        transform: rotate(12deg);
    }
    .bw-eyebrow {
        color: #b8f4e8;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .15em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .bw-title {
        color: white !important;
        font-size: clamp(2rem, 4vw, 3.15rem);
        line-height: 1.08;
        font-weight: 800;
        margin: 0 0 10px 0;
    }
    .bw-subtitle {
        color: #e1f6f5;
        max-width: 760px;
        font-size: 1.02rem;
        line-height: 1.65;
        margin: 0;
    }
    .bw-chiprow { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
    .bw-chip {
        border: 1px solid rgba(255,255,255,.27);
        color: white;
        background: rgba(255,255,255,.10);
        border-radius: 99px;
        padding: 6px 11px;
        font-size: .78rem;
        font-weight: 600;
    }
    .bw-section-note {
        color: #627487;
        margin-top: -10px;
        margin-bottom: 18px;
    }
    @media (max-width: 700px) {
        .block-container { padding-top: 1rem; }
        .bw-hero { padding: 24px 20px; border-radius: 20px; }
        .bw-hero:after { right: -8px; top: -8px; font-size: 90px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="bw-hero">
      <div class="bw-eyebrow">YOUR SMART ENERGY COMPANION</div>
      <div class="bw-title">BillWise India ⚡</div>
      <p class="bw-subtitle">Understand your electricity bills, spot surprising changes, explore appliance usage, and discover practical ways to save — all in one place.</p>
      <div class="bw-chiprow">
        <span class="bw-chip">✦ 5-month comparison</span>
        <span class="bw-chip">⌁ Multilingual OCR</span>
        <span class="bw-chip">↗ Bill surprise alerts</span>
        <span class="bw-chip">☘ Saving insights</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.subheader("Your electricity, made easier to understand")
st.markdown(
    '<p class="bw-section-note">Start by uploading up to five monthly bills. Review the detected details before saving.</p>',
    unsafe_allow_html=True,
)
st.warning(
    "Important: Indian electricity bills differ by state, DISCOM, language, and PDF format. "
    "This app uses multilingual OCR and editable fields, but no OCR system can guarantee perfect "
    "extraction from every bill. Verify every value before saving."
)

LANGUAGES = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin", "Gujarati": "guj",
    "Bengali": "ben", "Tamil": "tam", "Telugu": "tel", "Kannada": "kan",
    "Malayalam": "mal", "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep"
}
DISCOMS = [
    "Not sure / Other", "MSEDCL / Mahavitaran (Maharashtra)", "Adani Electricity Mumbai",
    "Tata Power", "BEST (Mumbai)", "Torrent Power", "Gujarat Urja Vikas Nigam / DISCOM",
    "BESCOM (Karnataka)", "TANGEDCO (Tamil Nadu)", "KSEB (Kerala)",
    "TSSPDCL / TGSPDCL (Telangana)", "APSPDCL / APEPDCL (Andhra Pradesh)",
    "TPDDL / BSES (Delhi)", "UPPCL (Uttar Pradesh)", "WBSEDCL (West Bengal)",
    "Bihar DISCOM", "JVVNL / AVVNL / JDVVNL (Rajasthan)", "Other Indian DISCOM"
]
AMOUNT_LABELS = [
    r"total\s*amount\s*due", r"net\s*amount\s*payable", r"amount\s*payable",
    r"amount\s*due", r"bill\s*amount", r"total\s*bill", r"grand\s*total",
    r"total\s*payable", r"current\s*bill\s*amount", r"net\s*amount",
    r"payable\s*amount", r"bill\s*total", r"amount\s*after\s*due\s*date",
    r"देयक\s*रक[्क्]?म", r"देयक\s*रक्कम", r"पूर्णाक\s*देयक", r"निव्वळ\s*रक[्क्]?म"
]
UNITS_LABELS = [
    r"units?\s*consumed", r"consumed\s*units", r"energy\s*consumed",
    r"kwh\s*consumed", r"billable\s*units", r"total\s*consumption",
    r"consumption\s*\(?\s*kwh\s*\)?", r"units?\s*\(\s*kwh\s*\)",
    r"energy\s*units", r"units\s*billed", r"consumption\s*units"
]
BILL_ID_LABELS = [r"consumer\s*number", r"consumer\s*no", r"account\s*number", r"customer\s*id"]
NUMBER_RE = re.compile(r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
CURRENCY_RE = re.compile(r"(?:₹|Rs\.?|INR|रु\.?|रुपये)\s*[.):：]?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)

if "bill_records" not in st.session_state:
    st.session_state.bill_records = []
if "chat" not in st.session_state:
    st.session_state.chat = []

def preprocess(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(1.5)

@st.cache_data(show_spinner=False, max_entries=64)
def installed_ocr_languages():
    if pytesseract is None:
        return ()
    try:
        return tuple(pytesseract.get_languages(config=""))
    except Exception:
        return ()

def ocr_image(image, language_codes, is_msedcl=False):
    """OCR with installed-language discovery and practical bilingual fallbacks."""
    if pytesseract is None:
        return "", "OCR dependency missing: pytesseract is not installed."
    installed = set(installed_ocr_languages())
    if not installed:
        return "", "Tesseract engine or traineddata is missing on Streamlit Cloud. Check packages.txt and app logs."

    # MSEDCL bills are commonly Marathi/English mixed. Selecting English in the UI
    # must not prevent the Marathi model from being tried automatically.
    candidates = []
    if is_msedcl:
        candidates.extend(["mar+eng", "eng+mar", "eng"])
    candidates.extend([language_codes, f"{language_codes}+eng", "eng"])
    attempts = []
    for candidate in candidates:
        parts = candidate.split("+")
        if all(part in installed for part in parts) and candidate not in attempts:
            attempts.append(candidate)

    best, best_score, used, errors = "", -1, "", []
    # A modest 200-DPI render plus a single bilingual pass is usually faster
    # and more useful than repeatedly running every available language.
    for lang in attempts[:3]:
        for psm in (6, 11):
            try:
                candidate = pytesseract.image_to_string(
                    image, lang=lang, config=f"--oem 1 --psm {psm}", timeout=45
                ).strip()
                score = sum(ch.isalnum() for ch in candidate)
                if score > best_score:
                    best, best_score, used = candidate, score, lang
                if score >= 80:
                    break
            except Exception as exc:
                errors.append(f"{lang}/psm{psm}: {type(exc).__name__}")
        if best_score >= 80:
            break

    if best:
        return best, f"OCR successful using {used}; detected {best_score} readable characters."
    if not attempts:
        return "", f"No compatible traineddata installed. Requested {language_codes}; installed: {', '.join(sorted(installed))}."
    detail = "; ".join(errors[:3])
    return "", "Tesseract ran but returned no readable text. " + (detail or "Try a clearer scan or higher-quality PDF.")

def readable_embedded_text(text):
    if not text or len(text.strip()) < 35:
        return False
    if any(marker in text for marker in ["�", "□", "Ã", "Â", "â€", "ï»¿"]):
        return False
    letters = [ch for ch in text if ch.isalpha()]
    extended = sum(0x00C0 <= ord(ch) <= 0x024F for ch in letters)
    if letters and extended / len(letters) > 0.18:
        return False
    visible = sum(ch.isalnum() or ch in "₹.,:/-%() \n\t" for ch in text)
    return visible / max(len(text), 1) >= 0.7

def _read_pdf_bytes(file_bytes, language_codes, force_ocr, dpi, filename=""):
    if fitz is None:
        return "", "PyMuPDF missing. Install requirements.txt."
    pages, notes = [], []
    is_msedcl = "msedcl" in (filename or "").lower()
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            for n, page in enumerate(pdf, 1):
                embedded = (page.get_text("text") or "").strip()
                needs_ocr = force_ocr or not readable_embedded_text(embedded)
                if needs_ocr:
                    # 2x is approximately 144 DPI for standard PDF points; avoid
                    # excessive render sizes that make cloud OCR time out.
                    scale = 1.5 if float(dpi) <= 2 else 2.0
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    scanned, note = ocr_image(preprocess(image), language_codes, is_msedcl=is_msedcl)
                    notes.append(f"Page {n}: {note}")
                    pages.append(scanned if scanned and (force_ocr or not readable_embedded_text(embedded)) else embedded)
                else:
                    pages.append(embedded)
                    notes.append(f"Page {n}: embedded PDF text used (fast path)")
        return "\n\n".join(pages), " | ".join(notes)
    except Exception as exc:
        return "", f"Could not read PDF: {type(exc).__name__}: {exc}"

@st.cache_data(show_spinner=False, max_entries=32)
def read_pdf_cached(file_bytes, language_codes, force_ocr, dpi, filename=""):
    return _read_pdf_bytes(file_bytes, language_codes, force_ocr, dpi, filename)

@st.cache_data(show_spinner=False, max_entries=64)
def read_image_cached(file_bytes, language_codes, filename=""):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return ocr_image(preprocess(img), language_codes, is_msedcl="msedcl" in (filename or "").lower())
    except Exception as exc:
        return "", f"Could not read image: {exc}"

def read_file(upload, language_codes, force_ocr, dpi):
    file_bytes = upload.getvalue()
    if Path(upload.name).suffix.lower() == ".pdf":
        return read_pdf_cached(file_bytes, language_codes, force_ocr, dpi, upload.name)
    return read_image_cached(file_bytes, language_codes, upload.name)

def parse_num(s):
    try:
        return float(s.replace(",", "").strip())
    except Exception:
        return None

def find_labeled_value(text, patterns, kind="number"):
    lines = [re.sub(r"\s+", " ", ln.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "")).strip() for ln in (text or "").splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        for pat in patterns:
            match = re.search(pat, line, re.I)
            if not match:
                continue
            search_lines = [line[match.end():]] + lines[i+1:i+3]
            for candidate_line in search_lines:
                # Amounts must carry a currency marker; never mistake dates/years for rupees.
                values = CURRENCY_RE.findall(candidate_line) if kind == "amount" else NUMBER_RE.findall(candidate_line)
                parsed = [parse_num(v) for v in values]
                parsed = [v for v in parsed if v is not None and v > 0]
                if parsed:
                    return parsed[0], line + (" | " + candidate_line if candidate_line != line[match.end():] else "")
    # MSEDCL Marathi table: OCR header includes "एकूण वापर" (total use),
    # followed by a meter row whose final numeric cell is total kWh.
    if kind == "number":
        lines_norm = [re.sub(r"\s+", " ", ln).strip() for ln in (text or "").splitlines() if ln.strip()]
        for i, line in enumerate(lines_norm):
            if "एकूण वापर" in line or ("चालु रिडिंग" in line and "मागील" in line):
                for row in lines_norm[i+1:i+4]:
                    nums = NUMBER_RE.findall(row)
                    vals = [parse_num(v) for v in nums]
                    vals = [v for v in vals if v is not None]
                    # Ignore meter readings (typically 4+ digits); last small cell is total kWh.
                    small = [v for v in vals if 0 < v <= 100000 and v < 1000]
                    if small:
                        return small[-1], line + " | " + row
    return None, ""

def extract_amount_candidates(text):
    found = []
    for line in (text or "").splitlines():
        # Only capture values explicitly marked as currency. Dates, page numbers and years are ignored.
        for value in CURRENCY_RE.findall(line):
            n = parse_num(value)
            if n is not None and 1 <= n <= 10000000:
                found.append({"Candidate amount (₹)": n, "Source line": line.strip()[:180]})
    return pd.DataFrame(found).drop_duplicates() if found else pd.DataFrame()

def guess_month(text, filename):
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    source = text or ""
    name = Path(filename).stem
    code = re.search(r"(?:^|[_-])(\d{2})(0[1-9]|1[0-2])(?:[_-]|$)", name)
    if code and "msedcl" in name.lower():
        return datetime(2000 + int(code.group(1)), int(code.group(2)), 1).strftime("%B %Y")
    # Prefer explicit billing-period/month labels, not arbitrary dates found in OCR.
    labeled = re.search(
        rf"(?:billing\s*(?:month|period)|bill\s*(?:month|period|for))[^\n]{{0,50}}?\b({months})\s*,?\s*(20\d{{2}})\b",
        source, re.I
    )
    if labeled:
        return f"{labeled.group(1).title()} {labeled.group(2)}"
    # MSEDCL filenames commonly contain YYMM, e.g. MSEDCL_2609 -> September 2026.
    # Prefer this structured filename code over unrelated dates/months in OCR noise.
    name = Path(filename).stem
    code = re.search(r"(?:^|[_-])(\d{2})(0[1-9]|1[0-2])(?:[_-]|$)", name)
    if code:
        return datetime(2000 + int(code.group(1)), int(code.group(2)), 1).strftime("%B %Y")
    m = re.search(rf"\b({months})\s*,?\s*(20\d{{2}})\b", source, re.I)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"
    bill_date = re.search(r"(?:bill\s*date|billing\s*date)[^\d]{0,12}(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", source, re.I)
    if bill_date:
        try:
            return datetime(int(bill_date.group(3)), int(bill_date.group(2)), int(bill_date.group(1))).strftime("%B %Y")
        except ValueError:
            pass
    return ""

def bill_form(upload, idx, text, read_note):
    st.caption(read_note)
    with st.expander("View extracted text", expanded=False):
        st.text_area("OCR output (check for errors)", text[:15000], height=180, key=f"text_{idx}")
    amount, amount_line = find_labeled_value(text, AMOUNT_LABELS, kind="amount")
    units, units_line = find_labeled_value(text, UNITS_LABELS, kind="number")
    month_guess = guess_month(text, upload.name)
    candidates = extract_amount_candidates(text)

    st.markdown("**Review and correct the automatically detected details**")
    c1, c2 = st.columns(2)
    with c1:
        month = st.text_input("Billing month", value=month_guess, key=f"month_{idx}", placeholder="e.g. June 2026")
        amount_value = st.number_input("Final payable amount (₹)", min_value=0.0, value=float(amount or 0), step=10.0, key=f"amount_{idx}")
        if amount is None:
            st.warning("Payable amount was not confidently detected. Enter it from the original bill.")
        st.caption("Amount evidence: " + (amount_line or "Not confidently found"))
    with c2:
        units_value = st.number_input("Units consumed (kWh)", min_value=0.0, value=float(units or 0), step=1.0, key=f"units_{idx}")
        if units is None:
            st.warning("Units were not confidently detected. Enter kWh from the original bill.")
        st.caption("Units evidence: " + (units_line or "Not confidently found"))

    if amount is None and not candidates.empty:
        st.warning("Several bill amounts may be present (current bill, arrears, late payment amount). Choose the final payable amount by checking the original bill.")
        st.dataframe(candidates, use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)
    with c3:
        discom = st.selectbox("Electricity company / DISCOM", DISCOMS, key=f"discom_{idx}")
    with c4:
        state = st.selectbox("State / UT", [
            "Not selected", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
            "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
            "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
            "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
            "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
            "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
            "Ladakh", "Puducherry", "Chandigarh", "Andaman and Nicobar Islands",
            "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep"
        ], key=f"state_{idx}")
    if st.button("Save verified bill", key=f"save_{idx}", type="primary"):
        if not month.strip() or amount_value <= 0 or units_value <= 0:
            st.error("Please correct the month, bill amount and units using the original bill before saving.")
        elif any(r["Billing month"].lower() == month.strip().lower() for r in st.session_state.bill_records):
            st.error("A bill for this month is already saved. Clear history or remove duplicate before saving.")
        else:
            st.session_state.bill_records.append({
                "Billing month": month.strip(),
                "Bill amount (₹)": float(amount_value),
                "Units (kWh)": float(units_value),
                "State/UT": state,
                "DISCOM": discom,
                "Source file": upload.name
            })
            st.success("Bill saved. Upload and verify the remaining months.")

with st.sidebar:
    st.header("Bill settings")
    chosen_language = st.selectbox("Main bill language", list(LANGUAGES.keys()), index=0)
    force_ocr = st.checkbox("Force OCR for scanned/garbled PDFs", value=False)
    dpi = st.slider("PDF OCR resolution (higher = slower)", 1, 3, 2)
    st.caption("Fast mode uses embedded PDF text first and caches repeated scans.")
    installed = set(installed_ocr_languages())
    if pytesseract is None or not installed:
        st.error("Server OCR engine is not available. Check packages.txt and Streamlit Cloud build logs.")
    else:
        ready = sorted(installed.intersection({"eng", "mar", "hin", "guj", "ben", "tam", "tel", "kan", "mal", "pan", "urd", "ori", "asm", "nep"}))
        st.success("OCR engine ready: " + (", ".join(ready) if ready else "No supported language packs found"))
    st.caption("MSEDCL PDFs automatically try Marathi + English OCR, even when English is selected.")

language_code = LANGUAGES[chosen_language]

st.header("01  ·  Upload your bills")
st.write("Upload up to 5 bills, including the current month. Add one bill for each month. Each bill opens a review form so you can correct OCR before saving.")
uploads = st.file_uploader(
    "Upload your last 5 monthly bills (PDF, PNG, JPG or JPEG)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)
if uploads:
    if len(uploads) > 5:
        st.warning("Please upload no more than 5 files in this step.")
    st.caption("For faster response, each bill is scanned only when you click its Scan button. Repeated scans are cached.")
    for idx, upload in enumerate(uploads[:5]):
        file_bytes = upload.getvalue()
        digest = hashlib.sha256(file_bytes).hexdigest()[:16]
        scan_key = f"bill_scan_{digest}"
        with st.expander(f"Bill {idx+1}: {upload.name}", expanded=(idx == 0)):
            if scan_key not in st.session_state:
                if st.button(f"Scan this bill", key=f"scan_button_{digest}", type="primary"):
                    with st.spinner("Reading bill… text-based PDFs are faster; scanned PDFs may take longer."):
                        st.session_state[scan_key] = read_file(upload, language_code, force_ocr, dpi)
                    st.rerun()
                st.info("Click **Scan this bill** to extract its details. You can scan and verify bills one at a time.")
            else:
                text, note = st.session_state[scan_key]
                if not text.strip():
                    st.error("No readable text extracted. Try the correct language, enable Force OCR, or enter the values manually.")
                    if st.button("Retry scan with current settings", key=f"retry_{digest}"):
                        st.session_state.pop(scan_key, None)
                        st.rerun()
                bill_form(upload, digest, text, note)

st.divider()
st.header("02  ·  Your monthly insights")
if st.session_state.bill_records:
    df = pd.DataFrame(st.session_state.bill_records)
    # Chronological sort when month labels parse; preserve otherwise.
    def month_sort(value):
        try:
            return pd.to_datetime(value, format="%B %Y")
        except Exception:
            return pd.Timestamp.max
    df = df.assign(_sort=df["Billing month"].map(month_sort)).sort_values("_sort").drop(columns="_sort")
    st.dataframe(df, use_container_width=True, hide_index=True)
    a, b, c = st.columns(3)
    a.metric("Bills saved", f"{len(df)} / 5")
    a.metric("Average monthly bill", f"₹{df['Bill amount (₹)'].mean():,.2f}")
    b.metric("Average monthly usage", f"{df['Units (kWh)'].mean():,.1f} kWh")
    c.metric("Highest bill", f"₹{df['Bill amount (₹)'].max():,.2f}")
    st.subheader("Comparison chart: bill amount and units")
    chart = df.set_index("Billing month")[["Bill amount (₹)", "Units (kWh)"]]
    st.line_chart(chart)
    left, right = st.columns(2)
    with left:
        st.subheader("Bill amount comparison")
        st.bar_chart(df.set_index("Billing month")["Bill amount (₹)"])
    with right:
        st.subheader("Usage comparison")
        st.bar_chart(df.set_index("Billing month")["Units (kWh)"])

    if len(df) >= 2:
        df2 = df.copy()
        df2["Bill change (%)"] = df2["Bill amount (₹)"].pct_change() * 100
        df2["Usage change (%)"] = df2["Units (kWh)"].pct_change() * 100
        st.subheader("Month-to-month changes")
        st.dataframe(df2[["Billing month", "Bill amount (₹)", "Bill change (%)", "Units (kWh)", "Usage change (%)"]].round(2), use_container_width=True, hide_index=True)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        if prev["Units (kWh)"] > 0:
            usage_change = (latest["Units (kWh)"] - prev["Units (kWh)"]) / prev["Units (kWh)"] * 100
            if usage_change >= 20:
                st.error(f"Usage alert: units increased by {usage_change:.1f}% from the previous saved month. Check usage, billing days and meter readings.")
            elif usage_change <= -20:
                st.success(f"Usage decreased by {abs(usage_change):.1f}% from the previous saved month.")
            else:
                st.info(f"Usage changed by {usage_change:+.1f}% from the previous saved month.")
        if prev["Bill amount (₹)"] > 0:
            bill_change = (latest["Bill amount (₹)"] - prev["Bill amount (₹)"]) / prev["Bill amount (₹)"] * 100
            if bill_change >= 20:
                st.warning(f"Bill amount increased by {bill_change:.1f}%. Compare units, tariff, fixed charges, arrears, taxes and billing days.")
    else:
        st.info("Upload and save at least 2 different months to unlock month-to-month comparison. Upload up to 5 months for a better pattern.")
    st.download_button("Download analysis CSV", df.to_csv(index=False).encode("utf-8-sig"), "billwise_5_month_analysis.csv", "text/csv")
    if st.button("Clear all saved bills"):
        st.session_state.bill_records = []
        st.rerun()
else:
    st.info("Your comparison dashboard will appear after you save verified bills. For meaningful trend analysis, add 4–5 different months.")

st.divider()
st.header("03  ·  Appliance energy estimator")
st.write("This is an estimate based on appliance wattage and hours entered by you; the bill alone cannot identify exact appliance-level consumption.")
APPLIANCES = {
    "Air Conditioner": 1500, "Geyser / Water Heater": 2000, "Refrigerator": 150,
    "Washing Machine": 500, "Ceiling Fan": 70, "LED Bulb": 9, "Television": 100,
    "Electric Iron": 1000, "Water Pump": 750, "Induction Cooktop": 1800,
    "Desktop Computer": 200, "Microwave": 1200, "Room Heater": 2000
}
with st.form("appliances"):
    selected_appliances = st.multiselect("Select appliances used at home", list(APPLIANCES), default=["Refrigerator", "Ceiling Fan"])
    appliance_rows = []
    for i, name in enumerate(selected_appliances):
        st.markdown(f"**{name}**")
        x, y, z = st.columns(3)
        watts = x.number_input("Rated watts", 1, 20000, APPLIANCES[name], key=f"watts_{i}")
        hours = y.number_input("Hours used daily", 0.0, 24.0, 4.0, 0.5, key=f"hours_{i}")
        quantity = z.number_input("Number of appliances", 1, 100, 1, key=f"quantity_{i}")
        appliance_rows.append((name, watts, hours, quantity))
    tariff = st.number_input("Approximate energy rate (₹/kWh)", 0.0, 100.0, 8.0, 0.5)
    calculate_appliances = st.form_submit_button("Estimate appliance consumption")
if calculate_appliances:
    rows = []
    for name, watts, hours, quantity in appliance_rows:
        kwh = watts / 1000 * hours * 30 * quantity
        rows.append({"Appliance": name, "Estimated kWh/month": round(kwh, 2), "Estimated energy cost (₹/month)": round(kwh * tariff, 2)})
    if rows:
        appliance_df = pd.DataFrame(rows).sort_values("Estimated kWh/month", ascending=False)
        st.dataframe(appliance_df, use_container_width=True, hide_index=True)
        st.bar_chart(appliance_df.set_index("Appliance")["Estimated kWh/month"])
        st.success(f"Highest estimated consumer from your inputs: {appliance_df.iloc[0]['Appliance']} ({appliance_df.iloc[0]['Estimated kWh/month']:.1f} kWh/month).")
    st.caption("These are approximate estimates, not actual smart-meter measurements. AC and geyser power varies by model and operating cycle.")

st.divider()
st.header("04  ·  Smart saving ideas")
st.markdown("""
- **AC:** Set a moderate temperature, clean filters and reduce unnecessary runtime.
- **Geyser:** Use a timer and switch it off after heating.
- **Refrigerator:** Check door seals and avoid frequent/long door openings.
- **Lighting:** Use LEDs and turn off unused lights.
- **Washing machine:** Run full loads when practical.
- **Water pump:** Check for leaks and avoid unnecessary pumping.
- **Compare the bill:** Check billing days, meter readings, tariff, fixed charges, taxes and previous dues.
- **If the amount rose but units did not:** Ask your DISCOM to explain tariff changes, arrears, meter reading and bill adjustments.
""")
if st.session_state.bill_records:
    latest_units = float(st.session_state.bill_records[-1]["Units (kWh)"])
    goal = st.slider("Illustrative monthly usage reduction goal", 0, 30, 10, 5)
    saving_rate = st.number_input("Rate for saving estimate (₹/kWh)", 0.0, 100.0, 8.0, 0.5, key="saving_rate")
    saved_units = latest_units * goal / 100
    x, y = st.columns(2)
    x.metric("Potential units saved", f"{saved_units:.1f} kWh/month")
    y.metric("Potential energy-charge saving", f"₹{saved_units * saving_rate:.2f}/month")
    st.caption("Illustrative estimate only. Actual savings depend on tariff slabs and fixed charges.")


st.divider()
st.header("05  ·  Bill Surprise Fingerprint")
st.write(
    "This checks whether a higher bill is more consistent with higher electricity use "
    "or with a change in bill amount that usage alone does not explain."
)

if len(st.session_state.bill_records) >= 2:
    ordered = pd.DataFrame(st.session_state.bill_records).copy()

    def _month_key(label):
        try:
            return pd.to_datetime(label, format="%B %Y")
        except Exception:
            return pd.Timestamp.max

    ordered["_month_order"] = ordered["Billing month"].map(_month_key)
    ordered = ordered.sort_values("_month_order").drop(columns="_month_order").reset_index(drop=True)
    prior = ordered.iloc[-2]
    latest = ordered.iloc[-1]

    prev_units = float(prior["Units (kWh)"])
    curr_units = float(latest["Units (kWh)"])
    prev_bill = float(prior["Bill amount (₹)"])
    curr_bill = float(latest["Bill amount (₹)"])

    usage_change = ((curr_units - prev_units) / prev_units * 100) if prev_units > 0 else None
    bill_change = ((curr_bill - prev_bill) / prev_bill * 100) if prev_bill > 0 else None

    d1, d2, d3 = st.columns(3)
    d1.metric("Latest units", f"{curr_units:,.1f} kWh",
              None if usage_change is None else f"{usage_change:+.1f}% vs prior")
    d2.metric("Latest bill", f"₹{curr_bill:,.2f}",
              None if bill_change is None else f"{bill_change:+.1f}% vs prior")
    if curr_units > 0:
        curr_cost_per_unit = curr_bill / curr_units
    else:
        curr_cost_per_unit = 0
    if prev_units > 0:
        prev_cost_per_unit = prev_bill / prev_units
    else:
        prev_cost_per_unit = 0
    d3.metric("Effective bill / unit", f"₹{curr_cost_per_unit:.2f}",
              f"{curr_cost_per_unit - prev_cost_per_unit:+.2f} vs prior")

    if usage_change is not None and bill_change is not None:
        if bill_change >= 15 and usage_change >= 15:
            st.error(
                "Likely usage-driven surprise: both bill amount and units increased. "
                "Review AC/geyser runtime, guests, seasonal use, and billing days."
            )
        elif bill_change >= 15 and usage_change < 5:
            st.warning(
                "Amount-up / usage-flat pattern: units changed little but the bill rose. "
                "Check tariff slabs, fixed charges, taxes, arrears, late fees, meter "
                "adjustments and the number of billing days."
            )
        elif bill_change >= 15 and usage_change < 15:
            st.warning(
                "Mixed pattern: the bill rose more than usage. Check both appliance use "
                "and bill components such as tariff, taxes, arrears and billing period."
            )
        elif usage_change >= 20 and bill_change < 15:
            st.info(
                "Usage-up / amount-muted pattern: units increased noticeably. Check "
                "billing days, tariff slabs, rebates or adjustments before drawing a conclusion."
            )
        else:
            st.success(
                "No large bill increase detected between the latest two saved months "
                "using the simple 15% bill / 20% usage rules."
            )
    st.caption(
        "These are transparent comparison rules, not proof of the cause. The bill itself "
        "may not include appliance-level measurements or all tariff details."
    )
else:
    st.info("Save at least two different months to generate a Bill Surprise Fingerprint.")

st.divider()
st.header("06  ·  Next-month usage estimate")
st.write(
    "A lightweight trend estimate based on your saved monthly units. With only 2–5 bills, "
    "this is an indicative baseline, not a reliable long-term forecast."
)
if len(st.session_state.bill_records) >= 3:
    forecast_df = pd.DataFrame(st.session_state.bill_records).copy()

    def _forecast_month_key(label):
        try:
            return pd.to_datetime(label, format="%B %Y")
        except Exception:
            return pd.Timestamp.max

    forecast_df["_date"] = forecast_df["Billing month"].map(_forecast_month_key)
    forecast_df = forecast_df.sort_values("_date").reset_index(drop=True)
    # Use a simple least-squares trend on the observed monthly sequence.
    import numpy as np
    y = forecast_df["Units (kWh)"].astype(float).to_numpy()
    x = np.arange(len(y), dtype=float)
    if len(y) >= 3 and np.all(np.isfinite(y)):
        slope, intercept = np.polyfit(x, y, 1)
        forecast_units = max(0.0, float(intercept + slope * len(y)))
        last_units = float(y[-1])
        st.metric("Indicative next-month units", f"{forecast_units:,.1f} kWh",
                  f"{forecast_units - last_units:+,.1f} kWh vs latest")
        if last_units > 0:
            st.metric(
                "Indicative energy cost at selected rate",
                f"₹{forecast_units * float(st.session_state.get('saving_rate', 8.0)):,.2f}"
            )
        st.caption(
            "This is a simple linear trend, not a trained model. It does not account for "
            "weather, season, billing days, tariff changes, occupancy or appliance changes."
        )
else:
    st.info("Save at least 3 different months to see an indicative next-month usage trend.")

st.divider()
st.header("07  ·  BillWise support assistant")
st.caption("This starter chatbot uses built-in rules and is not a connected generative AI service.")
def answer_question(question):
    q = question.lower()
    if any(w in q for w in ["language", "marathi", "hindi", "gujarati", "ocr", "text not", "scan"]):
        return "Choose the main bill language in the sidebar. If the PDF text looks garbled, enable Force OCR. Make sure Tesseract and the language pack are installed. Always verify the amount and units manually."
    if any(w in q for w in ["units", "kwh", "consumption", "usage"]):
        return "One electricity unit generally equals 1 kWh. Compare units across bills and account for different billing-day counts."
    if any(w in q for w in ["high bill", "bill increased", "why bill", "expensive", "amount increased"]):
        return "Compare kWh, billing days, current and previous meter readings, tariff slabs, fixed charges, taxes, arrears and late fees. If still unclear, contact the DISCOM using the number on your bill."
    if any(w in q for w in ["ac", "air conditioner", "geyser", "appliance", "fan", "fridge", "refrigerator"]):
        return "Use the appliance estimator: watts ÷ 1000 × hours per day × 30 × quantity. It estimates use, but cannot measure exact appliance consumption from a bill alone."
    if any(w in q for w in ["save", "reduce", "saving", "less bill"]):
        return "Try reducing AC runtime, using a geyser timer, switching to LEDs, running full washing-machine loads, and checking pumps or appliances left on. Compare kWh next month."
    if any(w in q for w in ["complaint", "wrong bill", "meter", "dispute"]):
        return "Keep your consumer/account number and bill ready. Compare current/previous readings and billing days, then contact the official DISCOM helpline listed on your bill. This demo cannot file a complaint for you."
    return "I can help with bill scanning, units, high bills, appliances, savings and billing complaints. Try asking: 'Why did my bill increase?' or 'How can I save electricity?'"

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
question = st.chat_input("Ask a question about your electricity bill")
if question:
    st.session_state.chat.append({"role": "user", "content": question})
    st.session_state.chat.append({"role": "assistant", "content": answer_question(question)})
    st.rerun()


st.markdown(
    """
    <div style="margin-top:2.5rem;padding:18px 6px;border-top:1px solid #dce8ec;
                color:#718096;font-size:.82rem;text-align:center;">
      <strong style="color:#087f8c;">BillWise India</strong> · Built to make electricity bills easier to understand.
      <br/>Always verify extracted values with your original bill. Estimates are informational, not official billing advice.
    </div>
    """,
    unsafe_allow_html=True,
)
