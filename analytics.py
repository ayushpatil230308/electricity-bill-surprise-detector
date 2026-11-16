"""Analysis built ONLY from the user's verified bills. No default or fake data."""
import numpy as np
import pandas as pd

from helpers import MONTH_NAMES, inr, month_label


def bills_df(bills) -> pd.DataFrame:
    cols = ["year", "month", "label", "bill", "units", "state", "discom", "source"]
    if not bills:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(bills).rename(columns={"amount": "bill"})
    df["label"] = [month_label(y, m) for y, m in zip(df["year"], df["month"])]
    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    return df[cols]


def pct_change(cur, prev):
    """((cur - prev) / prev) * 100, or None when prev is missing/zero."""
    if cur is None or prev is None or pd.isna(cur) or pd.isna(prev) or prev == 0:
        return None
    return (cur - prev) / prev * 100.0


def monthly_changes(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["label", "bill", "units"]].copy()
    out["bill_chg"] = [None] + [pct_change(df.bill[i], df.bill[i - 1]) for i in range(1, len(df))]
    out["unit_chg"] = [None] + [pct_change(df.units[i], df.units[i - 1]) for i in range(1, len(df))]
    return out


def summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    has_units = df.units.fillna(0) > 0
    return {
        "count": len(df),
        "avg_bill": df.bill.mean(),
        "avg_units": df.units[has_units].mean() if has_units.any() else None,
        "max_bill": df.bill.max(), "max_label": df.label[df.bill.idxmax()],
        "min_bill": df.bill.min(), "min_label": df.label[df.bill.idxmin()],
    }


# --------------------------------------------------------------- prediction
def _next_period(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)


def predict_next(df: pd.DataFrame) -> dict:
    """Transparent estimate from verified history (weighted average + unit trend)."""
    n = len(df)
    if n == 0:
        return {"status": "none"}
    ny, nm = _next_period(int(df.year.iloc[-1]), int(df.month.iloc[-1]))
    res = {"next_label": month_label(ny, nm), "n": n}
    bills = [float(b) for b in df.bill]
    last = bills[-1]

    if n == 1:
        res.update(status="insufficient",
                   message="Not enough verified history for a reliable prediction.",
                   estimate=last, low=last * 0.85, high=last * 1.15, last=last,
                   note=f"Simple estimate only: assumes next month is similar to your single verified bill ({inr(last)}). Upload at least 2 months for a trend-based estimate.")
        return res

    prev = bills[-2]
    avg2 = (last + prev) / 2
    steps = [f"Previous 2-month average = ({inr(prev)} + {inr(last)}) / 2 = {inr(avg2)}."]

    if n >= 3:
        w = (0.5, 0.3, 0.2)
        weighted = w[0] * bills[-1] + w[1] * bills[-2] + w[2] * bills[-3]
        steps.append(f"Weighted average of last 3 bills (50% / 30% / 20%, newest first) = {inr(weighted)}.")
    else:
        weighted = 0.6 * last + 0.4 * prev
        steps.append(f"Weighted average of last 2 bills (60% newest / 40% older) = {inr(weighted)}.")

    # unit-based estimate
    u = [float(x) if pd.notna(x) else 0.0 for x in df.units]
    unit_info = None
    estimate = weighted
    if n >= 2 and u[-1] > 0 and u[-2] > 0:
        u_last, u_prev = u[-1], u[-2]
        rate = (last + prev) / (u_last + u_prev)
        exp_units = u_last + 0.5 * (u_last - u_prev)
        exp_units = float(np.clip(exp_units, 0.8 * min(u_last, u_prev), 1.2 * max(u_last, u_prev)))
        unit_bill = exp_units * rate
        estimate = 0.5 * weighted + 0.5 * unit_bill
        chg = pct_change(u_last, u_prev)
        direction = "increasing" if chg > 3 else ("decreasing" if chg < -3 else "steady")
        steps.append(f"Recent cost per unit = ({inr(prev)} + {inr(last)}) / ({u_prev:g} + {u_last:g} kWh) = ₹{rate:.2f} per kWh.")
        steps.append(f"Expected units = latest units + half of the latest change = {exp_units:.0f} kWh (kept within ±20% of recent months). Unit-based bill = {inr(unit_bill)}.")
        steps.append(f"Final estimate = average of the weighted-bill value and the unit-based value = {inr(estimate)}.")
        unit_info = {"prev_units": u_prev, "cur_units": u_last, "exp_units": exp_units,
                     "direction": direction, "rate": rate, "unit_bill": unit_bill}
    else:
        steps.append("Verified units are not available for the last 2 bills, so only bill history was used.")

    spread_opts = [abs(last - prev) / 2, 0.08 * estimate]
    if n >= 3:
        spread_opts.append(0.8 * float(np.std(bills[-4:], ddof=1)))
    spread = max(spread_opts)
    confidence = "Low (2 bills)" if n == 2 else ("Medium (3–5 bills)" if n < 6 else "Higher (6+ bills)")
    res.update(status="ok", last=last, prev=prev, avg2=avg2, estimate=estimate,
               low=max(0.0, estimate - spread), high=estimate + spread,
               steps=steps, unit_info=unit_info, confidence=confidence)
    return res


