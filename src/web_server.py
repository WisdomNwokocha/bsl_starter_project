"""
web_server.py
-------------
Small backend for the web UI. The browser captures webcam frames and sends
them here; this reuses your EXACT existing extraction + trained model code
(utils.py, the same .joblib files spell_words.py uses) to predict a letter,
and sends the result back as JSON. All the "is this letter stable, has the
word finished" logic lives in the browser (word_builder.js) — this endpoint
only does the one thing that has to run in Python: MediaPipe + the model.

Usage:
    uvicorn src.web_server:app --reload --port 8000

Then open http://localhost:8000 in a browser.
"""

import os
import sys
import base64

import cv2
import joblib
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.append(os.path.dirname(__file__))
from utils import extract_landmarks_from_bgr_frame

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "bsl_fingerspelling_mlp.joblib")
LABEL_ENCODER_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "label_encoder.joblib")
WEB_UI_DIR = os.path.join(os.path.dirname(__file__), "..", "web_ui")
SIGN_CLIPS_DIR = os.path.join(os.path.dirname(__file__), "..", "web_ui", "sign_clips")

# Every label the app knows about. A label is "available" for the type-to-sign
# feature once a matching video file exists in web_ui/sign_clips/, named
# exactly LABEL.mp4 or LABEL.webm (e.g. A.mp4, NUMBER_7.webm).
KNOWN_LABELS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [f"NUMBER_{i}" for i in range(11)]
CLIP_EXTENSIONS = [".mp4", ".webm"]

app = FastAPI()

_model = None
_label_encoder = None


@app.on_event("startup")
def load_model():
    global _model, _label_encoder
    if not (os.path.exists(MODEL_PATH) and os.path.exists(LABEL_ENCODER_PATH)):
        print("WARNING: trained model not found at", MODEL_PATH)
        print("Run extract_landmarks.py and train_classifier.py first.")
        return
    _model = joblib.load(MODEL_PATH)
    _label_encoder = joblib.load(LABEL_ENCODER_PATH)
    print("Model loaded. Ready to predict.")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(WEB_UI_DIR, "index.html"))


@app.post("/predict")
async def predict(request: Request):
    if _model is None:
        return JSONResponse({"error": "model not loaded on server"}, status_code=503)

    body = await request.json()
    data_url = body.get("image", "")

    # Expecting a data URL like "data:image/jpeg;base64,/9j/4AAQ..."
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url

    try:
        image_bytes = base64.b64decode(encoded)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    except Exception as e:
        return JSONResponse({"error": f"could not decode image: {e}"}, status_code=400)

    if frame is None:
        return JSONResponse({"letter": None, "confidence": 0.0})

    features = extract_landmarks_from_bgr_frame(frame)
    if features is None:
        return JSONResponse({"letter": None, "confidence": 0.0})

    probabilities = _model.predict_proba(features.reshape(1, -1))[0]
    best_index = int(np.argmax(probabilities))
    confidence = float(probabilities[best_index])
    letter = str(_label_encoder.classes_[best_index])

    return JSONResponse({"letter": letter, "confidence": confidence})


@app.get("/available_clips")
def available_clips():
    """
    Tells the frontend which letters/numbers actually have a recorded sign
    clip available yet, so it can gracefully skip or flag anything not
    recorded yet instead of failing silently or with a broken video.

    Accepts EITHER of two folder layouts, so it's forgiving of how clips
    got organised:
      1. A flat file directly in sign_clips/, e.g. sign_clips/A.webm
      2. A folder per label with one or more takes inside, e.g.
         sign_clips/A/take1.webm — the first take found is used for playback.
    """
    available = {}
    for label in KNOWN_LABELS:
        # Layout 1: flat file
        found = False
        for ext in CLIP_EXTENSIONS:
            candidate = os.path.join(SIGN_CLIPS_DIR, label + ext)
            if os.path.exists(candidate):
                available[label] = f"/clips/{label}{ext}"
                found = True
                break

        if found:
            continue

        # Layout 2: a folder containing one or more takes
        label_folder = os.path.join(SIGN_CLIPS_DIR, label)
        if os.path.isdir(label_folder):
            for filename in sorted(os.listdir(label_folder)):
                if any(filename.lower().endswith(ext) for ext in CLIP_EXTENSIONS):
                    available[label] = f"/clips/{label}/{filename}"
                    break

    return JSONResponse(available)


@app.get("/available_animations")
def available_animations():
    """
    Tells the frontend which labels have a generated skeleton ANIMATION
    available (from extract_sign_animations.py), as opposed to /available_clips
    which lists raw video clips. These are two different, separately-generated
    things from the same source recordings.
    """
    available = {}
    for label in KNOWN_LABELS:
        candidate = os.path.join(WEB_UI_DIR, "sign_animations", f"{label}.json")
        if os.path.exists(candidate):
            available[label] = f"/static/sign_animations/{label}.json"
    return JSONResponse(available)


# Serve the actual video clip files referenced by the URLs above
os.makedirs(SIGN_CLIPS_DIR, exist_ok=True)
app.mount("/clips", StaticFiles(directory=SIGN_CLIPS_DIR), name="clips")

# Serve the web UI's own JS/CSS files (index.html is served by the route above)
app.mount("/static", StaticFiles(directory=WEB_UI_DIR), name="static")
