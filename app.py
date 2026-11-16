"""BillWise India – Indian electricity bill analysis & prediction (Streamlit)."""
import datetime as dt
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics
import ocr_utils
import validation
from helpers import MONTH_NAMES, STATES, fmt_pct, html_table, inr, kwh, month_label
from styles import CSS

st.set_page_config(page_title="BillWise India", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

NAVY, BLUE, CYAN, AMBER, INK = "#0B2A5B", "#0A6CFF", "#22B8E8", "#F5A400", "#0B1F3A"
MAX_FILES = 5

# ------------------------------------------------------------------ state
ss = st.session_state
ss.setdefault("bills", [])    # verified bills only (kept in this browser session, never on disk)
ss.setdefault("scans", {})    # per-file scan results (text + detected values, no file bytes)
ss.setdefault("flash", [])


def card(title, body_html):
    st.markdown(f'<div class="bw-card"><h4>{title}</h4>{body_html}</div>', unsafe_allow_html=True)


def metric(label, value, sub=""):
    st.markdown(f'<div class="bw-metric"><div class="l">{html.escape(label)}</div>'
                f'<div class="v">{html.escape(str(value))}</div><div class="s">{html.escape(sub)}</div></div>',
                unsafe_allow_html=True)


def box(kind, text):
    st.markdown(f'<div class="bw-{kind}">{text}</div>', unsafe_allow_html=True)


def show_chart(fig):
    cfg = {"displayModeBar": False}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg)


def style_fig(fig, xtitle, ytitle, categories=None):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, size=13), margin=dict(l=60, r=20, t=30, b=60), height=360,
        legend=dict(orientation="h", y=-0.28, font=dict(color=INK)),
    )
    fig.update_xaxes(title=dict(text=xtitle, font=dict(color=INK)), tickfont=dict(color=INK),
                     gridcolor="rgba(11,42,91,.10)", linecolor="#9CB3D1")
    fig.update_yaxes(title=dict(text=ytitle, font=dict(color=INK)), tickfont=dict(color=INK),
                     gridcolor="#E1ECF8", linecolor="#9CB3D1", rangemode="tozero")
    try:  # rounded bars (needs a recent Plotly); silently skipped otherwise
        fig.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
    except Exception:
        pass
    if categories is not None:
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=categories)
    return fig


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## Bill Settings")
    language = st.selectbox("Main bill language", ["English", "Hindi", "Marathi"], index=2,
                            help="Used to choose the OCR language for scanned bills. MSEDCL bills are mostly Marathi.")
    st.markdown("**OCR settings**")
    force_ocr = st.checkbox("Force OCR for scanned/garbled PDFs",
                            help="Ignore the PDF's own text and read the page image instead.")
    dpi = st.slider("OCR quality (resolution, DPI)", 150, 400, 250, 50,
                    help="Higher is more accurate but slower.")
    ready, langs_ok = ocr_utils.ocr_status()
    if ready:
        box("ok", f"<b>OCR Ready:</b> {', '.join(langs_ok) if langs_ok else 'English'}")
        missing = [l for l in ("English", "Hindi", "Marathi") if l not in langs_ok]
        if missing:
            box("info", f"Language data not installed: {', '.join(missing)}. See packages.txt.")
    else:
        box("warn", "<b>OCR not available</b> on this server. You can still enter bill values manually.")
    st.markdown("---")
    st.markdown("**Privacy**")
    st.caption("Bills are processed in memory only. Files are not saved to disk or shared. "
               "Your verified values live in this browser session and disappear when you close it.")
    if st.button("Clear all my data"):
        ss.bills, ss.scans, ss.flash = [], {}, []
        st.rerun()

# ------------------------------------------------------------------- hero
st.markdown("""
<div class="bw-hero">
  <h1>BillWise India <span class="bolt">⚡</span></h1>
  <p>Understand your electricity bill, track usage and predict your next bill.</p>
  <span class="bw-badge">Monthly Bill Analysis</span><span class="bw-badge">OCR Bill Scanner</span>
  <span class="bw-badge">Bill Comparison</span><span class="bw-badge">Bill Prediction</span>
  <span class="bw-badge">Energy Saving Insights</span>
  <div class="bw-spark"></div>
</div>
""", unsafe_allow_html=True)

