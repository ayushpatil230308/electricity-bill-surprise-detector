import io
import re
from pathlib import Path
from datetime import datetime

import fitz
import pandas as pd
import pytesseract
import streamlit as st
from PIL import Image, ImageEnhance, ImageOps

st.set_page_config(page_title="BillWise India", page_icon="⚡", layout="wide")
st.title("⚡ BillWise India")
st.subheader("Electricity Bill Reader and Savings Assistant")
st.write("Upload bills, verify extracted values, compare monthly usage, and estimate appliance electricity consumption.")
st.warning("OCR can make mistakes. Always verify the bill amount and units against the original bill.")

LANGUAGES = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin", "Gujarati": "guj",
    "Bengali": "ben", "Tamil": "tam", "Telugu": "tel", "Kannada": "kan",
    "Malayalam": "mal", "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep", "Sanskrit": "san"
}
AMOUNT_PATTERNS = [
    r"total\s*amount\s*due", r"net\s*amount\s*payable", r"amount\s*payable",
    r"amount\s*due", r"bill\s*amount", r"total\s*bill",
    r"current\s*bill\s*amount", r"grand\s*total", r"total\s*payable"
]
UNIT_PATTERNS = [
    r"units?\s*consumed", r"consumed\s*units", r"energy\s*consumed",
    r"kwh\s*consumed", r"consumption\s*\(?kwh\)?",
    r"billable\s*units", r"total\s*consumption"
]
NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:₹|Rs\.?|INR)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE
)

if "bill_records" not in st.session_state:
    st.session_state.bill_records = []
if "support_chat" not in st.session_state:
    st.session_state.support_chat = []

with st.sidebar:
    st.header("Settings")
    selected_languages = st.multiselect(
        "Languages on your bill", list(LANGUAGES.keys()),
        default=["English", "Marathi", "Hindi"]
    )
    force_ocr = st.checkbox("Force OCR for PDF files", value=False)
    dpi = st.slider("PDF OCR resolution", min_value=2, max_value=4, value=3)

language_codes = "+".join(LANGUAGES[x] for x in selected_languages) or "eng"

def clean_lines(text):
    return [re.sub(r"\s+", " ", line).strip()
            for line in (text or "").splitlines() if line.strip()]

def preprocess_image(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(1.4)

def perform_ocr(image, language_codes):
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        available = set()
    attempts = [language_codes, "eng"]
    best_text, best_score = "", -1
    for language in dict.fromkeys(attempts):
        if not language:
            continue
        required = language.split("+")
        if available and any(code not in available for code in required):
            continue
        try:
            text = pytesseract.image_to_string(
                image, lang=language, config="--oem 1 --psm 6"
            ).strip()
            score = sum(ch.isalnum() for ch in text)
            if score > best_score:
                best_text, best_score = text, score
        except Exception:
            continue
    return best_text

def read_pdf(upload, language_codes, force_ocr, dpi):
    pages = []
    with fitz.open(stream=upload.getvalue(), filetype="pdf") as document:
        for page in document:
            embedded = (page.get_text("text") or "").strip()
            should_ocr = force_ocr or len(embedded) < 45 or len(re.findall(r"\d", embedded)) < 5
            if should_ocr:
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi, dpi), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                ocr_text = perform_ocr(preprocess_image(image), language_codes)
                page_text = ocr_text if force_ocr and ocr_text else (
                    ocr_text if len(ocr_text) > len(embedded) else embedded
                )
            else:
                page_text = embedded
            pages.append(page_text)
    return "\n\n".join(pages)

def read_upload(upload, language_codes, force_ocr, dpi):
    if Path(upload.name).suffix.lower() == ".pdf":
        return read_pdf(upload, language_codes, force_ocr, dpi)
    image = Image.open(upload).convert("RGB")
    return perform_ocr(preprocess_image(image), language_codes)

