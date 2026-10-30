# BillWise India

A Streamlit prototype for reviewing electricity bills, comparing verified monthly usage, estimating appliance consumption, and generating savings suggestions.

## Files
- `app.py` — complete Streamlit application
- `requirements.txt` — Python dependencies
- `packages.txt` — system packages for Streamlit Community Cloud Tesseract OCR

## Deploy on Streamlit Community Cloud
1. Upload these files to the root of your GitHub repository.
2. Create or open the app in Streamlit Community Cloud.
3. Set the main file path to `app.py`.
4. Deploy or reboot the app.

## OCR notes
- Digital PDFs use embedded text when readable.
- Scanned PDFs use Tesseract OCR.
- MSEDCL-named PDFs try Marathi + English if both traineddata packs are installed.
- The app processes at most the first 3 PDF pages for speed.
- OCR extraction is not guaranteed. Verify month, kWh and payable amount against the original bill.
- The OCR timeout is bounded per attempt; slow scanned pages may still take time on free cloud resources.

## Important limitations
- This is a prototype, not an official DISCOM bill calculator.
- Saved bills are stored in Streamlit session state and may be lost when the session resets.
- Appliance usage is an estimate based on user-entered wattage and hours; a bill alone cannot identify the exact appliance consuming power.
- The next-month estimate is a simple trend, not a trained ML model.
- Do not upload unredacted bills to a public repository.
