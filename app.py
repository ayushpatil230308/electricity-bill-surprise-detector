import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Electricity Bill Detective",
    page_icon="⚡",
    layout="wide",
)


# -----------------------------
# Smooth color theme
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #F7FBFF 0%, #FFFFFF 55%, #F5FCF8 100%);
        color: #243447;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #EEF7FF 0%, #F3FBF8 100%);
        border-right: 1px solid #DCEAF4;
    }

    [data-testid="stSidebar"] * {
        color: #243447 !important;
    }

    h1, h2, h3, h4 {
        color: #183B56 !important;
    }

    p, label, .stMarkdown {
        color: #405568;
    }

    .app-hero {
        padding: 24px 28px;
        border-radius: 18px;
        background: linear-gradient(135deg, #E8F3FF 0%, #FFFFFF 60%, #EAF8F2 100%);
        border: 1px solid #D9E8F4;
        box-shadow: 0 8px 26px rgba(35, 75, 105, 0.08);
        margin-bottom: 22px;
    }

    .app-hero h1 {
        margin: 0;
        color: #183B56 !important;
    }

    .app-hero p {
        margin: 8px 0 0;
        color: #66798B !important;
    }

    .feature-card {
        padding: 16px 18px;
        min-height: 108px;
        border-radius: 15px;
        background: rgba(255,255,255,0.9);
        border: 1px solid #DCE8F1;
        box-shadow: 0 5px 18px rgba(35, 75, 105, 0.05);
    }

    .feature-card .title {
        font-weight: 700;
        color: #183B56;
        margin-bottom: 6px;
    }

    .feature-card .desc {
        color: #687C8E;
        font-size: 0.91rem;
        line-height: 1.45;
    }

    .step-pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #E6F2FF;
        color: #2268A8;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: .5px;
    }

    .soft-info {
        padding: 13px 15px;
        border-radius: 12px;
        background: #EEF7FF;
        border: 1px solid #D6E9FA;
        color: #315773;
    }

    .soft-success {
        padding: 13px 15px;
        border-radius: 12px;
        background: #EDF9F3;
        border: 1px solid #D2EDDF;
        color: #2E5A45;
    }

    div[data-testid="stDataEditor"] {
        border: 1px solid #DCE7F0;
        border-radius: 13px;
        overflow: hidden;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #CFE0EF;
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

st.title("⚡ Electricity Bill Detective & Savings Coach")
st.caption("Understand bill changes, find unusual usage, and plan practical savings.")

# -----------------------------
# Sidebar: household profile
# -----------------------------
st.sidebar.header("Household Profile")
household_size = st.sidebar.number_input("People in household", min_value=1, max_value=20, value=4)
no_ac = st.sidebar.checkbox("No AC", value=True)
appliances = st.sidebar.multiselect(
    "Main appliances",
    ["Fans", "Refrigerator", "TV", "Washing machine", "Microwave", "Water heater", "Other"],
    default=["Fans", "Refrigerator", "TV", "Washing machine", "Microwave"],
)

st.sidebar.info(
    "Start with your own bills. Add more households only with their consent, "
    "and never publish personal bill details."
)


# -----------------------------
# Bill upload / review
# -----------------------------
st.markdown('<span class="step-pill">STEP 01</span>', unsafe_allow_html=True)
st.header("📄 Upload your bills")
st.write(
    "Upload PDF or image bills here. Review the extracted information before using it in the analysis."
)

uploaded_bills = st.file_uploader(
    "Upload up to 5 monthly bills",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_bills:
    if len(uploaded_bills) > 5:
        st.warning("Only the first 5 uploaded bills will be reviewed.")
        uploaded_bills = uploaded_bills[:5]

    for i, bill in enumerate(uploaded_bills, start=1):
        with st.expander(f"Bill {i}: {bill.name}", expanded=(i == 1)):
            st.write(f"**File size:** {bill.size / 1024:.1f} KB")
            if bill.type in ["image/png", "image/jpeg"]:
                st.image(bill, use_container_width=True)
            elif bill.type == "application/pdf":
                st.info("PDF uploaded successfully. Review the original bill and enter verified values in the Monthly Bill History table below.")

            st.caption(
                "For privacy, do not publish consumer numbers, names, addresses, phone numbers, "
                "QR codes, or barcodes from real bills."
            )

st.divider()

# -----------------------------
# Monthly bill data
# -----------------------------
st.markdown('<span class="step-pill">STEP 02</span>', unsafe_allow_html=True)
st.header("Monthly bill history")

st.write(
    "Enter the figures printed on your bills. The app compares kWh, billing days, "
    "daily usage, and bill amount."
)

if "bills" not in st.session_state:
    st.session_state.bills = pd.DataFrame(
        [
            {"Month": "June 2026", "Billing days": 30, "Units (kWh)": 89, "Bill amount (₹)": 740},
            {"Month": "July 2026", "Billing days": 31, "Units (kWh)": 121, "Bill amount (₹)": 1100},
            {"Month": "August 2026", "Billing days": 31, "Units (kWh)": 93, "Bill amount (₹)": 770},
            {"Month": "September 2026", "Billing days": 30, "Units (kWh)": 97, "Bill amount (₹)": 800},
            {"Month": "October 2026", "Billing days": 31, "Units (kWh)": 79, "Bill amount (₹)": 680},
        ]
    )

edited = st.data_editor(
    st.session_state.bills,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Billing days": st.column_config.NumberColumn(min_value=1, step=1),
        "Units (kWh)": st.column_config.NumberColumn(min_value=0, step=1),
        "Bill amount (₹)": st.column_config.NumberColumn(min_value=0, step=10),
    },
)

if st.button("Update analysis", type="primary"):
    st.session_state.bills = edited
    st.rerun()

df = st.session_state.bills.copy()

if len(df) > 0:
    for col in ["Billing days", "Units (kWh)", "Bill amount (₹)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Billing days", "Units (kWh)", "Bill amount (₹)"])
    df["Units/day"] = df["Units (kWh)"] / df["Billing days"]
    df["₹/unit"] = df["Bill amount (₹)"] / df["Units (kWh)"].replace(0, pd.NA)

    # -----------------------------
    # Key metrics
    # -----------------------------
    st.subheader("Bill snapshot")

    c1, c2, c3, c4 = st.columns(4)
    latest = df.iloc[-1]
    c1.metric("Latest usage", f'{latest["Units (kWh)"]:.0f} kWh')
    c2.metric("Latest daily usage", f'{latest["Units/day"]:.2f} kWh/day')
    c3.metric("Latest bill", f'₹{latest["Bill amount (₹)"]:.0f}')
    c4.metric("Months tracked", f"{len(df)}")

    # -----------------------------
    # Detective
    # -----------------------------
    st.markdown('<span class="step-pill">STEP 03</span>', unsafe_allow_html=True)
