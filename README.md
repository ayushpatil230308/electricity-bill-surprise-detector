# BillWise India — All-India 5-Month Analyzer (Upgrade)

## Included
- Upload up to five monthly electricity bills.
- Multilingual Tesseract OCR attempt with editable extracted fields.
- Manual selection of state/UT and DISCOM.
- Bill and unit comparison charts.
- Bill Surprise Fingerprint: transparent rules distinguish usage-driven bill rises from amount rises with relatively flat usage.
- Indicative next-month units trend when at least three months are saved.
- Appliance usage estimator, savings suggestions, and built-in support chatbot.

## Deploy
1. Extract the ZIP.
2. Upload `app.py`, `requirements.txt`, and `packages.txt` to the root of your GitHub repository.
3. Deploy/redeploy `app.py` with Streamlit Community Cloud.
4. Check deployment logs if system packages fail.

## Important limitations — please read before public launch
- India has many DISCOMs and bill formats. The DISCOM list is a selection aid, not a guarantee that every company's PDF will parse perfectly.
- OCR accuracy depends on scan quality, fonts, language packs and PDF encoding. Verify every field.
- Five bills are useful for a basic comparison but are too little data for a dependable forecasting/ML model. The displayed next-month estimate is a simple linear trend, not a trained predictive model.
- The bill alone cannot identify which appliance actually used electricity; appliance figures are estimates based on user-entered wattage and hours.
- Chatbot answers use rules and are not a connected generative AI model.
- Data remains in the Streamlit session and is not stored permanently.
- Before public launch, add consent/privacy controls, persistent storage, automated tests with redacted real bills from multiple DISCOMs, monitoring, and clear user support. Do not promise zero complaints or perfect extraction.


## UI update
The app includes a responsive teal/green visual theme, hero banner, section hierarchy, refined sidebar, rounded metric cards, upload styling and a footer. The design uses Streamlit-native widgets and CSS styling; it does not change the underlying OCR accuracy limitations.
