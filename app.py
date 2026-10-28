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

def read_upload(upload, lang_codes, force_ocr, dpi):
    name = upload.name.lower()
    if name.endswith(".pdf"):
        all_text, methods = [], []
        with fitz.open(stream=upload.getvalue(), filetype="pdf") as doc:
            for page in doc:
                embedded = (page.get_text("text") or "").strip()
                # Prefer selectable text, OCR only if it is absent or user requests it.
                if len(embedded) > 60 and not force_ocr:
                    all_text.append(embedded)
                    methods.append("embedded PDF text")
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi, dpi), alpha=False)
                    img = prep_image(Image.open(io.BytesIO(pix.tobytes("png"))))
                    txt, method = ocr_image(img, lang_codes)
                    all_text.append(txt)
                    methods.append(method)
        return "\n".join(all_text), ", ".join(sorted(set(methods)))
    img = prep_image(Image.open(upload))
    return ocr_image(img, lang_codes)

def to_float(raw):
    try:
        return float(raw.replace(",", "").replace("₹", "").strip())
    except Exception:
        return None

def find_label_value(lines, patterns, lookahead=2):
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line, re.I):
                # Avoid reading the digits in the label itself; use a value after the label if possible.
                tail = re.split(pattern, line, maxsplit=1, flags=re.I)[-1]
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
                    return parsed[-1], evidence_line[:180]
    return None, ""

def extract_month(text):
    lines = clean_lines(text)
    for line in lines:
        if re.search(r"(bill\s*month|billing\s*month|billing\s*period|bill\s*date|invoice\s*date)", line, re.I):
            m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s*,?\s*20\d{2}\b", line, re.I)
            if m:
                return m.group(0).replace(",", "")
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s*,?\s*20\d{2}\b", text, re.I)
    return m.group(0).replace(",", "") if m else ""

def parse_msedcl(text):
    lines = clean_lines(text)
    amount, amount_evidence = find_label_value(lines, AMOUNT_LABELS)
    units, units_evidence = find_label_value(lines, UNIT_LABELS)
    # Conservative fallback for the tested legacy MSEDCL sample layout only.
    if amount is None:
        first_page = text.split("\f")[0]
        rs = re.findall(r"Rs\.\s*([\d,]+\.\d{2})", first_page, flags=re.I)
        if rs:
            amount = to_float(rs[0])
            amount_evidence = f"Fallback: first Rs. amount in tested MSEDCL layout ({rs[0]}); verify carefully"
    if units is None and "BILL OF SUPPLY" in text.upper():
        nums = []
        for line in lines:
            if re.fullmatch(r"\d{1,5}(?:\.\d+)?", line):
                nums.append(float(line))
        for i in range(max(0, len(nums)-2)):
            if nums[i] == nums[i+2] and nums[i+1] == 0 and 0 < nums[i] <= 2000:
                units = nums[i]
                units_evidence = f"Fallback: repeated value in tested MSEDCL-style consumption table ({units:g}); verify carefully"
                break
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
            if is_msedcl:
                amount_guess, units_guess, amount_ev, units_ev = parse_msedcl(text)
                parser = "MSEDCL-specific + general labels"
            else:
                amount_guess, units_guess, amount_ev, units_ev = parse_general(text)
                parser = "General label-based extraction"
            st.caption(f"Read method: {method} · Parser: {parser}")
            with st.expander("Show text read from this bill"):
                st.text_area("Extracted text", text, height=180, key=f"raw_{idx}")
            if amount_guess is None or units_guess is None:
                st.warning("One or more values could not be identified confidently. Enter them manually from the original bill.")
            else:
                st.success("Candidate values found. Verify them against the original bill before saving.")
            col1, col2 = st.columns(2)
            with col1:
                month_guess = extract_month(text)
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