st.header("🔎 Bill Increase Detective")

    if len(df) >= 2:
        previous = df.iloc[-2]
        current = df.iloc[-1]

        usage_change = current["Units/day"] - previous["Units/day"]
        usage_pct = (
            usage_change / previous["Units/day"] * 100
            if previous["Units/day"] else 0
        )

        bill_pct = (
            (current["Bill amount (₹)"] - previous["Bill amount (₹)"])
            / previous["Bill amount (₹)"]
            * 100
            if previous["Bill amount (₹)"]
            else 0
        )

        if usage_pct > 20:
            st.warning(
                f"Daily electricity usage increased by {usage_pct:.1f}% "
                f"compared with {previous['Month']}."
            )
        elif usage_pct < -20:
            st.success(
                f"Daily electricity usage decreased by {abs(usage_pct):.1f}% "
                f"compared with {previous['Month']}."
            )
        else:
            st.info(
                f"Daily electricity usage changed by {usage_pct:+.1f}% "
                f"compared with {previous['Month']}."
            )

        st.write(
            f"**Bill amount change:** {bill_pct:+.1f}%  \n"
            f"**Daily usage change:** {usage_pct:+.1f}%"
        )

        st.caption(
            "A higher bill does not automatically mean higher appliance usage. "
            "Billing days, tariff/charges, arrears, adjustments, and other bill "
            "components can also affect the amount."
        )

    # -----------------------------
    # History table + chart
    # -----------------------------
    st.markdown('<span class="step-pill">STEP 04</span>', unsafe_allow_html=True)
