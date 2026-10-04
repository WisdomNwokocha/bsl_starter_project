"""
extract_frames_from_clips.py
------------------------------
Bridges your data uses from your recorded videos, and supports two sources:

1. web_ui/sign_clips/<LABEL>.mp4 (ONE canonical clip per letter, also used
   directly by the "type to sign" playback feature) — contributes one
   training frame per label.

2. data/raw_videos/<LABEL>/*.mp4 (as MANY videos as you want per letter —
   different takes, different sessions, different signers) — contributes
   one training frame PER VIDEO, so more real recordings genuinely means
   more real training data, exactly like adding more images to
   data/raw/<LABEL>/ directly.

Both sources feed into the SAME place: data/raw/<LABEL>/, alongside
whatever's already there (e.g. your Kaggle images) — nothing is
overwritten, everything just adds up.

How it picks which frame to use from each video:
Not just "the middle frame" blindly — a video usually starts and ends with
the hand still moving into or out of position. Instead, this scans every
frame, keeps only the ones where MediaPipe actually detects a confident
hand shape, and picks the middle one of THOSE — the most likely moment the
sign was fully, clearly held.

Usage:
    python src/extract_frames_from_clips.py
"""

import os
import sys
import cv2

sys.path.append(os.path.dirname(__file__))
from utils import extract_landmarks_from_bgr_frame

SIGN_CLIPS_DIR = os.path.join(os.path.dirname(__file__), "..", "web_ui", "sign_clips")
RAW_VIDEOS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw_videos")
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

VALID_EXTENSIONS = (".mp4", ".webm", ".mov")


def find_best_frame(video_path):
    """
    Returns the single best still frame (as a BGR numpy array) from a video
    for training purposes, or None if no frame in the whole clip had a
    confidently detectable hand.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    frames_with_confident_hand = []

    while True:
        success, frame = cap.read()
        if not success:
            break
        if extract_landmarks_from_bgr_frame(frame) is not None:
            frames_with_confident_hand.append(frame)

    cap.release()

    if not frames_with_confident_hand:
        return None

    middle_index = len(frames_with_confident_hand) // 2
    return frames_with_confident_hand[middle_index]


def process_video(video_path, label, output_filename, counters):
    """Shared logic: extract the best frame from one video and save it."""
    best_frame = find_best_frame(video_path)

    if best_frame is None:
        print(f"  Skipped '{os.path.basename(video_path)}': no frame had a detectable hand.")
        counters["skipped"] += 1
        return

    label_dir = os.path.join(RAW_DATA_DIR, label)
    os.makedirs(label_dir, exist_ok=True)

    output_path = os.path.join(label_dir, output_filename)
    cv2.imwrite(output_path, best_frame)
    print(f"  Saved: data/raw/{label}/{output_filename}")
    counters["extracted"] += 1


def main():
    counters = {"extracted": 0, "skipped": 0}

    # --- Source 1: the single canonical clip per letter, if present ---
    # Supports BOTH layouts, matching web_server.py and
    # extract_sign_animations.py: a flat file (sign_clips/A.mp4) or a
    # folder containing one or more takes (sign_clips/A/take1.mp4).
    if os.path.isdir(SIGN_CLIPS_DIR):
        for entry in sorted(os.listdir(SIGN_CLIPS_DIR)):
            entry_path = os.path.join(SIGN_CLIPS_DIR, entry)

            if os.path.isfile(entry_path) and entry.lower().endswith(VALID_EXTENSIONS):
                # Flat file layout: "A.mp4" -> label "A"
                label = os.path.splitext(entry)[0]
                print(f"Processing canonical clip for '{label}' ({entry})...")
                process_video(entry_path, label, f"{label}_from_clip.jpg", counters)

            elif os.path.isdir(entry_path):
                # Folder layout: "A/take1.mp4" -> label "A"
                label = entry
                video_files = [
                    f for f in sorted(os.listdir(entry_path))
                    if f.lower().endswith(VALID_EXTENSIONS)
                ]
                if not video_files:
                    continue
                # Use the first take found as the canonical one for this source.
                chosen_file = video_files[0]
                print(f"Processing canonical clip for '{label}' ({chosen_file})...")
                process_video(
                    os.path.join(entry_path, chosen_file),
                    label,
                    f"{label}_from_clip.jpg",
                    counters,
                )

    # --- Source 2: as many raw take videos per letter as you've collected ---
    if os.path.isdir(RAW_VIDEOS_DIR):
        label_folders = sorted(
            d for d in os.listdir(RAW_VIDEOS_DIR)
            if os.path.isdir(os.path.join(RAW_VIDEOS_DIR, d))
        )
        for label in label_folders:
            label_dir = os.path.join(RAW_VIDEOS_DIR, label)
            video_files = [f for f in os.listdir(label_dir) if f.lower().endswith(VALID_EXTENSIONS)]
            if not video_files:
                continue
            print(f"Processing {len(video_files)} raw take(s) for '{label}': {video_files}")
            for video_file in video_files:
                # Use the original video's filename (minus extension) so multiple
                # takes never collide/overwrite each other.
                output_filename = f"{os.path.splitext(video_file)[0]}.jpg"
                process_video(
                    os.path.join(label_dir, video_file),
                    label,
                    output_filename,
                    counters,
                )

    if counters["extracted"] == 0 and counters["skipped"] == 0:
        print("No video clips found in either web_ui/sign_clips/ or data/raw_videos/.")
        print("Add some .mp4/.webm files first — see the README for folder structure.")
        return

    print(f"\nDone. Extracted {counters['extracted']} training frame(s), "
          f"skipped {counters['skipped']} clip(s) with no detectable hand.")
    print("These are IN ADDITION to any existing images already in data/raw/ — ")
    print("nothing was overwritten. Re-run extract_landmarks.py and train_classifier.py")
    print("to include this new data in your trained model.")


if __name__ == "__main__":
    main()
