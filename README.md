# BillWise India

A Streamlit electricity bill reader and savings assistant.

## Files
- `app.py`: Main application
- `requirements.txt`: Python dependencies
- `packages.txt`: Tesseract OCR system packages for Streamlit Community Cloud

## Run locally
1. Install Python 3.10 or later.
2. Create a virtual environment if desired.
3. Install dependencies: `pip install -r requirements.txt`
4. Install Tesseract OCR and the language packs you need on your operating system.
5. Run: `streamlit run app.py`

## Deploy on Streamlit Community Cloud
Push all three files to the root of your GitHub repository, then deploy `app.py`.

## Important limitations
- OCR extraction and label-based parsing may not correctly recognize every bill layout.
- Review and correct the month, bill amount and units before saving.
- Bill history is stored only in the active Streamlit session; it is not a permanent database.
- Appliance and savings calculations are estimates, not actual meter readings or guaranteed savings.
