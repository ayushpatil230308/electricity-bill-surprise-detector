
import io
import re
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Electricity Bill Detective",
    page_icon="⚡",
    layout="wide",
)

# ---------- Smooth, readable visual theme ----------
st.markdown(
    """
    <style>
    :root {
        --navy: #17324D;
        --blue: #2F80ED;
        --sky: #EAF4FF;
        --mint: #E9F8F2;
        --cream: #FFF8EC;
        --text: #213547;
        --muted: #66788A;
        --border: #DCE7F0;
    }

    .stApp {
        background: linear-gradient(180deg, #F7FBFF 0%, #FFFFFF 52%, #F7FCFA 100%);
        color: var(--text);
    }

    [data-testid="stHeader"] { background: transparent; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #EFF7FF 0%, #F4FBF8 100%);
        border-right: 1px solid #DCEAF4;
    }

    [data-testid="stSidebar"] * {
        color: #213547 !important;
    }

    h1, h2, h3, h4 {
        color: #17324D !important;
        letter-spacing: -0.2px;
    }

    p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
        color: #34495E;
    }

    .hero {
        padding: 24px 28px;
        border: 1px solid #DDEAF5;
        border-radius: 20px;
        background: linear-gradient(135deg, #EAF4FF 0%, #FFFFFF 58%, #EAF9F3 100%);
        box-shadow: 0 8px 28px rgba(37, 78, 111, 0.08);
        margin-bottom: 20px;
    }

    .hero h1 {
        margin: 0;
        font-size: 2.35rem;
        color: #17324D !important;
    }

    .hero p {
        margin: 8px 0 0;
        color: #5E7184 !important;
        font-size: 1.02rem;
    }

    .section-card {
        padding: 18px 20px;
        border: 1px solid #E1EAF2;
        border-radius: 16px;
        background: rgba(255,255,255,0.86);
        box-shadow: 0 5px 18px rgba(37, 78, 111, 0.05);
        margin: 12px 0 20px;
    }

    .mini-card {
        padding: 15px 16px;
        border-radius: 14px;
        background: #F6FAFD;
        border: 1px solid #E0EAF2;
        min-height: 92px;
    }

    .mini-title {
        font-weight: 700;
        color: #17324D;
        margin-bottom: 4px;
    }

    .mini-text {
        color: #607386;
        font-size: 0.9rem;
    }

    .step {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #EAF4FF;
        color: #2168B5;
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: .5px;
    }

    .success-box {
        padding: 14px 16px;
        border-radius: 13px;
        background: #EAF8F0;
        border: 1px solid #CFEBDD;
        color: #23543B;
    }

    .info-box {
        padding: 14px 16px;
        border-radius: 13px;
        background: #EDF6FF;
        border: 1px solid #D5E8FA;
        color: #234C70;
    }

    div[data-testid="stDataEditor"] {
        border: 1px solid #D9E5EF;
        border-radius: 14px;
        overflow: hidden;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #CFE0EF;
        min-height: 42px;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2F80ED, #2568C7);
        color: white;
        border: none;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Helpers ----------
def extract_numbers(text):
    cleaned = text.replace(",", "")
    units = None
    amount = None
    days = None

    unit_patterns = [
        r"(?:units?|consumption|kwh)\D{0,30}(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*kwh",
    ]
    amount_patterns = [
        r"(?:bill amount|amount payable|payable|total amount|net amount)\D{0,30}₹?\s*(\d+(?:\.\d+)?)",
        r"₹\s*(\d+(?:\.\d+)?)",
    ]

    for pattern in unit_patterns:
        m = re.search(pattern, cleaned, re.I)
        if m:
            units = float(m.group(1))
            break

    for pattern in amount_patterns:
        m = re.search(pattern, cleaned, re.I)
        if m:
            amount = float(m.group(1))
            break

    return units, amount, days


def try_extract(uploaded):
    name = uploaded.name.lower()
    raw_text = ""

    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(uploaded)
            raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            return "", None, f"PDF text extraction was unavailable: {exc}"

    elif name.endswith((".png", ".jpg", ".jpeg")):
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(uploaded)
            raw_text = pytesseract.image_to_string(image)
        except Exception as exc:
            return "", None, (
                "Image OCR is optional in this deployment. "
                f"Automatic OCR could not run: {exc}"
            )

    else:
        return "", None, "Unsupported file type."

    units, amount, days = extract_numbers(raw_text)
    return raw_text, (units, amount, days), None


def make_sample():
    return pd.DataFrame([
        {"Month": "June 2026", "Billing days": 30, "Units (kWh)": 89, "Bill amount (₹)": 740},
        {"Month": "July 2026", "Billing days": 31, "Units (kWh)": 121, "Bill amount (₹)": 1100},
        {"Month": "August 2026", "Billing days": 31, "Units (kWh)": 93, "Bill amount (₹)": 770},
        {"Month": "September 2026", "Billing days": 30, "Units (kWh)": 97, "Bill amount (₹)": 800},
        {"Month": "October 2026", "Billing days": 31, "Units (kWh)": 79, "Bill amount (₹)": 680},
    ])


# ---------- Header ----------
st.markdown(
    """
    <div class="hero">
        <h1>⚡ Electricity Bill Detective &amp; Savings Coach</h1>
        <p>Understand bill changes, find unusual usage, and plan practical savings.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
for col, title, text in [
    (c1, "📄 Scan your bills", "Upload PDF or photo bills and review extracted month, units and amount."),
    (c2, "🔎 Understand changes", "Compare monthly usage and identify bill increases worth checking."),
    (c3, "💡 Discover savings", "Use household details to explore practical, measurable savings actions."),
]:
    with col:
        st.markdown(
            f'<div class="mini-card"><div class="mini-title">{title}</div>'
            f'<div class="mini-text">{text}</div></div>',
            unsafe_allow_html=True,
        )

# ---------- Sidebar ----------
st.sidebar.markdown("### ⚙️ Household settings")
st.sidebar.selectbox("Bill language", ["English", "Hindi", "Marathi"])
st.sidebar.slider("OCR quality", 1, 5, 3, help="Higher can be slower when OCR is available.")
st.sidebar.markdown(
    '<div class="info-box"><b>OCR support:</b> PDF text extraction is built in. '
    'Image OCR is attempted when the OCR package is available. Always review extracted values.</div>',
    unsafe_allow_html=True,
)

household_size = st.sidebar.number_input("People in household", 1, 20, 4)
no_ac = st.sidebar.checkbox("No AC", True)
appliances = st.sidebar.multiselect(
    "Main appliances",
    ["Fans", "Refrigerator", "TV", "Washing machine", "Microwave", "Water heater", "Other"],
    default=["Fans", "Refrigerator", "TV", "Washing machine", "Microwave"],
)

# ---------- Upload ----------
st.markdown('<span class="step">STEP 01</span>', unsafe_allow_html=True)
st.header("Upload your bills")
st.write("Upload up to five monthly bills (PDF, PNG, JPG, JPEG). Open each bill and review the extracted values before saving.")

uploads = st.file_uploader(
    "Upload up to 5 monthly bills",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Keep personal identifiers private when sharing screenshots or publishing the project.",
)

if uploads:
    if len(uploads) > 5:
        st.error("Please upload a maximum of 5 bills.")
        uploads = uploads[:5]

    for i, uploaded in enumerate(uploads, start=1):
        with st.expander(f"Bill {i}: {uploaded.name}", expanded=(i == 1)):
            raw_text, extracted, error = try_extract(uploaded)

            left, right = st.columns([1.1, 1])
            with left:
                st.write(f"**File size:** {uploaded.size / 1024:.1f} KB")
                if uploaded.type == "application/pdf":
                    st.info("PDF uploaded. If it contains selectable text, the app will attempt text extraction.")
                else:
                    try:
                        from PIL import Image
                        image = Image.open(uploaded)
                        st.image(image, caption=uploaded.name, use_container_width=True)
                    except Exception:
                        pass

            with right:
                if extracted:
                    units, amount, days = extracted
                    if raw_text.strip():
                        st.success("Text extracted. Please verify the values before saving.")
                    else:
                        st.warning("No readable text was found automatically.")

                    st.number_input(
                        "Detected units (kWh)",
                        min_value=0.0,
                        value=float(units or 0),
                        key=f"units_{i}",
                    )
                    st.number_input(
                        "Detected bill amount (₹)",
                        min_value=0.0,
                        value=float(amount or 0),
                        key=f"amount_{i}",
                    )
                else:
                    st.warning("Automatic extraction did not produce reliable values. Enter them manually.")
                    st.number_input("Units (kWh)", min_value=0.0, value=0.0, key=f"manual_units_{i}")
                    st.number_input("Bill amount (₹)", min_value=0.0, value=0.0, key=f"manual_amount_{i}")

                if error:
                    st.caption(error)

            st.caption("Important: OCR is a convenience, not proof. Review month, units, billing days and amount against the original bill.")

# ---------- History ----------
st.markdown('<span class="step">STEP 02</span>', unsafe_allow_html=True)
st.header("Monthly bill history")

if "bills" not in st.session_state:
    st.session_state.bills = make_sample()

st.write("Start with your five bills. You can replace the sample values with your own verified figures.")

edited = st.data_editor(
    st.session_state.bills,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Billing days": st.column_config.NumberColumn(min_value=1, step=1),
        "Units (kWh)": st.column_config.NumberColumn(min_value=0, step=1),
        "Bill amount (₹)": st.column_config.NumberColumn(min_value=0, step=10),
    },
    key="bill_editor",
)

