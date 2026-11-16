# Electricity Bill Detective & Savings Coach

A Streamlit prototype for understanding household electricity-bill changes.

## Features

- Monthly bill history
- kWh/day normalization
- Bill amount comparison
- Bill Increase Detective
- Usage charts
- Appliance-aware savings suggestions
- Savings Experiment Tracker
- Editable sample history

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

This prototype uses the household's entered bill data. It does not guarantee savings or identify a causal appliance-level source of consumption without additional measurements.

For public deployment, add privacy controls, secure storage, authentication/authorization, OCR review, validation of official tariff rules, and tests before collecting other households' data.
