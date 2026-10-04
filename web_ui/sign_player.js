/**
 * sign_player.js
 * --------------
 * Drives the skeleton animation through the sequence produced by
 * buildSignSequence() (sign_sequence.js) — the "type/say a word, watch it
 * get signed" feature. Plays an animated hand skeleton built from REAL
 * recorded motion (extract_sign_animations.py), not a video clip and not
 * a fully generated character — see sign_animation_player.js for what
 * that tradeoff actually means.
 */

let availableAnimations = {};
let currentPlaybackId = 0; // lets a new playback request cancel an in-progress one

const signTextInput = document.getElementById("signTextInput");
const signItButton = document.getElementById("signItButton");
const micButton = document.getElementById("micButton");
const signCaption = document.getElementById("signCaption");

// Load once at startup, and again each time playback starts, in case new
// animations were added to the server since the page loaded.
fetchAvailableAnimations();

signItButton.addEventListener("click", () => playText(signTextInput.value.trim()));
signTextInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") playText(signTextInput.value.trim());
});

setupMicButton();

async function fetchAvailableAnimations() {
  try {
    const res = await fetch("/available_animations");
    availableAnimations = await res.json();
  } catch (err) {
    console.error("Could not load available animations:", err);
  }
}

async function playText(text) {
  if (!text) return;

  await fetchAvailableAnimations(); // pick up anything newly added

  const myPlaybackId = ++currentPlaybackId; // invalidates any previous in-flight playback
  const sequence = buildSignSequence(text, availableAnimations);

  for (const step of sequence) {
    if (myPlaybackId !== currentPlaybackId) return; // a newer request superseded this one
    await playStep(step);
  }

  if (myPlaybackId === currentPlaybackId) {
    signCaption.innerHTML = "";
    clearSkeletonCanvas();
  }
}

function playStep(step) {
  if (step.type === "space") {
    signCaption.innerHTML = "";
    clearSkeletonCanvas();
    return wait(300);
  }

  if (step.type === "unsupported") {
    signCaption.innerHTML = `<span class="unsupported">"${escapeHtml(step.displayChar)}" isn't a sign - skipping</span>`;
    clearSkeletonCanvas();
    return wait(500);
  }

  if (!step.clipUrl) {
    signCaption.innerHTML = `<span class="unsupported">${escapeHtml(step.displayChar)} - not recorded yet</span>`;
    clearSkeletonCanvas();
    return wait(500);
  }

  signCaption.textContent = step.displayChar;
  return playAnimationFromUrl(step.clipUrl);
}

async function playAnimationFromUrl(url) {
  try {
    const res = await fetch(url);
    const animationData = await res.json();
    await playSkeletonAnimation(animationData);
  } catch (err) {
    console.error("Could not play animation:", url, err);
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Voice input using the browser's built-in speech recognition — no server
 * involved, no extra dependency. IMPORTANT browser support caveat: this
 * works in Chrome and Edge; Firefox does not support the Web Speech
 * Recognition API at all as of now, and Safari's support has historically
 * been inconsistent. We detect and degrade gracefully rather than pretend
 * it'll work everywhere.
 *
 * IMPORTANT design note on why this listens for a FIXED window, rather
 * than letting the browser decide when you've finished speaking:
 * With the browser's own end-of-speech detection, very short utterances
 * (like a single letter) often don't carry enough signal for it to
 * confidently finalise a result at all — which is exactly why saying a
 * letter once did nothing, but saying it twice (more audio duration)
 * worked. Instead, we take control of the timing ourselves: listen for a
 * fixed ~2.5 seconds, capturing even partial/interim results as they
 * arrive, and use whatever was heard by the time that window closes.
 */
function setupMicButton() {
  const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognitionClass) {
    micButton.disabled = true;
    micButton.setAttribute("aria-label", "Voice input isn't supported in this browser (try Chrome or Edge)");
    micButton.textContent = "\u{1F3A4}";
    return;
  }

  const LISTEN_WINDOW_MS = 2500;

  const recognition = new SpeechRecognitionClass();
  recognition.lang = "en-GB";
  recognition.continuous = true;      // don't let the browser auto-stop on short pauses
  recognition.interimResults = true;  // capture partial results too, not just "final" ones
  recognition.maxAlternatives = 1;

  let isListening = false;
  let latestTranscript = "";
  let stopTimer = null;

  micButton.addEventListener("click", () => {
    if (isListening) {
      finishListening();
      return;
    }
    latestTranscript = "";
    recognition.start();
  });

  recognition.addEventListener("start", () => {
    isListening = true;
    micButton.classList.add("listening");
    micButton.textContent = "\u{1F534}";
    micButton.setAttribute("aria-label", "Listening...");
    // We control when listening ends, not the browser's own silence detection.
    stopTimer = setTimeout(finishListening, LISTEN_WINDOW_MS);
  });

  recognition.addEventListener("result", (event) => {
    // Take the most recent result available (interim or final) — this is
    // what lets a short "A" register immediately instead of needing to be
    // repeated to trigger the browser's own finalisation.
    const lastResult = event.results[event.results.length - 1];
    latestTranscript = lastResult[0].transcript;
    signTextInput.value = latestTranscript; // live feedback while listening
  });

  recognition.addEventListener("end", () => {
    isListening = false;
    micButton.classList.remove("listening");
    micButton.textContent = "\u{1F3A4}";
    micButton.setAttribute("aria-label", "Speak a word");
    clearTimeout(stopTimer);

    const heard = latestTranscript.trim();
    if (heard) playText(heard);
  });

  recognition.addEventListener("error", (event) => {
    console.error("Speech recognition error:", event.error);
    if (event.error === "not-allowed") {
      alert("Microphone access was blocked. Check your browser's site permissions.");
    }
  });

  function finishListening() {
    clearTimeout(stopTimer);
    if (isListening) recognition.stop(); // triggers the 'end' handler above, which plays the word
  }
}
