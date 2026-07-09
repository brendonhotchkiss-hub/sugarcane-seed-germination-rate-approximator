"""
germination_pipeline.py
-----------------------
Self-contained pipeline for sugarcane seed germination rate estimation.
Uses HSV segmentation, watershed separation, SVM germination classification,
and contour-based seed counting. Includes QR code reading for petri dish ID.

All functions are consolidated from the research codebase — only code
that executes in production is included.
"""

import cv2
import numpy as np
import joblib
from pathlib import Path
from skimage.measure import label, regionprops

# ── Configuration ─────────────────────────────────────────────────
TARGET_SIZE  = (1024, 1024)
PATCH_SIZE   = 64

# Contour counting — validated parameters (train/val search on 58-image dataset)
MIN_SEED_AREA           = 100
MAX_SEED_AREA           = 8000
CONTOUR_AVG_SEED_AREA   = 700
CONTOUR_MERGE_THRESHOLD = 900

# HSV ranges (must match training exactly)
LOWER_GREEN = np.array([25, 15, 30])
UPPER_GREEN = np.array([90, 255, 255])


# ── QR Code Reading ───────────────────────────────────────────────
def read_qr_code(img_path):
    """
    Attempt to decode a QR code from the full original image.
    Tries multiple scales and rotations, with zxingcpp as primary
    detector and OpenCV as fallback.
    """
    import PIL.Image
    import zxingcpp

    scales    = [1.0, 0.5, 0.25, 0.1]
    rotations = [0, 90, 180, 270]

    try:
        pil_img = PIL.Image.open(str(img_path))

        for scale in scales:
            w = int(pil_img.width  * scale)
            h = int(pil_img.height * scale)
            resized = pil_img.resize((w, h))

            for angle in rotations:
                rotated = resized.rotate(angle, expand=True)
                results = zxingcpp.read_barcodes(rotated)
                for r in results:
                    if r.text:
                        return r.text.strip()
    except Exception:
        pass

    # Fallback: OpenCV multi-scale
    img = cv2.imread(str(img_path))
    if img is None:
        return "Unknown"

    detector = cv2.QRCodeDetector()
    h, w = img.shape[:2]

    for scale in scales:
        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
        data, _, _ = detector.detectAndDecode(resized)
        if data:
            return data.strip()

        gray     = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        data, _, _ = detector.detectAndDecode(
            cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        )
        if data:
            return data.strip()

    return "Unknown"

