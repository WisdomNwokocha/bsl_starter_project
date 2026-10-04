"""
utils.py
--------
Shared helper functions for turning a camera frame / image into a fixed-length
numeric feature vector using MediaPipe Hands.

Why landmarks instead of raw pixels?
- BSL fingerspelling is two-handed, so a photo of a hand shape has a LOT of
  irrelevant information (background, lighting, skin tone, clothing).
- MediaPipe Hands gives us 21 (x, y, z) keypoints PER hand, already
  normalised to the hand's bounding box. Feeding those numbers into a
  classifier is far easier to train, needs much less data, and generalises
  much better across different people/backgrounds than raw pixels do.

Feature vector layout (126 numbers total):
    [ hand_1 = LEFT hand:  21 landmarks * (x, y, z) = 63 values ]
    [ hand_2 = RIGHT hand: 21 landmarks * (x, y, z) = 63 values ]
Hands are assigned to these slots using MediaPipe's own Left/Right
classification, NOT the order MediaPipe happened to detect them in —
detection order is not guaranteed consistent between frames/images, and
using it as if it were consistent silently scrambles which hand's data
lands in which slot (a real bug this file previously had).
If only one hand is detected, the other hand's 63 values are filled with 0.
If no hand is detected, the whole vector is None (caller should skip/handle it).

IMPORTANT — normalisation:
MediaPipe's raw landmark x/y values are normalised to the *whole video
frame*, NOT to the hand itself. That means the same hand shape produces
completely different numbers depending on where the hand sits in frame and
how large it appears (close to camera vs far away). A close-up training
photo and a normal webcam shot of the same sign will look nothing alike to
a model trained on raw coordinates.

To fix this, every hand's landmarks are re-centred on the wrist (landmark
0) and rescaled by the wrist-to-middle-finger-knuckle distance (landmark
9). This makes the features describe the *shape* of the hand, independent
of its position and distance from the camera — which is what actually
needs to generalise from training photos to a live webcam.
"""

import numpy as np
import mediapipe as mp

mp_hands = mp.solutions.hands

# One shared detector instance, reused across calls for speed.
_hands_detector = mp_hands.Hands(
    static_image_mode=False,   # False = optimised for video/webcam streams
    max_num_hands=2,           # BSL fingerspelling often uses both hands
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5,
)

NUM_LANDMARKS_PER_HAND = 21
VALUES_PER_LANDMARK = 3  # x, y, z
FEATURE_VECTOR_LENGTH = NUM_LANDMARKS_PER_HAND * VALUES_PER_LANDMARK * 2  # 126

# Landmark indices used for normalisation (see MediaPipe Hands landmark map)
WRIST_INDEX = 0
MIDDLE_FINGER_MCP_INDEX = 9  # knuckle at the base of the middle finger


def _normalize_single_hand(hand_landmarks):
    """
    Convert one MediaPipe hand_landmarks object into a (63,) flat array that
    is invariant to the hand's position in frame and its distance from the
    camera (translation + scale normalised). Not rotation-invariant — a
    sideways-tilted hand still looks different, which is a reasonable
    future improvement but out of scope for this starter version.
    """
    points = np.array(
        [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark],
        dtype=np.float32,
    )  # shape (21, 3)

    wrist = points[WRIST_INDEX].copy()
    points = points - wrist  # translate: wrist becomes the origin (0, 0, 0)

    scale = np.linalg.norm(points[MIDDLE_FINGER_MCP_INDEX])
    if scale < 1e-6:
        scale = 1.0  # avoid divide-by-zero on a degenerate detection
    points = points / scale  # rescale: hand size no longer matters

    return points.flatten()  # (63,)


def extract_landmarks_from_bgr_frame(frame_bgr):
    """
    Run MediaPipe Hands on a single BGR frame (the format OpenCV uses) and
    return a fixed-length (126,) numpy feature vector, or None if no hand
    was detected at all.

    Args:
        frame_bgr: np.ndarray, shape (H, W, 3), BGR color order (cv2 default)

    Returns:
        np.ndarray of shape (126,) or None
    """
    import cv2  # local import keeps this module importable without cv2 for pure-CSV use

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = _hands_detector.process(frame_rgb)

    if not results.multi_hand_landmarks:
        return None

    # Start with two hands' worth of zeros, then fill in whichever hands were found.
    feature_vector = np.zeros(FEATURE_VECTOR_LENGTH, dtype=np.float32)
    hand_block_length = NUM_LANDMARKS_PER_HAND * VALUES_PER_LANDMARK

    # IMPORTANT: assign each hand to a slot based on MediaPipe's own
    # Left/Right classification (multi_handedness), NOT on the order
    # MediaPipe happened to detect them in. Detection order is not
    # guaranteed to be consistent between frames/images — using it as if
    # it meant "hand 1 is always the same physical hand" silently scrambles
    # which hand's data lands in which feature slot, which is especially
    # damaging for two-handed signs where the two hands play different,
    # specific roles (e.g. one hand's shape vs. where it points on the
    # other hand). This was previously a real bug in this function.
    slot_for_label = {"Left": 0, "Right": 1}
    used_slots = set()

    hands_and_labels = list(zip(results.multi_hand_landmarks, results.multi_handedness))

    for hand_landmarks, handedness in hands_and_labels:
        label = handedness.classification[0].label  # "Left" or "Right"
        slot = slot_for_label.get(label)

        if slot is None or slot in used_slots:
            # Fallback for the rare case MediaPipe reports an unexpected
            # label, or (very rarely) both hands with the same label:
            # just take whichever slot is still free.
            slot = 0 if 0 not in used_slots else 1

        used_slots.add(slot)
        offset = slot * hand_block_length
        feature_vector[offset:offset + hand_block_length] = _normalize_single_hand(hand_landmarks)

        if len(used_slots) >= 2:
            break  # ignore any spurious 3rd+ hand detection

    return feature_vector


