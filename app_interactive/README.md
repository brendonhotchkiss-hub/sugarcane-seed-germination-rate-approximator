# Sugarcane Germination Analyzer — Interactive

Interactive germination rate estimation from petri dish images, with the ability to correct model predictions directly on the annotated image before exporting results.

---

## Requirements

- Windows PC
- Python 3.9–3.12 (not 3.13)
- The `venv/` virtual environment in the parent folder

---

## First-Time Setup

Open a terminal in the parent folder and run:

```
venv\Scripts\activate
pip install -r app_interactive\requirements.txt
```

This only needs to be done once.

---

## Running the App

**Option A — Double-click:**
Double-click `run.bat`. The app will open automatically in your browser at `http://localhost:5000`.

**Option B — Terminal:**
```
cd app_interactive
python server.py
```

**To stop the app:** close the terminal window or press `Ctrl+C`.

---

## Using the App

1. Click **📁 Click or drag images here** or drag and drop one or more petri dish images (JPG or PNG)
2. The model analyzes each image and displays results in the table
3. Use the **image list** on the left to switch between uploaded images
4. Inspect the annotated image and make corrections using the mouse controls below
5. The results table and aggregate rate update live as corrections are made
6. Click **📥 Export CSV** to save all results (model predictions + corrections)

---

## Mouse Controls

| Action | Result |
|---|---|
| Left click on image | Add missed seed marker 🎯 |
| Shift + Left click | Add missed germination marker 💚 |
| Right click on image | Mark false positive seed 🚫 |
| Shift + Right click | Mark false positive germination 💔 |
| Ctrl + Scroll | Zoom in / out toward cursor |
| Ctrl + Z | Undo last correction |

The **Undo** button in the sidebar also removes the last correction.

---

## Understanding the Annotated Image

| Box Color | Meaning |
|---|---|
| 🟠 Orange | Single detected seed (ungerminated) |
| 🔴 Red with `~N` label | Cluster of seeds — `~N` is the estimated count |
| 🟢 Green | Germination detected in this region |
| 🔴+🟢 overlap | Germination detected within a cluster |

User correction markers appear directly on the image at the clicked location. Ctrl+Z removes the most recent marker.

---

## Understanding the Results Table

Each row shows both the original model prediction and the corrected values side by side:

| Column | Description |
|---|---|
| Model Total | Seeds detected by the model |
| Model Germinated | Germinated seeds detected by the model |
| Model Rate (%) | Model germination rate |
| Corrected Total | After user corrections |
| Corrected Germinated | After user corrections |
| Corrected Rate (%) | Final corrected germination rate |

The **Aggregate Rate** in the toolbar shows the pooled corrected germination rate across all uploaded images.

---

## Known Limitations

- Performance degrades on high-germination dishes (>30% rate) with long, mature shoots
- Brown plant debris can be misidentified as seeds, causing overcounting
- Touching seed clusters are estimated rather than individually separated
- DSLR images produce more accurate results than phone camera images

---

## Files in This Folder

| File | Purpose |
|---|---|
| `server.py` | Flask backend — pipeline execution and correction state |
| `templates/index.html` | Frontend UI |
| `static/app.js` | Canvas interaction and correction logic |
| `germination_pipeline.py` | Image processing and SVM inference |
| `models/svm_germination.joblib` | Trained SVM model |
| `models/svm_scaler.joblib` | Feature scaler (required alongside model) |
| `requirements.txt` | Python dependencies |
| `run.bat` | One-click launcher for Windows |
