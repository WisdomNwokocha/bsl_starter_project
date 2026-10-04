"""
extract_sign_animations.py
----------------------------
Turns your recorded sign clips (web_ui/sign_clips/) into skeleton ANIMATION
data — the real hand motion from every usable frame of each clip, saved as
JSON, ready to be replayed as an animated skeleton in the browser instead
of playing the video itself.

This is Tier 1 of the "avatar" idea: an animated dot-and-line hand
skeleton driven by REAL recorded human motion. It is deliberately NOT a
polished illustrated character or a full 3D avatar — those are much
bigger undertakings (see the project's roadmap notes). This is the
honest, buildable version: real motion, simply rendered.

Accepts the same two folder layouts as the rest of the project:
    web_ui/sign_clips/A.mp4            (a flat file)
    web_ui/sign_clips/A/take1.webm     (a folder with one or more takes)

Usage:
    python src/extract_sign_animations.py
"""

import os
import sys
import json

import cv2

sys.path.append(os.path.dirname(__file__))
from utils import extract_raw_hand_landmarks

SIGN_CLIPS_DIR = os.path.join(os.path.dirname(__file__), "..", "web_ui", "sign_clips")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "web_ui", "sign_animations")

VALID_EXTENSIONS = (".mp4", ".webm", ".mov")


def find_clip_for_label(label_path_no_ext, label_folder):
    """Returns the path to the one clip to use for a given label, checking
    both supported layouts (flat file, or a folder of takes — first found)."""
    for ext in VALID_EXTENSIONS:
        flat_path = label_path_no_ext + ext
        if os.path.exists(flat_path):
            return flat_path

    if os.path.isdir(label_folder):
        for filename in sorted(os.listdir(label_folder)):
            if filename.lower().endswith(VALID_EXTENSIONS):
                return os.path.join(label_folder, filename)

    return None


def extract_animation_from_video(video_path):
    """
    Returns {"fps": ..., "frames": [...]} — the sequence of detected hand
    positions across the clip, or None if no frame had a detectable hand.

    Only frames where a hand was actually found are kept, so the animation
    plays as continuous motion rather than including dead time at the
    start/end of the recording before/after the hand entered frame.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 24  # fall back to a sane default if unavailable

    # Browser-recorded webm files often don't store frame-rate metadata the
    # way OpenCV expects, and can report wildly wrong values (e.g. 1000fps)
    # that would make the animation play back far too fast to see. Clamp to
    # a believable range for real human hand motion.
    if fps < 5 or fps > 60:
        print(f"  Note: video reported an implausible fps ({fps:.0f}), using 24 instead.")
        fps = 24

    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    frames = []

    while True:
        success, frame = cap.read()
        if not success:
            break
        hands = extract_raw_hand_landmarks(frame)
        if hands:
            frames.append(hands)

    cap.release()

    if not frames:
        return None

    return {"fps": fps, "sourceWidth": source_width, "sourceHeight": source_height, "frames": frames}


def main():
    if not os.path.isdir(SIGN_CLIPS_DIR):
        print(f"ERROR: {SIGN_CLIPS_DIR} not found.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Discover labels the same way web_server.py does: check every entry in
    # sign_clips/ that's either a matching flat file or a folder.
    candidates = set()
    for entry in os.listdir(SIGN_CLIPS_DIR):
        name_no_ext = os.path.splitext(entry)[0]
        candidates.add(name_no_ext)

    if not candidates:
        print(f"No clips found in {SIGN_CLIPS_DIR}.")
        return

    extracted = 0
    skipped = 0

    for label in sorted(candidates):
        label_path_no_ext = os.path.join(SIGN_CLIPS_DIR, label)
        label_folder = os.path.join(SIGN_CLIPS_DIR, label)

        clip_path = find_clip_for_label(label_path_no_ext, label_folder)
        if clip_path is None:
            continue

        print(f"Processing '{label}' ({os.path.basename(clip_path)})...")
        animation = extract_animation_from_video(clip_path)

        if animation is None:
            print(f"  Skipped: no frame in this clip had a detectable hand.")
            skipped += 1
            continue

        output_path = os.path.join(OUTPUT_DIR, f"{label}.json")
        with open(output_path, "w") as f:
            json.dump(animation, f)

        print(f"  Saved: web_ui/sign_animations/{label}.json "
              f"({len(animation['frames'])} frames)")
        extracted += 1

    print(f"\nDone. Extracted {extracted} animation(s), skipped {skipped}.")


if __name__ == "__main__":
    main()
