# BillWise India — OCR Repair Release

## Fixes in this build
- MSEDCL PDFs automatically try Marathi + English OCR even when the sidebar language is set to English.
- OCR engine and installed language packs are displayed in the sidebar, so a missing server dependency is visible instead of silently failing.
- Scanned PDFs are rendered at a faster 1.5x default resolution; increase the resolution only if the scan is unclear.
- OCR tries a small, prioritized set of language combinations and stops once usable text is found.
- Text-based PDFs use embedded text first; garbled/scanned pages use OCR.
- MSEDCL month codes such as `MSEDCL_2610` are interpreted as October 2026.
- MSEDCL Marathi amount labels and the total-consumption meter row have targeted parsing support.
- Amount parsing requires a currency marker or a recognized payable label; unrelated dates, page numbers and security-deposit values should not be accepted as payable amounts.
- Uncertain units or payable amounts remain flagged and must be checked against the original bill before saving.
- OCR results are cached during the Streamlit session; bills are scanned one at a time when Scan this bill is clicked.
- The app supports up to five monthly bills and retains comparison charts, anomaly alerts, appliance estimates, savings tips and the rule-based help panel.

## Upload to GitHub
1. Extract this ZIP.
2. Upload `app.py`, `requirements.txt`, `packages.txt`, and `README.md` to the root of your GitHub repository. Do not upload `__pycache__`.
3. Commit changes.
4. Open Streamlit Community Cloud and reboot/redeploy the app. Main file path: `app.py`.

## Honest testing status
- `app.py` passes Python syntax compilation.
- The MSEDCL OCR strategy was exercised locally against a redacted October 2026 sample bill: Marathi + English OCR produced readable text, including the bill amount and the meter-reading total-usage row.
- This ZIP has not yet been deployed to your Streamlit Cloud app, and all five bills have not been independently validated end-to-end. Confirm the sidebar says the OCR engine and `mar`/`eng` packs are ready after deployment.
- OCR accuracy varies with scan quality and bill layout. Always verify billing month, kWh and final payable amount against the original bill before saving. Never treat an OCR guess as a confirmed charge.
- Scanned PDFs still require OCR time; a 2-page MSEDCL scan can take several seconds per page depending on server load.
- Five bills support basic historical comparison, not a dependable trained ML forecast. Appliance usage is an estimate from user-entered wattage/hours; a bill alone cannot identify the exact appliance.
- Records are held in Streamlit session memory, not a persistent production database. Before public launch, add durable storage, privacy/consent controls, multi-DISCOM validation and monitoring.

## Server OCR dependencies
`packages.txt` installs Tesseract and language packs on Streamlit Community Cloud. If the sidebar reports missing `mar` or `eng`, check the app's deployment logs and rebuild/reboot the app.
