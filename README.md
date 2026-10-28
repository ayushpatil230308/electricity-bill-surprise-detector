# BillWise India — Working Starter Model

## Files
- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `packages.txt` — Tesseract packages for Streamlit Community Cloud
- `README.md` — setup guide

## Deploy on Streamlit Community Cloud
1. Extract this ZIP.
2. Upload all three project files (`app.py`, `requirements.txt`, `packages.txt`) to the root of your GitHub repository.
3. In Streamlit Community Cloud, deploy the repository and select `app.py` as the main file.
4. If already deployed, commit the replacement files and reboot the app.

## Run locally
1. Install Python 3.10+.
2. Install Tesseract OCR on your computer if you need image/PDF OCR.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.

## Honest limitations
- The Python source is syntax-compiled before packaging, but deployment depends on the host's package installation.
- OCR is not guaranteed to recognize every bill layout. Verify every extracted value.
- History is kept in the active Streamlit session and is not a permanent database.
- Appliance costs are estimates and do not account for every tariff component.
