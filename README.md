# BSL Fingerspelling Recognition — Starter Project

This is the smallest possible working prototype of **Phase 1** from the AI
Sign Language Translator SRS: point a camera, get text out. It starts with
the *easiest* version of that problem — recognising single fingerspelled
letters — rather than full sentences, so you can prove the whole pipeline
works end to end before tackling continuous sign recognition.

## How it works (high level)

Instead of feeding raw video pixels into a big deep learning model, this
project uses **MediaPipe Hands** to extract hand *keypoints* (skeletal
landmarks — 21 points per hand, in 3D) from each frame. Those numbers are
what actually get fed into the classifier. This is:
- Much cheaper to train (a small model, not a huge one)
- Much less data-hungry
- More robust to background, lighting, and skin tone than raw pixels

```
Camera frame → MediaPipe Hands → 126 numbers (hand landmarks) → classifier → predicted letter
```

## Project structure

```
bsl_starter_project/
├── README.md
├── requirements.txt
├── data/
│   ├── raw/            ← put the downloaded dataset here (see below)
│   └── processed/      ← extract_landmarks.py writes landmarks.csv here
├── models/             ← train_classifier.py saves the trained model here
└── src/
    ├── utils.py             ← shared MediaPipe landmark extraction logic
    ├── extract_landmarks.py ← Step 1: images → landmarks.csv
    ├── train_classifier.py  ← Step 2: landmarks.csv → trained model
    └── predict_webcam.py    ← Step 3: live webcam demo
```

## Setup

**Important: use Python 3.11 or 3.12, not 3.13.** MediaPipe does not yet
publish pip packages for Python 3.13, so `pip install mediapipe` will fail
outright on a 3.13 interpreter. Check your version first with
`python3 --version`.

### macOS (Homebrew)

```bash
# Install a compatible Python version alongside your existing one
brew install python@3.12

# Create the virtual environment using 3.12 specifically
/opt/homebrew/bin/python3.12 -m venv venv
source venv/bin/activate

# Inside an activated venv, 'pip' works normally (unlike the bare
# Homebrew Python install, where only 'pip3' / 'python3 -m pip' exist)
pip install -r requirements.txt
```

### Windows / Linux

