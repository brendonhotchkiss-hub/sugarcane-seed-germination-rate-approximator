"""
server.py
---------
Flask backend for the interactive sugarcane germination analyzer.
Handles image upload, pipeline execution, and correction state management.
Includes QR code reading for petri dish ID.
"""

import base64
import os
import tempfile
import webbrowser
from pathlib import Path
from threading import Timer

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

from germination_pipeline import (
    load_model,
    preprocess,
    hsv_segment,
    clean_mask,
    watershed_separate,
    annotate_and_count,
    read_qr_code,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

print("Loading SVM model...")
SVM, SCALER = load_model()
print("Model loaded.")

IMAGE_STORE = {}


def img_to_b64(img_rgb):
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buffer).decode("utf-8")


def compute_corrected_counts(name):
    entry = IMAGE_STORE[name]
    model_total      = entry["model_total"]
    model_germinated = entry["model_germinated"]
    corrections      = entry["corrections"]

    missed_seeds  = len([c for c in corrections if c["type"] == "missed_seed"])
    missed_germ   = len([c for c in corrections if c["type"] == "missed_germ"])
    false_seed    = len([c for c in corrections if c["type"] == "false_seed"])
    false_germ    = len([c for c in corrections if c["type"] == "false_germ"])
    cluster_delta = sum(c.get("delta", 0) for c in corrections
                        if c["type"] == "cluster_adjust")

    corrected_total      = model_total + missed_seeds - false_seed + cluster_delta
    corrected_germinated = model_germinated + missed_germ - false_germ
    corrected_total      = max(0, corrected_total)
    corrected_germinated = max(0, min(corrected_germinated, corrected_total))
    corrected_rate       = round(corrected_germinated / corrected_total * 100, 1) \
                           if corrected_total > 0 else 0.0

    return corrected_total, corrected_germinated, corrected_rate


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    for f in files:
        original_name = f.filename
        suffix = Path(original_name).suffix

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Read QR code before cropping
            petri_id = read_qr_code(tmp_path)

            img         = preprocess(tmp_path)
            combined, _ = hsv_segment(img)
            cleaned     = clean_mask(combined)
            watershed   = watershed_separate(img, cleaned)

            annotated, total, germinated = annotate_and_count(
                img, watershed, SVM, SCALER
            )

            rate = round(germinated / total * 100, 1) if total > 0 else 0.0

            IMAGE_STORE[original_name] = {
                "petri_id"         : petri_id,
                "model_total"      : total,
                "model_germinated" : germinated,
                "model_rate"       : rate,
                "annotated_b64"    : img_to_b64(annotated),
                "corrections"      : [],
            }

            results.append({
                "name"                 : original_name,
                "petri_id"             : petri_id,
                "model_total"          : total,
                "model_germinated"     : germinated,
                "model_rate"           : rate,
                "annotated_b64"        : img_to_b64(annotated),
                "corrected_total"      : total,
                "corrected_germinated" : germinated,
                "corrected_rate"       : rate,
            })

        except Exception as e:
            results.append({"name": original_name, "error": str(e)})
        finally:
            os.unlink(tmp_path)

    return jsonify(results)


@app.route("/correct", methods=["POST"])
def correct():
    data = request.get_json()
    name = data.get("name")

    if name not in IMAGE_STORE:
        return jsonify({"error": "Image not found"}), 404

    action      = data.get("action")
    corrections = IMAGE_STORE[name]["corrections"]

    if action == "undo":
        if corrections:
            corrections.pop()
    else:
        correction = {
            "type" : action,
            "x"    : data.get("x"),
            "y"    : data.get("y"),
        }
        if action == "cluster_adjust":
            correction["delta"] = data.get("delta", 0)
        corrections.append(correction)

    corrected_total, corrected_germinated, corrected_rate = \
        compute_corrected_counts(name)

    return jsonify({
        "name"                 : name,
        "corrected_total"      : corrected_total,
        "corrected_germinated" : corrected_germinated,
        "corrected_rate"       : corrected_rate,
        "corrections"          : corrections,
    })


@app.route("/export", methods=["GET"])
def export():
    rows = []
    for name, entry in IMAGE_STORE.items():
        ct, cg, cr = compute_corrected_counts(name)
        rows.append({
            "Petri ID"             : entry["petri_id"],
            "Image"                : name,
            "Model Total"          : entry["model_total"],
            "Model Germinated"     : entry["model_germinated"],
            "Model Rate (%)"       : entry["model_rate"],
            "Corrected Total"      : ct,
            "Corrected Germinated" : cg,
            "Corrected Rate (%)"   : cr,
        })
    return jsonify(rows)


def open_browser():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    Timer(1.5, open_browser).start()
    app.run(debug=False, port=5000)