st.markdown("## Dashboard")
st.markdown("**Your electricity, made easier to understand.**")
st.write("Upload your monthly bills, review detected values and turn your bill history into useful insights.")
c1, c2, c3 = st.columns(3)
with c1:
    card("🔎 Scan Your Bills",
         "<p>Upload electricity bills and extract:</p><ul><li>Billing month</li><li>Units consumed</li>"
         "<li>Final payable amount</li><li>Electricity company/DISCOM</li><li>State/UT</li></ul>")
with c2:
    card("📈 Understand Changes",
         "<p>Compare monthly:</p><ul><li>Bill amount</li><li>Electricity units</li>"
         "<li>Percentage changes</li><li>Usage trends</li></ul>")
with c3:
    card("💡 Discover Savings",
         "<p>Get practical electricity-saving recommendations linked to your own verified usage.</p>")
FLOW = ["Upload", "Scan", "Review", "Correct", "Save", "Insights", "Comparison", "Charts",
        "Surprise check", "Prediction", "Savings"]
st.markdown('<div class="bw-steps">' + "".join(f"<span>{html.escape(x)}</span>" for x in FLOW) + "</div>",
            unsafe_allow_html=True)


# ------------------------------------------------------- review/save form
def review_form(form_key, parsed, source):
    """Editable verification form. Nothing is saved until the user confirms."""
    today = dt.date.today()
    p_month = parsed.get("month") or today.month
    p_year = parsed.get("year") or today.year
    p_units = parsed.get("units")
    p_amount = parsed.get("amount")

    # Evidence-based flags BEFORE the user edits anything
    pre = validation.validate_bill(p_year, p_month, p_units, p_amount, ss.bills) if parsed.get("scanned") else []
    for n in parsed.get("notes", []):
        box("warn", f"⚠ {html.escape(n)}")
    for n in parsed.get("info", []):
        box("info", f"ℹ {html.escape(n)}")
    for i in pre:
        if i["field"] != "duplicate":
            box("warn", f"⚠ Please verify this value: {html.escape(i['msg'])}")
    alt = validation.suggest_amounts(p_units, parsed.get("amount_candidates", []))
    if p_amount and alt and p_amount not in alt:
        box("info", "Other amounts found on this bill that fit the units better: "
            + ", ".join(inr(a) for a in alt[:4]) + ". Check which one is the final payable amount.")

    st.markdown("##### Review and Correct Detected Details")
    with st.form(form_key):
        a, b = st.columns(2)
        month = a.selectbox("Billing Month", list(range(1, 13)), index=p_month - 1,
                            format_func=lambda m: MONTH_NAMES[m - 1], key=f"{form_key}_m")
        year = b.number_input("Billing Year", 2015, 2100, int(p_year), 1, key=f"{form_key}_y")
        units = a.number_input("Units Consumed (kWh)", 0.0, 1_000_000.0, float(p_units or 0.0), 1.0, key=f"{form_key}_u")
        amount = b.number_input("Final Payable Amount (₹)", 0.0, 10_000_000.0, float(p_amount or 0.0), 10.0, key=f"{form_key}_a")
        discom = a.text_input("Electricity Company / DISCOM", parsed.get("discom", ""), key=f"{form_key}_d")
        state_opts = ["— Select —"] + STATES
        s_idx = state_opts.index(parsed["state"]) if parsed.get("state") in STATES else 0
        state = b.selectbox("State / UT", state_opts, index=s_idx, key=f"{form_key}_s")
        confirm = st.checkbox("I have checked every highlighted value against my bill and it is correct",
                              key=f"{form_key}_c")
        submitted = st.form_submit_button("Save Verified Bill")

    if submitted:
        issues = validation.validate_bill(int(year), int(month), units, amount, ss.bills)
        errors = [i for i in issues if i["level"] == validation.ERROR]
        warns = [i for i in issues if i["level"] == validation.WARN]
        if state == "— Select —":
            warns.append({"level": "warn", "field": "state", "msg": "State/UT is not selected."})
        for e in errors:
            st.error(e["msg"])
        if errors:
            return False
        if warns and not confirm:
            for w in warns:
                box("warn", f"⚠ Please verify this value: {html.escape(w['msg'])}")
            st.info("Correct the values above, or tick the confirmation box if they match your bill, then save again.")
            return False
        ss.bills = [x for x in ss.bills if not (x["year"] == int(year) and x["month"] == int(month))]
        ss.bills.append({"year": int(year), "month": int(month), "amount": float(amount), "units": float(units),
                         "state": "" if state == "— Select —" else state,
                         "discom": discom.strip(), "source": source})
        ss.flash.append(f"Saved verified bill for {month_label(int(year), int(month))}.")
        return True
    return False


