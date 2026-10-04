"""
extract_landmarks.py
---------------------
STEP 1 of the pipeline.

Walks through data/raw/<LABEL>/*.jpg (or .png) images — one folder per
letter/sign — runs MediaPipe Hands on each image, and writes a single CSV
of landmark features to data/processed/landmarks.csv.

Expected input folder structure (this matches how the Kaggle BSL
Fingerspelling dataset is typically organised once unzipped):

    data/raw/
        A/
            img001.jpg
            img002.jpg
            ...
        B/
            img001.jpg
            ...
        ...
        Z/
            ...

Usage:
    python src/extract_landmarks.py
"""

import os
import sys
import csv
import cv2
from tqdm import tqdm

# allow running this script directly (python src/extract_landmarks.py)
sys.path.append(os.path.dirname(__file__))
from utils import extract_landmarks_from_bgr_frame, feature_column_names

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "landmarks.csv")

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")

# NOTE: this script writes only the REAL extracted landmarks, one row per
# successfully-detected image — no synthetic augmentation here. Augmentation
# happens later, in train_classifier.py, and only on the training split.
# (Augmenting here, before the train/test split, would let near-identical
# synthetic copies of the same photo end up on both sides of the split —
# that inflates test accuracy without the model actually being any better.)


def main():
    if not os.path.isdir(RAW_DATA_DIR):
        print(f"ERROR: raw data folder not found at {RAW_DATA_DIR}")
        print("Download the BSL fingerspelling dataset and place it there first")
        print("(one sub-folder per letter, e.g. data/raw/A/, data/raw/B/, ...).")
        sys.exit(1)

    labels = sorted(
        d for d in os.listdir(RAW_DATA_DIR)
        if os.path.isdir(os.path.join(RAW_DATA_DIR, d))
    )
    if not labels:
        print(f"ERROR: no label folders found inside {RAW_DATA_DIR}")
        sys.exit(1)

    print(f"Found {len(labels)} label folders: {labels}")

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    rows_written = 0
    images_skipped_no_hand = 0

    with open(OUTPUT_CSV, "w", newline="") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["label"] + feature_column_names())

        for label in labels:
            label_dir = os.path.join(RAW_DATA_DIR, label)
            image_files = [
                f for f in os.listdir(label_dir)
                if f.lower().endswith(VALID_EXTENSIONS)
            ]

            for image_file in tqdm(image_files, desc=f"Processing '{label}'"):
                image_path = os.path.join(label_dir, image_file)
                frame = cv2.imread(image_path)

                if frame is None:
                    continue  # unreadable/corrupt file, skip it

                features = extract_landmarks_from_bgr_frame(frame)

                if features is None:
                    images_skipped_no_hand += 1
                    continue  # MediaPipe couldn't find a hand in this image

                writer.writerow([label] + features.tolist())
                rows_written += 1

    print(f"\nDone. Wrote {rows_written} rows to {OUTPUT_CSV}")
    print(f"Skipped {images_skipped_no_hand} images where no hand was detected.")
    if images_skipped_no_hand > 0:
        print("Tip: a high skip count usually means poor lighting/framing in the")
        print("source images, or that images need cropping closer to the hand.")
    if rows_written > 0 and rows_written < 15 * len(labels):
        print("\nNote: that's a small number of real images per letter. This is")
        print("normal for a starter dataset — train_classifier.py will apply")
        print("synthetic augmentation to the training split to help compensate.")


if __name__ == "__main__":
    main()
