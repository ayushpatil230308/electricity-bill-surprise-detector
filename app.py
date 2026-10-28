import io
import re
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

st.set_page_config(page_title="BillWise India", page_icon="⚡", layout="wide")

st.title("⚡ BillWise India")
st.subheader("Electricity Bill Reader & Savings Assistant")
st.write(
    "Upload an electricity bill, review the extracted values, track monthly usage, "
    "and estimate appliance consumption."
)
st.info(
    "Please verify the amount and units against your original bill. OCR can misread "
    "numbers, and this demo does not connect to your electricity provider."
)

LANGUAGES = {
    "English": "eng",
    "Marathi": "mar",
    "Hindi": "hin",
    "Gujarati": "guj",
    "Tamil": "tam",
    "Telugu": "tel",
    "Bengali": "ben",
    "Kannada": "kan",
    "Malayalam": "mal",
    "Punjabi": "pan",
    "Urdu": "urd",
    "Odia": "ori",
    "Assamese": "asm",
    "Nepali": "nep",
    "Sanskrit": "san",
}

AMOUNT_LABELS = [
    "total amount due", "net amount payable", "amount payable",
    "amount due", "bill amount", "total bill", "grand total",
    "total payable", "current bill amount"
]
UNIT_LABELS = [
    "units consumed", "consumed units", "energy consumed",
    "kwh consumed", "billable units", "total consumption",
    "consumption kwh", "units (kwh)"
]

if "records" not in st.session_state:
    st.session_state.records = []

