# Electricity Bill Detective & Savings Coach

A browser-deployable Streamlit project for household electricity-bill analysis.

## Included
- Smooth light-blue/light-mint visual theme
- Bill PDF/photo upload section
- PDF text extraction when the PDF contains selectable text
- Optional image OCR with graceful fallback to manual entry
- Review-before-saving workflow
- Five-month sample history (June–October 2026)
- Daily kWh normalization
- Bill Increase Detective
- Usage charts
- Appliance-aware Savings Coach
- Savings Experiment Tracker

## GitHub + Streamlit Cloud
Upload the files in this folder to your GitHub repository. Set the Streamlit entry point to `app.py`.

## Privacy
Do not publish consumer numbers, names, addresses, phone numbers, QR codes, barcodes, or other personal bill identifiers. For other households, collect consent before storing or analyzing their bills.

## OCR note
PDF extraction works without an OCR engine for text-based PDFs. Image OCR requires a working Tesseract installation in the deployment environment; if OCR is unavailable, the app remains usable through manual review and entry.