if st.button("Update analysis", type="primary"):
    st.session_state.bills = edited
    st.rerun()

df = st.session_state.bills.copy()

for col in ["Billing days", "Units (kWh)", "Bill amount (₹)"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["Billing days", "Units (kWh)", "Bill amount (₹)"])
df = df[df["Billing days"] > 0].copy()
df["Units/day"] = df["Units (kWh)"] / df["Billing days"]
df["₹/unit"] = df["Bill amount (₹)"] / df["Units (kWh)"].replace(0, pd.NA)

# ---------- Snapshot ----------
st.subheader("Bill snapshot")
if not df.empty:
    latest = df.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Latest usage", f'{latest["Units (kWh)"]:.0f} kWh')
    m2.metric("Latest daily usage", f'{latest["Units/day"]:.2f} kWh/day')
    m3.metric("Latest bill", f'₹{latest["Bill amount (₹)"]:.0f}')
    m4.metric("Months tracked", str(len(df)))

# ---------- Detective ----------
st.markdown('<span class="step">STEP 03</span>', unsafe_allow_html=True)
st.header("🔎 Bill Increase Detective")

if len(df) >= 2:
    previous = df.iloc[-2]
    current = df.iloc[-1]

    usage_pct = (
        (current["Units/day"] - previous["Units/day"]) / previous["Units/day"] * 100
        if previous["Units/day"] else 0
    )
    bill_pct = (
        (current["Bill amount (₹)"] - previous["Bill amount (₹)"])
        / previous["Bill amount (₹)"] * 100
        if previous["Bill amount (₹)"] else 0
    )

    if usage_pct > 20:
        st.warning(f"Daily usage increased by {usage_pct:.1f}% compared with {previous['Month']}.")
    elif usage_pct < -20:
        st.success(f"Daily usage decreased by {abs(usage_pct):.1f}% compared with {previous['Month']}.")
    else:
        st.info(f"Daily usage changed by {usage_pct:+.1f}% compared with {previous['Month']}.")

    a, b = st.columns(2)
    a.metric("Bill amount change", f"{bill_pct:+.1f}%")
    b.metric("Daily usage change", f"{usage_pct:+.1f}%")

    st.markdown(
        '<div class="info-box"><b>Detective note:</b> A higher bill does not automatically mean higher appliance usage. '
        'Billing days, tariff/charges, arrears, adjustments and other bill components can also affect the amount.</div>',
        unsafe_allow_html=True,
    )

