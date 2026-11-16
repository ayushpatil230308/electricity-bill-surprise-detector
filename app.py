import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Electricity Bill Detective",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #F7F9FC; color: #17212B; }
    [data-testid="stSidebar"] { background-color: #EAF2FB; }
    [data-testid="stSidebar"] * { color: #17212B !important; }
    h1, h2, h3, h4 { color: #0D2A43 !important; }
    .stMarkdown, .stText, p, label { color: #17212B; }
    div[data-testid="stAlert"] p { color: #17212B !important; }
    div[data-testid="stAlert"][kind="info"] { background-color: #E3F2FD; }
    div[data-testid="stAlert"][kind="warning"] { background-color: #FFF4D6; }
    div[data-testid="stAlert"][kind="success"] { background-color: #E8F5E9; }
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
# Monthly bill data
# -----------------------------
st.header("1. Monthly bill history")

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
    st.header("2. 🔎 Bill Increase Detective")

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
    st.header("3. 📊 Usage history")

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
    st.header("4. 💡 Savings Coach")

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
    st.header("5. 🧪 Savings Experiment Tracker")

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
