/**
 * sign_sequence.js
 * ----------------
 * Turns typed text into an ordered list of clips to play, fingerspelling
 * it letter by letter using your REAL recorded clips (from the data
 * collector tool) rather than a generated animation. Kept as pure logic,
 * separate from the actual <video> playback driving code, so it can be
 * tested without a browser.
 */

/**
 * @param {string} text - what the user typed, e.g. "HI 7"
 * @param {Object<string,string>} availableClips - map of label -> clip URL,
 *   as returned by the /available_clips backend endpoint. e.g.
 *   { "A": "/clips/A.mp4", "NUMBER_7": "/clips/NUMBER_7.webm" }
 * @returns {Array<{label: string, displayChar: string, clipUrl: string|null, type: string}>}
 *   type is one of: "letter", "number", "space", "unsupported"
 *   clipUrl is null when nothing has been recorded for that label yet,
 *   or when the character isn't signable at all (type "space"/"unsupported").
 */
function buildSignSequence(text, availableClips) {
  const sequence = [];

  for (const char of text.toUpperCase()) {
    if (char === " ") {
      sequence.push({ label: null, displayChar: " ", clipUrl: null, type: "space" });
      continue;
    }

    let label = null;
    let type = "unsupported";

    if (char >= "A" && char <= "Z") {
      label = char;
      type = "letter";
    } else if (char >= "0" && char <= "9") {
      label = `NUMBER_${char}`;
      type = "number";
    }

    if (label === null) {
      sequence.push({ label: null, displayChar: char, clipUrl: null, type: "unsupported" });
      continue;
    }

    const clipUrl = availableClips[label] || null;
    sequence.push({ label, displayChar: char, clipUrl, type });
  }

  return sequence;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { buildSignSequence };
}
