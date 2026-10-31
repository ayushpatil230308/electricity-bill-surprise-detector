# BillWise India — Smart Energy Companion

A Streamlit prototype for reviewing electricity bills, comparing verified monthly usage, estimating appliance consumption, and exploring practical savings suggestions.

## Project files
- `app.py` — complete Streamlit application with responsive dashboard styling and lightweight CSS animations
- `requirements.txt` — Python dependencies
- `packages.txt` — system packages for Streamlit Community Cloud OCR
- `.gitignore` — ignores Python cache and local secrets

## Deploy on Streamlit Community Cloud
1. Download and extract this ZIP.
2. Upload the contents of the `BillWise_India_Full_Code` folder to the **root** of your GitHub repository (not inside another nested folder).
3. In Streamlit Community Cloud, create/open the app and select `app.py` as the main file.
4. Deploy. If the app already exists, commit the updated files to GitHub and reboot the app.

## OCR behaviour
- Digital PDFs use embedded text when readable.
- Scanned PDFs use Tesseract OCR.
- MSEDCL-named PDFs try Marathi + English when both language packs are installed.
- For speed, at most the first 3 PDF pages are processed.
- OCR may misread fields. Verify billing month, kWh and final payable amount against the original bill before saving.
- Scanned pages can still take time on Streamlit Community Cloud's shared resources.

## Important limitations
- This is a prototype, not an official DISCOM bill calculator.
- Saved bills are held in Streamlit session state and may be lost when a session resets.
- Appliance consumption is estimated from user-entered wattage and hours; a bill alone cannot identify the exact appliance consuming power.
- The next-month usage estimate is a simple linear trend, not a trained ML model.
- Never commit real electricity bills or unredacted personal information to a public GitHub repository.

## Local run (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```
