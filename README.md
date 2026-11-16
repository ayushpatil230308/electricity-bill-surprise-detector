# BillWise India ⚡

Understand your electricity bill, track usage and predict your next bill.
Built for Indian consumers (especially MSEDCL / Mahavitaran, Maharashtra) with
Python, Streamlit, Pandas, Plotly and Tesseract OCR.

## Features
- Upload up to 5 bills (PDF / PNG / JPG / JPEG) and scan each with **Scan This Bill**
- OCR in English, Hindi and Marathi (PDF text layer first, OCR fallback for scanned/garbled PDFs)
- **Never trusts OCR**: every value is editable, suspicious values show "⚠ Please verify this value"
- Monthly insights, month-to-month change (N/A when previous value is 0), Plotly charts
- Bill surprise detector, next-month estimate with range, personalised saving tips
- No fake data: everything comes only from bills you verified and saved

## How the prediction works (transparent, not a black-box ML model)
1. Previous 2-month average = (older + latest) / 2
2. Weighted average of recent bills (60/40 for 2 bills, 50/30/20 for 3+)
3. If verified units exist: expected units = latest units + half of the latest change (clamped ±20%),
   multiplied by your recent cost per kWh
4. Estimate = mean of (2) and (3); range from recent bill variation (minimum ±8%)
5. With fewer than 2 bills: "Not enough verified history for a reliable prediction." plus a clearly labelled simple estimate

## Project structure
```
app.py            Streamlit UI
analytics.py      comparison, prediction, surprise detection, saving tips
ocr_utils.py      text extraction + field detection (DISCOM, month, units, amount)
validation.py     OCR-error and data checks
helpers.py        formatting + safe HTML tables
styles.py         high-contrast CSS theme
requirements.txt  Python packages
packages.txt      system packages for Streamlit Cloud (Tesseract, languages, Poppler)
.streamlit/config.toml  theme
tests/            regression tests (synthetic data)
```

## Deploy on Streamlit Cloud (no VS Code needed)
1. Create a GitHub repository and upload all files (GitHub web "Add file → Upload files" works).
   Keep `app.py` at the repository root.
2. Go to https://share.streamlit.io → **New app** → choose the repo, branch `main`, main file `app.py`.
3. Deploy. Streamlit Cloud installs `requirements.txt` and `packages.txt` automatically.

## Run locally (optional)
```
pip install -r requirements.txt
# install Tesseract + eng/hin/mar language data (e.g. sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar)
streamlit run app.py
```

## Tested on real MSEDCL bills
Tested on five real MSEDCL / Mahavitaran LT residential bills (Jun-Oct 2026, bilingual Marathi/English PDFs).
All five read correctly (billing month, units, final payable amount), both from the PDF text layer and
from image-only OCR. Notes on how MSEDCL bills are handled:
- The PDF text layer has clean numbers but garbled Marathi labels, so the text layer is parsed first and OCR is only a fallback.
- Units come from the meter-reading row (previous reading, multiplier, units, adjustment, total).
- The final payable amount is the amount payable by the due date (the top box of the bill), not the pay-early or pay-late amounts.
- Billing month comes from the bill date, because the "Bill Period" line is followed by the next reading date.
- Other DISCOMs (BEST, Tata Power, BSES, ...) use generic label matching and may need tuning; you can always correct values in the form.

Run the regression tests with `python tests/test_parsing.py`.

## Privacy
Uploaded files are read in memory only and are not written to disk. Verified values live in the
browser session (Streamlit session state) and disappear when the session ends. Use
"Clear all my data" in the sidebar at any time. Avoid uploading bills to public/shared deployments
you do not control.

## Notes
- OCR is best-effort; always check the values against your bill.
- Estimates are not guaranteed; real bills depend on tariff slabs, fuel adjustment charges, taxes and billing days.
