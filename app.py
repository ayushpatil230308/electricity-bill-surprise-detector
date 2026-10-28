import io
import re
from datetime import datetime
from pathlib import Path

import fitz
import pandas as pd
import pytesseract
import streamlit as st
from PIL import Image, ImageEnhance, ImageOps

st.set_page_config(page_title="BillWise India", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container{max-width:1250px;padding-top:1.4rem}
.hero{padding:1.25rem 1.4rem;border:1px solid rgba(128,128,128,.3);border-radius:18px;margin-bottom:1rem}
.muted{opacity:.8;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>⚡ BillWise India</h1>
<p><b>Multilingual electricity-bill reader, usage analyzer, appliance estimator and savings coach.</b></p>
<p class="muted">Upload a bill, verify the extracted fields, compare usage, estimate appliance energy, and get practical savings guidance.</p>
</div>
""", unsafe_allow_html=True)

st.warning("Reliability notice: extraction results are candidates, not official readings. Verify the month, amount and kWh against the original bill before saving. A bill alone cannot identify the exact appliance consuming electricity.")

LANGS = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin", "Gujarati": "guj",
    "Bengali": "ben", "Tamil": "tam", "Telugu": "tel", "Kannada": "kan",
    "Malayalam": "mal", "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep", "Sanskrit": "san"
}
PROVIDERS = [
    "Auto-detect / Other", "MSEDCL / Mahavitaran", "Adani Electricity", "Tata Power",
    "BEST Mumbai", "BESCOM", "TANGEDCO", "BSES", "Torrent Power", "Other provider"
]
AMOUNT_PATTERNS = [
    r"total\s*amount\s*due", r"net\s*amount\s*payable", r"amount\s*payable",
    r"amount\s*due", r"bill\s*amount", r"total\s*bill", r"net\s*bill\s*amount",
    r"current\s*bill\s*amount", r"payable\s*amount", r"grand\s*total",
    r"total\s*payable", r"bill\s*total", r"amount\s*to\s*be\s*paid"
]
UNIT_PATTERNS = [
    r"units?\s*consumed", r"consumption\s*(?:units|kwh)", r"energy\s*consumed",
    r"consumed\s*units", r"total\s*consumption", r"units?\s*\(\s*kwh\s*\)",
    r"kwh\s*consumed", r"consumption\s*in\s*kwh", r"active\s*energy\s*\(\s*kwh\s*\)",
    r"energy\s*\(\s*kwh\s*\)", r"billable\s*units"
]
NUM = re.compile(r"(?<![A-Za-z])(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)(?![A-Za-z])", re.I)

with st.sidebar:
    st.header("Bill reading settings")
    provider = st.selectbox("Electricity provider", PROVIDERS)
    selected_languages = st.multiselect("OCR languages", list(LANGS), default=["English", "Marathi", "Hindi"])
    force_ocr = st.checkbox("Force OCR even when PDF text exists", value=False)
    dpi = st.slider("OCR quality", min_value=2, max_value=4, value=3)
    st.caption("Choose the language(s) visible on the bill. OCR language packs are installed by packages.txt; some hosting builds may not provide every pack.")

if "bill_records" not in st.session_state:
    st.session_state.bill_records = []
if "support_chat" not in st.session_state:
    st.session_state.support_chat = []

def clean_lines(text):
    return [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]

def text_quality(text):
    if not text or len(text.strip()) < 45:
        return False
    t = text.strip()
    printable = sum(ch.isalnum() or ch in "₹.,:/-%() \n\t" for ch in t)
    replacement = t.count("\ufffd") + t.count("\u25a1")
    return printable / max(len(t), 1) > 0.65 and replacement < 4

def preprocess_image(img):
    img = ImageOps.grayscale(img)
    img = ImageOps.autocontrast(img)
    return ImageEnhance.Contrast(img).enhance(1.45)

def ocr_image(img, lang_codes):
    attempts = []
    if lang_codes:
        attempts.append(lang_codes)
    if "eng" not in attempts:
        attempts.append("eng")
    for lang in attempts:
        try:
            txt = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
            if txt.strip():
                return txt, f"Tesseract OCR ({lang})"
        except Exception:
            continue
    return "", "OCR unavailable (selected language packs may be missing)"

def read_upload(upload, lang_codes, force_ocr, dpi):
    suffix = Path(upload.name).suffix.lower()
    if suffix == ".pdf":
        all_text, methods = [], []
        with fitz.open(stream=upload.getvalue(), filetype="pdf") as doc:
            for page in doc:
                embedded = (page.get_text("text") or "").strip()
                should_ocr = force_ocr or not text_quality(embedded)
                # Legacy multilingual bills can have a text layer that exists but is garbled.
                # OCR is attempted when English labels are mostly absent.
                if not should_ocr:
                    english_labels = any(k in embedded.lower() for k in
                        ["amount", "payable", "consumption", "units", "kwh", "bill of supply", "total"])
                    if not english_labels and len(re.findall(r"\d", embedded)) < 10:
                        should_ocr = True
                if should_ocr:
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi, dpi), alpha=False)
                    img = preprocess_image(Image.open(io.BytesIO(pix.tobytes("png"))))
                    ocr_text, method = ocr_image(img, lang_codes)
                    all_text.append(embedded + "\n\n[OCR TEXT]\n" + ocr_text)
                    methods.extend(["Embedded PDF text" if embedded else "", method])
                else:
                    all_text.append(embedded)
                    methods.append("Embedded PDF text")
        return "\n\n".join(x for x in all_text if x.strip()), " + ".join(sorted(set(x for x in methods if x)))
    img = preprocess_image(Image.open(upload))
    return ocr_image(img, lang_codes)

def parse_number(s):
    try:
        return float(s.replace(",", "").replace("₹", "").strip())
    except Exception:
        return None

def label_value(text, patterns, lookahead=2):
    lines = clean_lines(text)
    for i, line in enumerate(lines):
        for pat in patterns:
            m = re.search(pat, line, re.I)
            if not m:
                continue
            candidates = NUM.findall(line[m.end():])
            evidence = line
            if not candidates:
                for nextline in lines[i+1:i+1+lookahead]:
                    candidates = NUM.findall(nextline)
                    if candidates:
                        evidence = f"{line} | {nextline}"
                        break
            values = [parse_number(v) for v in candidates]
            values = [v for v in values if v is not None]
            if values:
                return values[-1], evidence[:180]
    return None, ""

def coordinate_msedcl(pdf_bytes):
    """Parser for the tested 575x822, two-page MSEDCL PDF template."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if len(doc) < 2 or abs(doc[0].rect.width - 575) > 8:
                return None, None, "", "", ""
            p1, p2 = doc[0], doc[1]
            w1, w2 = p1.get_text("words"), p2.get_text("words")
            # The tested template's top-right first date is bill issue month.
            dates = []
            for w in w1:
                x0, y0, x1, y1, word = w[:5]
                if x0 > 500 and 65 <= y0 <= 82 and re.fullmatch(r"\d{2}-\d{2}-\d{4}", word):
                    dates.append((abs(y0 - 72), word))
            month, month_ev = "", ""
            if dates:
                date_text = sorted(dates)[0][1]
                month = datetime.strptime(date_text, "%d-%m-%Y").strftime("%B %Y")
                month_ev = f"Bill date used for month: {date_text}"
            # Consumption row in the tested template: three columns e.g. 89, 0, 89.
            row_numbers = []
            for w in w1:
                x0, y0, x1, y1, word = w[:5]
                if 350 <= x0 <= 390 and 270 <= y0 <= 285 and re.fullmatch(r"\d{1,4}", word):
                    v = int(word)
                    if 1 <= v <= 5000:
                        row_numbers.append((x0, v))
            units, units_ev = (None, "")
            if row_numbers:
                units = sorted(row_numbers, key=lambda z: z[0])[-1][1]
                units_ev = f"MSEDCL consumption table candidate: {units} kWh"
            # Summary page: total current bill value in the tested layout.
            vals = []
            for w in w2:
                x0, y0, x1, y1, word = w[:5]
                if x0 >= 505 and 218 <= y0 <= 229 and re.fullmatch(r"\d[\d,]*\.\d{2}", word):
                    v = parse_number(word)
                    if v is not None and 1 <= v <= 100000:
                        vals.append((x0, v))
            amount, amount_ev = (None, "")
            if vals:
                amount = sorted(vals, key=lambda z: z[0])[-1][1]
                amount_ev = f"MSEDCL summary-table candidate: ₹{amount:.2f}"
            if not any(v is not None for v in (amount, units, month)):
                return None, None, "", "", ""
            return amount, units, amount_ev, units_ev, month
    except Exception:
        return None, None, "", "", ""

def extract_month(text, filename=""):
    # Prefer a readable month-year in text.
    month_names = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    m = re.search(rf"\b{month_names}\s*,?\s*20\d{{2}}\b", text, re.I)
    if m:
        return m.group(0).replace(",", "")
    # Then prefer dates with a billing period end date, if a label exists.
    lines = clean_lines(text)
    for i, line in enumerate(lines):
        if re.search(r"bill\s*period|billing\s*period|period\s*from|reading\s*date", line, re.I):
            joined = " ".join(lines[i:i+3])
            dates = re.findall(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b", joined)
            if dates:
                try:
                    dt = datetime.strptime(dates[-1].replace("/", "-"), "%d-%m-%Y")
                    return dt.strftime("%B %Y")
                except Exception:
                    pass
    # MSEDCL filename code fallback: _YYMM_
    m = re.search(r"_(\d{2})(0[1-9]|1[0-2])_", filename)
    if m:
        return datetime(2000 + int(m.group(1)), int(m.group(2)), 1).strftime("%B %Y")
    return ""

def parse_bill(upload, text, provider_name):
    is_msedcl = provider_name == "MSEDCL / Mahavitaran" or any(
        x in (upload.name + " " + text[:2500]).upper() for x in ["MSEDCL", "MAHADISCOM", "MAHAVITARAN"]
    )
    if is_msedcl and upload.name.lower().endswith(".pdf"):
        amount, units, amount_ev, units_ev, month = coordinate_msedcl(upload.getvalue())
        if amount is not None or units is not None or month:
            return amount, units, amount_ev, units_ev, month, "MSEDCL layout-aware"
    amount, amount_ev = label_value(text, AMOUNT_PATTERNS)
    units, units_ev = label_value(text, UNIT_PATTERNS)
    month = extract_month(text, upload.name)
    return amount, units, amount_ev, units_ev, month, "Multilingual text/OCR labels"

def anomaly_messages(amount, units, records):
    out = []
    if amount > 0 and units > 0:
        ratio = amount / units
        if ratio < 1 or ratio > 50:
            out.append(("warning", f"Amount divided by units is ₹{ratio:.2f}/kWh. This is only a rough ratio including charges; verify the bill."))
    if units > 3000:
        out.append(("warning", "Usage exceeds 3,000 kWh. Verify the value and property type."))
    if records:
        prev = records[-1]
        for val, old, label in [(units, float(prev["Units (kWh)"]), "consumption"),
                                (amount, float(prev["Bill amount (₹)"]), "bill amount")]:
            if old > 0 and val > 0 and abs((val-old)/old*100) >= 50:
                out.append(("warning", f"{label.capitalize()} changed by {(val-old)/old*100:+.0f}% versus the last saved bill. This is a review alert, not proof of an error."))
    return out

st.header("1. Upload and verify electricity bills")
uploads = st.file_uploader("Upload PDF, JPG, JPEG or PNG bills", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

if uploads:
    lang_codes = "+".join(LANGS[x] for x in selected_languages) if selected_languages else "eng"
    for idx, upload in enumerate(uploads):
        with st.expander(f"Review: {upload.name}", expanded=(idx == 0)):
            try:
                text, read_method = read_upload(upload, lang_codes, force_ocr, dpi)
            except Exception as e:
                st.error(f"Could not read this file: {e}")
                continue
            amount_guess, units_guess, amount_ev, units_ev, month_guess, parser = parse_bill(upload, text, provider)
            st.caption(f"Read method: {read_method} · Parser: {parser}")
            with st.expander("Show extracted text/OCR for troubleshooting"):
                st.text_area("Text read from bill", text[:12000], height=200, key=f"text_{idx}")
            if amount_guess is None or units_guess is None or not month_guess:
                st.warning("Some fields could not be read confidently. Please verify and fill any missing values from the original bill; the app will not silently guess.")
            else:
                st.success("Candidate values extracted. Verify each field against the original bill before saving.")
            c1, c2 = st.columns(2)
            with c1:
                month = st.text_input("Billing month", value=month_guess, key=f"month_{idx}")
                amount = st.number_input("Total bill amount (₹)", min_value=0.0, value=float(amount_guess or 0), step=10.0, key=f"amount_{idx}")
                st.caption("Evidence: " + (amount_ev or "No matching label found"))
            with c2:
                units = st.number_input("Units consumed (kWh)", min_value=0.0, value=float(units_guess or 0), step=1.0, key=f"units_{idx}")
                st.caption("Evidence: " + (units_ev or "No matching label found"))
            for level, msg in anomaly_messages(amount, units, st.session_state.bill_records):
                st.warning(msg) if level == "warning" else st.info(msg)
            if st.button("Save verified bill", key=f"save_{idx}", type="primary"):
                if not month.strip() or amount <= 0 or units <= 0:
                    st.error("Enter a month, positive amount and positive kWh after checking the original bill.")
                elif any(r["Bill month"].lower() == month.strip().lower() for r in st.session_state.bill_records):
                    st.error("This month is already saved. Clear session history before replacing it.")
                else:
                    st.session_state.bill_records.append({
                        "Bill month": month.strip(), "Bill amount (₹)": float(amount),
                        "Units (kWh)": float(units), "Provider": provider, "Source file": upload.name
                    })
                    st.success("Saved for this session only.")

st.divider()
st.header("2. Bill history and comparison")
if st.session_state.bill_records:
    df = pd.DataFrame(st.session_state.bill_records)
    df["_sort"] = pd.to_datetime(df["Bill month"], errors="coerce")
    df = df.sort_values("_sort").drop(columns="_sort")
    st.dataframe(df, use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    with a:
        st.subheader("Monthly bill amount (₹)")
        st.bar_chart(df.set_index("Bill month")["Bill amount (₹)"])
    with b:
        st.subheader("Monthly usage (kWh)")
        st.bar_chart(df.set_index("Bill month")["Units (kWh)"])
    if len(df) >= 2:
        old, new = df.iloc[-2], df.iloc[-1]
        x, y, z = st.columns(3)
        x.metric("Latest bill", f"₹{new['Bill amount (₹)']:,.2f}")
        y.metric("Latest usage", f"{new['Units (kWh)']:,.0f} kWh")
        if old["Units (kWh)"] > 0:
            z.metric("Usage change", f"{(new['Units (kWh)']-old['Units (kWh)'])/old['Units (kWh)']*100:+.1f}%")
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8-sig"), "billwise_report.csv", "text/csv")
    if st.button("Clear session bill history"):
        st.session_state.bill_records = []
        st.rerun()
else:
    st.info("Save verified bills to see month-to-month comparisons.")

st.divider()
st.header("3. High-energy appliance estimator")
st.write("Estimate which appliances may use the most energy from rated power and hours of use. This is an estimate, not a measurement from the bill.")
appliance_defaults = {
    "Air conditioner (AC)": 1500, "Water geyser": 2000, "Refrigerator": 150,
    "Washing machine": 500, "Microwave": 1200, "Electric iron": 1000,
    "Water pump": 750, "Ceiling fan": 70, "LED bulb": 9, "Desktop computer": 200,
    "Television": 100, "Induction cooktop": 1800, "Other appliance": 500
}
with st.form("appliance_form"):
    selected_appliances = st.multiselect("Choose appliances in your home", list(appliance_defaults),
        default=["Air conditioner (AC)", "Water geyser", "Refrigerator", "Ceiling fan"])
    appliance_rows = []
    for i, name in enumerate(selected_appliances):
        cols = st.columns([2, 1, 1, 1])
        cols[0].markdown(f"**{name}**")
        watts = cols[1].number_input("Rated watts", min_value=1, max_value=20000,
            value=appliance_defaults[name], key=f"w_{i}_{name}")
        hours = cols[2].number_input("Hours/day", min_value=0.0, max_value=24.0,
            value=4.0 if "AC" in name else (1.0 if "geyser" in name.lower() else 8.0),
            step=0.5, key=f"h_{i}_{name}")
        quantity = cols[3].number_input("Quantity", min_value=1, max_value=100, value=1, key=f"q_{i}_{name}")
        appliance_rows.append((name, watts, hours, quantity))
    tariff = st.number_input("Approximate energy rate (₹/kWh)", min_value=0.0, max_value=100.0, value=8.0, step=0.5)
    submitted = st.form_submit_button("Estimate appliance usage")
if submitted and appliance_rows:
    results = []
    for name, watts, hours, quantity in appliance_rows:
        kwh = watts / 1000 * hours * 30 * quantity
        results.append({"Appliance": name, "Estimated kWh/month": round(kwh, 2),
                        "Estimated energy cost (₹)": round(kwh * tariff, 2)})
    adf = pd.DataFrame(results).sort_values("Estimated kWh/month", ascending=False)
    st.dataframe(adf, use_container_width=True, hide_index=True)
    st.bar_chart(adf.set_index("Appliance")["Estimated kWh/month"])
    top = adf.iloc[0]
    st.info(f"Highest estimated user-entered appliance: {top['Appliance']} at {top['Estimated kWh/month']:.1f} kWh/month. Verify actual power and hours; AC input varies with model, temperature and compressor cycling.")
    st.caption("Formula: kWh/month = watts ÷ 1000 × hours/day × 30 × quantity. Cost estimate excludes fixed charges, taxes and tariff slabs.")
else:
    st.caption("Choose appliances, enter the wattage printed on the label/manual and typical hours of use, then submit.")

st.divider()
st.header("4. Electricity savings coach")
st.markdown("""
- **Air conditioner:** set a comfortable temperature (often around 24–26°C), clean filters, close doors/windows and use a fan to improve comfort at a higher setpoint.
- **Geyser:** use a timer, heat only the water needed, and switch it off after use.
- **Refrigerator:** keep door seals in good condition, avoid frequent long door openings, and allow airflow around the appliance.
- **Fans and lights:** use LEDs, switch off unused lights/fans and consider efficient fan models.
- **Washing machine:** run full loads when practical and use suitable eco/cold-water modes.
- **General:** compare kWh as well as rupees. Billing days, arrears, tariff slabs, taxes and fixed charges can change the bill independently of usage.
""")
if st.session_state.bill_records:
    latest_units = float(st.session_state.bill_records[-1]["Units (kWh)"])
    st.info(f"Latest saved usage is {latest_units:.1f} kWh. Set a personal reduction target below to estimate possible energy savings.")
    target = st.slider("Target reduction in monthly usage (%)", 0, 30, 10, 5)
    rate = st.number_input("Approximate marginal rate for savings estimate (₹/kWh)", 0.0, 100.0, 8.0, 0.5, key="savings_rate")
    saved_kwh = latest_units * target / 100
    st.metric("Potential monthly energy-cost reduction (estimate)", f"₹{saved_kwh*rate:,.0f}", f"{saved_kwh:.1f} kWh less")
    st.caption("Illustrative estimate only. Actual savings depend on the tariff slab, appliance behavior and other bill charges.")

st.divider()
st.header("5. Free customer support assistant")
st.write("This support assistant is free and works without an API key. It uses built-in troubleshooting guidance, not a generative AI model.")

def support_answer(q):
    q = q.lower()
    if any(x in q for x in ["high bill", "bill increased", "bill high", "unexpected", "expensive"]):
        return "Compare kWh, billing days, previous/current meter readings, tariff slabs, fixed charges, taxes, arrears and adjustments. A higher rupee amount alone does not prove a fault. If the bill still seems wrong, contact your provider through the official contact details on the bill."
    if any(x in q for x in ["wrong amount", "amount wrong", "incorrect amount", "wrong units", "units wrong", "not detected", "blank", "0.00"]):
        return "Open 'Show extracted text/OCR' and compare the visible bill fields. Confirm the amount due (not a subtotal, paid amount or arrears) and the consumption in kWh (not kW, sanctioned load or meter reading). Correct the fields manually and do not save until verified. If OCR is poor, choose the printed language in the sidebar or try a clearer scan."
    if any(x in q for x in ["ac", "air conditioner", "geyser", "fridge", "refrigerator", "appliance", "device", "which uses"]):
        return "Use the appliance estimator: enter each device's rated watts, hours per day and quantity. The app ranks estimated monthly kWh. It cannot identify an appliance from a household bill alone; actual device-level measurement requires smart plugs or circuit monitoring."
    if any(x in q for x in ["reduce", "save electricity", "saving", "lower bill"]):
        return "Start with the largest estimated kWh appliances. Reduce AC run time or raise its setpoint slightly, use a geyser timer, use LEDs, run full washing-machine loads, and switch off idle devices. Estimated savings are not guaranteed; compare measured kWh across similar billing periods."
    if any(x in q for x in ["pdf", "upload", "language", "marathi", "hindi", "ocr", "scan", "error"]):
        return "Try a readable PDF or a sharp, upright JPG/PNG image. Select the language(s) printed on the bill and enable Force OCR for scanned/garbled PDFs. If a language pack is unavailable on hosting, OCR may fall back to English. Verify extracted fields manually."
    if any(x in q for x in ["complaint", "meter", "dispute", "fault"]):
        return "This website cannot test a physical meter or submit an official complaint. Keep your bill and meter-reading evidence, then contact your electricity provider through official channels."
    return "I can help with bill scanning, language/OCR settings, amount and kWh verification, monthly comparisons, appliance estimates and savings advice. Please don't share consumer numbers, full addresses or payment details here."

for msg in st.session_state.support_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
question = st.chat_input("Ask BillWise Support…")
if question:
    st.session_state.support_chat.append({"role": "user", "content": question})
    answer = support_answer(question)
    st.session_state.support_chat.append({"role": "assistant", "content": answer})
    st.rerun()
if st.button("Clear support conversation"):
    st.session_state.support_chat = []
    st.rerun()

st.divider()
st.caption("Privacy: bills and records are processed in this app session; this prototype does not provide permanent accounts or saved cloud history. Do not upload private bills to public GitHub. Extraction supports multiple languages only when the required OCR language data is available. Test each provider format before public use.")
