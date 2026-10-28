# BillWise India — Electricity Bill Detective

This combined version brings together:
1. Reliability-first bill extraction with manual verification and evidence display.
2. Multi-provider/general label-based extraction and OCR attempts.
3. Rule-based anomaly flags for unusually high amounts, usage, amount-per-unit ratios, and large changes versus previous saved bills.
4. Bill history charts, CSV export, and practical savings suggestions.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Tesseract OCR must be installed for image/scanned bills. Streamlit Community Cloud uses `packages.txt` for Linux system packages.

## Deploy
1. Back up the existing GitHub repository.
2. Replace `app.py`, `requirements.txt`, and `packages.txt` with these files.
3. Commit the changes to the main branch.
4. Wait for Streamlit Community Cloud to rebuild.
5. Test using representative bills from each target provider, including scanned and regional-language examples.

## Reliability and limitations
- No bill parser can be guaranteed correct for every provider/layout/language without representative tests.
- The app presents candidates and asks the user to check values against the original bill before saving.
- Anomaly flags are warnings, not proof of an incorrect bill, meter fault, or cause.
- The savings section is general advice, not a guaranteed rupee-saving prediction.
- This version uses transparent rules; it does not train an ML model.
- Session data is not configured for permanent storage. Public hosting and upload handling should be reviewed before production use.
- Do not claim universal support until testing establishes performance across the target providers.


## Free customer support
The support chat uses built-in troubleshooting rules and does not require a paid AI API or API key. It is a rule-based FAQ assistant, not a generative AI model.
