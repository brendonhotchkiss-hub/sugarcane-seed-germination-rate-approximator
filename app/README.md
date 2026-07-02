# Sugarcane Germination Analyzer

Automated germination rate estimation from petri dish images.  
Developed by Brendon Hotchkiss — UTA / USDA ARS internship, 2026.  
Supervised by Dr. Li Wang (coding) and Dr. Keo Corak (plant science).

---

## Requirements

- Windows PC
- Python 3.9–3.12 (not 3.13)
- The `venv/` virtual environment in the parent `sugarcane-analysis/` folder

---

## First-Time Setup

Open a terminal in the `sugarcane-analysis/` folder and run:

```
venv\Scripts\activate
pip install -r app\requirements.txt
```

This only needs to be done once.

---

## Running the App

**Option A — Double-click:**  
Double-click `run.bat` inside the `app/` folder. The app will open automatically in your browser.

**Option B — Terminal:**
```
cd app
streamlit run app.py
```

**To stop the app:** close the terminal window or press `Ctrl+C`.

---

## Using the App

1. Click **Browse files** to select one or more petri dish images (JPG or PNG)
2. The app analyzes each image and displays a results table showing:
   - Total seed count
   - Germinated seed count
   - Germination rate (%)
3. Use the **image selector** below the table to view the annotated image for any uploaded image
4. Click **🔍 Expand for full resolution inspection** to zoom in on details
5. Click **📥 Download results as CSV** to save the results table

---

## Understanding the Annotated Image

| Box Color | Meaning |
|---|---|
| 🟠 Orange | Single detected seed (ungerminated) |
| 🔴 Red with `~N` label | Cluster of seeds too close to separate individually — `~N` is the estimated count |
| 🟢 Green | Germination detected in this region |
| 🔴+🟢 overlap | A cluster where germination was also detected — individual germinated count within the cluster is unknown |

---

## Known Limitations

- **Brown plant debris** can be misidentified as seeds, causing overcounting on heavily contaminated dishes
- **High-germination dishes** (>30% rate) with long, mature shoots may be undercounted — the model was trained predominantly on earlier-stage germination images
- **Touching seeds** that cannot be separated by the watershed algorithm are grouped into a single red cluster box
- **Phone camera images** are supported but may produce less accurate results than DSLR images — the model was trained on Canon DSLR photographs

---

## Files in This Folder

| File | Purpose |
|---|---|
| `app.py` | Streamlit user interface |
| `germination_pipeline.py` | Image processing and SVM inference |
| `models/svm_germination.joblib` | Trained SVM model |
| `models/svm_scaler.joblib` | Feature scaler (required alongside model) |
| `requirements.txt` | Python dependencies |
| `run.bat` | One-click launcher for Windows |
