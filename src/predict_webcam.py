"""
predict_webcam.py
------------------
STEP 3 of the pipeline — the fun part.

Opens your device webcam, runs MediaPipe Hands on each frame in real time,
feeds the landmarks into your trained model, and overlays the predicted
letter/sign on screen.

This is the first, small-scale proof of the Phase 1 SRS goal:
"point your camera, get text back" — just starting with single letters
instead of full sentences.

Usage:
    python src/predict_webcam.py

Press 'q' to quit.
"""

import os
import sys
import cv2
import joblib
import numpy as np

sys.path.append(os.path.dirname(__file__))
from utils import extract_landmarks_from_bgr_frame

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "bsl_fingerspelling_mlp.joblib")
LABEL_ENCODER_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "label_encoder.joblib")

CONFIDENCE_THRESHOLD = 0.6  # below this, show "..." instead of guessing


def main():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(LABEL_ENCODER_PATH)):
        print("ERROR: trained model not found.")
        print("Run 'python src/extract_landmarks.py' then 'python src/train_classifier.py' first.")
        return

    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(LABEL_ENCODER_PATH)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (device 0). Check camera permissions/index.")
        return

    print("Webcam started. Press 'q' to quit.")

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            break

        # Run detection on the RAW (unmirrored) frame — this must match the
        # orientation the training images were captured in. Only the frame
        # shown on screen gets mirrored, purely for a natural selfie-view.
        features = extract_landmarks_from_bgr_frame(frame)
        display_frame = cv2.flip(frame, 1)

        display_text = "No hand detected"
        if features is not None:
            probabilities = model.predict_proba(features.reshape(1, -1))[0]
            best_index = int(np.argmax(probabilities))
            confidence = probabilities[best_index]
            predicted_label = label_encoder.classes_[best_index]

            if confidence >= CONFIDENCE_THRESHOLD:
                display_text = f"{predicted_label} ({confidence:.0%})"
            else:
                display_text = f"...not sure ({confidence:.0%})"

        cv2.putText(
            display_frame, display_text, (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA,
        )
        cv2.imshow("BSL Fingerspelling - Prototype", display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
