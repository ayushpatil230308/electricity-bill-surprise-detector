import io
import re
from datetime import datetime
import pandas as pd
import streamlit as st
import fitz
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

st.set_page_config(page_title="BillWise India | Electricity Bill Detective", page_icon="⚡", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1180px;}
.hero {padding: 1.4rem 1.5rem; border: 1px solid rgba(128,128,128,.28); border-radius: 18px; margin-bottom: 1rem;}
.small-note {font-size: .9rem; opacity: .82;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>⚡ BillWise India</h1><p>Electricity bill reader, bill-change checker, and savings coach.</p><p class="small-note">Designed for multiple Indian providers, with verification steps to help prevent misleading results.</p></div>', unsafe_allow_html=True)

st.warning("Safety first: extracted values are suggestions, not official readings. Check them against the original bill. If a value cannot be identified clearly, enter it manually. This tool cannot confirm meter faults or guarantee savings.")

PROVIDERS = [
    "Auto-detect / Other", "MSEDCL / Mahavitaran", "Adani Electricity", "Tata Power",
    "BEST Mumbai", "BESCOM", "TANGEDCO", "BSES", "Torrent Power", "Other provider"
]
LANGS = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin", "Gujarati": "guj",
    "Bengali": "ben", "Tamil": "tam", "Telugu": "tel", "Kannada": "kan",
    "Malayalam": "mal", "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep"
}
AMOUNT_LABELS = [
    r"total\s*amount\s*due", r"net\s*amount\s*payable", r"amount\s*payable",
    r"amount\s*due", r"bill\s*amount", r"total\s*bill", r"net\s*bill\s*amount",
    r"current\s*bill\s*amount", r"payable\s*amount", r"grand\s*total",
    r"total\s*payable", r"bill\s*total", r"amount\s*to\s*be\s*paid"
]
UNIT_LABELS = [
    r"units?\s*consumed", r"consumption\s*(?:units|kwh)", r"energy\s*consumed",
    r"consumed\s*units", r"total\s*consumption", r"units?\s*\(\s*kwh\s*\)",
    r"kwh\s*consumed", r"consumption\s*in\s*kwh", r"active\s*energy\s*\(\s*kwh\s*\)",
    r"energy\s*\(\s*kwh\s*\)", r"billable\s*units"
]
NUMBER = r"(?<![A-Za-z])(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)(?![A-Za-z])"

with st.sidebar:
    st.header("Reading settings")
    provider = st.selectbox("Electricity provider", PROVIDERS)
    languages = st.multiselect("OCR languages (for scanned/image bills)", list(LANGS), default=["English", "Marathi", "Hindi"])
    force_ocr = st.checkbox("Force OCR", value=False, help="Try this if selectable PDF text is missing or unreadable.")
    dpi = st.slider("OCR quality", 2, 4, 3)
    st.caption("OCR language packs may not all be available on every deployment. English fallback is attempted if selected languages fail.")

if "records" not in st.session_state:
    st.session_state.records = []

def clean_lines(text):
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]