def parse_number(value):
    try:
        return float(value.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None

def find_labeled_value(text, patterns):
    lines = clean_lines(text)
    for index, line in enumerate(lines):
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if not match:
                continue
            candidates = NUMBER_PATTERN.findall(line[match.end():])
            if not candidates and index + 1 < len(lines):
                candidates = NUMBER_PATTERN.findall(lines[index + 1])
            values = [parse_number(v) for v in candidates]
            values = [v for v in values if v is not None]
            if values:
                return values[-1], line
    return None, ""

def extract_month(text, filename):
    month_names = (
        "January|February|March|April|May|June|July|August|"
        "September|October|November|December"
    )
    match = re.search(rf"\b({month_names})\s*,?\s*(20\d{{2}})\b", text, re.I)
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

st.header("1. Upload Electricity Bills")
uploads = st.file_uploader(
    "Select PDF or image files", type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)
if uploads:
    for index, upload in enumerate(uploads):
        with st.expander(upload.name, expanded=True):
            try:
                text = read_upload(upload, language_codes, force_ocr, dpi)
            except Exception as error:
                st.error(f"Could not read file: {error}")
                continue
            st.text_area("Extracted bill text", text[:10000], height=160, key=f"bill_text_{index}")
            amount_guess, amount_evidence = find_labeled_value(text, AMOUNT_PATTERNS)
            units_guess, units_evidence = find_labeled_value(text, UNIT_PATTERNS)
            month_guess = extract_month(text, upload.name)
            col1, col2 = st.columns(2)
            with col1:
                month = st.text_input("Billing month", value=month_guess, key=f"month_{index}")
                amount = st.number_input("Bill amount (₹)", min_value=0.0, value=float(amount_guess or 0), step=10.0, key=f"amount_{index}")
                st.caption("Amount label: " + (amount_evidence or "Not detected"))
            with col2:
                units = st.number_input("Units consumed (kWh)", min_value=0.0, value=float(units_guess or 0), step=1.0, key=f"units_{index}")
                st.caption("Units label: " + (units_evidence or "Not detected"))
            if st.button("Save verified bill", key=f"save_bill_{index}"):
                if not month.strip() or amount <= 0 or units <= 0:
                    st.error("Enter the correct month, amount and units.")
                elif any(record["Billing month"].lower() == month.strip().lower()
                         for record in st.session_state.bill_records):
                    st.error("This billing month is already saved.")
                else:
                    st.session_state.bill_records.append({
                        "Billing month": month.strip(), "Bill amount (₹)": float(amount),
                        "Units (kWh)": float(units), "Source file": upload.name
                    })
                    st.success("Bill saved successfully.")

st.divider()
st.header("2. Monthly Bill History")
if st.session_state.bill_records:
    df = pd.DataFrame(st.session_state.bill_records)
    st.dataframe(df, use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Bill Amount")
        st.bar_chart(df.set_index("Billing month")["Bill amount (₹)"])
    with col2:
        st.subheader("Electricity Usage")
        st.bar_chart(df.set_index("Billing month")["Units (kWh)"])
    if len(df) >= 2:
        previous, latest = df.iloc[-2], df.iloc[-1]
        col1, col2 = st.columns(2)
        col1.metric("Latest Bill", f"₹{latest['Bill amount (₹)']:,.2f}")
        if previous["Units (kWh)"] > 0:
            percentage = (latest["Units (kWh)"] - previous["Units (kWh)"]) / previous["Units (kWh)"] * 100
            col2.metric("Usage Change", f"{percentage:+.1f}%")
            if abs(percentage) >= 50:
                st.warning("Usage changed substantially. Verify the readings and billing periods.")
    st.download_button(
        "Download Bill History CSV", data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="billwise_history.csv", mime="text/csv"
    )
    if st.button("Clear Bill History"):
        st.session_state.bill_records = []
        st.rerun()
else:
    st.info("Upload and save a verified bill to begin tracking.")

st.divider()
st.header("3. Appliance Electricity Estimator")
appliances = {
    "Air Conditioner": 1500, "Geyser": 2000, "Refrigerator": 150,
    "Washing Machine": 500, "Ceiling Fan": 70, "LED Bulb": 9,
    "Television": 100, "Electric Iron": 1000, "Water Pump": 750,
    "Induction Cooktop": 1800
}
with st.form("appliance_estimator"):
    selected = st.multiselect(
        "Choose appliances", list(appliances.keys()),
        default=["Air Conditioner", "Refrigerator", "Ceiling Fan"]
    )
    appliance_data = []
    for index, name in enumerate(selected):
        st.markdown(f"**{name}**")
        col1, col2, col3 = st.columns(3)
        watts = col1.number_input("Power (watts)", min_value=1, max_value=20000,
                                  value=appliances[name], key=f"power_{index}")
        hours = col2.number_input("Hours per day", min_value=0.0, max_value=24.0,
                                  value=4.0, step=0.5, key=f"hours_{index}")
        quantity = col3.number_input("Quantity", min_value=1, max_value=100,
                                     value=1, key=f"quantity_{index}")
        appliance_data.append((name, watts, hours, quantity))
    tariff = st.number_input("Estimated rate (₹ per kWh)", min_value=0.0,
                              max_value=100.0, value=8.0, step=0.5)
    calculate = st.form_submit_button("Calculate Usage")
if calculate:
    results = []
    for name, watts, hours, quantity in appliance_data:
        monthly_units = watts / 1000 * hours * 30 * quantity
        results.append({
            "Appliance": name, "Estimated units/month": round(monthly_units, 2),
            "Estimated cost/month (₹)": round(monthly_units * tariff, 2)
        })
    if results:
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True, hide_index=True)
        st.bar_chart(result_df.set_index("Appliance")["Estimated units/month"])
        total_units = result_df["Estimated units/month"].sum()
        total_cost = result_df["Estimated cost/month (₹)"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Estimated Monthly Units", f"{total_units:.2f} kWh")
        col2.metric("Estimated Monthly Energy Cost", f"₹{total_cost:.2f}")
    else:
        st.info("Select at least one appliance.")
    st.caption("Formula: watts ÷ 1000 × hours per day × 30 × quantity. Cost excludes fixed charges, taxes and tariff slabs.")

st.divider()
st.header("4. Electricity Saving Suggestions")
st.markdown("""
- **Air conditioner:** Clean filters and reduce unnecessary operating time.
- **Geyser:** Heat only the water you need and switch it off after use.
- **Lighting:** Use LED bulbs and turn off unused lights.
- **Refrigerator:** Check door seals and avoid leaving the door open.
- **Washing machine:** Run full loads where practical.
- **Bill checking:** Compare kWh, billing days, fixed charges and tariff changes.
""")
if st.session_state.bill_records:
    latest_units = float(st.session_state.bill_records[-1]["Units (kWh)"])
    target = st.slider("Target monthly consumption reduction (%)", 0, 30, 10, 5)
    rate = st.number_input("Rate for savings estimate (₹/kWh)", min_value=0.0,
                           max_value=100.0, value=8.0, step=0.5, key="savings_rate")
    saved_units = latest_units * target / 100
    saved_cost = saved_units * rate
    col1, col2 = st.columns(2)
    col1.metric("Potential Units Saved", f"{saved_units:.1f} kWh/month")
    col2.metric("Potential Energy Cost Saved", f"₹{saved_cost:.2f}/month")
    st.caption("This is an estimate, not a guaranteed reduction in your bill.")

st.divider()
st.header("5. BillWise Support Assistant")

def support_answer(question):
    q = question.lower()

    if any(x in q for x in [
        "language", "marathi", "hindi", "gujarati", "ocr", "wrong text", "garbled"
    ]):
        return (
            "Select the languages printed on your bill in the sidebar. "
            "Install the matching Tesseract language packs. If OCR is incorrect, "
            "check the original bill and enter the values manually."
        )

    if any(x in q for x in ["units", "kwh", "consumption", "usage"]):
        return (
            "One electricity unit generally equals 1 kWh. Compare monthly units "
            "and billing days, not just the total bill amount."
        )

    if any(x in q for x in ["high bill", "bill increased", "amount", "expensive"]):
        return (
            "Compare consumption, billing days, meter readings, arrears, fixed "
            "charges, taxes and tariff slabs to investigate a high bill."
        )

    if any(x in q for [
        "ac", "air conditioner", "geyser", "appliance", "fan", "fridge", "refrigerator"
    ]):
        return (
            "Estimated monthly units = watts ÷ 1000 × daily operating hours × 30 "
            "× quantity. Actual consumption may differ."
        )

    if any(x in q for ["save", "reduce", "saving"]):
        return (
            "Reduce unnecessary AC runtime, use a geyser timer, switch to LED "
            "lighting and run full washing-machine loads. Compare monthly kWh "
            "to check whether your efforts are helping."
        )

    return (
        "I can help with OCR and languages, electricity units, high bills, "
        "appliance estimates and energy-saving suggestions. Ask a specific question."
    )

for message in st.session_state.support_chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask a question about your electricity bill")
if question:
    st.session_state.support_chat.append({"role": "user", "content": question})
    answer = support_answer(question)
    st.session_state.support_chat.append({"role": "assistant", "content": answer})
    st.rerun()