# ---------- Charts ----------
st.markdown('<span class="step">STEP 04</span>', unsafe_allow_html=True)
st.header("📊 Usage history")

if not df.empty:
    display = df[["Month", "Billing days", "Units (kWh)", "Units/day", "Bill amount (₹)", "₹/unit"]].copy()
    display["Units/day"] = display["Units/day"].round(2)
    display["₹/unit"] = display["₹/unit"].round(2)
    st.dataframe(display, use_container_width=True, hide_index=True)

    chart_df = df.set_index("Month")

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(chart_df.index, chart_df["Units (kWh)"], marker="o", linewidth=2)
    ax.set_title("Monthly electricity usage")
    ax.set_ylabel("Units (kWh)")
    ax.grid(alpha=0.18)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    st.pyplot(fig)

    fig2, ax2 = plt.subplots(figsize=(8, 3.5))
    ax2.plot(chart_df.index, chart_df["Units/day"], marker="o", linewidth=2)
    ax2.set_title("Daily-normalized usage")
    ax2.set_ylabel("kWh/day")
    ax2.grid(alpha=0.18)
    ax2.tick_params(axis="x", rotation=35)
    fig2.tight_layout()
    st.pyplot(fig2)

# ---------- Savings ----------
st.markdown('<span class="step">STEP 05</span>', unsafe_allow_html=True)
st.header("💡 Savings Coach")