def feature_column_names():
    """Returns the 126 column names used in the processed CSV, for readability."""
    names = []
    for hand_index in (1, 2):
        for point_index in range(NUM_LANDMARKS_PER_HAND):
            for axis in ("x", "y", "z"):
                names.append(f"hand{hand_index}_p{point_index}_{axis}")
    return names


def augment_landmark_vector(feature_vector, rng, rotation_range_degrees=12.0, noise_std=0.02):
    """
    Create ONE synthetic variation of an already-normalised (126,) landmark
    feature vector, by applying a small random in-plane rotation and a
    small amount of per-point jitter to each hand present in the vector.

    This exists to help small datasets (e.g. ~10 photos per letter) go
    further: a handful of real photos becomes a few hundred realistic
    variations, roughly simulating the natural wobble in hand angle and
    finger position a live camera would see. It is NOT a substitute for
    real data diversity (different people, lighting, backgrounds) — treat
    it as a way to get more mileage out of a small dataset, not a fix for
    a dataset that's fundamentally too small or too narrow.

    Args:
        feature_vector: np.ndarray, shape (126,) — output of
            extract_landmarks_from_bgr_frame for one image.
        rng: a numpy random Generator (np.random.default_rng(seed)),
            passed in so callers control reproducibility.
        rotation_range_degrees: max random in-plane rotation applied, in
            either direction (e.g. 12.0 means anywhere from -12 to +12).
        noise_std: standard deviation of Gaussian noise added to each
            coordinate, in the same normalised units the vector is already in.

    Returns:
        np.ndarray, shape (126,) — a new, synthetic feature vector.
    """
    augmented = feature_vector.copy()
    hand_block_length = NUM_LANDMARKS_PER_HAND * VALUES_PER_LANDMARK  # 63

    angle_radians = np.deg2rad(rng.uniform(-rotation_range_degrees, rotation_range_degrees))
    cos_a, sin_a = np.cos(angle_radians), np.sin(angle_radians)

    for hand_index in (0, 1):
        start = hand_index * hand_block_length
        block = augmented[start:start + hand_block_length]

        if not np.any(block):
            continue  # this hand slot is all zeros (hand wasn't present) - leave it alone

        points = block.reshape(NUM_LANDMARKS_PER_HAND, VALUES_PER_LANDMARK).copy()

        # small in-plane (x/y) rotation around the origin (the wrist, since
        # normalisation already centred each hand on its own wrist)
        x, y = points[:, 0].copy(), points[:, 1].copy()
        points[:, 0] = x * cos_a - y * sin_a
        points[:, 1] = x * sin_a + y * cos_a

        # small per-point jitter, simulating natural variation in exact
        # finger position/angle between real signing attempts
        points += rng.normal(0.0, noise_std, size=points.shape)

        augmented[start:start + hand_block_length] = points.flatten()

    return augmented


def extract_raw_hand_landmarks(frame_bgr):
    """
    Returns each detected hand's RAW landmark positions (MediaPipe's native
    0-1 image-relative coordinates), with NO translation/scale normalisation.

    This is deliberately different from extract_landmarks_from_bgr_frame():
    that function normalises each hand for CLASSIFICATION (so the same sign
    looks the same regardless of hand position/size in frame). This function
    is for ANIMATION — we want the opposite here, since we need to preserve
    real proportions and natural motion to animate a believable skeleton
    performing the sign, not throw that information away.

    Returns:
        A list of hands actually detected (0, 1, or 2 items), each:
        {"handedness": "Left" or "Right", "points": [[x, y], ...21 pairs]}
        Returns an empty list if no hand was detected at all.
    """
    import cv2

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = _hands_detector.process(frame_rgb)

    hands = []
    if not results.multi_hand_landmarks:
        return hands

    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
        label = handedness.classification[0].label  # "Left" or "Right"
        points = [[lm.x, lm.y] for lm in hand_landmarks.landmark]
        hands.append({"handedness": label, "points": points})

    return hands
