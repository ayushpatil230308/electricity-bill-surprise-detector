import io
import re
from pathlib import Path
from datetime import datetime

import fitz
import pandas as pd
import pytesseract
import streamlit as st
from PIL import Image, ImageEnhance, ImageOps

st.set_page_config(
    page_title="BillWise India",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
.block-container {max-width:1250px; padding-top:1.4rem}
.hero {padding:1.25rem; border:1px solid rgba(128,128,128,.3);
border-radius:18px; margin-bottom:1rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>⚡ BillWise India</h1>
<p><b>Multilingual Electricity Bill Reader and Savings Assistant</b></p>
<p>Read bills, compare monthly consumption, estimate appliance energy,
and discover ways to save electricity.</p>
</div>
""", unsafe_allow_html=True)

st.warning(
    "Extracted values are candidates. Verify the billing month, amount "
    "and kWh against the original bill before saving."
)

LANGS = {
    "English": "eng", "Marathi": "mar", "Hindi": "hin",
    "Gujarati": "guj", "Bengali": "ben", "Tamil": "tam",
    "Telugu": "tel", "Kannada": "kan", "Malayalam": "mal",
    "Punjabi": "pan", "Urdu": "urd", "Odia": "ori",
    "Assamese": "asm", "Nepali": "nep", "Sanskrit": "san"
}

PROVIDERS = [
    "Auto-detect / Other", "MSEDCL / Mahavitaran",
    "Adani Electricity", "Tata Power", "BEST Mumbai",
    "BESCOM", "TANGEDCO", "BSES", "Torrent Power",
    "Other provider"
]

AMOUNT_PATTERNS = [
    r"total\s*amount\s*due",
    r"net\s*amount\s*payable",
    r"amount\s*payable",
    r"amount\s*due",
    r"bill\s*amount",
    r"total\s*bill",
    r"net\s*bill\s*amount",
    r"current\s*bill\s*amount",
    r"payable\s*amount",
    r"grand\s*total",
    r"total\s*payable",
    r"bill\s*total",
    r"amount\s*to\s*be\s*paid"
]

UNIT_PATTERNS = [
    r"units?\s*consumed",
    r"consumption\s*(?:units|kwh)",
    r"energy\s*consumed",
    r"consumed\s*units",
    r"total\s*consumption",
    r"units?\s*\(\s*kwh\s*\)",
    r"kwh\s*consumed",
    r"consumption\s*in\s*kwh",
    r"active\s*energy\s*\(\s*kwh\s*\)",
    r"energy\s*\(\s*kwh\s*\)",
    r"billable\s*units"
]

NUM = re.compile(
    r"(?<![A-Za-z])(?:₹|Rs\.?|INR)?\s*"
    r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
    r"(?![A-Za-z])",
    re.I
)

with st.sidebar:
    st.header("Bill Reading Settings")

    provider = st.selectbox("Electricity provider", PROVIDERS)

    selected_languages = st.multiselect(
        "Languages printed on the bill",
        list(LANGS.keys()),
        default=["English", "Marathi", "Hindi"]
    )

    force_ocr = st.checkbox(
        "Force OCR even when PDF text exists",
        value=False
    )

    dpi = st.slider("OCR quality", 2, 4, 3)

    st.caption(
        "OCR language packs must be installed on the server. "
        "Choose the languages present on your bill."
    )

if "bill_records" not in st.session_state:
    st.session_state.bill_records = []

if "support_chat" not in st.session_state:
    st.session_state.support_chat = []


def clean_lines(text):
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in (text or "").splitlines()
        if line.strip()
    ]


def text_quality(text):
    if not text or len(text.strip()) < 45:
        return False

    bad_markers = ("�", "□", "Ã", "Â", "â€", "ï»¿")
    bad_count = sum(text.count(x) for x in bad_markers)

    readable = sum(
        ch.isalnum() or ch in "₹.,:/-%() \n\t"
        for ch in text
    )

    ratio = readable / max(len(text), 1)

    return "�" not in text and bad_count < 3 and ratio > 0.65


def preprocess_image(image):
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    return ImageEnhance.Contrast(image).enhance(1.45)


def ocr_image(image, language_codes):
    attempts = []

    if language_codes:
        attempts.append(language_codes)
        attempts.extend(language_codes.split("+"))

    if "eng" not in attempts:
        attempts.append("eng")

    attempts = list(dict.fromkeys(attempts))

    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        available = set()

    best_text = ""
    best_method = "OCR unavailable: check Tesseract and language packs"
    best_score = -1

    for language in attempts:
        required = language.split("+")

        if available and any(code not in available for code in required):
            continue

        try:
            result = pytesseract.image_to_string(
                image,
                lang=language,
                config="--oem 1 --psm 6"
            ).strip()

            if not result:
                continue

            readable = sum(
                ch.isalnum() or ch in "₹.,:/-%() \n\t"
                for ch in result
            )

            score = readable / max(len(result), 1) * 100

            if any(code in required for code in ("mar", "hin", "san", "nep")):
                devanagari_count = sum(
                    "\u0900" <= ch <= "\u097f"
                    for ch in result
                )
                score += min(devanagari_count, 100) * 0.15

            if score > best_score:
                best_text = result
                best_method = f"Tesseract OCR ({language})"
                best_score = score

        except Exception:
            continue

    return best_text, best_method


def read_upload(upload, language_codes, force_ocr, dpi):
    suffix = Path(upload.name).suffix.lower()

    if suffix == ".pdf":
        all_text = []
        methods = []

        with fitz.open(
            stream=upload.getvalue(),
            filetype="pdf"
        ) as document:

            for page in document:
                embedded = (page.get_text("text") or "").strip()

                should_ocr = force_ocr or not text_quality(embedded)

                if not should_ocr:
                    labels = [
                        "amount", "payable", "consumption",
                        "units", "kwh", "total", "energy"
                    ]

                    if (
                        not any(x in embedded.lower() for x in labels)
                        and len(re.findall(r"\d", embedded)) < 10
                    ):
                        should_ocr = True

                if should_ocr:
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(dpi, dpi),
                        alpha=False
                    )

                    image = Image.open(
                        io.BytesIO(pixmap.tobytes("png"))
                    ).convert("RGB")

                    image = preprocess_image(image)

                    ocr_text, method = ocr_image(
                        image, language_codes
                    )

                    if ocr_text and (
                        force_ocr or not text_quality(embedded)
                    ):
                        all_text.append(ocr_text)
                    elif embedded and ocr_text:
                        all_text.append(embedded + "\n\n" + ocr_text)
                    elif ocr_text:
                        all_text.append(ocr_text)
                    else:
                        all_text.append(embedded)

                    if embedded:
                        methods.append("Embedded PDF text")

                    methods.append(method)

                else:
                    all_text.append(embedded)
                    methods.append("Embedded PDF text")

        return (
            "\n\n".join(x for x in all_text if x.strip()),
            " + ".join(sorted(set(methods)))
        )

    image = Image.open(upload).convert("RGB")
    image = preprocess_image(image)
    return ocr_image(image, language_codes)


def parse_number(value):
    try:
        return float(value.replace(",", "").replace("₹", "").strip())
    except (ValueError, AttributeError):
        return None


def label_value(text, patterns, lookahead=2):
    lines = clean_lines(text)

    for index, line in enumerate(lines):
        for pattern in patterns:
            match = re.search(pattern, line, re.I)

            if not match:
                continue

            candidates = NUM.findall(line[match.end():])
            evidence = line

            if not candidates:
                for next_line in lines[index + 1:index + 1 + lookahead]:
                    candidates = NUM.findall(next_line)

                    if candidates:
                        evidence = f"{line} | {next_line}"
                        break

            values = [
                parse_number(value)
                for value in candidates
            ]

            values = [value for value in values if value is not None]

            if values:
                return values[-1], evidence[:180]

    return None, ""


def extract_month(text, filename=""):
    months = (
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
    )

    match = re.search(
        rf"\b{months}\s*,?\s*20\d{{2}}\b",
        text or "",
        re.I
    )

    if match:
        return match.group(0).replace(",", "")

    lines = clean_lines(text)

    for index, line in enumerate(lines):
        if re.search(
            r"bill\s*period|billing\s*period|period\s*from|reading\s*date",
            line,
            re.I
        ):
            joined = " ".join(lines[index:index + 3])
            dates = re.findall(
                r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",
                joined
            )

            for date_text in reversed(dates):
                try:
                    date = datetime.strptime(
                        date_text.replace("/", "-"),
                        "%d-%m-%Y"
                    )
                    return date.strftime("%B %Y")
                except ValueError:
                    pass

    match = re.search(
        r"_(\d{2})(0[1-9]|1[0-2])_",
        filename
    )

    if match:
        return datetime(
            2000 + int(match.group(1)),
            int(match.group(2)),
            1
        ).strftime("%B %Y")

    return ""


def parse_bill(upload, text, provider_name):
    amount, amount_evidence = label_value(text, AMOUNT_PATTERNS)
    units, units_evidence = label_value(text, UNIT_PATTERNS)
    month = extract_month(text, upload.name)

    return (
        amount,
        units,
        amount_evidence,
        units_evidence,
        month,
        "Text/OCR label matching"
    )


def anomaly_messages(amount, units, records):
    messages = []

    if amount > 0 and units > 0:
        ratio = amount / units

        if ratio < 1 or ratio > 50:
            messages.append(
                f"Amount divided by units is ₹{ratio:.2f}/kWh. "
                "This rough ratio includes charges; verify the bill."
            )

    if units > 3000:
        messages.append(
            "Usage exceeds 3,000 kWh. Verify the value and property type."
        )

    if records:
        previous = records[-1]

        for value, old, label in [
            (units, float(previous["Units (kWh)"]), "Consumption"),
            (amount, float(previous["Bill amount (₹)"]), "Bill amount")
        ]:
            if old > 0 and value > 0:
                change = (value - old) / old * 100

                if abs(change) >= 50:
                    messages.append(
                        f"{label} changed by {change:+.0f}% compared "
                        "with the last saved bill. Please review."
                    )

    return messages


# SECTION 1: BILL UPLOAD

st.header("1. Upload and verify electricity bills")

uploads = st.file_uploader(
    "Upload PDF, JPG, JPEG or PNG bills",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploads:
    language_codes = "+".join(
        LANGS[name] for name in selected_languages
    ) if selected_languages else "eng"

    for index, upload in enumerate(uploads):
        with st.expander(
            f"Review: {upload.name}",
            expanded=(index == 0)
        ):
            try:
                text, read_method = read_upload(
                    upload, language_codes, force_ocr, dpi
                )
            except Exception as error:
                st.error(f"Could not read this file: {error}")
                continue

            (
                amount_guess,
                units_guess,
                amount_evidence,
                units_evidence,
                month_guess,
                parser
            ) = parse_bill(upload, text, provider)

            st.caption(
                f"Read method: {read_method} | Parser: {parser}"
            )

            with st.expander("Show extracted text/OCR"):
                st.text_area(
                    "Text read from bill",
                    text[:12000],
                    height=220,
                    key=f"text_{index}"
                )

            st.warning(
                "Verify the extracted fields against your original bill."
            )

            col1, col2 = st.columns(2)

            with col1:
                month = st.text_input(
                    "Billing month",
                    value=month_guess,
                    key=f"month_{index}"
                )

                amount = st.number_input(
                    "Total bill amount (₹)",
                    min_value=0.0,
                    value=float(amount_guess or 0),
                    step=10.0,
                    key=f"amount_{index}"
                )

                st.caption(
                    "Amount evidence: "
                    + (amount_evidence or "No matching label found")
                )

            with col2:
                units = st.number_input(
                    "Units consumed (kWh)",
                    min_value=0.0,
                    value=float(units_guess or 0),
                    step=1.0,
                    key=f"units_{index}"
                )

                st.caption(
                    "Units evidence: "
                    + (units_evidence or "No matching label found")
                )

            for message in anomaly_messages(
                amount, units, st.session_state.bill_records
            ):
                st.warning(message)

            if st.button(
                "Save verified bill",
                key=f"save_{index}",
                type="primary"
            ):
                if not month.strip() or amount <= 0 or units <= 0:
                    st.error(
                        "Enter the correct month, amount and units "
                        "after checking the original bill."
                    )
                elif any(
                    r["Bill month"].lower() == month.strip().lower()
                    for r in st.session_state.bill_records
                ):
                    st.error(
                        "This month is already saved. Clear history "
                        "before saving a replacement."
                    )
                else:
                    st.session_state.bill_records.append({
                        "Bill month": month.strip(),
                        "Bill amount (₹)": float(amount),
                        "Units (kWh)": float(units),
                        "Provider": provider,
                        "Source file": upload.name
                    })
                    st.success("Bill saved for this session.")


# SECTION 2: BILL HISTORY

st.divider()
st.header("2. Bill history and comparison")

if st.session_state.bill_records:
    df = pd.DataFrame(st.session_state.bill_records)
    df["_sort"] = pd.to_datetime(df["Bill month"], errors="coerce")
    df = df.sort_values("_sort", na_position="last").drop(columns="_sort")

    st.dataframe(df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Monthly bill amount (₹)")
        st.bar_chart(df.set_index("Bill month")["Bill amount (₹)"])

    with col2:
        st.subheader("Monthly usage (kWh)")
        st.bar_chart(df.set_index("Bill month")["Units (kWh)"])

    if len(df) >= 2:
        old, new = df.iloc[-2], df.iloc[-1]
        a, b, c = st.columns(3)

        a.metric("Latest bill", f"₹{new['Bill amount (₹)']:,.2f}")
        b.metric("Latest usage", f"{new['Units (kWh)']:,.0f} kWh")

        if old["Units (kWh)"] > 0:
            change = (
                (new["Units (kWh)"] - old["Units (kWh)"])
                / old["Units (kWh)"] * 100
            )
            c.metric("Usage change", f"{change:+.1f}%")

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "billwise_report.csv",
        "text/csv"
    )

    if st.button("Clear session bill history"):
        st.session_state.bill_records = []
        st.rerun()
else:
    st.info("Save verified bills to compare monthly amounts and usage.")


# SECTION 3: APPLIANCE ESTIMATOR

st.divider()
st.header("3. High-energy appliance estimator")

st.write(
    "Estimate appliance energy from power rating and hours of use. "
    "These are estimates, not measurements from the bill."
)

appliance_defaults = {
    "Air conditioner (AC)": 1500,
    "Water geyser": 2000,
    "Refrigerator": 150,
    "Washing machine": 500,
    "Microwave": 1200,
    "Electric iron": 1000,
    "Water pump": 750,
    "Ceiling fan": 70,
    "LED bulb": 9,
    "Desktop computer": 200,
    "Television": 100,
    "Induction cooktop": 1800,
    "Other appliance": 500
}

with st.form("appliance_form"):
    selected_appliances = st.multiselect(
        "Choose appliances in your home",
        list(appliance_defaults),
        default=[
            "Air conditioner (AC)",
            "Water geyser",
            "Refrigerator",
            "Ceiling fan"
        ]
    )

    appliance_rows = []

    for index, name in enumerate(selected_appliances):
        cols = st.columns([2, 1, 1, 1])
        cols[0].markdown(f"**{name}**")

        watts = cols[1].number_input(
            "Rated watts",
            min_value=1,
            max_value=20000,
            value=appliance_defaults[name],
            key=f"watts_{index}_{name}"
        )

        default_hours = (
            4.0 if "AC" in name
            else 1.0 if "geyser" in name.lower()
            else 8.0
        )

        hours = cols[2].number_input(
            "Hours/day",
            min_value=0.0,
            max_value=24.0,
            value=default_hours,
            step=0.5,
            key=f"hours_{index}_{name}"
        )

        quantity = cols[3].number_input(
            "Quantity",
            min_value=1,
            max_value=100,
            value=1,
            key=f"quantity_{index}_{name}"
        )

        appliance_rows.append((name, watts, hours, quantity))

    tariff = st.number_input(
        "Approximate energy rate (₹/kWh)",
        min_value=0.0,
        max_value=100.0,
        value=8.0,
        step=0.5
    )

    submitted = st.form_submit_button("Estimate appliance usage")

if submitted:
    if not appliance_rows:
        st.info("Choose at least one appliance.")
    else:
        results = []

        for name, watts, hours, quantity in appliance_rows:
            kwh = watts / 1000 * hours * 30 * quantity

            results.append({
                "Appliance": name,
                "Estimated kWh/month": round(kwh, 2),
                "Estimated energy cost (₹)": round(kwh * tariff, 2)
            })

        appliance_df = pd.DataFrame(results).sort_values(
            "Estimated kWh/month",
            ascending=False
        )

        st.dataframe(
            appliance_df,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            appliance_df.set_index("Appliance")["Estimated kWh/month"]
        )

        top = appliance_df.iloc[0]

        st.info(
            f"Highest estimated appliance: {top['Appliance']} "
            f"at {top['Estimated kWh/month']:.1f} kWh/month. "
            "Actual usage may differ."
        )

        st.caption(
            "Formula: kWh/month = watts ÷ 1000 × hours/day × 30 × quantity. "
            "Cost excludes fixed charges, taxes and tariff slabs."
        )


# SECTION 4: SAVINGS COACH

st.divider()
st.header("4. Electricity savings coach")

st.markdown("""
- **Air conditioner:** clean filters, close doors and windows, and use a
  comfortable temperature setting.
- **Geyser:** heat only the water needed and switch it off after use.
- **Refrigerator:** maintain door seals and allow airflow around the unit.
- **Lights:** use LEDs and switch off unused lights.
- **Washing machine:** run full loads when practical.
- **General:** compare kWh as well as rupees because tariffs, billing days,
  taxes and fixed charges affect the final amount.
""")

if st.session_state.bill_records:
    latest_units = float(
        st.session_state.bill_records[-1]["Units (kWh)"]
    )

    st.info(f"Latest saved usage: {latest_units:.1f} kWh")

    target = st.slider(
        "Target reduction in monthly usage (%)",
        0, 30, 10, 5
    )

    rate = st.number_input(
        "Estimated energy rate (₹/kWh)",
        min_value=0.0,
        max_value=100.0,
        value=8.0,
        step=0.5,
        key="savings_rate"
    )

    saved_units = latest_units * target / 100
    saved_cost = saved_units * rate

    col1, col2 = st.columns(2)

    col1.metric(
        "Potential energy reduction",
        f"{saved_units:.1f} kWh/month"
    )

    col2.metric(
        "Approximate energy-cost reduction",
        f"₹{saved_cost:,.2f}/month"
    )

    st.caption(
        "This is an estimate, not a guaranteed bill reduction."
    )


# SECTION 5: BUILT-IN CUSTOMER SUPPORT

st.divider()
st.header("5. Customer support assistant")

st.write(
    "Ask questions about electricity bills, OCR, units, appliances "
    "or saving electricity. This offline helper requires no paid AI API."
)


def support_answer(question):
    q = question.lower()

    if any(x in q for x in [
        "language", "marathi", "hindi", "gujarati",
        "ocr", "garbled", "wrong text"
    ]):
        return (
            "Select the languages present on your bill in the sidebar. "
            "For a PDF with corrupted embedded text, try enabling Force OCR. "
            "The relevant Tesseract language packs must be installed. "
            "If text remains unclear, verify the fields manually."
        )

    if any(x in q for x in ["units", "kwh", "consumption", "usage"]):
        return (
            "One electricity unit usually equals 1 kWh. Compare monthly "
            "kWh values as well as bill amounts, because tariffs and "
            "billing charges can change the amount."
        )

    if any(x in q for x in [
        "high bill", "bill increased", "amount", "expensive"
    ]):
        return (
            "Compare current kWh with previous months. Check billing days, "
            "arrears, meter readings, tariff slabs, taxes and fixed charges."
        )

    if any(x in q for x in [
        "ac", "air conditioner", "geyser", "appliance",
        "fan", "fridge", "refrigerator"
    ]):
        return (
            "Estimated kWh/month = watts ÷ 1000 × hours/day × 30 × quantity. "
            "Actual use depends on operating time, settings and appliance condition."
        )

    if any(x in q for ["save", "reduce", "saving"]):
        return (
            "Consider reducing unnecessary AC runtime, using a geyser timer, "
            "switching to LEDs and running full washing-machine loads. "
            "Track monthly kWh to assess the effect."
        )

    return (
        "I can help with OCR and language issues, understanding kWh, "
        "investigating high bills, appliance estimates and energy savings. "
        "Ask a specific question."
    )


for message in st.session_state.support_chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask BillWise a question...")

if question:
    st.session_state.support_chat.append({
        "role": "user",
        "content": question
    })

    answer = support_answer(question)

    st.session_state.support_chat.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()