if not df.empty:
    latest_daily = float(df.iloc[-1]["Units/day"])
    if latest_daily >= 3.5:
        st.markdown(
            '<div class="info-box"><b>Starting point:</b> Your latest daily usage is higher than the '
            'recent baseline. Focus first on measuring long-running loads rather than guessing which appliance is responsible.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="success-box"><b>Good trend:</b> Your latest daily usage is below several earlier months. '
            'Continue monitoring the next bill to see whether the reduction persists.</div>',
            unsafe_allow_html=True,
        )

tips = []
if "Fans" in appliances:
    tips.append("Fans — record approximate hours of use each day and avoid running unused fans.")
if "Refrigerator" in appliances:
    tips.append("Refrigerator — check door seals, temperature setting and unusual continuous running.")
if "Washing machine" in appliances:
    tips.append("Washing machine — group loads where practical and note how often it runs.")
if "TV" in appliances:
    tips.append("TV — switch it off fully when it will not be used for a long period.")
if "Microwave" in appliances:
    tips.append("Microwave — measure usage before treating it as a major contributor; runtime matters.")
if "Water heater" in appliances:
    tips.append("Water heater — track heating duration and schedule rather than assuming a fixed saving.")

for tip in tips:
    st.write("• " + tip)

st.caption("These are practical investigation suggestions, not guaranteed savings.")

# ---------- Experiment ----------
st.markdown('<span class="step">STEP 06</span>', unsafe_allow_html=True)
st.header("🧪 Savings Experiment Tracker")

st.write("Test one household change and compare daily usage in the following period.")

with st.form("experiment_form"):
    change = st.text_input("Change tested", placeholder="Example: reduced unnecessary fan running")
    before = st.number_input("Before daily usage (kWh/day)", min_value=0.0, value=0.0, step=0.1)
    after = st.number_input("After daily usage (kWh/day)", min_value=0.0, value=0.0, step=0.1)
    submitted = st.form_submit_button("Calculate change")

if submitted:
    if before > 0:
        pct = (after - before) / before * 100
        if pct < 0:
            st.success(f"{change or 'Your experiment'}: daily usage changed by {pct:.1f}% (reduction).")
        elif pct > 0:
            st.warning(f"{change or 'Your experiment'}: daily usage changed by +{pct:.1f}%.")
        else:
            st.info("No change in daily usage was recorded.")
        st.caption("This is an observational comparison. Weather, occupancy, appliance use and billing-period length can affect results.")
    else:
        st.error("Enter a before-usage value greater than 0.")

st.divider()
st.caption("Prototype for household electricity-bill analysis. Review official tariff rules before making financial estimates.")
