/**
 * word_builder.js
 * ----------------
 * JavaScript port of the project's word_builder.py — same tested logic,
 * same behavior, adapted for the browser's polling rate instead of a
 * webcam loop's native frame rate. See word_builder.py for the full
 * reasoning behind why stability + pause detection work this way.
 *
 * IMPORTANT: stability/pause thresholds here are expressed in POLLS, not
 * "frames" the way the Python version counts native ~30fps webcam frames.
 * The web UI only polls the server every POLL_INTERVAL_MS (see app.js),
 * so these numbers are recalibrated to roughly the same real-world timing
 * (~0.5s to commit a letter, ~1.5s pause to finish a word) at that slower
 * polling rate.
 */

class WordBuilder {
  constructor({ stabilityPolls = 4, confidenceThreshold = 0.6, wordPausePolls = 10 } = {}) {
    this.stabilityPolls = stabilityPolls;
    this.confidenceThreshold = confidenceThreshold;
    this.wordPausePolls = wordPausePolls;

    this.candidateLetter = null;
    this.candidateCount = 0;
    this.lastCommitted = null;
    this.word = "";

    this.gapPollCount = 0;
    this._wordCompletionAlreadySignaled = false;
  }

  /**
   * Call once per poll with that poll's prediction.
   * Returns { letterCommitted, wordCompleted } — mirrors the Python
   * (letter_committed, word_completed) tuple exactly.
   */
  update(predictedLetter, confidence) {
    const noConfidentHand = predictedLetter === null || predictedLetter === undefined || confidence < this.confidenceThreshold;

    if (noConfidentHand) {
      this.candidateLetter = null;
      this.candidateCount = 0;
      this.lastCommitted = null;

      this.gapPollCount += 1;

      let wordCompleted = false;
      if (this.word && this.gapPollCount === this.wordPausePolls && !this._wordCompletionAlreadySignaled) {
        wordCompleted = true;
        this._wordCompletionAlreadySignaled = true;
      }

      return { letterCommitted: null, wordCompleted };
    }

    this.gapPollCount = 0;
    this._wordCompletionAlreadySignaled = false;

    if (predictedLetter === this.candidateLetter) {
      this.candidateCount += 1;
    } else {
      this.candidateLetter = predictedLetter;
      this.candidateCount = 1;
    }

    const justReachedStability = this.candidateCount === this.stabilityPolls;
    const differentFromLastCommit = predictedLetter !== this.lastCommitted;

    if (justReachedStability && differentFromLastCommit) {
      this.word += predictedLetter;
      this.lastCommitted = predictedLetter;
      return { letterCommitted: predictedLetter, wordCompleted: false };
    }

    return { letterCommitted: null, wordCompleted: false };
  }

  clear() {
    this.word = "";
    this.candidateLetter = null;
    this.candidateCount = 0;
    this.lastCommitted = null;
    this.gapPollCount = 0;
    this._wordCompletionAlreadySignaled = false;
  }
}

// Support both browser (<script> global) and Node (for testing) usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { WordBuilder };
}
