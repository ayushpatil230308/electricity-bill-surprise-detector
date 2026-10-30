# BillWise India — Fast OCR & Review Update

## What's improved in this build
- Upload up to five electricity bills (PDF, PNG, JPG/JPEG).
- Bills are scanned **one at a time** when the user clicks **Scan this bill**, rather than running OCR on every uploaded bill during every page refresh.
- Repeated scans are cached for the current Streamlit session.
- Text-based PDFs use their embedded text first (fast path). OCR is used when text is missing/garbled or when Force OCR is enabled.
- Default OCR resolution is reduced to 2x for a faster first pass; increase it if a scanned bill is unclear.
- Amount candidates are extracted only when a rupee marker (`₹`, `Rs`, `INR`) is present. Dates and years are no longer treated as currency candidates.
- Month detection prefers an explicit billing-period label and recognizes MSEDCL filename codes such as `MSEDCL_2609` as September 2026.
- If amount or units cannot be confidently detected, the app warns the user and requires manual verification before saving. It does not silently treat an unrecognized value as valid.
- Air Conditioner is no longer selected by default in the appliance estimator.
- Existing comparison charts, bill-change alerts, appliance estimates, saving tips, and rule-based help remain available.

## Deploy / update on GitHub
1. Download and extract this ZIP.
2. Open the extracted folder.
3. Upload `app.py`, `requirements.txt`, `packages.txt`, and `README.md` to the **root** of your GitHub repository.
4. Commit the changes.
5. In Streamlit Community Cloud, open the app and reboot/redeploy it if it does not update automatically.
6. The main file path must be `app.py`.

## Important testing notes
- This build has been syntax-checked and its month/amount parsing helpers have been tested with sample text. It has **not** been live-tested against all five of your original PDFs or on your Streamlit deployment.
- OCR speed depends on PDF size, page count, scan quality, language and server resources. Scanned PDFs will still take longer than text-based PDFs.
- No generic OCR parser can guarantee correct extraction from every Indian DISCOM format. Always compare month, kWh and final payable amount with the original bill before saving.
- Amount candidates are clues, not a declaration of the payable amount. Prefer the exact `Net Amount Payable` / `Total Amount Due` field on the bill.
- The filename YYMM month fallback is intended for filenames matching a pattern like `MSEDCL_2609`; do not rely on it for arbitrary filenames.
- Five monthly bills are enough for basic comparison, not a dependable trained ML forecast. The displayed trend estimate is illustrative and not a trained ML model.
- Appliance consumption is estimated from wattage and hours entered by the user. A bill alone cannot identify the exact appliance responsible for usage.
- Chatbot answers are rule-based, not a live generative AI service. Saved bill records remain in Streamlit session memory and are not persistent across all sessions.
- Before public launch, add persistent storage, privacy/consent controls, tests using redacted bills from multiple DISCOMs, and monitoring.

## Server packages
`packages.txt` installs Tesseract and the listed language packs on Streamlit Community Cloud. If a language is unavailable, use English OCR or enter the bill values manually, and inspect the deployment logs.
