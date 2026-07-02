# Sugarcane Germination Rate Analyzer

Automated sugarcane seed germination rate estimation from petri dish images.  
Developed by Brendon Hotchkiss — UTA / USDA ARS internship, 2026.  
Supervised by Dr. Li Wang (coding) and Dr. Keo Corak (plant science).

---

## Overview

This repository contains two versions of the germination analyzer, both powered by the same trained SVM model and image processing pipeline.

### `app/` — Display-Only Tool
Built with Streamlit. Upload one or more images and instantly see results in a clean table with annotated image viewer. Best for quick batch analysis.

### `app_interactive/` — Interactive Tool
Built with Flask. Same analysis as the display-only tool, plus the ability to correct model predictions directly on the annotated image before exporting. Best for careful inspection and ground-truth correction.

---

## How It Works

1. The image is cropped to the petri dish using Hough Circle Transform
2. Seeds are segmented using HSV color thresholding (tan/beige seed bodies + green shoots)
3. Touching seeds are separated using watershed algorithm
4. Each seed region is classified as germinated or ungerminated by a trained SVM
5. Total seeds are counted using contour detection with merge estimation for touching clusters
6. Germination rate is calculated as germinated / total × 100%

**Model:** SVM trained on 4,955 manually labeled 64×64 seed patches  
**Counting:** Contour-based with validated parameters (AVG_SEED_AREA=700, MERGE_THRESHOLD=900)  
**Validated on:** 58 petri dish images with full ground truth annotation

---

## Performance

Evaluated against ground truth annotations across 58 diverse petri dish images:

| Metric | Result |
|---|---|
| Germination count MAE | 3.31 seeds |
| Germination rate MAE | 6.63 percentage points |

Performance degrades on high-germination dishes (>30% rate) with long, mature shoots, and on dishes with heavy brown plant debris. See the research repository for full methodology and findings.

---

## Setup

### Requirements
- Windows PC
- Python 3.9–3.12 (not 3.13)

### First-Time Installation
Open a terminal in the repository root and run:

```
python -m venv venv
venv\Scripts\activate
pip install -r app\requirements.txt
pip install -r app_interactive\requirements.txt
```

---

## Running the Tools

### Display-Only Tool
```
cd app
streamlit run app.py
```
Or double-click `app\run.bat`

### Interactive Tool
```
cd app_interactive
python server.py
```
Or double-click `app_interactive\run.bat`

Both tools open automatically in your browser when ready.  
Stop either tool by pressing `Ctrl+C` in the terminal.

---

## Known Limitations

- Performance degrades on high-germination dishes with long, mature shoots
- Brown plant debris can be misidentified as seeds
- Touching seed clusters are estimated rather than individually counted
- DSLR images produce more accurate results than phone camera images

---

## Repository Structure

```
├── app/                    Display-only Streamlit tool
│   ├── app.py
│   ├── germination_pipeline.py
│   ├── models/
│   ├── requirements.txt
│   ├── run.bat
│   └── README.md
│
├── app_interactive/        Interactive Flask tool with correction layer
│   ├── server.py
│   ├── templates/
│   ├── static/
│   ├── germination_pipeline.py
│   ├── models/
│   ├── requirements.txt
│   ├── run.bat
│   └── README.md
│
└── README.md               This file
```
