/**
 * hand_skeleton.js
 * ----------------
 * The fixed topology of a hand skeleton — which of the 21 MediaPipe hand
 * landmarks connect to which others, so we can draw lines between the
 * right points rather than just floating dots. This is a fixed, known
 * layout (MediaPipe's own standard hand connection map), not something
 * derived from data — kept as pure data/logic, no DOM, so it's testable.
 */

// Each pair is [fromPointIndex, toPointIndex]. Points are numbered 0-20
// per MediaPipe's hand landmark convention (0 = wrist).
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],        // thumb
  [0, 5], [5, 6], [6, 7], [7, 8],        // index finger
  [5, 9], [9, 10], [10, 11], [11, 12],   // middle finger
  [9, 13], [13, 14], [14, 15], [15, 16], // ring finger
  [13, 17], [17, 18], [18, 19], [19, 20],// pinky finger
  [0, 17],                                // wrist to pinky base (closes the palm)
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { HAND_CONNECTIONS };
}