# ----------------------------------------------------------- bill surprise
def detect_surprise(df: pd.DataFrame, threshold: float = 20.0):
    """Compare the latest bill with the average of up to 3 bills before it."""
    if len(df) < 2:
        return None
    base = df.iloc[max(0, len(df) - 4):-1]
    cur = df.iloc[-1]
    avg = float(base.bill.mean())
    inc = pct_change(float(cur.bill), avg)
    if inc is None:
        return None
    reasons = []
    flagged = inc >= threshold
    if flagged:
        b_units = base.units[base.units.fillna(0) > 0]
        u_inc = pct_change(cur.units, b_units.mean()) if len(b_units) and cur.units and cur.units > 0 else None
        if u_inc is not None and u_inc >= 10:
            reasons.append(f"Higher electricity usage – units are about {u_inc:.0f}% above your recent average.")
        elif u_inc is not None:
            reasons.append(f"Units changed only {u_inc:+.0f}% while the bill rose, so tariff or other charges (fuel adjustment, taxes, arrears) may be involved.")
        reasons += ["Seasonal appliance usage (AC, cooler, geyser or heater).",
                    "A longer billing cycle (more days than usual).",
                    "Tariff or charge changes – check the charges breakdown on the bill."]
    return {"flagged": flagged, "current": float(cur.bill), "label": cur.label,
            "average": avg, "increase": inc, "reasons": reasons, "base_count": len(base)}


# ------------------------------------------------------------ saving tips
def savings_tips(df: pd.DataFrame):
    """Practical tips tied to the user's own verified numbers."""
    if df.empty:
        return []
    has_u = df.units.fillna(0) > 0
    tips = []
    avg_units = float(df.units[has_u].mean()) if has_u.any() else None
    rate = float(df.bill[has_u].sum() / df.units[has_u].sum()) if has_u.any() else None

    if avg_units and rate:
        tips.append(("Know what a unit costs you",
                     f"Your effective cost is about ₹{rate:.2f} per kWh (bill ÷ units, including all charges). Saving 10% of your average {avg_units:.0f} kWh ≈ {avg_units * 0.1:.0f} kWh ≈ {inr(avg_units * 0.1 * rate)} every month."))
        if avg_units >= 250:
            tips.append(("Cooling is likely your biggest load",
                         f"At {avg_units:.0f} kWh/month an AC probably contributes a lot. Running a ~1.5-ton AC 1 hour less per day saves roughly 35–45 kWh/month (≈ {inr(40 * rate)}). Set it to 24–26 °C and use the fan/sleep mode."))
        elif avg_units >= 100:
            tips.append(("Check lighting and fans",
                         f"If you still use old 40–60 W bulbs/tubes, replacing 5 of them with 9 W LEDs (5 hrs/day) saves about 35 kWh/month (≈ {inr(35 * rate)}). BLDC fans use roughly half the power of regular fans."))
        else:
            tips.append(("You are already a low user",
                         f"At about {avg_units:.0f} kWh/month, focus on the always-on loads: fridge door seals, standby devices and old bulbs."))
        tips.append(("Cut standby power",
                     f"TVs, set-top boxes, chargers and routers on standby often add 5–10% to home usage – roughly {avg_units * 0.05:.0f}–{avg_units * 0.10:.0f} kWh ({inr(avg_units * 0.05 * rate)}–{inr(avg_units * 0.10 * rate)}) a month for you. Use a switched power strip."))
    else:
        tips.append(("Add units to unlock personal tips",
                     "Your saved bills have no verified units, so tips below are general. Edit or re-save bills with units for usage-based advice."))
        tips.append(("Cut standby power", "Switch off TVs, set-top boxes and chargers at the socket when not in use."))

    if len(df) >= 2:
        chg = pct_change(df.units.iloc[-1], df.units.iloc[-2])
        if chg is not None and chg >= 10:
            tips.append(("Your usage just went up",
                         f"Units rose {chg:.0f}% from {df.label.iloc[-2]} to {df.label.iloc[-1]}. List any appliance you started using more (AC, geyser, pump, new devices) and check its hours of use."))
    hi = df.loc[df.bill.idxmax()]
    if len(df) >= 2:
        tips.append(("Plan around your highest bill",
                     f"{hi.label} was your highest bill ({inr(hi.bill)}). Compare what was different that month and set a target slightly below it."))
    tips.append(("Choose efficient appliances",
                 "When replacing an AC, fridge or geyser, pick inverter/5-star (BEE) models. Run washing machines and pumps with full loads, and use a geyser timer."))
    return tips