def prep_image(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return ImageEnhance.Contrast(img).enhance(1.4)

def ocr_image(img, lang_codes):
    try:
        return pytesseract.image_to_string(img, lang=lang_codes or "eng", config="--psm 6"), "OCR"
    except Exception:
        try:
            return pytesseract.image_to_string(img, lang="eng", config="--psm 6"), "English OCR fallback"
        except Exception as e:
            return "", f"OCR unavailable: {e}"

def text_quality(text):
    """Conservative quality check: flag empty, very short, replacement-heavy, or garbled text."""
    if not text or len(text.strip()) < 60:
        return False
    t = text.strip()
    replacement = t.count("\ufffd") + t.count("\u25a1")
    # Mixed Marathi/Hindi bills can have non-Latin text legitimately, so don't reject solely for that.
    # Flag pages where letters/digits/punctuation are sparse compared with total length.
    useful = sum(ch.isalnum() or ch in "₹.,:/-%() " for ch in t)
    ratio = useful / max(1, len(t))
    return replacement < 3 and ratio > 0.68

def prep_image(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return ImageEnhance.Contrast(img).enhance(1.5)

def run_ocr(img, lang_codes):
    attempts = []
    for lang in [lang_codes or "eng", "eng"]:
        if lang in attempts:
            continue
        attempts.append(lang)
        try:
            txt = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
            if txt.strip():
                return txt, f"OCR ({lang})"
        except Exception:
            continue
    return "", "OCR unavailable"

def read_upload(upload, lang_codes, force_ocr, dpi):
    """Read embedded text first, but OCR weak text too; combine text and OCR for better numeric recovery."""
    name = upload.name.lower()
    if name.endswith(".pdf"):
        page_texts, methods = [], []
        with fitz.open(stream=upload.getvalue(), filetype="pdf") as doc:
            for page in doc:
                embedded = (page.get_text("text") or "").strip()
                need_ocr = force_ocr or not text_quality(embedded)
                # For multilingual/legacy bills, OCR is also tried when the embedded text has few
                # useful English bill labels. Numeric fields may still be present in embedded text.
                if not need_ocr:
                    has_labels = any(x in embedded.lower() for x in [
                        "amount", "payable", "consumption", "units", "kwh", "bill of supply", "total"
                    ])
                    if not has_labels and any("\u0900" <= ch <= "\u0dff" for ch in embedded):
                        need_ocr = True
                if need_ocr:
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi, dpi), alpha=False)
                    img = prep_image(Image.open(io.BytesIO(pix.tobytes("png"))))
                    ocr_text, method = run_ocr(img, lang_codes)
                    # Keep both sources; parser can use English labels/dates from embedded text and
                    # recover fields that only OCR can read.
                    combined = embedded + "\n\n[OCR TEXT]\n" + ocr_text
                    page_texts.append(combined)
                    methods.extend(["embedded PDF text" if embedded else "", method])
                else:
                    page_texts.append(embedded)
                    methods.append("embedded PDF text")
        return "\n\n".join(x for x in page_texts if x.strip()), " + ".join(sorted(set(x for x in methods if x)))
    img = prep_image(Image.open(upload))
    return run_ocr(img, lang_codes)

def to_float(raw):
    try:
        return float(raw.replace(",", "").replace("₹", "").strip())
    except Exception:
        return None

def find_label_value(lines, patterns, lookahead=2):
    """Only accept numbers tied to a known label; never guess from the first currency number."""
    for i, line in enumerate(lines):
        for pattern in patterns:
            match = re.search(pattern, line, re.I)
            if match:
                tail = line[match.end():]
                vals = re.findall(NUMBER, tail, flags=re.I)
                evidence_line = line
                if not vals:
                    for nxt in lines[i+1:i+1+lookahead]:
                        vals = re.findall(NUMBER, nxt, flags=re.I)
                        if vals:
                            evidence_line = f"{line} | next line: {nxt}"
                            break
                parsed = [to_float(v) for v in vals]
                parsed = [v for v in parsed if v is not None]
                if parsed:
                    # Prefer the last number after a label; labels with multiple numbers should be reviewed.
                    return parsed[-1], evidence_line[:180]
    return None, ""

def extract_month(text):
    lines = clean_lines(text)
    month_names = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    for line in lines:
        if re.search(r"(bill\s*month|billing\s*month|billing\s*period|bill\s*date|invoice\s*date)", line, re.I):
            m = re.search(rf"\b{month_names}\s*,?\s*20\d{{2}}\b", line, re.I)
            if m:
                return m.group(0).replace(",", "")
            m = re.search(r"\b(0?[1-9]|1[0-2])[-/](20\d{2})\b", line)
            if m:
                return datetime(int(m.group(2)), int(m.group(1)), 1).strftime("%B %Y")
    m = re.search(rf"\b{month_names}\s*,?\s*20\d{{2}}\b", text, re.I)
    return m.group(0).replace(",", "") if m else ""

