/**
 * mode_toggle.js
 * --------------
 * Switches between the two features on this page: camera-based sign
 * detection, and typing/speaking a word to see it signed back. Only one
 * is shown (and actively running) at a time — switching away from camera
 * detection pauses its background polling rather than leaving it running
 * unseen.
 */

const detectModeBtn = document.getElementById("detectModeBtn");
const signModeBtn = document.getElementById("signModeBtn");
const detectModeSection = document.getElementById("detectModeSection"); // camera preview box
const detectModeContent = document.getElementById("detectModeContent"); // word display etc.
const signModeSection = document.getElementById("signModeSection");

detectModeBtn.addEventListener("click", () => switchMode("detect"));
signModeBtn.addEventListener("click", () => switchMode("sign"));

function switchMode(mode) {
  const showDetect = mode === "detect";

  detectModeBtn.classList.toggle("active", showDetect);
  signModeBtn.classList.toggle("active", !showDetect);

  detectModeSection.classList.toggle("hidden", !showDetect);
  detectModeContent.classList.toggle("hidden", !showDetect);
  signModeSection.classList.toggle("hidden", showDetect);

  // Only poll the camera/prediction endpoint while that mode is actually visible.
  if (showDetect) {
    if (typeof resumeDetection === "function") resumeDetection();
  } else {
    if (typeof pauseDetection === "function") pauseDetection();
  }
}