def prep_image(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(1.35)

def ocr_image(image, language_code):
    if pytesseract is None:
        return "", "The pytesseract Python package is not installed."
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception as exc:
        return "", (
            "Tesseract OCR is not installed or unavailable on this server. "
            "Install Tesseract and its language packs. Details: " + str(exc)
        )

    language_code = language_code or "eng"
    candidates = [language_code, "eng"]
    for lang in dict.fromkeys(candidates):
        required = lang.split("+")
        if any(code not in available for code in required):
            continue
        try:
            result = pytesseract.image_to_string(
                image, lang=lang, config="--oem 1 --psm 6"
            ).strip()
            if result:
                return result, f"OCR language used: {lang}"
        except Exception:
            continue

    return "", (
        "No suitable Tesseract language pack was found. "
        "Try English or install the required language pack."
    )

def read_pdf(upload, language_code, force_ocr, dpi):
    if fitz is None:
        return "", "PyMuPDF is missing. Install the requirements.txt packages."
    text_pages = []
    notes = []
    try:
        with fitz.open(stream=upload.getvalue(), filetype="pdf") as doc:
            for page in doc:
                embedded = (page.get_text("text") or "").strip()
                use_ocr = force_ocr or len(embedded) < 40
                if use_ocr:
                    pix = page.get_pixmap(matrix=fitz.Matrix(dpi, dpi), alpha=False)
                    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    ocr_text, note = ocr_image(prep_image(image), language_code)
                    if ocr_text and (force_ocr or len(ocr_text) > len(embedded)):
                        text_pages.append(ocr_text)
                    else:
                        text_pages.append(embedded or ocr_text)
                    notes.append(note)
                else:
                    text_pages.append(embedded)
                    notes.append("Read embedded PDF text")
        return "\n\n".join(text_pages), "; ".join(dict.fromkeys(notes))
    except Exception as exc:
        return "", f"Could not read PDF: {exc}"

def read_upload(upload, language_code, force_ocr, dpi):
    suffix = Path(upload.name).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(upload, language_code, force_ocr, dpi)
    try:
        image = Image.open(upload).convert("RGB")
        return ocr_image(prep_image(image), language_code)
    except Exception as exc:
        return "", f"Could not read image: {exc}"

def parse_number(s):
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None

def find_value(text, labels):
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines() if x.strip()]
    number_pattern = re.compile(r"(?<![A-Za-z])(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
    for i, line in enumerate(lines):
        lower = line.lower()
        if any(label in lower for label in labels):
            match_at = 0
            for label in labels:
                position = lower.find(label)
                if position >= 0:
                    match_at = max(match_at, position + len(label))
            values = number_pattern.findall(line[match_at:])
            evidence = line
            if not values and i + 1 < len(lines):
                values = number_pattern.findall(lines[i + 1])
                evidence = line + " | " + lines[i + 1]
            parsed = [parse_number(v) for v in values]
            parsed = [v for v in parsed if v is not None]
            if parsed:
                return parsed[-1], evidence
    return None, ""

def guess_month(text, filename):
    months = (
        "January|February|March|April|May|June|July|August|"
        "September|October|November|December"
    )
    match = re.search(rf"\b({months})\s*,?\s*(20\d{{2}})\b", text, re.I)
    if match:
        return f"{match.group(1).title()} {match.group(2)}"
    date_match = re.search(r"\b(\d{2})[-/](\d{2})[-/](\d{4})\b", text)
    if date_match:
        day, month, year = map(int, date_match.groups())
        try:
            return datetime(year, month, day).strftime("%B %Y")
        except ValueError:
            pass
    return Path(filename).stem

with st.sidebar:
    st.header("Bill Reading Settings")
    chosen_language = st.selectbox("Main bill language", list(LANGUAGES.keys()), index=0)
    force_ocr = st.checkbox("Force OCR for PDFs", value=False)
    dpi = st.slider("PDF OCR resolution", min_value=2, max_value=4, value=3)
    st.caption("OCR requires Tesseract installed on the hosting system.")

language_code = LANGUAGES[chosen_language]

st.header("1. Upload and review a bill")
uploads = st.file_uploader(
    "Upload PDF, PNG, JPG or JPEG bills",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploads:
    for idx, upload in enumerate(uploads):
        with st.expander(f"Review {upload.name}", expanded=(idx == 0)):
            text, read_note = read_upload(upload, language_code, force_ocr, dpi)
            st.caption(read_note)
            st.text_area("Extracted text (review this carefully)", text[:12000], height=180, key=f"ocr_text_{idx}")

            amount_guess, amount_evidence = find_value(text, AMOUNT_LABELS)
            units_guess, units_evidence = find_value(text, UNIT_LABELS)
            month_guess = guess_month(text, upload.name)

            c1, c2 = st.columns(2)
            with c1:
                month = st.text_input("Billing month", value=month_guess, key=f"month_{idx}")
                amount = st.number_input(
                    "Total bill amount (₹)", min_value=0.0,
                    value=float(amount_guess or 0), step=10.0, key=f"amount_{idx}"
                )
                st.caption("Amount label found: " + (amount_evidence or "Not detected"))
            with c2:
                units = st.number_input(
                    "Units consumed (kWh)", min_value=0.0,
                    value=float(units_guess or 0), step=1.0, key=f"units_{idx}"
                )
                st.caption("Units label found: " + (units_evidence or "Not detected"))

            if st.button("Save verified bill", key=f"save_{idx}", type="primary"):
                if not month.strip() or amount <= 0 or units <= 0:
                    st.error("Enter a month, positive bill amount, and positive units.")
                elif any(row["Billing month"].lower() == month.strip().lower() for row in st.session_state.records):
                    st.error("A bill for this month is already saved in this session.")
                else:
                    st.session_state.records.append({
                        "Billing month": month.strip(),
                        "Bill amount (₹)": float(amount),
                        "Units (kWh)": float(units),
                        "Source file": upload.name
                    })
                    st.success("Verified bill saved for this session.")

st.divider()
st.header("2. Monthly history and comparison")
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df, use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Bill amount (₹)")
        st.bar_chart(df.set_index("Billing month")["Bill amount (₹)"])
    with right:
        st.subheader("Consumption (kWh)")
        st.bar_chart(df.set_index("Billing month")["Units (kWh)"])
    if len(df) >= 2:
        previous, latest = df.iloc[-2], df.iloc[-1]
        col1, col2 = st.columns(2)
        col1.metric("Latest bill", f"₹{latest['Bill amount (₹)']:,.2f}")
        if previous["Units (kWh)"] > 0:
            change = (latest["Units (kWh)"] - previous["Units (kWh)"]) / previous["Units (kWh)"] * 100
            col2.metric("Usage change vs previous saved bill", f"{change:+.1f}%")
            if abs(change) >= 50:
                st.warning("Large usage change detected. Verify units and billing periods.")
    st.download_button(
        "Download CSV report", df.to_csv(index=False).encode("utf-8-sig"),
        file_name="billwise_history.csv", mime="text/csv"
    )
    if st.button("Clear saved session history"):
        st.session_state.records = []
        st.rerun()
else:
    st.info("No bills saved yet. Upload a bill and press Save verified bill.")

st.divider()
st.header("3. Appliance usage estimator")
appliance_defaults = {
    "Air Conditioner": 1500, "Geyser": 2000, "Refrigerator": 150,
    "Washing Machine": 500, "Ceiling Fan": 70, "LED Bulb": 9,
    "Television": 100, "Electric Iron": 1000, "Water Pump": 750,
    "Induction Cooktop": 1800, "Desktop Computer": 200
}
with st.form("appliance_form"):
    chosen = st.multiselect(
        "Select appliances", list(appliance_defaults),
        default=["Air Conditioner", "Refrigerator", "Ceiling Fan"]
    )
    appliance_rows = []
    for idx, name in enumerate(chosen):
        st.markdown(f"**{name}**")
        c1, c2, c3 = st.columns(3)
        watts = c1.number_input("Power in watts", min_value=1, max_value=20000,
                                value=appliance_defaults[name], key=f"w_{idx}")
        hours = c2.number_input("Hours used per day", min_value=0.0, max_value=24.0,
                                value=4.0, step=0.5, key=f"h_{idx}")
        quantity = c3.number_input("Quantity", min_value=1, max_value=100,
                                   value=1, key=f"q_{idx}")
        appliance_rows.append((name, watts, hours, quantity))
    rate = st.number_input("Estimated rate (₹ per kWh)", min_value=0.0,
                           max_value=100.0, value=8.0, step=0.5)
    estimate = st.form_submit_button("Estimate monthly usage")

if estimate:
    rows = []
    for name, watts, hours, quantity in appliance_rows:
        units = watts / 1000 * hours * 30 * quantity
        rows.append({
            "Appliance": name,
            "Estimated kWh/month": round(units, 2),
            "Estimated energy cost (₹)": round(units * rate, 2)
        })
    if rows:
        results = pd.DataFrame(rows)
        st.dataframe(results, use_container_width=True, hide_index=True)
        st.bar_chart(results.set_index("Appliance")["Estimated kWh/month"])
        st.metric("Total estimated monthly energy cost", f"₹{results['Estimated energy cost (₹)'].sum():,.2f}")
    else:
        st.info("Select at least one appliance.")
    st.caption("Estimate formula: watts ÷ 1000 × hours/day × 30 × quantity. Actual usage and bills vary.")

st.divider()
st.header("4. Electricity saving suggestions")
st.markdown("""
- **AC:** Clean filters, close doors and windows, and avoid unnecessary runtime.
- **Geyser:** Heat only the water you need and switch it off after use.
- **Lighting:** Use LEDs and switch off unused lights.
- **Refrigerator:** Check door seals and allow airflow around the appliance.
- **Washing machine:** Run full loads where practical.
- **Bill checking:** Compare kWh, billing days, meter readings, fixed charges and tariff changes.
""")
if st.session_state.records:
    latest_units = float(st.session_state.records[-1]["Units (kWh)"])
    target = st.slider("Example target usage reduction (%)", 0, 30, 10, 5)
    saving_rate = st.number_input("Energy rate for savings estimate (₹/kWh)", 0.0, 100.0, 8.0, 0.5)
    saved_units = latest_units * target / 100
    st.metric("Potential units saved per month", f"{saved_units:.1f} kWh")
    st.metric("Potential energy-cost reduction", f"₹{saved_units * saving_rate:.2f}/month")
    st.caption("Illustrative estimate only; not a guaranteed bill reduction.")

st.divider()
st.header("5. Offline support assistant")

def support_answer(question):
    q = question.lower()

    if any(word in q for word in ["language", "marathi", "hindi", "gujarati", "ocr", "wrong text"]):
        return (
            "Choose the language printed on your bill in the sidebar. OCR needs "
            "Tesseract and the matching language pack installed. If values are "
            "unclear, enter them manually after checking the original bill."
        )
    if any(word in q for word in ["units", "kwh", "consumption", "usage"]):
        return (
            "One electricity unit generally equals 1 kWh. Compare monthly units "
            "and billing days as well as the amount due."
        )
    if any(word in q for word in ["high bill", "bill increased", "amount", "expensive"]):
        return (
            "Check consumption, billing days, meter readings, arrears, fixed "
            "charges, taxes and tariff slabs to investigate a higher bill."
        )
    if any(word in q for word in ["ac", "air conditioner", "geyser", "appliance", "fan", "fridge"]):
        return (
            "Estimated monthly units = watts ÷ 1000 × hours used per day × 30 "
            "× quantity. Actual energy use depends on the appliance and usage."
        )
    if any(word in q for word in ["save", "reduce", "saving"]):
        return (
            "Reduce unnecessary AC runtime, use a geyser timer, switch to LEDs, "
            "and run full washing-machine loads. Track monthly kWh to see changes."
        )
    return (
        "I can help with bill OCR, units, high bills, appliance estimates and "
        "energy-saving suggestions. Please ask a specific question."
    )

if "chat" not in st.session_state:
    st.session_state.chat = []

for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask a question about your electricity bill")
if question:
    st.session_state.chat.append({"role": "user", "content": question})
    st.session_state.chat.append({"role": "assistant", "content": support_answer(question)})
    st.rerun()