def parse_msedcl_layout(pdf_bytes):
    """Coordinate-aware extraction for the tested two-page MSEDCL bill layout.

    This uses stable positions in the supplied MSEDCL template rather than garbled Marathi
    embedded labels: bill issue date at the top-right of page 1, total consumption in the
    reading table on page 1, and total bill payable in the summary table on page 2.
    Returns candidates plus short evidence strings. None means the layout did not match.
    """
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if len(doc) < 2:
                return None, None, "", "", ""
            page1 = doc[0]
            page2 = doc[1]
            words1 = page1.get_text("words")
            words2 = page2.get_text("words")

            # MSEDCL bill issue date is in a stable top-right box (x > 500, y ~ 72).
            date_candidates = []
            for w in words1:
                x0, y0, x1, y1, word = w[:5]
                if x0 > 500 and 62 <= y0 <= 86 and re.fullmatch(r"\d{2}-\d{2}-\d{4}", word):
                    date_candidates.append((abs(y0 - 72), word))
            month = ""
            if date_candidates:
                date_text = sorted(date_candidates)[0][1]
                dt = datetime.strptime(date_text, "%d-%m-%Y")
                month = dt.strftime("%B %Y")
                month_evidence = f"MSEDCL bill date: {date_text}"
            else:
                month_evidence = ""

            # Total consumption is in the right-most total-usage cell of the reading table.
            # Avoid the nearby multiplier (1.00), current/previous meter readings and the 0 cell.
            unit_candidates = []
            for w in words1:
                x0, y0, x1, y1, word = w[:5]
                if x0 >= 350 and 268 <= y0 <= 291 and re.fullmatch(r"\d{1,4}", word):
                    value = int(word)
                    if 1 <= value <= 5000:
                        unit_candidates.append((x0, value))
            units = None
            units_evidence = ""
            if unit_candidates:
                # The total-consumption cell is the rightmost integer in this row.
                units = sorted(unit_candidates, key=lambda x: x[0])[-1][1]
                units_evidence = f"MSEDCL reading-table total consumption: {units} kWh"

            # Total bill payable is in the summary table on page 2 at x > 500, y ~ 223.
            amount_candidates = []
            for w in words2:
                x0, y0, x1, y1, word = w[:5]
                if x0 >= 505 and 215 <= y0 <= 235 and re.fullmatch(r"\d+\.\d{2}", word):
                    value = float(word.replace(",", ""))
                    if 1 <= value <= 100000:
                        amount_candidates.append((x0, value))
            amount = None
            amount_evidence = ""
            if amount_candidates:
                # The target cell contains one amount in the total-bill-payable row.
                amount = sorted(amount_candidates, key=lambda x: x[0])[-1][1]
                amount_evidence = f"MSEDCL summary-table total bill payable: ₹{amount:.2f}"

            # Treat this as a layout match only if at least two key fields were found.
            matched = sum(v is not None for v in (amount, units, month))
            if matched < 2:
                return None, None, "", "", ""
            return amount, units, amount_evidence, units_evidence, month
    except Exception:
        return None, None, "", "", ""

def parse_msedcl(text):
    lines = clean_lines(text)
    amount, amount_evidence = find_label_value(lines, AMOUNT_LABELS)
    units, units_evidence = find_label_value(lines, UNIT_LABELS)
    # Deliberately do not use "first Rs. amount" as a fallback: it may be a charge/subtotal.
    # If labels are not recoverable, ask the user to verify/enter the values.
    return amount, units, amount_evidence, units_evidence

def parse_general(text):
    lines = clean_lines(text)
    amount, amount_evidence = find_label_value(lines, AMOUNT_LABELS)
    units, units_evidence = find_label_value(lines, UNIT_LABELS)
    return amount, units, amount_evidence, units_evidence

def anomaly_checks(amount, units, history):
    messages = []
    if amount <= 0:
        messages.append(("error", "Bill amount must be greater than zero."))
    if units <= 0:
        messages.append(("error", "Units must be greater than zero."))
    if units > 3000:
        messages.append(("warning", "Usage exceeds 3,000 kWh. This may be valid for some premises, but double-check the bill and premises type."))
    if amount > 100000:
        messages.append(("warning", "Bill amount exceeds ₹1,00,000. Verify the amount and decimal placement."))
    if units > 0 and amount > 0:
        rate = amount / units
        if rate < 1 or rate > 50:
            messages.append(("warning", f"Bill amount per unit is about ₹{rate:.2f}/kWh. This simple ratio includes taxes/charges and is not the tariff; double-check the values."))
    if history and units > 0 and amount > 0:
        prev = history[-1]
        for key, value, label in [
            ("Units (kWh)", units, "consumption"),
            ("Bill amount (₹)", amount, "bill amount")
        ]:
            old = float(prev[key])
            if old > 0:
                change = (value-old)/old*100
                if abs(change) >= 50:
                    messages.append(("warning", f"{label.capitalize()} changed by {change:+.0f}% versus the previous saved bill. This is a review flag, not proof of a billing error."))
    return messages

