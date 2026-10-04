"""
word_builder.py
----------------
Turns a stream of per-frame letter predictions into an actual spelled word.

Why this is needed:
Your existing model predicts a letter fresh on every single camera frame,
with no memory of what came before. If you sign H then I, it just flashes
"H" then "I" — it doesn't know those are two separate letters you meant to
combine into "HI". This class adds that missing layer, using nothing but
the predictions your existing model already produces frame by frame.

How it decides a letter was "really" signed (not just a lucky guess or a
transition frame):
- The SAME letter must be predicted with high confidence for several
  consecutive frames in a row (a real held sign is stable; a hand moving
  between shapes flickers between guesses).
- Once a letter is committed, it won't be committed again until either a
  DIFFERENT letter is held, or there's a gap (hand removed / low
  confidence) — this stops holding one letter still from spelling it out
  five times in a row.

How it decides a WORD is finished (for automatic speech, no button needed):
- After at least one letter has been spelled, a SUSTAINED pause (hand
  removed or unclear for a longer stretch than the normal short gaps
  between letters) is treated as "the word is done" — mirroring how a
  pause naturally happens in real signed conversation between words.
"""


class WordBuilder:
    def __init__(self, stability_frames=15, confidence_threshold=0.6, word_pause_frames=45):
        """
        Args:
            stability_frames: how many consecutive confident frames the
                SAME letter must appear in before it counts as "signed".
                Higher = fewer accidental commits, but slower to respond.
                15 frames at ~30fps webcam is roughly half a second held still.
            confidence_threshold: minimum model confidence to consider a
                prediction at all. Below this, treated the same as "no hand".
            word_pause_frames: how many consecutive "no confident hand"
                frames in a row count as "the word is finished, not just a
                normal gap between letters". Must be noticeably longer than
                the normal brief gap a signer takes between individual
                letters of the same word. 45 frames at ~30fps is roughly
                1.5 seconds of stillness.
        """
        self.stability_frames = stability_frames
        self.confidence_threshold = confidence_threshold
        self.word_pause_frames = word_pause_frames

        self.candidate_letter = None   # letter currently being "watched"
        self.candidate_count = 0       # how many frames in a row it's held
        self.last_committed = None     # last letter actually added to the word
        self.word = ""

        self.gap_frame_count = 0                  # consecutive "no hand" frames right now
        self._word_completion_already_signaled = False  # avoid re-firing every frame during one long pause

    def update(self, predicted_letter, confidence):
        """
        Call this once per camera frame with that frame's prediction.

        Returns:
            (letter_committed, word_completed) tuple:
            - letter_committed: the letter just added to the word this call,
              or None if nothing was committed this call.
            - word_completed: True exactly once, the moment a sustained
              pause confirms the current word is finished (only if the
              word isn't empty). The caller should read/speak
              self.word at that point, THEN call clear().
        """
        no_confident_hand = predicted_letter is None or confidence < self.confidence_threshold

        if no_confident_hand:
            # Treat a gap (hand removed, or an unclear/low-confidence frame)
            # as a reset point — this is what allows the SAME letter to be
            # signed twice in a row later (e.g. spelling "HELLO" has two L's).
            self.candidate_letter = None
            self.candidate_count = 0
            self.last_committed = None

            self.gap_frame_count += 1

            word_completed = False
            if (self.word and
                    self.gap_frame_count == self.word_pause_frames and
                    not self._word_completion_already_signaled):
                word_completed = True
                self._word_completion_already_signaled = True

            return (None, word_completed)

        # A confident hand IS present this frame — any pause has ended.
        self.gap_frame_count = 0
        self._word_completion_already_signaled = False

        if predicted_letter == self.candidate_letter:
            self.candidate_count += 1
        else:
            # prediction changed — start counting stability for the new letter
            self.candidate_letter = predicted_letter
            self.candidate_count = 1

        just_reached_stability = self.candidate_count == self.stability_frames
        different_from_last_commit = predicted_letter != self.last_committed

        if just_reached_stability and different_from_last_commit:
            self.word += predicted_letter
            self.last_committed = predicted_letter
            return (predicted_letter, False)

        return (None, False)

    def clear(self):
        """Reset everything — start spelling a new word from scratch."""
        self.word = ""
        self.candidate_letter = None
        self.candidate_count = 0
        self.last_committed = None
        self.gap_frame_count = 0
        self._word_completion_already_signaled = False