# ── Preprocessing ─────────────────────────────────────────────────
def crop_to_dish(img_path, working_size=1000):
    """Detect petri dish via Hough Circle Transform and crop to it."""
    img = cv2.imread(str(img_path))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    orig_h, orig_w = img.shape[:2]

    scale = working_size / max(orig_h, orig_w)
    small = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)))
    gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray_small, (15, 15), 0)

    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT,
        dp=1.2, minDist=100, param1=60, param2=40,
        minRadius=50, maxRadius=600
    )

    if circles is None:
        return img_rgb, None

    circles = np.round(circles[0, :]).astype("int")
    x, y, r = circles[0]
    x, y, r = int(x / scale), int(y / scale), int(r / scale)

    mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
    cv2.circle(mask, (x, y), int(r * 0.90), 255, -1)

    result = img_rgb.copy()
    result[mask == 0] = 0

    x1, y1 = max(x - r, 0), max(y - r, 0)
    x2, y2 = min(x + r, orig_w), min(y + r, orig_h)
    cropped = result[y1:y2, x1:x2]

    # Auto brightness correction
    cropped_lab = cv2.cvtColor(cropped, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(cropped_lab)
    if np.mean(l[l > 10]) < 80:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        cropped = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

    return cropped, (x, y, r)


def preprocess(img_path):
    """Crop to dish and resize to TARGET_SIZE."""
    cropped, _ = crop_to_dish(img_path)
    return cv2.resize(cropped, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)


# ── Segmentation ──────────────────────────────────────────────────
def hsv_segment(img):
    """
    HSV Method 2: target tan/beige seed bodies and green shoots.
    Returns combined mask and separate green mask.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    tan_mask   = cv2.inRange(hsv, np.array([8, 15, 80]),  np.array([35, 180, 255]))
    green_mask = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
    combined   = cv2.bitwise_or(tan_mask, green_mask)
    return combined, green_mask


# ── Mask Cleaning ─────────────────────────────────────────────────
def clean_mask(mask, kernel_size=5):
    """Morphological opening, closing, dilation to clean binary mask."""
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    opened  = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)
    closed  = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    dilated = cv2.dilate(closed, kernel, iterations=1)
    return dilated


# ── Watershed Separation ──────────────────────────────────────────
def watershed_separate(img, cleaned_mask):
    """Watershed algorithm to separate touching seeds."""
    dist_transform = cv2.distanceTransform(cleaned_mask, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist_transform, 0.4 * dist_transform.max(), 255, 0)
    sure_fg = sure_fg.astype(np.uint8)

    sure_bg = cv2.dilate(
        cleaned_mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=3
    )
    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    markers = cv2.watershed(img_bgr, markers)

    result_mask = np.zeros_like(cleaned_mask)
    result_mask[markers > 1] = 255
    return result_mask


# ── Text Drawing Helper ───────────────────────────────────────────
def draw_label(img, text, x, y, text_color, bg_color):
    """Draw text with a filled background rectangle for visibility."""
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness  = 1
    padding    = 2

    (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    rect_x1 = x
    rect_y1 = max(y - text_h - padding * 2, 0)
    rect_x2 = min(x + text_w + padding * 2, img.shape[1])
    rect_y2 = y

    cv2.rectangle(img, (rect_x1, rect_y1), (rect_x2, rect_y2), bg_color, -1)
    cv2.putText(img, text, (x + padding, y - padding),
                font, font_scale, text_color, thickness)


# ── SVM Feature Extraction ────────────────────────────────────────
def extract_features(patch_bgr):
    """
    Extract 199-feature vector from a 64x64 BGR patch.
    Must match features used during SVM training exactly.
    """
    patch_hsv = cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)
    features  = []

    for i in range(3):
        hist = cv2.calcHist([patch_hsv], [i], None, [32], [0, 256])
        features.append(cv2.normalize(hist, hist).flatten())

    for i in range(3):
        hist = cv2.calcHist([patch_bgr], [i], None, [32], [0, 256])
        features.append(cv2.normalize(hist, hist).flatten())

    green_mask  = cv2.inRange(patch_hsv, LOWER_GREEN, UPPER_GREEN)
    green_ratio = np.sum(green_mask > 0) / (PATCH_SIZE * PATCH_SIZE)
    features.append(np.array([green_ratio]))

    for i in range(3):
        ch = patch_hsv[:, :, i].astype(np.float32)
        features.append(np.array([ch.mean(), ch.std()]))

    return np.concatenate(features)


def extract_patch(img, cy, cx):
    """Extract 64x64 BGR patch centered on (cy, cx)."""
    half = PATCH_SIZE // 2
    h, w = img.shape[:2]
    y1, y2 = max(cy - half, 0), min(cy + half, h)
    x1, x2 = max(cx - half, 0), min(cx + half, w)
    patch_rgb = img[y1:y2, x1:x2]
    patch_bgr = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2BGR)
    return cv2.resize(patch_bgr, (PATCH_SIZE, PATCH_SIZE), interpolation=cv2.INTER_LINEAR)


# ── Model Loading ─────────────────────────────────────────────────
def load_model(model_dir="models"):
    """Load trained SVM and scaler from disk."""
    model_dir   = Path(model_dir)
    model_path  = model_dir / "svm_germination.joblib"
    scaler_path = model_dir / "svm_scaler.joblib"

    if not model_path.exists() or not scaler_path.exists():
        raise FileNotFoundError(
            f"SVM model not found in {model_dir}. "
            "Ensure svm_germination.joblib and svm_scaler.joblib are present."
        )
    return joblib.load(model_path), joblib.load(scaler_path)


# ── Combined Annotation + Count + Classify ────────────────────────
def annotate_and_count(img, watershed_mask, svm, scaler):
    """
    In a single pass:
      - Count seeds (contour-based with merge estimation)
      - Classify germination (SVM)
      - Draw all annotations onto one image

    Returns:
        annotated    — RGB image with all boxes drawn
        total_seeds  — estimated total seed count
        germinated   — estimated germinated seed count
    """
    annotated   = img.copy()
    total_seeds = 0
    germinated  = 0

    # Contour pass — seed counting and base boxes
    contours, _ = cv2.findContours(
        watershed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_SEED_AREA or area > MAX_SEED_AREA:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        if area >= CONTOUR_MERGE_THRESHOLD:
            estimated = max(1, round(area / CONTOUR_AVG_SEED_AREA))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 0, 0), 2)
            draw_label(annotated, f"~{estimated}", x, y,
                       text_color=(255, 255, 255), bg_color=(180, 0, 0))
            total_seeds += estimated
        else:
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 165, 0), 2)
            total_seeds += 1

    # SVM pass — germination classification + green overlay
    labeled = label(watershed_mask)
    regions = regionprops(labeled)

    patches, valid_regions = [], []
    for region in regions:
        if region.area < MIN_SEED_AREA or region.area > MAX_SEED_AREA:
            continue
        cy, cx = int(region.centroid[0]), int(region.centroid[1])
        patches.append(extract_patch(img, cy, cx))
        valid_regions.append(region)

    if patches:
        features        = np.array([extract_features(p) for p in patches])
        features_scaled = scaler.transform(features)
        preds           = svm.predict(features_scaled)

        for region, pred in zip(valid_regions, preds):
            if pred == 1:
                minr, minc, maxr, maxc = region.bbox
                cv2.rectangle(annotated, (minc, minr), (maxc, maxr),
                              (0, 200, 0), 2)
                germinated += 1

    return annotated, total_seeds, germinated


# ── Full Pipeline ─────────────────────────────────────────────────
def analyze_image(img_path, original_filename, svm, scaler):
    """
    Run the full germination analysis pipeline on a single image.

    Parameters:
        img_path          — path to temp file on disk
        original_filename — original filename from the user's upload
        svm               — trained SVM from load_model()
        scaler            — fitted scaler from load_model()

    Returns:
        dict with keys:
            petri_id         — decoded QR code string, or "Unknown"
            image_name       — original filename
            total_seeds      — estimated total seed count
            germinated_seeds — estimated germinated seed count
            germination_rate — germination rate as percentage (1dp)
            annotated_img    — RGB numpy array with full annotation overlay
    """
    # Read QR code from original image before any cropping
    petri_id = read_qr_code(img_path)

    img         = preprocess(img_path)
    combined, _ = hsv_segment(img)
    cleaned     = clean_mask(combined)
    watershed   = watershed_separate(img, cleaned)

    annotated, total, germinated = annotate_and_count(img, watershed, svm, scaler)

    rate = round(germinated / total * 100, 1) if total > 0 else 0.0

    return {
        "petri_id"         : petri_id,
        "image_name"       : original_filename,
        "total_seeds"      : total,
        "germinated_seeds" : germinated,
        "germination_rate" : rate,
        "annotated_img"    : annotated,
    }