st.subheader("1. Upload and review a bill")
uploads = st.file_uploader("Upload one or more electricity bills", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

if uploads:
    for idx, upload in enumerate(uploads):
        with st.expander(f"Review: {upload.name}", expanded=(idx == 0)):
            try:
                lang_codes = "+".join(LANGS[x] for x in languages) if languages else "eng"
                text, method = read_upload(upload, lang_codes, force_ocr, dpi)
            except Exception as e:
                st.error(f"Unable to read this file: {e}")
                continue
            if not text.strip():
                st.error("No readable text was found. Try a clearer image or enter details manually.")
                text = ""
            is_msedcl = provider == "MSEDCL / Mahavitaran" or (
                provider == "Auto-detect / Other" and any(x in (text + " " + upload.name).upper() for x in ["MSEDCL", "MAHADISCOM", "MAHAVITARAN"])
            )
            layout_month_guess = ""
            if is_msedcl:
                amount_guess, units_guess, amount_ev, units_ev, layout_month_guess = (None, None, "", "", "")
                if upload.name.lower().endswith(".pdf"):
                    amount_guess, units_guess, amount_ev, units_ev, layout_month_guess = parse_msedcl_layout(upload.getvalue())
                # Coordinate-aware extraction is preferred for the tested two-page MSEDCL template.
                if amount_guess is not None or units_guess is not None:
                    parser = "MSEDCL layout-aware extraction"
                else:
                    amount_guess, units_guess, amount_ev, units_ev = parse_msedcl(text)
                    parser = "MSEDCL label-based fallback"
            else:
                amount_guess, units_guess, amount_ev, units_ev = parse_general(text)
                parser = "General label-based extraction"
            st.caption(f"Read method: {method} · Parser: {parser}")
            with st.expander("Show text read from this bill"):
                st.text_area("Extracted text", text, height=180, key=f"raw_{idx}")
            if amount_guess is None or units_guess is None:
                st.warning("One or more values could not be identified confidently. The app will not guess these values. Enter them from the original bill and verify before saving.")
            else:
                st.success("Candidate values found. Verify them against the original bill before saving.")
            col1, col2 = st.columns(2)
            with col1:
                month_guess = layout_month_guess or extract_month(text)
                month = st.text_input("Billing month (e.g. October 2026)", value=month_guess, key=f"month_{idx}")
                amount = st.number_input("Total bill amount (₹) — verify", min_value=0.0, value=float(amount_guess or 0.0), step=10.0, key=f"amount_{idx}")
                st.caption("Evidence: " + (amount_ev or "No matching label found"))
            with col2:
                units = st.number_input("Units consumed (kWh) — verify", min_value=0.0, value=float(units_guess or 0.0), step=1.0, key=f"units_{idx}")
                st.caption("Evidence: " + (units_ev or "No matching label found"))
            checks = anomaly_checks(amount, units, st.session_state.records)
            for level, message in checks:
                getattr(st, level if level in ("error", "warning", "info", "success") else "info")(message)
            if st.button("Save after checking original bill", key=f"save_{idx}", type="primary"):
                if not month.strip() or amount <= 0 or units <= 0:
                    st.error("Enter a month and positive amount and units after checking the original bill.")
                elif any(r["Bill month"].lower() == month.strip().lower() for r in st.session_state.records):
                    st.error("A bill for this month is already saved. Remove/clear records first if you want to replace it.")
                else:
                    st.session_state.records.append({
                        "Bill month": month.strip(), "Bill amount (₹)": float(amount),
                        "Units (kWh)": float(units), "Provider": provider, "Source file": upload.name
                    })
                    st.success("Saved to this session. No official bill data is changed.")

st.divider()
st.subheader("2. Your bill history")
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    df["_date"] = pd.to_datetime(df["Bill month"], errors="coerce")
    df = df.sort_values("_date", na_position="last").drop(columns=["_date"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    with a:
        st.markdown("**Bill amount (₹)**")
        st.bar_chart(df.set_index("Bill month")["Bill amount (₹)"])
    with b:
        st.markdown("**Consumption (kWh)**")
        st.bar_chart(df.set_index("Bill month")["Units (kWh)"])
    if len(df) >= 2:
        previous, latest = df.iloc[-2], df.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Latest bill", f"₹{latest['Bill amount (₹)']:,.0f}")
        c2.metric("Latest usage", f"{latest['Units (kWh)']:,.0f} kWh")
        if previous["Bill amount (₹)"]:
            pct = (latest["Bill amount (₹)"]-previous["Bill amount (₹)"])/previous["Bill amount (₹)"]*100
            c3.metric("Bill change", f"{pct:+.1f}%")
        st.info("Change flags identify unusual differences only. They do not establish a meter fault, incorrect bill, or cause of the change.")
    st.download_button("Download CSV report", df.to_csv(index=False).encode("utf-8-sig"), "billwise_india_report.csv", "text/csv")
    if st.button("Clear session bill history"):
        st.session_state.records = []
        st.rerun()
else:
    st.info("Your history will appear here after you review and save at least one bill.")

st.subheader("3. Practical savings coach")
st.markdown("""
- Compare consumption in kWh, not just the rupee amount; tariffs, taxes, fixed charges and billing days can change.
- Use LED lighting and energy-saving settings on appliances.
- Switch off appliances when not needed and avoid leaving high-power devices running unnecessarily.
- If usage rises unexpectedly, compare the number of billing days and meter readings first; then contact your electricity provider if the bill still looks incorrect.
- Treat any savings estimate as an estimate unless it is based on measured appliance power, usage time, and the applicable tariff.
""")

with st.expander("How this website handles reliability"):
    st.markdown("""
    - Uses selectable PDF text when available and OCR for scanned pages or images.
    - Uses a dedicated parsing path for the tested MSEDCL-style format and general label matching for other bills.
    - Shows evidence lines where possible and asks users to verify extracted values.
    - Highlights unusual values and changes but does not automatically declare a bill wrong.
    - No machine-learning model is trained in this version; anomaly checks use transparent rules.
    - This is a prototype, not a certified billing system. Some providers, layouts, and language scans need further testing.
    """)


st.divider()
st.divider()
st.header("4. 💬 BillWise Customer Support")
st.write("Free built-in troubleshooting for bill reading, uploads, comparisons, appliance estimates, and electricity-saving questions. No paid AI API or API key is needed.")

def built_in_support_reply(question):
    q = question.lower()
    if any(x in q for x in ["wrong amount", "incorrect amount", "wrong bill amount", "amount is wrong", "bill amount wrong"]):
        return ("Compare the suggested amount with the original bill's 'Total Amount Due', 'Net Amount Payable', or equivalent field. Do not save until corrected. If it keeps reading the wrong number, note the provider name and try a clearer bill.")
    if any(x in q for x in ["unit", "units", "kwh", "consumption"]):
        return ("Check the bill's consumption section and confirm the value is in kWh. Do not confuse current meter reading, previous reading, meter multiplier, or sanctioned load with units consumed. Correct the value manually if it does not match the bill.")
    if any(x in q for x in ["high bill", "bill increased", "too much", "unexpected bill", "expensive"]):
        return ("Compare kWh usage, billing days, meter readings, tariff, fixed charges, taxes, arrears, and adjustments with the previous bill. A higher amount alone does not prove an error. For an unresolved dispute, contact the electricity provider using official details on the bill.")
    if any(x in q for x in ["pdf", "upload", "cannot upload", "can't upload", "error", "not working", "blank"]):
        return ("Try a clear PDF or JPG/PNG image, check that the PDF is not password-protected, and make sure the text is readable. For scanned bills, use a sharper image and select the appropriate OCR languages. Do not upload private bills to a public GitHub repository.")
    if any(x in q for x in ["save", "history", "record", "csv", "download"]):
        return ("Saved records stay in the active app session; permanent account history is not configured. Download the CSV if you need a copy. Session data may be lost if the app restarts.")
    if any(x in q for x in ["save money", "saving", "reduce", "electricity consumption", "electricity usage"]):
        return ("Compare kWh usage rather than only rupees. Use LED lighting, switch off unused appliances, and review high-power appliances and their usage hours. Savings depend on appliance power, time used, and your tariff, so no fixed saving can be guaranteed.")
    if any(x in q for x in ["appliance", "geyser", "refrigerator", "fridge", "fan", "ac", "air conditioner", "device"]):
        return ("To estimate an appliance's electricity use, enter its power in watts and hours used per day. Estimated monthly kWh = watts ÷ 1000 × hours per day × 30. This is an estimate, not a measurement from the bill.")
    if any(x in q for x in ["complaint", "meter fault", "meter problem", "dispute", "wrong reading"]):
        return ("This website can help review bill details, but it cannot verify a physical meter or file an official complaint. Keep a copy of the bill and meter reading, then contact your electricity provider through official channels.")
    return ("I can help with bill uploads, extracting amount or units, monthly comparisons, unusual bill changes, appliance-use estimates, and energy-saving tips. Describe the issue without sharing account numbers, full addresses, phone numbers, or payment details.")

if "support_messages" not in st.session_state:
    st.session_state.support_messages = []
for message in st.session_state.support_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
question = st.chat_input("Ask free BillWise Support…")
if question:
    st.session_state.support_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    answer = built_in_support_reply(question)
    st.session_state.support_messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
if st.button("Clear support chat"):
    st.session_state.support_messages = []
    st.rerun()

st.caption("Privacy: this code keeps records in the current Streamlit session and does not configure permanent storage. Avoid committing real bills to a public repository. Review your hosting provider's privacy terms before inviting the public.")
