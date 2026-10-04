"""
train_classifier.py
--------------------
STEP 2 of the pipeline.

Loads data/processed/landmarks.csv (produced by extract_landmarks.py),
trains a simple neural network classifier to map landmark features -> letter,
evaluates it on a held-out test split, and saves the trained model +
label encoder to the models/ folder.

Why an MLP (small neural net) instead of a big deep learning model?
Because the input is only 126 numbers (not raw pixels), a small classifier
is enough to get strong accuracy, trains in seconds/minutes on a laptop CPU,
and is a good, honest baseline before you invest in anything heavier.

Usage:
    python src/train_classifier.py
"""

import os
import numpy as np
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

import sys
sys.path.append(os.path.dirname(__file__))
from utils import augment_landmark_vector

PROCESSED_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "landmarks.csv")
MODEL_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "bsl_fingerspelling_mlp.joblib")
LABEL_ENCODER_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "label_encoder.joblib")

# How many synthetic variations to generate per REAL training example.
# Applied only to the training split, never the test split, so reported
# accuracy stays an honest measure of real-world generalisation. Small
# datasets (e.g. ~10 photos/letter) benefit the most from this; set to 0
# to disable augmentation entirely once you have plenty of real data.
AUGMENTATIONS_PER_TRAINING_EXAMPLE = 25


def _augment_training_set(X_train, y_train, rng):
    """Expand the training set by generating synthetic jittered/rotated
    copies of each real training example. Never touches the test set."""
    augmented_X = [X_train]
    augmented_y = [y_train]

    for _ in range(AUGMENTATIONS_PER_TRAINING_EXAMPLE):
        synthetic_batch = np.array([
            augment_landmark_vector(row, rng) for row in X_train
        ])
        augmented_X.append(synthetic_batch)
        augmented_y.append(y_train)

    return np.vstack(augmented_X), np.concatenate(augmented_y)


def main():
    if not os.path.exists(PROCESSED_CSV):
        print(f"ERROR: {PROCESSED_CSV} not found.")
        print("Run 'python src/extract_landmarks.py' first to generate it.")
        return

    df = pd.read_csv(PROCESSED_CSV)
    if len(df) == 0:
        print("ERROR: landmarks.csv is empty. Check your raw images / extraction step.")
        return

    print(f"Loaded {len(df)} REAL labeled examples across {df['label'].nunique()} classes.")
    print(df["label"].value_counts().sort_index())

    feature_columns = [c for c in df.columns if c != "label"]
    X = df[feature_columns].values
    y_raw = df["label"].values

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    # Split FIRST, on real data only, so the test set is never contaminated
    # by synthetic near-duplicates of a training example.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    real_train_count = len(X_train)

    if AUGMENTATIONS_PER_TRAINING_EXAMPLE > 0:
        rng = np.random.default_rng(seed=42)
        X_train, y_train = _augment_training_set(X_train, y_train, rng)
        print(f"\nExpanded training set from {real_train_count} real examples to "
              f"{len(X_train)} examples using synthetic augmentation.")
        print("(Test set remains 100% real, untouched, for an honest accuracy check.)")

    print(f"\nTraining on {len(X_train)} examples, testing on {len(X_test)} REAL examples...")

    model = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        max_iter=500,
        random_state=42,
        early_stopping=True,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\nTest accuracy (on real, unaugmented data): {accuracy:.2%}\n")
    print("Per-class report:")
    print(classification_report(
        y_test, y_pred, target_names=label_encoder.classes_, zero_division=0
    ))

    if real_train_count < 15 * len(label_encoder.classes_):
        print("Note: this model was trained on relatively few real photos per")
        print("letter. Augmentation helps, but adding more real, varied photos")
        print("per letter (different lighting/angles) will help accuracy more.")

    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    joblib.dump(model, MODEL_OUTPUT_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_OUTPUT_PATH)

    print(f"Saved trained model to: {MODEL_OUTPUT_PATH}")
    print(f"Saved label encoder to: {LABEL_ENCODER_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
