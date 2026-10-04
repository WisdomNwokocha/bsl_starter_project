"""
spell_words.py
--------------
Like predict_webcam.py, but instead of just showing the current letter's
guess, this accumulates STABLE, HELD letters into an actual spelled word —
and now speaks each word aloud automatically once you pause, without
needing to press any button. A sustained pause after spelling something is
treated as "that word is finished" (mirroring how a pause naturally works
in real conversation), at which point it's spoken and the word resets so
you can go straight into the next one.

Controls:
    c - clear the current word and start spelling a new one (manual override)
    q - quit

Usage:
    python src/spell_words.py
"""

import os
import sys
import cv2
import joblib
import numpy as np

sys.path.append(os.path.dirname(__file__))
from utils import extract_landmarks_from_bgr_frame
from word_builder import WordBuilder
from speech import speak

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "bsl_fingerspelling_mlp.joblib")
LABEL_ENCODER_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "label_encoder.joblib")

CONFIDENCE_THRESHOLD = 0.6
STABILITY_FRAMES = 15      # ~0.5s held steady before a letter counts as "signed"
WORD_PAUSE_FRAMES = 45     # ~1.5s paused before a word counts as "finished" and gets spoken

# How many frames to keep showing "Said: <word>" on screen after speaking it,
# purely for visual confirmation alongside the audio.
SPOKEN_LABEL_DISPLAY_FRAMES = 60


def main():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(LABEL_ENCODER_PATH)):
        print("ERROR: trained model not found.")
        print("Run 'python src/extract_landmarks.py' then 'python src/train_classifier.py' first.")
        return

    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(LABEL_ENCODER_PATH)
    word_builder = WordBuilder(
        stability_frames=STABILITY_FRAMES,
        confidence_threshold=CONFIDENCE_THRESHOLD,
        word_pause_frames=WORD_PAUSE_FRAMES,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: could not open webcam (device 0). Check camera permissions/index.")
        return

    print("Webcam started. Hold each letter steady to spell a word.")
    print("Pause for about 1.5s after finishing a word — it will be spoken automatically.")
    print("Press 'c' to clear manually, 'q' to quit.")

    last_spoken_word = ""
    last_spoken_display_countdown = 0

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            break

        # Run detection on the raw (unmirrored) frame, matching training data
        # orientation; only the displayed copy gets mirrored for a natural view.
        features = extract_landmarks_from_bgr_frame(frame)
        display_frame = cv2.flip(frame, 1)

        predicted_letter = None
        confidence = 0.0
        if features is not None:
            probabilities = model.predict_proba(features.reshape(1, -1))[0]
            best_index = int(np.argmax(probabilities))
            confidence = probabilities[best_index]
            predicted_letter = label_encoder.classes_[best_index]

        _, word_completed = word_builder.update(predicted_letter, confidence)

        if word_completed:
            last_spoken_word = word_builder.word
            last_spoken_display_countdown = SPOKEN_LABEL_DISPLAY_FRAMES
            speak(last_spoken_word)      # non-blocking — loop keeps running immediately
            word_builder.clear()         # ready for the next word right away

        # --- On-screen display ---
        # Big line: the word currently being built
        cv2.putText(
            display_frame, word_builder.word or "(spell a word...)", (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 0), 3, cv2.LINE_AA,
        )

        # Smaller line: what it currently thinks you're holding, and how
        # close it is to committing (helps you understand WHY nothing
        # happened yet, instead of it feeling unresponsive)
        if predicted_letter is not None:
            progress = min(word_builder.candidate_count, STABILITY_FRAMES)
            status = f"Holding: {predicted_letter} ({confidence:.0%})  [{progress}/{STABILITY_FRAMES}]"
        else:
            status = "No hand detected"
        cv2.putText(
            display_frame, status, (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA,
        )

        # Brief on-screen confirmation of the last spoken word, alongside the audio
        if last_spoken_display_countdown > 0:
            cv2.putText(
                display_frame, f"Said: {last_spoken_word}", (20, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA,
            )
            last_spoken_display_countdown -= 1

        cv2.putText(
            display_frame, "c: clear   q: quit", (20, display_frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA,
        )

        cv2.imshow("BSL Word Spelling", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            word_builder.clear()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
