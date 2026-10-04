/**
 * sign_animation_player.js
 * -------------------------
 * Draws an animated hand skeleton on <canvas id="signCanvas">, replaying
 * REAL recorded hand motion (from extract_sign_animations.py) frame by
 * frame — this is the "animated character" doing the sign, built from
 * genuine human movement rather than a video clip or a fully generated
 * character. See project notes: this is deliberately the simple,
 * buildable "Tier 1" version (a moving skeleton), not a polished
 * illustrated character or a full 3D avatar.
 */

const signCanvas = document.getElementById("signCanvas");
const skeletonCtx = signCanvas.getContext("2d");

// Internal drawing resolution — kept fixed regardless of how large the
// canvas is displayed on screen (CSS handles the visual scaling).
const CANVAS_WIDTH = 480;
const CANVAS_HEIGHT = 360;
signCanvas.width = CANVAS_WIDTH;
signCanvas.height = CANVAS_HEIGHT;

const POINT_RADIUS = 5;
const LINE_WIDTH = 3;
const POINT_COLOR = "#E6A54B";  // amber, matching the app's design system
const LINE_COLOR = "#F2EEE6";   // warm off-white

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
 * the canvas's fixed 4:3 shape. Rather than stretch the skeleton to fill
 * the canvas (which would visibly distort the hand), this computes a
 * "fit within, preserve proportions, center it" transform — the same
 * general idea as `object-fit: contain` for images/video.
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
 * Draws every hand present in a single frame of animation data.
 * @param {Array<{handedness: string, points: number[][]}>} handsInFrame
 * @param {{scale: number, offsetX: number, offsetY: number, sourceWidth: number, sourceHeight: number}} transform
 */
function drawHandsFrame(handsInFrame, transform) {
  skeletonCtx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

  for (const hand of handsInFrame) {
    // Points are stored as 0-1 fractions of the ORIGINAL recording's frame,
    // so convert to real source pixels first, then apply the aspect-fit
    // transform onto the canvas — this keeps hand proportions correct
    // regardless of the source recording's actual resolution/aspect ratio.
    const screenPoints = hand.points.map(([x, y]) => [
      x * transform.sourceWidth * transform.scale + transform.offsetX,
      y * transform.sourceHeight * transform.scale + transform.offsetY,
    ]);

    skeletonCtx.strokeStyle = LINE_COLOR;
    skeletonCtx.lineWidth = LINE_WIDTH;
    skeletonCtx.lineCap = "round";

    for (const [fromIndex, toIndex] of HAND_CONNECTIONS) {
      const [x1, y1] = screenPoints[fromIndex];
      const [x2, y2] = screenPoints[toIndex];
      skeletonCtx.beginPath();
      skeletonCtx.moveTo(x1, y1);
      skeletonCtx.lineTo(x2, y2);
      skeletonCtx.stroke();
    }

    skeletonCtx.fillStyle = POINT_COLOR;
    for (const [x, y] of screenPoints) {
      skeletonCtx.beginPath();
      skeletonCtx.arc(x, y, POINT_RADIUS, 0, Math.PI * 2);
      skeletonCtx.fill();
    }
  }
}

function clearSkeletonCanvas() {
  skeletonCtx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
}
