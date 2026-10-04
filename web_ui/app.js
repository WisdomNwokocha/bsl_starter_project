/**
 * app.js
 * ------
 * Wires together: camera capture -> periodic prediction requests to the
 * Python backend -> the WordBuilder state machine -> UI updates and
 * speech, using the browser's own built-in speech synthesis (works on
 * any OS, unlike the desktop version's macOS-only `say` command).
 */

const POLL_INTERVAL_MS = 150; // ~6-7 predictions per second

// Recalibrated for this polling rate — see word_builder.js's header comment.
const wordBuilder = new WordBuilder({
  stabilityPolls: 4,      // ~0.5s-0.6s held steady at this poll rate
  confidenceThreshold: 0.6,
  wordPausePolls: 10,      // ~1.5s paused
});

const video = document.getElementById("video");
const canvas = document.getElementById("captureCanvas");
const ctx = canvas.getContext("2d");

const wordDisplay = document.getElementById("wordDisplay");
const statusText = document.getElementById("statusText");
const progressDots = document.getElementById("progressDots");
const confirmation = document.getElementById("confirmation");
const cameraDot = document.getElementById("cameraDot");
const startOverlay = document.getElementById("startOverlay");
const startButton = document.getElementById("startButton");
const clearButton = document.getElementById("clearButton");

let pollTimer = null;

startButton.addEventListener("click", startCamera);
clearButton.addEventListener("click", () => {
  wordBuilder.clear();
  renderWord();
});

// Exposed so the mode toggle (mode_toggle.js) can pause detection when
// you switch to the type/speak-to-sign mode, rather than wastefully
// polling the server in the background while you're not using it.
function pauseDetection() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function resumeDetection() {
  if (!pollTimer && video.srcObject) {
    pollTimer = setInterval(captureAndPredict, POLL_INTERVAL_MS);
  }
}

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
    startOverlay.classList.add("hidden");
    cameraDot.classList.remove("off");
    pollTimer = setInterval(captureAndPredict, POLL_INTERVAL_MS);
  } catch (err) {
    alert("Could not access camera: " + err.message);
  }
}

function captureAndPredict() {
  if (video.videoWidth === 0) return; // camera not ready yet

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  // Draw the RAW (unmirrored) frame for detection — only the on-screen
  // <video> element is visually mirrored via CSS, matching the same
  // "detect on raw, display mirrored" approach as the desktop version.
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.7);

  fetch("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: dataUrl }),
  })
    .then((res) => res.json())
    .then(handlePrediction)
    .catch((err) => {
      statusText.textContent = "Connection error — is the server running?";
      console.error(err);
    });
}

function handlePrediction(result) {
  const { letter, confidence } = result;
  const { wordCompleted } = wordBuilder.update(letter, confidence || 0);

  if (wordCompleted) {
    const finishedWord = wordBuilder.word;
    speak(finishedWord);
    showConfirmation(finishedWord);
    wordBuilder.clear();
  }

  renderWord();
  renderStatus(letter, confidence);
}

function renderWord() {
  const hasWord = wordBuilder.word.length > 0;
  wordDisplay.textContent = hasWord ? wordBuilder.word : "(spell a word...)";
  wordDisplay.classList.toggle("empty", !hasWord);
}

function renderStatus(letter, confidence) {
  if (letter) {
    const pct = Math.round((confidence || 0) * 100);
    statusText.innerHTML = `Holding: <span class="letter">${letter}</span> (${pct}%)`;
  } else {
    statusText.textContent = "No hand detected";
  }

  const total = wordBuilder.stabilityPolls;
  const filled = Math.min(wordBuilder.candidateCount, total);
  progressDots.innerHTML = "";
  for (let i = 0; i < total; i++) {
    const dot = document.createElement("div");
    dot.className = "dot" + (i < filled ? " filled" : "");
    progressDots.appendChild(dot);
  }
}

function showConfirmation(word) {
  wordDisplay.classList.add("spoken");
  confirmation.textContent = `Said: ${word}`;
  confirmation.classList.add("visible");

  setTimeout(() => {
    wordDisplay.classList.remove("spoken");
    confirmation.classList.remove("visible");
  }, 1800);
}

function speak(text) {
  if (!text || !window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(utterance);
}