```bash
# Use a 3.11 or 3.12 install (via python.org, pyenv, etc.)
python3.12 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

If you only have Python 3.13 installed and don't want to install another
version system-wide, `pyenv` (macOS/Linux) or the Python installer from
python.org (Windows) both let multiple versions coexist cleanly.

## Step 0 — Get the dataset

Download the BSL Fingerspelling Dataset from Kaggle:
https://www.kaggle.com/datasets/alifsathar/bsl-fingerspelling-dataset

Unzip it so you end up with one folder per letter under `data/raw/`, e.g.:

```
data/raw/A/*.jpg
data/raw/B/*.jpg
...
data/raw/Z/*.jpg
```

(If the download comes in a different structure, just reorganise it into
this "one folder per label" layout — that's all the scripts expect.)

## Step 1 — Extract hand landmarks from the images

```bash
python src/extract_landmarks.py
```

This reads every image in `data/raw/<LETTER>/`, runs MediaPipe Hands on it,
and writes one row per successfully-detected hand to
`data/processed/landmarks.csv`. Images where no hand is detected are
skipped and counted (a high skip count usually means the source images are
poorly lit or the hand isn't clearly in frame).

## Step 2 — Train the classifier

```bash
python src/train_classifier.py
```

This loads `landmarks.csv`, splits it into train/test sets, trains a small
neural network (scikit-learn `MLPClassifier`), prints accuracy and a
per-letter breakdown, and saves:
- `models/bsl_fingerspelling_mlp.joblib` — the trained model
- `models/label_encoder.joblib` — maps model outputs back to letters

Expect this to take seconds to a couple of minutes on a normal laptop CPU
— this is a small model on a small number of features, deliberately.

## Step 3 — Try it live on your webcam

```bash
python src/predict_webcam.py
```

Opens your webcam, shows the predicted letter on screen in real time.
Press `q` to quit.

## Fixed: very low accuracy with a small dataset (e.g. ~10 photos/letter)

If you have only a handful of real photos per letter, `train_classifier.py`
now automatically generates synthetic variations (small random rotation +
jitter) of each **training** example to give the model more to learn from.
Critically, this only happens to the training split — the test set stays
100% real and untouched, so the accuracy number you see is still an honest
measure, not inflated by near-duplicate synthetic copies leaking between
train and test.

This helps, but it is not a substitute for more real, varied photos
(different lighting, angles, hand positions) — if accuracy is still weak
after this, adding more real images per letter is the next lever to pull.

Also double check your `data/raw/<LETTER>/` folders: if you merged
Kaggle's `train/` and `test/` folders together, make sure you didn't
accidentally copy the `train` folder itself into `data/raw/` (you'd see a
stray `data/raw/train/` folder alongside your letter folders — delete it
if so, since it gets read as if it were a 27th sign label).

## Fixed: webcam predictions being unreliable/low-confidence

An earlier version of this project had a bug that made real-world webcam
accuracy much worse than it should be: MediaPipe's raw landmark
coordinates are normalised to the *whole video frame*, not to the hand
itself — so the same hand shape produces very different numbers depending
on where it sits in frame and how close it is to the camera. A close-up
training photo and a normal webcam shot of the same letter looked
completely different to the model.

This is now fixed in `utils.py`: every hand's landmarks are re-centred on
the wrist and rescaled by hand size before being used, so the features
describe hand *shape* rather than *position in the picture*.
`predict_webcam.py` was also fixed to run detection on the raw camera
frame (matching how training photos are captured) and only mirror the
image for on-screen display.

**If you trained a model before this fix, delete `data/processed/landmarks.csv`
and everything in `models/`, then redo Steps 1 and 2** — the old
landmarks.csv was built with the un-normalised (buggy) coordinates and
won't match the fixed extraction code.

```bash
rm data/processed/landmarks.csv models/*.joblib
python src/extract_landmarks.py
python src/train_classifier.py
python src/predict_webcam.py
```

## What this does and doesn't prove

**This proves:** your capture → landmark extraction → classification →
live inference pipeline all work together, on a real (if narrow) sign
recognition task.

**This does NOT yet prove:** recognition of full words, sentences,
grammar, non-manual markers (facial expression/mouth patterns), or
continuous natural signing. That's a substantially harder problem —
see "Next steps" below.

## Next steps (in rough order of difficulty)

1. **Isolated whole-word signs** — same landmark approach, but the model
   needs to look at a *sequence* of frames (a short video clip) rather
   than a single image, since a whole sign involves movement. This is
   where you'd move from a simple MLP to something sequence-aware
   (e.g. an LSTM/GRU, or a Transformer, over a sequence of landmark
   vectors).
2. **Bring in native BSL signers** to validate the isolated-word dataset
   and flag anything ambiguous or dialect-specific before scaling up.
3. **Continuous signing (full sentences)** using a large dataset like
   BOBSL (BBC-Oxford British Sign Language dataset,
   https://www.robots.ox.ac.uk/~vgg/data/bobsl/). This is a big jump in
   difficulty: you'll need temporal alignment between video and subtitle
   text, and a translation model (not just classification) since sign
   order and grammar differ from English word order.
4. **Non-manual markers** — facial expression and mouth patterns carry
   real grammatical meaning in BSL (e.g. marking questions), so a
   production-quality system eventually needs MediaPipe's face landmarks
   too, not just hands.

## A note on scope

This starter project intentionally does the *easiest* 20% of Phase 1 first
(isolated letters) so you have a working, testable pipeline immediately.
The SRS's actual Phase 1 target — real-time sign-to-text from natural
continuous signing — is a considerably larger undertaking best tackled
once this foundation is solid and validated.
