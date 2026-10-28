# BillWise India

A free Streamlit prototype for electricity-bill review, monthly comparisons, appliance energy estimates, savings tips, and built-in customer support.

## Files
- `app.py`: Streamlit website
- `requirements.txt`: Python dependencies
- `packages.txt`: Tesseract OCR and selected language data for Streamlit Community Cloud

## Deploy
1. Upload these four files to the root of a GitHub repository.
2. In Streamlit Community Cloud choose the repository, branch, and main file `app.py`.
3. Commit changes to redeploy.

## Language support
The app supports embedded PDF text and OCR for the language packs listed in `packages.txt`. Users should select the language(s) actually printed on their bill. This does not guarantee perfect reading for every script, provider, scan quality, or bill layout. Verify amount, month, and kWh against the original before saving.

## Features
- PDF/image upload and extracted text preview
- Layout-aware extraction for the tested two-page MSEDCL PDF layout
- General label-based extraction fallback
- Monthly bill/usage charts and CSV export
- Appliance estimator based on rated watts and hours/day
- Estimated savings calculations and practical suggestions
- Free built-in support assistant without a paid API key

## Important limitations
- A bill normally reports total household consumption, not individual appliance usage. Appliance ranking is estimated from user-entered wattage and hours; actual appliance-level identification requires monitoring hardware.
- Customer support is rule-based built-in guidance, not a generative AI model.
- Records are stored in the current Streamlit session only; permanent user accounts/history are not implemented.
- This is a prototype, not a certified billing system. Validate each provider/layout before public use.
