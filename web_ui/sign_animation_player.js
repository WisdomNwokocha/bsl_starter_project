/**
 * sign_animation_player.js
 * -------------------------
 * Draws an animated hand on <canvas id="signCanvas">, replaying REAL
 * recorded hand motion (from extract_sign_animations.py) frame by frame.
 *
 * Rendered as a filled, tapered hand silhouette (no dots, no skeleton
 * lines) — a solid shape that reads as an actual hand, applied to your
 * real tracked motion data on every frame, not a fixed illustration.
 * No body/arm — just the hand, centered in the canvas.
 */

const signCanvas = document.getElementById("signCanvas");
const skeletonCtx = signCanvas.getContext("2d");

const CANVAS_WIDTH = 480;
const CANVAS_HEIGHT = 360;
signCanvas.width = CANVAS_WIDTH;
signCanvas.height = CANVAS_HEIGHT;

const SKIN_LIGHT = "#E8CCAC";
const SKIN_DARK = "#C49A6E";
const SKIN_OUTLINE = "#B08F6B";

// Underlay (dark outline) and top (skin-colored) stroke widths for each
// position along a finger, from base (index 0) to tip (index 3) — this is
// what creates the tapered look. Applies to every finger/thumb the same way.
const UNDERLAY_WIDTHS = [21, 17, 13, 10];
const TOP_WIDTHS = [17, 13, 10, 7];

let skinGradient = null;

function getSkinGradient() {
  // Built once against fixed canvas dimensions and reused every frame —
  // regardless of where the hand actually is, this keeps a consistent
  // light-to-dark wash rather than recalculating (and slightly changing)
  // the gradient every frame as the hand moves.
  if (!skinGradient) {
    skinGradient = skeletonCtx.createLinearGradient(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    skinGradient.addColorStop(0, SKIN_LIGHT);
    skinGradient.addColorStop(1, SKIN_DARK);
  }
  return skinGradient;
}

/**
 * Plays one complete animation sequence and resolves when it's finished.
 * @param {{fps: number, sourceWidth: number, sourceHeight: number, frames: Array}} animationData
 */
function playSkeletonAnimation(animationData) {
  return new Promise((resolve) => {
    const { fps, frames } = animationData;
    const frameDurationMs = 1000 / fps;
    const transform = computeAspectFitTransform(animationData);
    let frameIndex = 0;

    function drawNextFrame() {
      if (frameIndex >= frames.length) {
        resolve();
        return;
      }
      drawHandsFrame(frames[frameIndex], transform);
      frameIndex += 1;
      setTimeout(drawNextFrame, frameDurationMs);
    }

    drawNextFrame();
  });
}

/**
 * The recording's real aspect ratio (e.g. 16:9 webcam) won't always match
 * the canvas's fixed 4:3 shape. Rather than stretch the hand to fill the
 * canvas (which would visibly distort it), this computes a "fit within,
 * preserve proportions, center it" transform — the same idea as
 * `object-fit: contain` for images/video.
 */
function computeAspectFitTransform({ sourceWidth, sourceHeight }) {
  const scale = Math.min(CANVAS_WIDTH / sourceWidth, CANVAS_HEIGHT / sourceHeight);
  const drawWidth = sourceWidth * scale;
  const drawHeight = sourceHeight * scale;
  const offsetX = (CANVAS_WIDTH - drawWidth) / 2;
  const offsetY = (CANVAS_HEIGHT - drawHeight) / 2;
  return { scale, offsetX, offsetY, sourceWidth, sourceHeight };
}

/**
 * Draws every hand present in a single frame as a filled, tapered
 * silhouette — a solid palm shape plus tapered fingers/thumb, all in one
 * consistent skin tone, built from the REAL tracked point positions for
 * this exact frame (works for any hand shape, not just one fixed pose).
 * @param {Array<{handedness: string, points: number[][]}>} handsInFrame
 * @param {{scale: number, offsetX: number, offsetY: number, sourceWidth: number, sourceHeight: number}} transform
 */
function drawHandsFrame(handsInFrame, transform) {
  skeletonCtx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

  for (const hand of handsInFrame) {
    const screenPoints = hand.points.map(([x, y]) => [
      x * transform.sourceWidth * transform.scale + transform.offsetX,
      y * transform.sourceHeight * transform.scale + transform.offsetY,
    ]);

    drawPalmFill(screenPoints);
    for (const group of FINGER_GROUPS) {
      drawTaperedFinger(screenPoints, group);
    }
  }
}

function drawPalmFill(screenPoints) {
  // A straight-edged polygon across the wrist and the four finger bases.
  // Deliberately kept simple/robust rather than a hand-tuned curved
  // outline: a curved shape tuned to look good for one open-hand pose can
  // look wrong for other real hand shapes (a closed fist, a fingerspelled
  // letter) — this works reasonably for any real tracked hand position.
  const palmOutlineIndices = [0, 5, 9, 13, 17];
  skeletonCtx.beginPath();
  palmOutlineIndices.forEach((pointIndex, i) => {
    const [x, y] = screenPoints[pointIndex];
    if (i === 0) skeletonCtx.moveTo(x, y);
    else skeletonCtx.lineTo(x, y);
  });
  skeletonCtx.closePath();
  skeletonCtx.fillStyle = getSkinGradient();
  skeletonCtx.strokeStyle = SKIN_OUTLINE;
  skeletonCtx.lineWidth = 1.5;
  skeletonCtx.fill();
  skeletonCtx.stroke();
}

function drawTaperedFinger(screenPoints, group) {
  skeletonCtx.lineCap = "round";

  // Underlay first (wider, darker) for a soft outline...
  group.connections.forEach(([fromIndex, toIndex], segmentIndex) => {
    const [x1, y1] = screenPoints[fromIndex];
    const [x2, y2] = screenPoints[toIndex];
    skeletonCtx.strokeStyle = SKIN_OUTLINE;
    skeletonCtx.lineWidth = UNDERLAY_WIDTHS[segmentIndex];
    skeletonCtx.beginPath();
    skeletonCtx.moveTo(x1, y1);
    skeletonCtx.lineTo(x2, y2);
    skeletonCtx.stroke();
  });

  // ...then the skin-toned fill on top, narrower, creating the taper.
  group.connections.forEach(([fromIndex, toIndex], segmentIndex) => {
    const [x1, y1] = screenPoints[fromIndex];
    const [x2, y2] = screenPoints[toIndex];
    skeletonCtx.strokeStyle = getSkinGradient();
    skeletonCtx.lineWidth = TOP_WIDTHS[segmentIndex];
    skeletonCtx.beginPath();
    skeletonCtx.moveTo(x1, y1);
    skeletonCtx.lineTo(x2, y2);
    skeletonCtx.stroke();
  });
}

function clearSkeletonCanvas() {
  skeletonCtx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
}