# ----------------------------------------------------------------- upload
st.markdown("## 1. Upload Bills")
for msg in ss.flash:
    box("ok", "✅ " + html.escape(msg))
ss.flash = []

files = st.file_uploader(f"Upload up to {MAX_FILES} monthly electricity bills (PDF, PNG, JPG, JPEG)",
                         type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
if files and len(files) > MAX_FILES:
    st.warning(f"Only the first {MAX_FILES} files will be used.")
    files = files[:MAX_FILES]

for f in files or []:
    key = f"{f.name}-{f.size}"
    st.markdown(f'<div class="bw-file">📄 {html.escape(f.name)} · {f.size / 1024:.0f} KB</div>', unsafe_allow_html=True)
    scan = ss.scans.get(key)
    if scan and scan.get("saved"):
        box("ok", "✅ Verified and saved. Scroll down for insights.")
        continue
    if st.button("Scan This Bill", key=f"scan_{key}"):
        with st.spinner("Reading your bill…"):
            try:
                text, method, notes = ocr_utils.extract_text(f.getvalue(), f.name, language, force_ocr, dpi)
                parsed = ocr_utils.parse_bill(text)
            except Exception:
                text, method, notes, parsed = "", "none", ["We could not read this bill. Please enter the values manually."], {}
            parsed = {**{"notes": [], "amount_candidates": []}, **parsed}
            parsed["notes"] = notes + parsed.get("notes", [])
            parsed["scanned"] = True
            ss.scans[key] = {"text": text, "method": method, "parsed": parsed, "saved": False}
        scan = ss.scans[key]
    if scan:
        parsed = scan["parsed"]
        st.caption(f"Reading method: {scan['method']}. Detected values are suggestions only – please verify them.")
        if parsed.get("amount") is None:
            box("warn", "⚠ We could not confidently detect the bill amount. Please enter it manually.")
        with st.expander("OCR Output – Verify It"):
            txt = scan["text"].strip() or "(No text could be read from this file.)"
            st.markdown(f'<div class="bw-ocr">{html.escape(txt[:6000])}</div>', unsafe_allow_html=True)
        if review_form(f"form_{key}", parsed, f.name):
            scan["saved"] = True
            st.rerun()

with st.expander("No file or OCR not working? Add a bill manually"):
    if review_form("form_manual", {"scanned": False, "notes": [], "amount_candidates": []}, "Manual entry"):
        st.rerun()

# -------------------------------------------------------------- analytics
df = analytics.bills_df(ss.bills)
st.markdown("## 2. Monthly Insights")
if df.empty:
    box("info", "No verified bills yet. Upload and verify a bill above – nothing is shown until you save real data.")
    st.stop()

s = analytics.summary(df)
m1, m2, m3, m4, m5 = st.columns(5)
with m1: metric("Bills Saved", s["count"], "verified bills")
with m2: metric("Average Monthly Bill", inr(s["avg_bill"]), "verified bills only")
with m3: metric("Average Monthly Usage", kwh(s["avg_units"]) if s["avg_units"] else "N/A", "verified units only")
with m4: metric("Highest Bill", inr(s["max_bill"]), s["max_label"])
with m5: metric("Lowest Bill", inr(s["min_bill"]), s["min_label"])

rows = [[r.label, inr(r.bill), kwh(r.units), r.state or "—", r.discom or "—", r.source] for r in df.itertuples()]
st.markdown(html_table(["Billing Month", "Bill Amount", "Units", "State/UT", "DISCOM", "Source File"], rows),
            unsafe_allow_html=True)

dl, rm = st.columns([1, 2])
with dl:
    st.download_button("Download verified bills (CSV)", df.rename(columns={"bill": "bill_amount_inr"}).to_csv(index=False),
                       "billwise_verified_bills.csv", "text/csv")
with rm:
    with st.expander("Manage saved bills"):
        pick = st.selectbox("Select a bill", df.label.tolist(), key="rm_pick")
        if st.button("Remove selected bill"):
            r = df[df.label == pick].iloc[0]
            ss.bills = [b for b in ss.bills if not (b["year"] == r.year and b["month"] == r.month)]
            st.rerun()

# --------------------------------------------------------- comparison
st.markdown("## 3. Month-to-Month Changes")
if len(df) < 2:
    box("info", "Save at least 2 months to see changes.")
else:
    ch = analytics.monthly_changes(df)
    rows = [[r.label, inr(r.bill), fmt_pct(r.bill_chg), kwh(r.units), fmt_pct(r.unit_chg)] for r in ch.itertuples()]
    st.markdown(html_table(["Billing Month", "Bill Amount", "Bill Change (%)", "Units Consumed", "Usage Change (%)"], rows),
                unsafe_allow_html=True)
    st.caption("Change % = ((current − previous) ÷ previous) × 100. Shown as N/A when the previous value is zero or missing.")

# ------------------------------------------------------------- charts
st.markdown("## 4. Usage & Bill Charts")
pred = analytics.predict_next(df)
labels = df.label.tolist()

st.markdown("##### Monthly Bill Amount")
fig = go.Figure(go.Bar(x=labels, y=df.bill, name="Verified bill", marker_color=BLUE,
                       text=[inr(v) for v in df.bill], textposition="outside", cliponaxis=False,
                       textfont=dict(color=INK)))
cats = list(labels)
top = float(df.bill.max())
if pred.get("status") == "ok":
    est = pred["estimate"]
    fig.add_bar(x=[pred["next_label"]], y=[est], name="Estimated next bill", marker_color=AMBER,
                text=[inr(est)], textposition="outside", cliponaxis=False, textfont=dict(color=INK),
                error_y=dict(type="data", symmetric=False, array=[pred["high"] - est],
                             arrayminus=[est - pred["low"]], color=NAVY))
    cats.append(pred["next_label"])
    top = max(top, pred["high"])
fig.update_yaxes(range=[0, top * 1.25])
show_chart(style_fig(fig, "Billing Month", "Bill Amount (₹)", cats))

has_units = (df.units.fillna(0) > 0)
st.markdown("##### Monthly Electricity Usage")
if has_units.any():
    d = df[has_units]
    fig = go.Figure(go.Scatter(x=d.label, y=d.units, mode="lines+markers+text", name="Units",
                               line=dict(color=BLUE, width=3), marker=dict(size=10, color=CYAN, line=dict(color=NAVY, width=2)),
                               text=[f"{u:.0f}" for u in d.units], textposition="top center", textfont=dict(color=INK)))
    fig.update_yaxes(range=[0, float(d.units.max()) * 1.25])
    show_chart(style_fig(fig, "Billing Month", "Units (kWh)", d.label.tolist()))
else:
    box("info", "No verified units yet, so the usage chart is hidden.")

st.markdown("##### Bill vs Usage")
if has_units.sum() >= 2:
    d = df[has_units]
    fig = go.Figure(go.Scatter(x=d.units, y=d.bill, mode="markers+text", name="Your bills",
                               marker=dict(size=13, color=BLUE, line=dict(color=NAVY, width=2)),
                               text=d.label, textposition="top center", textfont=dict(color=INK)))
    if d.units.nunique() >= 2:
        k, c = np.polyfit(d.units, d.bill, 1)
        xs = np.linspace(d.units.min(), d.units.max(), 20)
        fig.add_trace(go.Scatter(x=xs, y=k * xs + c, mode="lines", name="Trend (fit to your bills)",
                                 line=dict(color=AMBER, width=2, dash="dash")))
    fig.update_xaxes(rangemode="tozero")
    show_chart(style_fig(fig, "Units (kWh)", "Bill Amount (₹)"))
else:
    box("info", "Save at least 2 bills with units to see the bill-vs-usage relationship.")

# ----------------------------------------------------------- surprise
st.markdown("## 5. Bill Surprise Detector")
sur = analytics.detect_surprise(df)
if sur is None:
    box("info", "Save at least 2 months to check for unusually high bills.")
elif sur["flagged"]:
    box("warn", f"<b>⚠ Higher-than-usual bill detected</b> ({html.escape(sur['label'])})")
    a, b, c = st.columns(3)
    with a: metric("Current bill", inr(sur["current"]), sur["label"])
    with b: metric("Average bill", inr(sur["average"]), f"previous {sur['base_count']} month(s)")
    with c: metric("Increase", f"{sur['increase']:+.0f}%", "vs average")
    st.markdown("**Possible reasons (suggestions, not confirmed facts):**")
    for r in sur["reasons"]:
        st.markdown(f"- {r}")
else:
    box("ok", f"✅ Your latest bill ({inr(sur['current'])}) is within the usual range "
              f"(recent average {inr(sur['average'])}, {sur['increase']:+.0f}%).")

# --------------------------------------------------------- prediction
st.markdown("## 6. Next Month Bill Prediction")
if pred["status"] == "insufficient":
    box("warn", "<b>Not enough verified history for a reliable prediction.</b>")
    st.markdown(f'<div class="bw-predict"><div class="l">Simple estimate for {pred["next_label"]} (not a reliable forecast)</div>'
                f'<div class="big">{inr(pred["estimate"])}</div>'
                f'<div class="r">Rough range: {inr(pred["low"])} – {inr(pred["high"])}</div></div>', unsafe_allow_html=True)
    st.write(pred["note"])
else:
    a, b = st.columns(2)
    with a: metric("Previous Month Bill", inr(pred["last"]), df.label.iloc[-1])
    with b: metric("Previous 2-Month Average", inr(pred["avg2"]), f"{df.label.iloc[-2]} & {df.label.iloc[-1]}")
    st.markdown(f'<div class="bw-predict"><div class="l">Estimated next bill – {pred["next_label"]}</div>'
                f'<div class="big">{inr(pred["estimate"])}</div>'
                f'<div class="r">Expected range: {inr(pred["low"])} – {inr(pred["high"])}</div>'
                f'<div class="l">Confidence: {pred["confidence"]}</div></div>', unsafe_allow_html=True)
    with st.expander("How this estimate was calculated", expanded=True):
        for step in pred["steps"]:
            st.markdown(f"- {step}")
        st.markdown("- Seasonal effects (summer/winter) are not modelled with so little history.")
    ui = pred["unit_info"]
    if ui:
        st.markdown("##### Usage Trend")
        u1, u2, u3, u4 = st.columns(4)
        with u1: metric("Previous units", kwh(ui["prev_units"]))
        with u2: metric("Current units", kwh(ui["cur_units"]), f"trend {ui['direction']}")
        with u3: metric("Expected next-month units", kwh(ui["exp_units"]))
        with u4: metric("Expected bill", inr(pred["estimate"]), f"unit-based part {inr(ui['unit_bill'])}")
box("info", "Prediction is an estimate based on your verified bill history. Actual charges may vary depending on "
            "units, tariff, taxes and other charges.")

# ------------------------------------------------------------- savings
st.markdown("## 7. Energy Saving Insights")
tips = analytics.savings_tips(df)
cols = st.columns(2)
for i, (title, body) in enumerate(tips):
    with cols[i % 2]:
        card(html.escape(title), f"<p>{html.escape(body)}</p>")
        st.write("")
st.caption("Savings figures are approximate and use your own average cost per unit. Real savings depend on your appliances and habits.")
