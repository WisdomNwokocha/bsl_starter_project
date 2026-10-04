/**
 * hand_skeleton.js
 * ----------------
 * The fixed topology of a hand skeleton — which of the 21 MediaPipe hand
 * landmarks connect to which others, so we can draw lines between the
 * right points rather than just floating dots. This is a fixed, known
 * layout (MediaPipe's own standard hand connection map), not something
 * derived from data — kept as pure data/logic, no DOM, so it's testable.
 *
 * Grouped by finger (not just a flat list) so the renderer can color each
 * finger distinctly — this is what actually makes the animation easy to
 * read: a viewer can track one finger through motion by its color, rather
 * than every point/line looking identical.
 */

// Each group: name, its point indices (in order from base to tip), the
// connections within it, and a color. Colors are hardcoded hex (not the
// app's theme-adaptive classes) because this is a fixed-look, always-dark
// canvas element, not a UI surface that should shift with light/dark mode.
const FINGER_GROUPS = [
  { name: "thumb",  points: [0, 1, 2, 3, 4],     connections: [[0, 1], [1, 2], [2, 3], [3, 4]],         color: "#E6A54B" },
  { name: "index",  points: [0, 5, 6, 7, 8],     connections: [[0, 5], [5, 6], [6, 7], [7, 8]],         color: "#7FB69E" },
  { name: "middle", points: [5, 9, 10, 11, 12],  connections: [[5, 9], [9, 10], [10, 11], [11, 12]],    color: "#E08D6D" },
  { name: "ring",   points: [9, 13, 14, 15, 16], connections: [[9, 13], [13, 14], [14, 15], [15, 16]],  color: "#7A9CC6" },
  { name: "pinky",  points: [13, 17, 18, 19, 20],connections: [[13, 17], [17, 18], [18, 19], [19, 20]], color: "#B79FD1" },
];

// The wrist-to-pinky-base connection that closes the palm outline — kept
// separate since it isn't part of any single finger.
const PALM_CONNECTOR = [0, 17];
const WRIST_POINT_INDEX = 0;

// Fingertip indices — drawn larger, since these carry the most meaning
// for fingerspelling (which fingers are extended/where they point).
const FINGERTIP_INDICES = [4, 8, 12, 16, 20];

// Flat list of every connection, kept for anything that just needs "every
// line in the hand" without caring about per-finger grouping/color.
const HAND_CONNECTIONS = FINGER_GROUPS.flatMap((group) => group.connections).concat([PALM_CONNECTOR]);

if (typeof module !== "undefined" && module.exports) {
  module.exports = { HAND_CONNECTIONS, FINGER_GROUPS, PALM_CONNECTOR, WRIST_POINT_INDEX, FINGERTIP_INDICES };
}
