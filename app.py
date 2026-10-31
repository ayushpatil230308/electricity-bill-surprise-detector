import io
import re
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance

try:
    import fitz  # PyMuPDF
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

# --------------------------- UI STYLE ---------------------------------
st.markdown("""
<style>
/* BillWise palette: soft gray + charcoal + indigo/cyan, with restrained brass highlights */
/* High-contrast accessibility override: never allow white text on the light canvas. */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"], .main, .block-container { background-color:#F8F9FA; color:#1E293B !important; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div,
.stMarkdown, [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"],
[data-testid="stText"], [data-testid="stHeader"] { color:#1E293B; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp strong { color:#172033 !important; }
.stApp [data-testid="stCaptionContainer"] p { color:#526176 !important; }
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="input"] > div { color:#1E293B !important; background:#FFFFFF !important; }
.stApp [data-baseweb="select"] span { color:#1E293B !important; }
.stApp [data-testid="stAlert"] p, .stApp [data-testid="stAlert"] div { color:#1E293B !important; }
.stApp [data-testid="stDataFrame"] *, .stApp [data-testid="stTable"] * { color:#1E293B !important; }
[data-testid="stSidebar"] { color:#F8FAFC !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color:#F8FAFC !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] * { color:#1E293B !important; }

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');
:root{--ink:#1E293B;--muted:#64748B;--teal:#4F46E5;--mint:#CFFAFE;--line:#E2E8F0;--shadow:0 12px 34px rgba(30,41,59,.08)}
.stApp{background:radial-gradient(ellipse at 7% 0%,rgba(79,70,229,.11),transparent 30%),radial-gradient(ellipse at 95% 20%,rgba(6,182,212,.10),transparent 27%),#F8F9FA;font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{background:rgba(248,249,250,.88);backdrop-filter:blur(12px)}
[data-testid="stSidebar"]{background:linear-gradient(160deg,#0F172A 0%,#26345B 58%,#4F46E5 100%)}
[data-testid="stSidebar"] *{color:#f3fbfc!important}
[data-testid="stSidebar"] input,[data-testid="stSidebar"] [data-baseweb="select"] *{color:#1E293B!important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#E2E8F0!important}
.block-container{padding-top:1.35rem;padding-bottom:3rem;max-width:1360px}
h1,h2,h3{font-family:'Manrope',sans-serif!important;color:var(--ink);letter-spacing:-.035em}
h2{font-size:1.55rem!important;margin-top:1.35rem!important}
h3{font-size:1.12rem!important}
p,li{color:#475569}
[data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#f8fcfc);border:1px solid var(--line);border-radius:19px;padding:17px 18px;box-shadow:var(--shadow);transition:transform .22s ease,box-shadow .22s ease}
[data-testid="stMetric"]:hover{transform:translateY(-3px);box-shadow:0 17px 38px rgba(16,43,58,.13)}
[data-testid="stMetricLabel"]{color:#64748B!important;font-weight:700}
[data-testid="stMetricValue"]{color:#4F46E5;font-family:'Manrope',sans-serif;font-weight:800}
[data-testid="stExpander"]{border:1px solid #E2E8F0!important;border-radius:17px!important;background:#ffffffd9;box-shadow:0 5px 20px rgba(16,43,58,.035);transition:border-color .2s ease,box-shadow .2s ease}
[data-testid="stExpander"]:hover{border-color:#67E8F9!important;box-shadow:0 9px 25px rgba(8,127,140,.08)}
[data-testid="stFileUploader"] section{border:2px dashed #818CF8;border-radius:21px;background:linear-gradient(135deg,#EEF2FF,#ECFEFF);transition:all .22s ease}
[data-testid="stFileUploader"] section:hover{border-color:#4F46E5;background:linear-gradient(135deg,#E0E7FF,#CFFAFE);transform:translateY(-2px)}
.stButton>button,.stDownloadButton>button{border-radius:13px!important;font-weight:800!important;border:1px solid #CBD5E1!important;transition:transform .18s ease,box-shadow .18s ease,filter .18s ease!important}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);box-shadow:0 9px 20px rgba(8,127,140,.14);filter:brightness(1.02)}
.stButton>button[kind="primary"]{background:linear-gradient(110deg,#4F46E5,#06B6D4)!important;color:white!important;border:0!important;box-shadow:0 7px 18px rgba(8,127,140,.2)}
[data-testid="stTabs"] button{font-weight:700}
[data-testid="stAlert"]{border-radius:14px}
[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#4F46E5,#38c7a7)}
.bw-hero{position:relative;overflow:hidden;background:linear-gradient(115deg,#0F172A 0%,#3730A3 56%,#06B6D4 100%);background-size:180% 180%;color:white;border-radius:28px;padding:34px 36px;margin:4px 0 25px;box-shadow:0 20px 48px rgba(8,127,140,.22);animation:bw-hero-in .7s ease both,bw-gradient 18s ease-in-out infinite alternate}
.bw-hero:before{content:"";position:absolute;width:310px;height:310px;border-radius:50%;right:-75px;top:-155px;background:rgba(255,255,255,.10);filter:blur(1px);pointer-events:none}
.bw-hero:after{content:"";position:absolute;width:180px;height:180px;border-radius:50%;right:155px;bottom:-125px;background:rgba(167,243,208,.13);pointer-events:none}
.bw-hero-inner{position:relative;z-index:1;max-width:900px}
.bw-eyebrow{color:#C7D2FE;font-size:.75rem;font-weight:800;letter-spacing:.17em;text-transform:uppercase}
.bw-title{color:white!important;font-size:clamp(2.1rem,4.2vw,3.35rem);font-weight:800;margin:8px 0 7px;line-height:1.12}
.bw-subtitle{color:#E0F2FE;max-width:760px;line-height:1.7;font-size:1.02rem;margin:0}
.bw-chip{display:inline-flex;align-items:center;border:1px solid #ffffff45;color:white;background:#ffffff18;border-radius:99px;padding:7px 12px;margin:17px 6px 0 0;font-size:.77rem;font-weight:700;backdrop-filter:blur(8px)}
.bw-live{display:inline-flex;align-items:center;gap:7px;color:#CFFAFE;font-size:.78rem;font-weight:700;margin-top:18px}
.bw-dot{width:8px;height:8px;border-radius:50%;background:#67E8F9;box-shadow:0 0 0 5px #67E8F922;animation:bw-pulse 2s ease-in-out infinite}
.bw-section-kicker{color:#4F46E5;font-size:.72rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase;margin-bottom:2px}
.bw-mini-card{background:linear-gradient(145deg,#fff,#F8FAFC);border:1px solid #E0E7FF;border-radius:17px;padding:15px 16px;box-shadow:0 7px 22px rgba(16,43,58,.045);height:100%}
.bw-mini-icon{font-size:1.35rem;margin-bottom:7px}
.bw-mini-title{color:#1E293B;font-weight:800;font-size:.94rem}
.bw-mini-copy{color:#64748B;font-size:.78rem;line-height:1.5;margin-top:4px}
hr{border-color:#E2E8F0!important;margin:1.4rem 0!important}
@keyframes bw-hero-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes bw-gradient{0%{background-position:0% 50%}100%{background-position:100% 50%}}
@keyframes bw-pulse{0%,100%{box-shadow:0 0 0 4px #67E8F920}50%{box-shadow:0 0 0 8px #67E8F908}}
@media(max-width:700px){.block-container{padding-top:.8rem}.bw-hero{padding:25px 21px;border-radius:22px}.bw-chip{margin-top:10px}.bw-title{font-size:2.15rem}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bw-hero">
 <div class="bw-hero-inner">
  <div class="bw-eyebrow">YOUR SMART ENERGY COMPANION</div>
  <div class="bw-title">BillWise India <span style="white-space:nowrap">⚡</span></div>
  <p class="bw-subtitle">Make sense of every unit. Catch unusual bill changes. Find practical ways to save — all in one simple dashboard.</p>
  <span class="bw-chip">📊 5-month comparison</span><span class="bw-chip">🌐 Multilingual OCR</span>
  <span class="bw-chip">🔔 Bill surprise alerts</span><span class="bw-chip">🌱 Saving insights</span>
  <div class="bw-live"><span class="bw-dot"></span> Smart energy dashboard</div>
 </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="bw-section-kicker">WELCOME TO YOUR DASHBOARD</div>', unsafe_allow_html=True)
st.subheader("Your electricity, made easier to understand")
st.caption("Upload up to five monthly bills, review detected values and turn your bill history into useful insights.")
quick1, quick2, quick3 = st.columns(3)
with quick1:
    st.markdown('<div class="bw-mini-card"><div class="bw-mini-icon">📄</div><div class="bw-mini-title">Scan your bills</div><div class="bw-mini-copy">Upload PDF or photo bills and review the extracted month, units and amount.</div></div>', unsafe_allow_html=True)
with quick2:
    st.markdown('<div class="bw-mini-card"><div class="bw-mini-icon">📈</div><div class="bw-mini-title">Understand changes</div><div class="bw-mini-copy">Compare monthly usage and identify bill increases worth checking.</div></div>', unsafe_allow_html=True)
with quick3:
    st.markdown('<div class="bw-mini-card"><div class="bw-mini-icon">💡</div><div class="bw-mini-title">Discover savings</div><div class="bw-mini-copy">Estimate appliance consumption and explore practical energy-saving tips.</div></div>', unsafe_allow_html=True)
st.warning("OCR suggestions are not guaranteed. Check the highlighted source text and original bill before saving any month, kWh or payable amount.")
st.info("Auto-fill confidence depends on PDF clarity, language pack and bill layout. If the source line is unclear, correct the field manually rather than trusting the suggestion.")

# --------------------------- CONSTANTS --------------------------------
LANGUAGES = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin", "Gujarati": "guj",
    "Bengali": "ben", "Tamil": "tam", "Telugu": "tel", "Kannada": "kan",
    "Malayalam": "mal", "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep"
}
DISCOMS = [
    "Not sure / Other", "MSEDCL / Mahavitaran (Maharashtra)",
    "Adani Electricity Mumbai", "Tata Power", "BEST (Mumbai)", "Torrent Power",
    "GUVNL / Gujarat DISCOM", "BESCOM (Karnataka)", "TANGEDCO (Tamil Nadu)",
    "KSEB (Kerala)", "TGSPDCL (Telangana)", "APSPDCL / APEPDCL (Andhra Pradesh)",
    "TPDDL / BSES (Delhi)", "UPPCL (Uttar Pradesh)", "WBSEDCL (West Bengal)",
    "Bihar DISCOM", "JVVNL / AVVNL / JDVVNL (Rajasthan)", "Other Indian DISCOM"
]
STATES = [
    "Not selected", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Puducherry", "Chandigarh", "Andaman and Nicobar Islands",
    "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep"
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
NUMBER_RE = re.compile(r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
CURRENCY_RE = re.compile(r"(?:₹|Rs\.?|INR|रु\.?|रुपये)\s*[.):：]?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)

# --------------------------- SESSION -----------------------------------
for key, default in {
    "bill_records": [], "chat": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --------------------------- OCR HELPERS -------------------------------
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
    bad_markers = ["�", "□", "Ã", "Â", "â€", "ï»¿"]
    if any(marker in text for marker in bad_markers):
        return False
    letters = [ch for ch in text if ch.isalpha()]
    extended = sum(0x00C0 <= ord(ch) <= 0x024F for ch in letters)
    if letters and extended / len(letters) > 0.18:
        return False
    visible = sum(ch.isalnum() or ch in "₹.,:/-%() \n\t" for ch in text)
    return visible / max(len(text), 1) >= 0.70

def ocr_image(image, language_codes, is_msedcl=False):
    """Confidence-aware OCR with at most two bounded passes to limit cloud CPU."""
    if pytesseract is None:
        return "", "pytesseract dependency is missing."
    installed = set(installed_ocr_languages())
    if not installed:
        return "", "Tesseract engine or traineddata is unavailable on the server."

    if is_msedcl and {"mar", "eng"}.issubset(installed):
        primary = "mar+eng"
    elif language_codes in installed and "eng" in installed:
        primary = language_codes if language_codes == "eng" else f"{language_codes}+eng"
    elif language_codes in installed:
        primary = language_codes
    elif "eng" in installed:
        primary = "eng"
    else:
        return "", f"Requested language {language_codes} is not installed."

    best_text, best_score, best_conf = "", -1.0, 0.0
    errors = []
    for psm, timeout_s in [(6, 18), (11, 12)]:
        try:
            data = pytesseract.image_to_data(
                image, lang=primary, config=f"--oem 1 --psm {psm}",
                output_type=pytesseract.Output.DICT, timeout=timeout_s
            )
            words, confidences = [], []
            for word, conf in zip(data.get("text", []), data.get("conf", [])):
                word = str(word).strip()
                try:
                    confidence = float(conf)
                except (TypeError, ValueError):
                    confidence = -1
                if word and confidence >= 0:
                    words.append(word)
                    confidences.append(confidence)
            result = " ".join(words).strip()
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            # Prefer readable text with stronger OCR confidence, not merely longer noise.
            score = avg_conf + min(len(result), 500) / 100
            if result and score > best_score:
                best_text, best_score, best_conf = result, score, avg_conf
            if len(result) >= 45 and avg_conf >= 58:
                return result, f"OCR text extracted; average word confidence {avg_conf:.0f}% (PSM {psm}). Verify fields."
        except Exception as exc:
            errors.append(type(exc).__name__)
    if best_text:
        return best_text, f"Partial OCR; average word confidence {best_conf:.0f}%. Please verify all fields."
    return "", "OCR returned no readable text. " + ", ".join(errors)

@st.cache_data(show_spinner=False, max_entries=64)
def cached_page_ocr(png_bytes, language_codes, is_msedcl):
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    return ocr_image(preprocess(image), language_codes, is_msedcl)

def _read_pdf_bytes(file_bytes, language_codes, force_ocr, dpi, filename=""):
    if fitz is None:
        return "", "PyMuPDF is missing. Check requirements.txt."
    pages, notes = [], []
    is_msedcl = "msedcl" in (filename or "").lower()
    scale_map = {1: 1.15, 2: 1.35, 3: 1.60}
    scale = scale_map.get(int(dpi), 1.35)
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            if len(pdf) == 0:
                return "", "PDF has no pages."
            # Electricity bill information is usually on the first pages.
            total = min(len(pdf), 3)
            progress = st.progress(0)
            status = st.status("Preparing PDF...", expanded=True)
            for i in range(total):
                page = pdf[i]
                status.update(label=f"Processing page {i + 1} of {total}...")
                embedded = (page.get_text("text") or "").strip()
                if not force_ocr and readable_embedded_text(embedded):
                    pages.append(embedded)
                    notes.append(f"Page {i+1}: embedded text used.")
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    scanned, note = cached_page_ocr(
                        pix.tobytes("png"), language_codes, is_msedcl
                    )
                    pages.append(scanned or embedded)
                    notes.append(f"Page {i+1}: {note}")
                progress.progress((i + 1) / total)
            status.update(label="PDF processing finished.", state="complete", expanded=False)
            if len(pdf) > total:
                notes.append(f"Only first {total} pages processed for speed.")
        return "\n\n".join(pages), " | ".join(notes)
    except Exception as exc:
        return "", f"PDF error: {type(exc).__name__}: {exc}"

def read_pdf_cached(file_bytes, language_codes, force_ocr, dpi, filename=""):
    # Do not cache this wrapper: it renders Streamlit progress/status widgets.
    # The expensive per-page OCR result is cached by cached_page_ocr().
    return _read_pdf_bytes(file_bytes, language_codes, force_ocr, dpi, filename)

@st.cache_data(show_spinner=False, max_entries=64)
def read_image_cached(file_bytes, language_codes, filename=""):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return ocr_image(preprocess(image), language_codes, "msedcl" in filename.lower())
    except Exception as exc:
        return "", f"Image reading error: {type(exc).__name__}: {exc}"

def read_file(upload, language_codes, force_ocr, dpi):
    data = upload.getvalue()
    if Path(upload.name).suffix.lower() == ".pdf":
        return read_pdf_cached(data, language_codes, force_ocr, dpi, upload.name)
    return read_image_cached(data, language_codes, upload.name)

# --------------------------- FIELD EXTRACTION --------------------------
def parse_num(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None

def find_labeled_value(text, patterns, kind="number"):
    lines = [
        re.sub(r"\s+", " ", ln).strip()
        for ln in (text or "").replace("\u200b", "").replace("\ufeff", "").splitlines()
        if ln.strip()
    ]
    for i, line in enumerate(lines):
        for pattern in patterns:
            match = re.search(pattern, line, re.I)
            if not match:
                continue
            candidates = [line[match.end():]] + lines[i+1:i+3]
            for candidate in candidates:
                values = (CURRENCY_RE.findall(candidate) or NUMBER_RE.findall(candidate)) if kind == "amount" else NUMBER_RE.findall(candidate)
                parsed = [parse_num(v) for v in values]
                parsed = [v for v in parsed if v is not None and v > 0]
                if parsed:
                    return parsed[0], candidate[:180]

    if kind == "number":
        for i, line in enumerate(lines):
            if "एकूण वापर" in line or ("चालु रिडिंग" in line and "मागील" in line):
                for row in lines[i+1:i+4]:
                    vals = [parse_num(v) for v in NUMBER_RE.findall(row)]
                    vals = [v for v in vals if v is not None and 0 < v < 1000]
                    if vals:
                        return vals[-1], row[:180]
    return None, ""

def extract_amount_candidates(text):
    found = []
    for line in (text or "").splitlines():
        for value in CURRENCY_RE.findall(line):
            number = parse_num(value)
            if number is not None and 1 <= number <= 10_000_000:
                found.append({"Candidate amount (₹)": number, "Source line": line.strip()[:180]})
    return pd.DataFrame(found).drop_duplicates() if found else pd.DataFrame()

def guess_month(text, filename):
    months = "January|February|March|April|May|June|July|August|September|October|November|December"
    name = Path(filename).stem
    code = re.search(r"(?:^|[_-])(\d{2})(0[1-9]|1[0-2])(?:[_-]|$)", name)
    if code and "msedcl" in name.lower():
        return datetime(2000 + int(code.group(1)), int(code.group(2)), 1).strftime("%B %Y")
    match = re.search(
        rf"(?:billing\s*(?:month|period)|bill\s*(?:month|period|for))[^\n]{{0,50}}?\b({months})\s*,?\s*(20\d{{2}})\b",
        text or "", re.I
    )
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    match = re.search(rf"\b({months})\s*,?\s*(20\d{{2}})\b", text or "", re.I)
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    return ""

# --------------------------- BILL REVIEW -------------------------------
def bill_form(upload, idx, text, note):
    st.caption(note)
    with st.expander("View extracted text", expanded=False):
        st.text_area("OCR output — verify it", text[:15000], height=180, key=f"text_{idx}")

    amount, amount_evidence = find_labeled_value(text, AMOUNT_LABELS, "amount")
    units, units_evidence = find_labeled_value(text, UNITS_LABELS, "number")
    month_guess = guess_month(text, upload.name)
    candidates = extract_amount_candidates(text)

    st.markdown("**Review and correct detected details**")
    c1, c2 = st.columns(2)
    with c1:
        month = st.text_input("Billing month", value=month_guess, key=f"month_{idx}", placeholder="e.g. October 2026")
        amount_value = st.number_input("Final payable amount (₹)", min_value=0.0, value=float(amount or 0), step=10.0, key=f"amount_{idx}")
        if amount is None:
            st.warning("Payable amount not confidently detected. Check the original bill.")
        st.caption("Amount evidence: " + (amount_evidence or "Not confidently found"))
    with c2:
        units_value = st.number_input("Units consumed (kWh)", min_value=0.0, value=float(units or 0), step=1.0, key=f"units_{idx}")
        if units is None:
            st.warning("Units not confidently detected. Check the original bill.")
        st.caption("Units evidence: " + (units_evidence or "Not confidently found"))

    if amount is None and not candidates.empty:
        st.warning("Candidate amounts are not confirmed payable amounts. Check the final payable line on the bill.")
        st.dataframe(candidates, use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)
    with c3:
        discom = st.selectbox("Electricity company / DISCOM", DISCOMS, key=f"discom_{idx}",
                              index=1 if "msedcl" in upload.name.lower() else 0)
    with c4:
        state = st.selectbox("State / UT", STATES, key=f"state_{idx}",
                             index=14 if "msedcl" in upload.name.lower() else 0)

    if st.button("Save verified bill", key=f"save_{idx}", type="primary"):
        if not month.strip() or amount_value <= 0 or units_value <= 0:
            st.error("Enter valid month, payable amount and kWh from the original bill before saving.")
        elif any(r["Billing month"].lower() == month.strip().lower() for r in st.session_state.bill_records):
            st.error("This billing month is already saved.")
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

# --------------------------- SIDEBAR -----------------------------------
with st.sidebar:
    st.header("Bill settings")
    chosen_language = st.selectbox("Main bill language", list(LANGUAGES), index=0)
    force_ocr = st.checkbox("Force OCR for scanned/garbled PDFs", value=False)
    dpi = st.slider("PDF OCR quality (higher = slower)", 1, 3, 2)
    st.caption("Digital PDFs use embedded text when readable. Scanned PDFs use OCR.")
    installed = set(installed_ocr_languages())
    if pytesseract is None or not installed:
        st.error("OCR engine not available. Check Streamlit Cloud build logs.")
    else:
        expected = {"eng", "mar", "hin", "guj", "ben", "tam", "tel", "kan", "mal", "pan", "urd", "ori", "asm", "nep"}
        ready = sorted(installed.intersection(expected))
        st.success("OCR ready: " + (", ".join(ready) if ready else "No supported language data"))
    st.caption("MSEDCL filename detection enables Marathi + English OCR when both language packs are installed.")

language_code = LANGUAGES[chosen_language]

# --------------------------- UPLOAD & SCAN -----------------------------
st.markdown('<div class="bw-section-kicker">STEP 01</div>', unsafe_allow_html=True)
st.header("Upload your bills")
st.write("Upload up to five monthly bills. Open each bill and click Scan this bill. Verify values before saving.")
uploads = st.file_uploader(
    "Upload up to 5 monthly bills (PDF, PNG, JPG, JPEG)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploads:
    if len(uploads) > 5:
        st.warning("Only the first five files will be processed.")
    st.caption("Each bill is scanned only after you click its Scan button. Repeated page scans are cached.")
    for idx, upload in enumerate(uploads[:5]):
        data = upload.getvalue()
        digest = hashlib.sha256(data).hexdigest()[:16]
        scan_key = f"bill_scan_{digest}"
        with st.expander(f"Bill {idx+1}: {upload.name}", expanded=(idx == 0)):
            if scan_key not in st.session_state:
                if st.button("Scan this bill", key=f"scan_{digest}", type="primary"):
                    with st.spinner("Processing this bill. Large scanned pages may take longer on the free cloud server."):
                        st.session_state[scan_key] = read_file(upload, language_code, force_ocr, dpi)
                    st.rerun()
                st.info("Click Scan this bill to begin. Scan one bill at a time.")
            else:
                extracted_text, scan_note = st.session_state[scan_key]
                if not extracted_text.strip():
                    st.error("No readable text extracted. Check OCR language packs, PDF quality or enter details manually.")
                    if st.button("Clear scan result and retry", key=f"retry_{digest}"):
                        st.session_state.pop(scan_key, None)
                        st.rerun()
                bill_form(upload, digest, extracted_text, scan_note)

# --------------------------- DASHBOARD ---------------------------------
st.divider()
st.markdown('<div class="bw-section-kicker">STEP 02</div>', unsafe_allow_html=True)
st.header("Monthly insights")
if st.session_state.bill_records:
    df = pd.DataFrame(st.session_state.bill_records)
    df["_sort"] = pd.to_datetime(df["Billing month"], format="%B %Y", errors="coerce")
    df = df.sort_values("_sort", na_position="last").drop(columns="_sort")
    st.dataframe(df, use_container_width=True, hide_index=True)

    a, b, c = st.columns(3)
    a.metric("Bills saved", f"{len(df)} / 5")
    b.metric("Average monthly bill", f"₹{df['Bill amount (₹)'].mean():,.2f}")
    c.metric("Average monthly usage", f"{df['Units (kWh)'].mean():,.1f} kWh")

    st.subheader("Monthly bill and usage")
    st.line_chart(df.set_index("Billing month")[["Bill amount (₹)", "Units (kWh)"]])
    left, right = st.columns(2)
    with left:
        st.bar_chart(df.set_index("Billing month")["Bill amount (₹)"])
    with right:
        st.bar_chart(df.set_index("Billing month")["Units (kWh)"])

    if len(df) >= 2:
        compare = df.copy()
        compare["Bill change (%)"] = compare["Bill amount (₹)"].pct_change() * 100
        compare["Usage change (%)"] = compare["Units (kWh)"].pct_change() * 100
        st.subheader("Month-to-month changes")
        st.dataframe(compare[["Billing month", "Bill amount (₹)", "Bill change (%)", "Units (kWh)", "Usage change (%)"]].round(2),
                     use_container_width=True, hide_index=True)
        previous, latest = df.iloc[-2], df.iloc[-1]
        if previous["Units (kWh)"] > 0:
            change = (latest["Units (kWh)"] - previous["Units (kWh)"]) / previous["Units (kWh)"] * 100
            if change >= 20:
                st.error(f"Usage increased by {change:.1f}%. Check appliance use, billing days and meter readings.")
            elif change <= -20:
                st.success(f"Usage decreased by {abs(change):.1f}%.")
            else:
                st.info(f"Usage changed by {change:+.1f}%.")
        if previous["Bill amount (₹)"] > 0:
            bill_change = (latest["Bill amount (₹)"] - previous["Bill amount (₹)"]) / previous["Bill amount (₹)"] * 100
            if bill_change >= 20:
                st.warning(f"Bill amount increased by {bill_change:.1f}%. Check units, tariff, fixed charges, taxes, arrears and billing days.")

    st.download_button("Download analysis CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       "billwise_5_month_analysis.csv", "text/csv")
    if st.button("Clear all saved bills"):
        st.session_state.bill_records = []
        st.rerun()
else:
    st.info("Your comparison dashboard appears after saving verified bills. Add 4–5 different months for a better trend.")

# --------------------------- APPLIANCE ESTIMATOR ------------------------
st.divider()
st.markdown('<div class="bw-section-kicker">STEP 03</div>', unsafe_allow_html=True)
st.header("Appliance energy estimator")
st.caption("Estimates use the wattage and daily hours you enter. A bill alone cannot identify exact appliance-level consumption.")
APPLIANCES = {
    "Geyser / Water Heater": 2000, "Refrigerator": 150, "Washing Machine": 500,
    "Ceiling Fan": 70, "LED Bulb": 9, "Television": 100, "Electric Iron": 1000,
    "Water Pump": 750, "Induction Cooktop": 1800, "Desktop Computer": 200,
    "Microwave": 1200, "Room Heater": 2000, "Air Conditioner": 1500
}
with st.form("appliances"):
    selected = st.multiselect("Select appliances used at home", list(APPLIANCES),
                              default=["Refrigerator", "Ceiling Fan"])
    appliance_rows = []
    for i, name in enumerate(selected):
        st.markdown(f"**{name}**")
        x, y, z = st.columns(3)
        watts = x.number_input("Rated watts", 1, 20000, APPLIANCES[name], key=f"w_{i}")
        hours = y.number_input("Hours used daily", 0.0, 24.0, 4.0, 0.5, key=f"h_{i}")
        quantity = z.number_input("Quantity", 1, 100, 1, key=f"q_{i}")
        appliance_rows.append((name, watts, hours, quantity))
    tariff = st.number_input("Approximate energy rate (₹/kWh)", 0.0, 100.0, 8.0, 0.5)
    submitted = st.form_submit_button("Estimate appliance consumption")
if submitted:
    rows = []
    for name, watts, hours, quantity in appliance_rows:
        units = watts / 1000 * hours * 30 * quantity
        rows.append({"Appliance": name, "Estimated kWh/month": round(units, 2),
                     "Estimated energy cost (₹/month)": round(units * tariff, 2)})
    if rows:
        appliance_df = pd.DataFrame(rows).sort_values("Estimated kWh/month", ascending=False)
        st.dataframe(appliance_df, use_container_width=True, hide_index=True)
        st.bar_chart(appliance_df.set_index("Appliance")["Estimated kWh/month"])
        st.success(f"Highest estimated consumer: {appliance_df.iloc[0]['Appliance']}.")
    else:
        st.info("Select at least one appliance.")

# --------------------------- SAVINGS -----------------------------------
st.divider()
st.header("04 · Smart saving ideas")
st.markdown("""
- **Geyser:** Use a timer and switch it off after heating.
- **Refrigerator:** Check door seals and avoid frequent/long door openings.
- **Lighting:** Use LEDs and turn off unused lights.
- **Washing machine:** Run full loads when practical.
- **Water pump:** Check leaks and avoid unnecessary pumping.
- **Bill review:** Compare billing days, meter readings, tariff, fixed charges, taxes and previous dues.
- **Amount increased but units did not:** Ask the DISCOM to explain tariff changes, arrears, meter reading and adjustments.
""")
if st.session_state.bill_records:
    latest_units = float(st.session_state.bill_records[-1]["Units (kWh)"])
    goal = st.slider("Illustrative monthly usage reduction goal", 0, 30, 10, 5)
    rate = st.number_input("Rate for savings estimate (₹/kWh)", 0.0, 100.0, 8.0, 0.5)
    saved = latest_units * goal / 100
    x, y = st.columns(2)
    x.metric("Potential units saved", f"{saved:.1f} kWh/month")
    y.metric("Potential energy-charge saving", f"₹{saved * rate:.2f}/month")
    st.caption("Illustrative estimate only. Actual savings depend on tariff slabs and fixed charges.")

# --------------------------- BILL SURPRISE FINGERPRINT -----------------
st.divider()
st.header("05 · Bill Surprise Fingerprint")
st.write("Compares the latest two verified bills. This indicates patterns, not proof of cause.")
if len(st.session_state.bill_records) >= 2:
    ordered = pd.DataFrame(st.session_state.bill_records).copy()
    ordered["_date"] = pd.to_datetime(ordered["Billing month"], format="%B %Y", errors="coerce")
    ordered = ordered.sort_values("_date", na_position="last")
    prior, latest = ordered.iloc[-2], ordered.iloc[-1]
    pu, cu = float(prior["Units (kWh)"]), float(latest["Units (kWh)"])
    pb, cb = float(prior["Bill amount (₹)"]), float(latest["Bill amount (₹)"])
    usage_change = (cu - pu) / pu * 100 if pu > 0 else None
    bill_change = (cb - pb) / pb * 100 if pb > 0 else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Latest units", f"{cu:.1f} kWh", None if usage_change is None else f"{usage_change:+.1f}%")
    c2.metric("Latest bill", f"₹{cb:,.2f}", None if bill_change is None else f"{bill_change:+.1f}%")
    current_rate = cb / cu if cu > 0 else 0
    previous_rate = pb / pu if pu > 0 else 0
    c3.metric("Effective bill / unit", f"₹{current_rate:.2f}", f"{current_rate-previous_rate:+.2f}")
    if usage_change is not None and bill_change is not None:
        if bill_change >= 15 and usage_change >= 15:
            st.error("Likely usage-driven pattern: both bill amount and units increased. Check usage and billing days.")
        elif bill_change >= 15 and usage_change < 5:
            st.warning("Amount-up / usage-flat pattern. Check tariff slabs, fixed charges, taxes, arrears, late fees and billing days.")
        elif bill_change >= 15:
            st.warning("Mixed pattern: bill rose more than usage. Review both appliance use and bill components.")
        elif usage_change >= 20:
            st.info("Usage increased noticeably. Check billing days, meter readings and appliance use.")
        else:
            st.success("No large increase detected using the simple comparison thresholds.")
else:
    st.info("Save at least two verified months to generate this comparison.")

# --------------------------- SIMPLE TREND ESTIMATE ----------------------
st.divider()
st.header("06 · Next-month usage estimate")
st.caption("Indicative linear trend only; this is not a trained ML forecast.")
if len(st.session_state.bill_records) >= 3:
    import numpy as np
    forecast_df = pd.DataFrame(st.session_state.bill_records).copy()
    forecast_df["_date"] = pd.to_datetime(forecast_df["Billing month"], format="%B %Y", errors="coerce")
    forecast_df = forecast_df.sort_values("_date")
    y = forecast_df["Units (kWh)"].astype(float).to_numpy()
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    prediction = max(0.0, float(intercept + slope * len(y)))
    st.metric("Indicative next-month units", f"{prediction:.1f} kWh",
              f"{prediction-y[-1]:+.1f} kWh vs latest")
    st.caption("Does not account for weather, season, billing days, tariff, occupancy or appliance changes.")
else:
    st.info("Save at least 3 verified months to see an indicative trend.")

# --------------------------- SUPPORT ASSISTANT --------------------------
st.divider()
st.header("07 · BillWise support assistant")
st.caption("Rule-based starter assistant; not a connected generative AI service.")
def answer_question(question):
    q = question.lower()
    if any(w in q for w in ["language", "marathi", "hindi", "gujarati", "ocr", "text not", "scan"]):
        return "Choose the bill language in the sidebar. Scanned PDFs require Tesseract and the correct traineddata language pack. Always verify extracted fields."
    if any(w in q for w in ["units", "kwh", "consumption", "usage"]):
        return "One electricity unit generally equals 1 kWh. Compare units across bills and account for different billing-day counts."
    if any(w in q for w in ["high bill", "bill increased", "why bill", "expensive", "amount increased"]):
        return "Compare kWh, billing days, meter readings, tariff slabs, fixed charges, taxes, arrears and late fees. Contact your DISCOM if still unclear."
    if any(w in q for w in ["ac", "air conditioner", "geyser", "appliance", "fan", "fridge", "refrigerator"]):
        return "Estimated appliance use = watts ÷ 1000 × hours/day × 30 × quantity. This is an estimate, not a measurement."
    if any(w in q for w in ["save", "reduce", "saving", "less bill"]):
        return "Use LEDs, reduce unnecessary appliance runtime, use a geyser timer, run full washing-machine loads and compare kWh next month."
    if any(w in q for w in ["complaint", "wrong bill", "meter", "dispute"]):
        return "Keep your consumer number and bill ready. Compare meter readings and billing days, then contact the official DISCOM helpline printed on the bill."
    return "Ask me about bill scanning, units, high bills, appliances, savings or billing complaints."

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])
question = st.chat_input("Ask a question about your electricity bill")
if question:
    st.session_state.chat.append({"role": "user", "content": question})
    st.session_state.chat.append({"role": "assistant", "content": answer_question(question)})
    st.rerun()

st.markdown("""
<div style="margin-top:2.5rem;padding:18px 6px;border-top:1px solid #dce8ec;color:#718096;font-size:.82rem;text-align:center;">
<strong style="color:#4F46E5;">BillWise India</strong> · Built to make electricity bills easier to understand.
<br>Always verify extracted values with your original bill. Estimates are informational, not official billing advice.
</div>
""", unsafe_allow_html=True)