st.header("📊 Usage history")

    display_df = df[
        ["Month", "Billing days", "Units (kWh)", "Units/day", "Bill amount (₹)", "₹/unit"]
    ].copy()
    display_df["Units/day"] = display_df["Units/day"].round(2)
    display_df["₹/unit"] = display_df["₹/unit"].round(2)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    chart_df = df.set_index("Month")

    fig1, ax1 = plt.subplots()
    ax1.plot(chart_df.index, chart_df["Units (kWh)"], marker="o")
    ax1.set_ylabel("Units (kWh)")
    ax1.set_title("Monthly electricity usage")
    ax1.tick_params(axis="x", rotation=45)
    fig1.tight_layout()
    st.pyplot(fig1)

    fig2, ax2 = plt.subplots()
    ax2.plot(chart_df.index, chart_df["Units/day"], marker="o")
    ax2.set_ylabel("kWh/day")
    ax2.set_title("Daily-normalized usage")
    ax2.tick_params(axis="x", rotation=45)
    fig2.tight_layout()
    st.pyplot(fig2)

    # -----------------------------
    # Savings coach
    # -----------------------------
    st.markdown('<span class="step-pill">STEP 05</span>', unsafe_allow_html=True)
st.header("💡 Savings Coach")

    recommendations = []

    if latest["Units/day"] >= 3.5:
        recommendations.append(
            "Your latest daily usage is relatively high compared with the recent "
            "history. Start by checking fans, refrigerator operation, water heating, "
            "and long-running appliances."
        )
    else:
        recommendations.append(
            "Your latest daily usage is lower than several earlier months. "
            "Keep the habits that helped reduce consumption and monitor the next bill."
        )

    if "Fans" in appliances:
        recommendations.append(
            "Fans: track how many hours they run each day and avoid leaving unused fans running."
        )

    if "Refrigerator" in appliances:
        recommendations.append(
            "Refrigerator: check door-seal condition, temperature setting, and whether "
            "the compressor seems to run unusually often."
        )

    if "Washing machine" in appliances:
        recommendations.append(
            "Washing machine: group loads where practical instead of running very small loads repeatedly."
        )

    if "TV" in appliances:
        recommendations.append(
            "TV: switch it off at the wall when it will not be used for a long period."
        )

    if "Microwave" in appliances:
        recommendations.append(
            "Microwave: its individual contribution depends strongly on usage time, "
            "so measure before assuming it is a major source."
        )

    for item in recommendations:
        st.write("• " + item)

    st.info(
        "These are investigation suggestions, not guaranteed savings. "
        "The next step is to connect recommendations to measured changes in your bill history."
    )

    # -----------------------------
    # Experiment tracker
    # -----------------------------
    st.markdown('<span class="step-pill">STEP 06</span>', unsafe_allow_html=True)
st.header("🧪 Savings Experiment Tracker")

    st.write(
        "Record one change you make at home and compare the following billing period."
    )

    with st.form("experiment"):
        experiment = st.text_input(
            "What change did you try?",
            placeholder="Example: reduced unnecessary fan running",
        )
        before_usage = st.number_input(
            "Before daily usage (kWh/day)",
            min_value=0.0,
            value=0.0,
            step=0.1,
        )
        after_usage = st.number_input(
            "After daily usage (kWh/day)",
            min_value=0.0,
            value=0.0,
            step=0.1,
        )
        submitted = st.form_submit_button("Calculate change")

    if submitted:
        if before_usage > 0:
            change = (after_usage - before_usage) / before_usage * 100
            if change < 0:
                st.success(f"Daily usage changed by {change:.1f}% — a reduction.")
            elif change > 0:
                st.warning(f"Daily usage changed by +{change:.1f}%.")
            else:
                st.info("No change in daily usage was recorded.")

            st.caption(
                "This comparison is observational. Weather, occupancy, appliance use, "
                "billing-period length, and other factors can affect the result."
            )
        else:
            st.error("Enter a before-usage value greater than 0.")

st.divider()
st.caption(
    "Prototype: Electricity Bill Detective & Savings Coach. "
    "Verify official tariff and bill rules before using financial estimates."
)
